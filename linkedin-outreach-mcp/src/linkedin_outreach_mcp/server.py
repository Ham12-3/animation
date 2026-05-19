#!/usr/bin/env python3
"""LinkedIn outreach MCP server.

Exposes LinkedIn search + messaging + connection-request tools to an
MCP-capable AI app (Claude Desktop, etc). The AI does the talking and the
deciding; this server only performs discrete browser actions in YOUR own
already-open, already-logged-in Chrome.

It never sees or stores your password. You launch Chrome with remote
debugging and log into LinkedIn by hand; this server attaches over the
Chrome DevTools Protocol and drives that visible window.

Design principles baked in:
  * Nothing is sent unless a tool is called a second time with confirm=True.
    The first call returns a PREVIEW so the AI can show you and ask.
  * When the page/state is ambiguous, tools return status "needs_user_input"
    instead of guessing, so the AI asks you a question.
  * Conservative daily message / weekly invite caps + an append-only log.

Automated LinkedIn activity violates LinkedIn's User Agreement and can get
the account restricted or banned. Keep volume low and messages genuine.
"""

from __future__ import annotations

import asyncio
import csv
import datetime as dt
import os
import random
import re
import urllib.parse
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import Error as PWError
from playwright.async_api import TimeoutError as PWTimeout

CDP_URL = os.environ.get("LINKEDIN_MCP_CDP_URL", "http://127.0.0.1:9222")
DAILY_MSG_CAP = int(os.environ.get("LINKEDIN_MCP_DAILY_MSG_CAP", "25"))
WEEKLY_INVITE_CAP = int(os.environ.get("LINKEDIN_MCP_WEEKLY_INVITE_CAP", "80"))
MIN_DELAY = float(os.environ.get("LINKEDIN_MCP_MIN_DELAY", "6"))
MAX_DELAY = float(os.environ.get("LINKEDIN_MCP_MAX_DELAY", "16"))
NOTE_LIMIT = 300  # LinkedIn invitation note hard limit
LOG_PATH = Path(
    os.environ.get("LINKEDIN_MCP_LOG", str(Path.home() / ".linkedin-mcp" / "activity_log.csv"))
)

INSTRUCTIONS = """\
This server drives the user's own logged-in Chrome to do LinkedIn outreach.

Workflow you should follow:
1. Call linkedin_status first. If it is not ready, tell the user exactly what
   to do (start Chrome with remote debugging, log into LinkedIn) and stop.
2. Use search_people with the criteria the user gave you. Show the user the
   results and let THEM confirm who to contact. Do not invent people.
3. For each chosen person call reach_out WITHOUT confirm (preview). It tells
   you whether it will send a direct message (already connected) or a
   connection request with a note (not connected). Show the user the exact
   text and the path, and ask for explicit approval.
4. Only after the user approves, call reach_out again with confirm=true.
5. The connection 'note' must be a SHORT version of the direct 'message'
   (LinkedIn caps notes at 300 characters).

Hard rule: if any tool returns status "needs_user_input", "ambiguous", or
"error", do NOT guess or retry blindly. Ask the user a clear question and
wait. Never fabricate a profile, name, or send result.
"""

mcp = FastMCP("linkedin-outreach", instructions=INSTRUCTIONS)

_state: dict[str, Any] = {"pw": None, "browser": None}
_lock = asyncio.Lock()


# --------------------------------------------------------------------------- #
# Browser plumbing
# --------------------------------------------------------------------------- #
async def _get_page() -> Page:
    """Attach to the user's running Chrome (once) and return a usable page."""
    async with _lock:
        browser: Browser | None = _state.get("browser")
        if browser is not None and browser.is_connected():
            ctx = browser.contexts[0]
            for pg in ctx.pages:
                if not pg.is_closed():
                    return pg
            return await ctx.new_page()

        pw = await async_playwright().start()
        try:
            browser = await pw.chromium.connect_over_cdp(CDP_URL)
        except PWError as exc:
            await pw.stop()
            raise RuntimeError(
                f"Could not attach to Chrome at {CDP_URL}. Start Chrome with "
                f"--remote-debugging-port and log into LinkedIn first. ({exc})"
            ) from exc
        if not browser.contexts:
            await pw.stop()
            raise RuntimeError("Attached to Chrome but it has no open window/tab.")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        _state.update(pw=pw, browser=browser)
        return page


async def _pause() -> None:
    await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def _clean_url(url: str) -> str:
    url = url.split("?")[0].rstrip("/")
    return url


# --------------------------------------------------------------------------- #
# Audit log + rate caps
# --------------------------------------------------------------------------- #
def _log(action: str, profile_url: str, status: str, detail: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    new = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["timestamp", "action", "profile_url", "status", "detail"])
        w.writerow(
            [dt.datetime.now().isoformat(timespec="seconds"), action, profile_url, status, detail]
        )


def _count(action: str, since: dt.datetime) -> int:
    if not LOG_PATH.exists():
        return 0
    n = 0
    with LOG_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("action") != action or row.get("status") != "sent":
                continue
            try:
                ts = dt.datetime.fromisoformat(row.get("timestamp", ""))
            except ValueError:
                continue
            if ts >= since:
                n += 1
    return n


def _caps_snapshot() -> dict[str, int]:
    now = dt.datetime.now()
    msgs = _count("message", now.replace(hour=0, minute=0, second=0, microsecond=0))
    invites = _count("connect", now - dt.timedelta(days=7))
    return {
        "messages_sent_today": msgs,
        "messages_remaining_today": max(0, DAILY_MSG_CAP - msgs),
        "invites_sent_this_week": invites,
        "invites_remaining_this_week": max(0, WEEKLY_INVITE_CAP - invites),
    }


# --------------------------------------------------------------------------- #
# LinkedIn DOM helpers (best-effort; LinkedIn changes its HTML often)
# --------------------------------------------------------------------------- #
async def _first_visible(page: Page, selectors: list[str], timeout: int = 4000):
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except (PWTimeout, PWError):
            continue
    return None


async def _profile_state(page: Page, profile_url: str) -> dict[str, Any]:
    await page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(random.uniform(2.5, 4.5))

    title = await page.title()
    if "Sign in" in title or "Join LinkedIn" in title or "/authwall" in page.url:
        return {"status": "needs_user_input",
                "reason": "LinkedIn is not logged in (hit a sign-in / auth wall).",
                "page_title": title}

    name = None
    h1 = page.locator("h1").first
    try:
        await h1.wait_for(state="visible", timeout=5000)
        name = (await h1.inner_text()).strip()
    except (PWTimeout, PWError):
        pass

    main = page.locator("main")
    msg_btn = await _first_visible(
        page,
        ["main button[aria-label^='Message']", "main a[aria-label^='Message']",
         "main button:has-text('Message')"],
        timeout=2500,
    )
    pending = await _first_visible(
        page, ["main button:has-text('Pending')", "main button[aria-label*='Pending']"],
        timeout=1500,
    )
    connect = await _first_visible(
        page,
        ["main button[aria-label^='Invite']", "main button:has-text('Connect')"],
        timeout=1500,
    )
    connect_in_more = False
    if connect is None and pending is None:
        # On 2nd/3rd-degree profiles "Connect" is often hidden behind "More".
        more = await _first_visible(
            page, ["main button[aria-label='More actions']",
                    "main button:has-text('More')"], timeout=1500)
        if more is not None:
            try:
                await more.click()
                await asyncio.sleep(0.8)
                item = page.get_by_role("button", name=re.compile(r"^Connect$", re.I)).first
                await item.wait_for(state="visible", timeout=2000)
                connect_in_more = True
                await page.keyboard.press("Escape")
            except (PWTimeout, PWError):
                try:
                    await page.keyboard.press("Escape")
                except PWError:
                    pass

    degree = None
    try:
        body = await main.inner_text()
        m = re.search(r"\b(1st|2nd|3rd)\b", body)
        if m:
            degree = m.group(1)
    except PWError:
        pass

    can_message = msg_btn is not None
    can_connect = (connect is not None) or connect_in_more
    is_pending = pending is not None

    if not (can_message or can_connect or is_pending):
        return {"status": "ambiguous",
                "reason": "Could not find a Message, Connect, or Pending control. "
                          "LinkedIn layout may have changed or this is a restricted profile.",
                "name": name, "page_title": title, "url": page.url}

    return {
        "status": "ok",
        "name": name,
        "degree": degree,
        "can_message": can_message,
        "can_connect": can_connect,
        "pending": is_pending,
        "connect_behind_more": connect_in_more,
        "url": _clean_url(page.url),
    }


async def _send_dm(page: Page, message: str) -> dict[str, Any]:
    btn = await _first_visible(
        page,
        ["main button[aria-label^='Message']", "main a[aria-label^='Message']",
         "main button:has-text('Message')"],
    )
    if btn is None:
        return {"status": "error", "detail": "Message button disappeared."}
    await btn.click()
    editor = await _first_visible(
        page,
        ["div.msg-form__contenteditable[contenteditable='true']",
         "div[role='textbox'][contenteditable='true']",
         "div[aria-label*='message'][contenteditable='true']"],
    )
    if editor is None:
        return {"status": "error", "detail": "Message compose box did not open."}
    await editor.click()
    await asyncio.sleep(random.uniform(0.4, 0.9))
    for line in message.split("\n"):
        await editor.type(line, delay=random.uniform(20, 55))
        await editor.press("Shift+Enter")
    await asyncio.sleep(random.uniform(0.5, 1.1))
    send = await _first_visible(
        page,
        ["button.msg-form__send-button", "button:has-text('Send')"],
    )
    if send is None or not await send.is_enabled():
        return {"status": "error", "detail": "Send button not found or disabled."}
    await send.click()
    return {"status": "sent"}


async def _send_invite(page: Page, note: str) -> dict[str, Any]:
    connect = await _first_visible(
        page, ["main button[aria-label^='Invite']", "main button:has-text('Connect')"],
        timeout=2500,
    )
    if connect is None:
        more = await _first_visible(
            page, ["main button[aria-label='More actions']", "main button:has-text('More')"])
        if more is None:
            return {"status": "error", "detail": "No Connect or More button found."}
        await more.click()
        await asyncio.sleep(0.8)
        connect = page.get_by_role("button", name=re.compile(r"^Connect$", re.I)).first
        try:
            await connect.wait_for(state="visible", timeout=2500)
        except (PWTimeout, PWError):
            return {"status": "error", "detail": "Connect not found in the More menu."}
    await connect.click()
    await asyncio.sleep(random.uniform(1.0, 2.0))

    add_note = await _first_visible(
        page, ["button[aria-label='Add a note']", "button:has-text('Add a note')"],
        timeout=4000,
    )
    if add_note is None:
        # LinkedIn may show a limit dialog instead (free-account note limit).
        body = ""
        try:
            body = await page.locator("div[role='dialog']").first.inner_text()
        except PWError:
            pass
        return {"status": "needs_user_input",
                "detail": "Could not open the note field. LinkedIn may be limiting "
                          "personalized invites on this account.",
                "linkedin_dialog_text": body[:500]}
    await add_note.click()
    textarea = await _first_visible(
        page, ["textarea[name='message']", "#custom-message",
                "div[role='dialog'] textarea"],
    )
    if textarea is None:
        return {"status": "error", "detail": "Note text box did not appear."}
    await textarea.click()
    await textarea.fill(note[:NOTE_LIMIT])
    await asyncio.sleep(random.uniform(0.5, 1.0))
    send = await _first_visible(
        page,
        ["button[aria-label='Send invitation']", "button[aria-label='Send now']",
         "div[role='dialog'] button:has-text('Send')"],
    )
    if send is None or not await send.is_enabled():
        return {"status": "error", "detail": "Send-invitation button not found/disabled."}
    await send.click()
    return {"status": "sent"}


# --------------------------------------------------------------------------- #
# MCP tools
# --------------------------------------------------------------------------- #
@mcp.tool()
async def linkedin_status() -> dict[str, Any]:
    """Check that the server can drive your Chrome and that LinkedIn is logged in.

    Always call this first. If it is not ready, tell the user the exact steps
    (start Chrome with --remote-debugging-port, open linkedin.com, log in)
    and stop until they confirm.
    """
    try:
        page = await _get_page()
    except RuntimeError as exc:
        return {"status": "not_ready", "reason": str(exc)}
    try:
        await page.goto("https://www.linkedin.com/feed/",
                         wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2.0)
    except (PWTimeout, PWError) as exc:
        return {"status": "not_ready", "reason": f"Could not load LinkedIn feed: {exc}"}
    title = await page.title()
    logged_in = "/feed" in page.url and "Sign in" not in title and "authwall" not in page.url
    return {
        "status": "ready" if logged_in else "not_logged_in",
        "logged_in": logged_in,
        "current_url": page.url,
        "caps": _caps_snapshot(),
        "note": None if logged_in else
        "Open the debugged Chrome window and log into LinkedIn by hand, then retry.",
    }


@mcp.tool()
async def search_people(query: str, max_results: int = 10) -> dict[str, Any]:
    """Search LinkedIn People for the user's criteria and return matches.

    `query` is free text (e.g. "fintech product managers in London").
    Returns a list of {name, headline, profile_url, degree}. This parsing is
    best-effort; if it returns status "needs_user_input" the page may be a
    login/captcha wall — ask the user, do not retry blindly. Always show the
    user the results and let them pick who to contact; never invent people.
    """
    max_results = max(1, min(max_results, 25))
    try:
        page = await _get_page()
    except RuntimeError as exc:
        return {"status": "not_ready", "reason": str(exc)}

    url = ("https://www.linkedin.com/search/results/people/?keywords="
           + urllib.parse.quote(query))
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except (PWTimeout, PWError) as exc:
        return {"status": "error", "reason": f"Search navigation failed: {exc}"}
    await asyncio.sleep(random.uniform(3.0, 5.0))

    title = await page.title()
    if "Sign in" in title or "authwall" in page.url:
        return {"status": "needs_user_input",
                "reason": "Hit a LinkedIn sign-in wall. The user must log in in the Chrome window.",
                "page_title": title}

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    items = page.locator("li").filter(has=page.locator("a[href*='/in/']"))
    count = min(await items.count(), 60)
    for i in range(count):
        li = items.nth(i)
        try:
            link = li.locator("a[href*='/in/']").first
            href = _clean_url(await link.get_attribute("href") or "")
            if not href or href in seen:
                continue
            raw = (await li.inner_text()).strip()
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if not lines:
                continue
            name = next((ln for ln in lines if ln.lower() != "status is offline"), lines[0])
            dm = re.search(r"\b(1st|2nd|3rd)\b", raw)
            headline = ""
            for ln in lines[1:]:
                if ln.lower() not in ("1st", "2nd", "3rd") and "connection" not in ln.lower():
                    headline = ln
                    break
            seen.add(href)
            results.append({
                "name": name,
                "headline": headline,
                "degree": dm.group(1) if dm else None,
                "profile_url": href,
            })
            if len(results) >= max_results:
                break
        except (PWTimeout, PWError):
            continue

    if not results:
        return {"status": "needs_user_input",
                "reason": "No results could be parsed. LinkedIn layout may have changed, "
                          "or there is a captcha / commercial-use limit. Ask the user to "
                          "look at the Chrome window.",
                "page_title": title, "url": page.url}
    return {"status": "ok", "query": query, "count": len(results), "results": results}


@mcp.tool()
async def get_profile(profile_url: str) -> dict[str, Any]:
    """Open a LinkedIn profile and report how the user can contact this person.

    Returns name, connection degree, and can_message / can_connect / pending.
    If status is "ambiguous" or "needs_user_input", ask the user instead of
    guessing.
    """
    try:
        page = await _get_page()
    except RuntimeError as exc:
        return {"status": "not_ready", "reason": str(exc)}
    try:
        return await _profile_state(page, profile_url)
    except (PWTimeout, PWError) as exc:
        return {"status": "error", "reason": f"Could not read profile: {exc}"}


@mcp.tool()
async def reach_out(
    profile_url: str,
    message: str,
    note: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Contact one person the right way, with a mandatory preview step.

    Decides automatically:
      * If the user is ALREADY CONNECTED -> sends `message` as a direct DM.
      * If NOT connected -> sends a connection request with `note` attached.
        `note` MUST be a short version of `message` (max 300 chars).

    Call it FIRST with confirm=false: it performs NO action and returns a
    preview ({path, text_to_send, caps}). Show the user that preview and get
    explicit approval. Only then call again with confirm=true.

    If it returns status "needs_user_input" / "ambiguous" / "cap_reached" /
    "already_pending" / "error", do NOT proceed — explain to the user and ask.
    """
    if len(note) > NOTE_LIMIT:
        return {"status": "error",
                "reason": f"note is {len(note)} chars; LinkedIn allows {NOTE_LIMIT}. "
                          "Shorten the note and try again."}
    try:
        page = await _get_page()
    except RuntimeError as exc:
        return {"status": "not_ready", "reason": str(exc)}

    try:
        state = await _profile_state(page, profile_url)
    except (PWTimeout, PWError) as exc:
        return {"status": "error", "reason": f"Could not read profile: {exc}"}
    if state.get("status") != "ok":
        return state  # needs_user_input / ambiguous -> AI must ask the user

    if state["pending"]:
        return {"status": "already_pending", "name": state.get("name"),
                "detail": "A connection request to this person is already pending; nothing to do."}

    caps = _caps_snapshot()
    if state["can_message"]:
        path, text, action = "direct_message", message, "message"
        if caps["messages_remaining_today"] <= 0:
            return {"status": "cap_reached", "path": path, "caps": caps,
                    "detail": f"Daily message cap ({DAILY_MSG_CAP}) reached. Resets tomorrow."}
    elif state["can_connect"]:
        path, text, action = "connection_request_with_note", note, "connect"
        if caps["invites_remaining_this_week"] <= 0:
            return {"status": "cap_reached", "path": path, "caps": caps,
                    "detail": f"Weekly invite cap ({WEEKLY_INVITE_CAP}) reached."}
    else:
        return {"status": "ambiguous", "name": state.get("name"),
                "detail": "Cannot determine whether to message or connect. Ask the user."}

    if not confirm:
        return {
            "status": "preview",
            "name": state.get("name"),
            "degree": state.get("degree"),
            "path": path,
            "text_to_send": text,
            "caps": caps,
            "next_step": "Show this to the user. If they approve, call reach_out "
                         "again with the same arguments and confirm=true.",
        }

    if path == "direct_message":
        result = await _send_dm(page, message)
    else:
        result = await _send_invite(page, note)

    sent = result.get("status") == "sent"
    _log(action, _clean_url(profile_url), "sent" if sent else result.get("status", "error"),
         path if sent else result.get("detail", ""))
    if sent:
        await _pause()
        return {"status": "sent", "name": state.get("name"), "path": path,
                "text_sent": text, "caps": _caps_snapshot()}
    return {"status": result.get("status", "error"), "path": path,
            "detail": result.get("detail") or result.get("linkedin_dialog_text"),
            "name": state.get("name")}


@mcp.tool()
async def activity_log(limit: int = 20) -> dict[str, Any]:
    """Return the most recent actions this server took (audit trail + caps)."""
    rows: list[dict[str, str]] = []
    if LOG_PATH.exists():
        with LOG_PATH.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    return {"status": "ok", "caps": _caps_snapshot(),
            "recent": rows[-max(1, min(limit, 200)):]}


def main() -> None:
    """Console entry point: run the server over stdio (for MCP clients)."""
    mcp.run()


if __name__ == "__main__":
    main()
