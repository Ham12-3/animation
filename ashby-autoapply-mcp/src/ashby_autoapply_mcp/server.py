#!/usr/bin/env python3
"""Ashby Auto-Apply MCP server.

Discovers jobs from Ashby company job boards (via Ashby's public posting
API), then drives YOUR own already-open, already-logged-in Chrome to fill
and submit the application — using a profile.json you control.

It never sees or stores any password. You launch Chrome with remote
debugging; this server attaches over the Chrome DevTools Protocol and drives
that visible window so you can watch.

What it does NOT do:
  * It does not invent answers. Any required question it cannot confidently
    fill from your profile (free-text, EEO/demographic, work-authorization
    nuance, screening questions) is returned as "needs_user_input" so the AI
    asks you. It only auto-submits when every required field is filled with
    no unknowns left.
  * Ashby has no global cross-company search. You provide the company board
    slugs (companies.json or a tool argument); discovery is limited to those.

Mass auto-applying with a weak/generic profile produces low-quality
applications that waste your reputation and recruiters' time. Keep the
profile accurate, keep the daily cap low, review the log.
"""

from __future__ import annotations

import asyncio
import csv
import datetime as dt
import json
import os
import random
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import Error as PWError
from playwright.async_api import TimeoutError as PWTimeout

CDP_URL = os.environ.get("ASHBY_MCP_CDP_URL", "http://127.0.0.1:9222")
DAILY_CAP = int(os.environ.get("ASHBY_MCP_DAILY_CAP", "15"))
MIN_DELAY = float(os.environ.get("ASHBY_MCP_MIN_DELAY", "5"))
MAX_DELAY = float(os.environ.get("ASHBY_MCP_MAX_DELAY", "12"))
# Auto-submit when the form is fully and confidently filled. The user opted
# into this; set ASHBY_MCP_AUTOSUBMIT=0 to require an explicit confirm=True.
AUTOSUBMIT = os.environ.get("ASHBY_MCP_AUTOSUBMIT", "1").lower() not in ("0", "false", "no")

CONFIG_DIR = Path(os.environ.get("ASHBY_MCP_DIR", str(Path.home() / ".ashby-mcp")))
PROFILE_PATH = Path(os.environ.get("ASHBY_MCP_PROFILE", str(CONFIG_DIR / "profile.json")))
COMPANIES_PATH = Path(os.environ.get("ASHBY_MCP_COMPANIES", str(CONFIG_DIR / "companies.json")))
LOG_PATH = Path(os.environ.get("ASHBY_MCP_LOG", str(CONFIG_DIR / "application_log.csv")))

POSTING_API = "https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"
HTTP_HEADERS = {"User-Agent": "ashby-autoapply-mcp/0.1 (+personal job search)"}

INSTRUCTIONS = """\
This server discovers Ashby jobs and applies in the user's own Chrome.

Workflow:
1. Call ashby_status first. If Chrome isn't attached or profile.json /
   resume are missing, tell the user exactly what to fix and stop.
2. find_jobs to discover roles matching the user's profile. Show the user
   the list; let THEM choose which to apply to. Never invent jobs.
3. For each chosen job call auto_apply. It fills the form from profile.json,
   uploads the resume, and (if every required field is confidently filled)
   submits. If it returns status "needs_user_input", it lists the exact
   questions it could not answer - ASK THE USER those questions, then call
   auto_apply again passing the answers in `extra_answers`.
4. Never guess EEO/demographic, work-authorization, sponsorship, salary, or
   free-text screening answers. If unsure, ask.

If any tool returns status "needs_user_input"/"ambiguous"/"error", do not
retry blindly - explain and ask the user.
"""

mcp = FastMCP("ashby-autoapply", instructions=INSTRUCTIONS)

_state: dict[str, Any] = {"pw": None, "browser": None}
_lock = asyncio.Lock()


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def _load_profile() -> dict[str, Any] | None:
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_companies() -> list[str]:
    try:
        data = json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("companies", [])
    return [str(s).strip() for s in data if str(s).strip()]


# --------------------------------------------------------------------------- #
# HTTP (Ashby public posting API) - blocking, run in a thread
# --------------------------------------------------------------------------- #
def _http_get_json(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        return 0, {"_error": str(exc)}


async def _fetch_board(board: str) -> tuple[str, int, Any]:
    status, data = await asyncio.to_thread(_http_get_json, POSTING_API.format(board=board))
    return board, status, data


# --------------------------------------------------------------------------- #
# Pure filtering (unit-testable, no network)
# --------------------------------------------------------------------------- #
def filter_jobs(
    jobs: list[dict[str, Any]],
    titles: list[str],
    keywords: list[str],
    location: str,
    remote_only: bool,
) -> list[dict[str, Any]]:
    """Keep jobs whose title matches any target title/keyword and location."""
    t_terms = [t.lower() for t in titles if t]
    k_terms = [k.lower() for k in keywords if k]
    loc = (location or "").lower().strip()
    out = []
    for j in jobs:
        if j.get("isListed") is False:
            continue
        title = (j.get("title") or "").lower()
        jloc = (j.get("location") or "").lower()
        sec = " ".join(
            (s.get("location") or "") for s in (j.get("secondaryLocations") or [])
        ).lower()
        is_remote = bool(j.get("isRemote"))
        if t_terms or k_terms:
            hay = f"{title}"
            if not any(term in hay for term in t_terms + k_terms):
                continue
        if remote_only and not is_remote:
            continue
        if loc and loc not in jloc and loc not in sec and not (is_remote and loc == "remote"):
            continue
        out.append(j)
    return out


# --------------------------------------------------------------------------- #
# Browser plumbing
# --------------------------------------------------------------------------- #
async def _get_page() -> Page:
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
                f"--remote-debugging-port first. ({exc})"
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


# --------------------------------------------------------------------------- #
# Audit log + daily cap
# --------------------------------------------------------------------------- #
def _log(job_url: str, status: str, detail: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    new = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["timestamp", "job_url", "status", "detail"])
        w.writerow([dt.datetime.now().isoformat(timespec="seconds"), job_url, status, detail])


def _applied_today() -> int:
    if not LOG_PATH.exists():
        return 0
    today = dt.date.today().isoformat()
    n = 0
    with LOG_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("status") == "submitted" and (row.get("timestamp") or "").startswith(today):
                n += 1
    return n


def _already_applied(job_url: str) -> bool:
    if not LOG_PATH.exists():
        return False
    with LOG_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("job_url") == job_url and row.get("status") == "submitted":
                return True
    return False


# --------------------------------------------------------------------------- #
# Form filling (best-effort; Ashby forms are dynamic and vary a lot)
# --------------------------------------------------------------------------- #
async def _fill_field(page: Page, label_patterns: list[str], value: str) -> bool:
    if not value:
        return False
    for pat in label_patterns:
        try:
            loc = page.get_by_label(re.compile(pat, re.I)).first
            await loc.wait_for(state="visible", timeout=2500)
            tag = await loc.evaluate("e => e.tagName.toLowerCase()")
            if tag in ("input", "textarea"):
                await loc.fill(value)
                return True
        except (PWTimeout, PWError):
            continue
    return False


async def _upload_resume(page: Page, resume_path: str) -> bool:
    if not resume_path or not Path(resume_path).expanduser().is_file():
        return False
    try:
        file_input = page.locator("input[type='file']").first
        await file_input.wait_for(state="attached", timeout=4000)
        await file_input.set_input_files(str(Path(resume_path).expanduser()))
        await asyncio.sleep(2.0)
        return True
    except (PWTimeout, PWError):
        return False


async def _unanswered_required(page: Page) -> list[str]:
    """Collect labels of required fields that still look empty/unanswered."""
    out: list[str] = []
    try:
        groups = page.locator(
            "div:has(label:has-text('*')), [aria-required='true'], "
            ".ashby-application-form-question--required"
        )
        n = min(await groups.count(), 60)
        for i in range(n):
            g = groups.nth(i)
            try:
                txt = (await g.inner_text()).strip().splitlines()[0][:120]
            except (PWError, IndexError):
                continue
            filled = False
            for sel in ("input", "textarea"):
                el = g.locator(sel).first
                try:
                    if await el.count() and (await el.input_value()).strip():
                        filled = True
                        break
                except (PWError, PWTimeout):
                    pass
            if not filled and txt and txt not in out:
                out.append(txt)
    except (PWError, PWTimeout):
        pass
    return out


async def _open_application(page: Page, apply_url: str) -> dict[str, Any]:
    try:
        await page.goto(apply_url, wait_until="domcontentloaded", timeout=30000)
    except (PWTimeout, PWError) as exc:
        return {"status": "error", "detail": f"Could not open apply page: {exc}"}
    await asyncio.sleep(random.uniform(2.5, 4.5))
    title = await page.title()
    if "ashbyhq.com" not in page.url:
        return {"status": "ambiguous",
                "detail": f"Apply URL did not land on an Ashby page (got {page.url}). Ask the user."}
    # Some boards show the posting first with an "Apply" button.
    try:
        btn = page.get_by_role("button", name=re.compile(r"^Apply", re.I)).first
        await btn.wait_for(state="visible", timeout=2500)
        await btn.click()
        await asyncio.sleep(1.5)
    except (PWTimeout, PWError):
        pass
    return {"status": "ok", "page_title": title}


# --------------------------------------------------------------------------- #
# MCP tools
# --------------------------------------------------------------------------- #
@mcp.tool()
async def ashby_status() -> dict[str, Any]:
    """Check Chrome attachment, profile.json, resume file, and companies list.

    Always call this first. If anything is missing, tell the user the exact
    file path to create/fix and stop until they confirm.
    """
    profile = _load_profile()
    companies = _load_companies()
    problems: list[str] = []
    if profile is None:
        problems.append(f"profile.json missing or invalid at {PROFILE_PATH} "
                         "(copy profile.example.json and fill it in).")
    else:
        for req in ("full_name", "email", "resume_path"):
            if not profile.get(req):
                problems.append(f"profile.json is missing required field: {req}")
        rp = profile.get("resume_path", "")
        if rp and not Path(rp).expanduser().is_file():
            problems.append(f"resume_path points to a missing file: {rp}")
    if not companies:
        problems.append(f"companies.json missing/empty at {COMPANIES_PATH} "
                         "(copy companies.example.json and edit it).")
    try:
        page = await _get_page()
        chrome_ok, chrome_detail = True, page.url
    except RuntimeError as exc:
        chrome_ok, chrome_detail = False, str(exc)
        problems.append(chrome_detail)
    return {
        "status": "ready" if not problems else "not_ready",
        "chrome_attached": chrome_ok,
        "chrome_detail": chrome_detail,
        "profile_loaded": profile is not None,
        "companies_count": len(companies),
        "autosubmit": AUTOSUBMIT,
        "applied_today": _applied_today(),
        "daily_cap": DAILY_CAP,
        "problems": problems,
    }


@mcp.tool()
async def verify_companies(companies: list[str] | None = None) -> dict[str, Any]:
    """Ping each Ashby board's public API and report which slugs are valid.

    Use this after the user edits companies.json so bad slugs are caught
    early. Returns valid boards (with job counts) and invalid ones.
    """
    boards = companies or _load_companies()
    if not boards:
        return {"status": "needs_user_input",
                "detail": f"No companies to verify. Edit {COMPANIES_PATH}."}
    results = await asyncio.gather(*[_fetch_board(b) for b in boards])
    valid, invalid = [], []
    for board, code, data in results:
        if code == 200 and isinstance(data, dict) and isinstance(data.get("jobs"), list):
            valid.append({"board": board, "open_jobs": len(data["jobs"])})
        else:
            invalid.append({"board": board, "http_status": code})
    return {"status": "ok", "valid": valid, "invalid": invalid,
            "note": "Invalid slugs are wrong/case-sensitive. The slug is the path in "
                    "jobs.ashbyhq.com/<slug>."}


@mcp.tool()
async def find_jobs(
    keywords: str = "",
    location: str = "",
    remote_only: bool | None = None,
    companies: list[str] | None = None,
    max_results: int = 25,
) -> dict[str, Any]:
    """Discover Ashby jobs matching the user's profile across company boards.

    Empty args fall back to profile.json (target_titles, keywords, locations,
    remote_only). `companies` overrides companies.json for this call. Always
    show the user the results and let them choose; never invent jobs.
    """
    profile = _load_profile() or {}
    boards = companies or _load_companies()
    if not boards:
        return {"status": "needs_user_input",
                "detail": f"No company boards configured. Edit {COMPANIES_PATH} "
                          "or pass `companies`."}
    titles = profile.get("target_titles", []) or []
    kw = [k for k in re.split(r"[,\s]+", keywords) if k] or profile.get("keywords", []) or []
    loc = location or (profile.get("locations", [""]) or [""])[0]
    ro = profile.get("remote_only", False) if remote_only is None else remote_only

    results = await asyncio.gather(*[_fetch_board(b) for b in boards])
    jobs_out: list[dict[str, Any]] = []
    errors: list[str] = []
    for board, code, data in results:
        if code != 200 or not isinstance(data, dict):
            errors.append(f"{board} (HTTP {code})")
            continue
        matched = filter_jobs(data.get("jobs", []), titles, kw, loc, ro)
        for j in matched:
            jobs_out.append({
                "company": board,
                "title": j.get("title"),
                "location": j.get("location"),
                "isRemote": bool(j.get("isRemote")),
                "employmentType": j.get("employmentType"),
                "jobUrl": j.get("jobUrl"),
                "applyUrl": j.get("applyUrl") or j.get("jobUrl"),
                "applied_already": _already_applied(j.get("jobUrl") or j.get("applyUrl") or ""),
            })
    jobs_out.sort(key=lambda x: (x["company"], x["title"] or ""))
    return {
        "status": "ok" if jobs_out else "no_matches",
        "match_count": len(jobs_out),
        "results": jobs_out[:max(1, min(max_results, 100))],
        "boards_searched": len(boards),
        "board_errors": errors,
        "filter_used": {"titles": titles, "keywords": kw, "location": loc, "remote_only": ro},
    }


@mcp.tool()
async def get_job(company: str, job_url: str = "") -> dict[str, Any]:
    """Fetch one posting's details (description text) so the user can decide.

    `company` is the Ashby board slug; `job_url` selects the specific posting.
    """
    _, code, data = await _fetch_board(company)
    if code != 200 or not isinstance(data, dict):
        return {"status": "error", "detail": f"Could not fetch board '{company}' (HTTP {code})."}
    for j in data.get("jobs", []):
        if not job_url or job_url in (j.get("jobUrl"), j.get("applyUrl")):
            desc = j.get("descriptionPlain") or re.sub(
                r"<[^>]+>", " ", j.get("descriptionHtml") or "")
            return {"status": "ok", "title": j.get("title"),
                    "location": j.get("location"), "isRemote": bool(j.get("isRemote")),
                    "applyUrl": j.get("applyUrl") or j.get("jobUrl"),
                    "description": re.sub(r"\s+", " ", desc).strip()[:4000]}
    return {"status": "needs_user_input",
            "detail": "Job not found on that board (it may have closed). Ask the user."}


@mcp.tool()
async def auto_apply(
    apply_url: str,
    extra_answers: dict[str, str] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Fill and (if complete) submit one Ashby application in the user's Chrome.

    Fills standard fields + uploads the resume from profile.json. `extra_answers`
    is a {question: answer} map for things only the user can answer (you must
    have ASKED the user first - never fabricate these).

    Outcomes:
      * "needs_user_input" + `questions`: required fields it would not guess.
        Ask the user those exact questions, then call again with the answers
        in `extra_answers`.
      * "preview": form filled but autosubmit is off / confirm=false. Tell the
        user what will be submitted; call again with confirm=true to send.
      * "submitted": application was sent.
      * "cap_reached"/"already_applied"/"error"/"ambiguous": explain, don't retry.
    """
    profile = _load_profile()
    if profile is None:
        return {"status": "error", "detail": f"profile.json invalid/missing at {PROFILE_PATH}."}
    if _already_applied(apply_url):
        return {"status": "already_applied", "detail": "Log shows this job was already submitted."}
    if _applied_today() >= DAILY_CAP:
        return {"status": "cap_reached",
                "detail": f"Daily cap of {DAILY_CAP} reached. Resets tomorrow."}

    try:
        page = await _get_page()
    except RuntimeError as exc:
        return {"status": "error", "detail": str(exc)}

    opened = await _open_application(page, apply_url)
    if opened["status"] != "ok":
        return opened

    answers = {k.lower(): v for k, v in (extra_answers or {}).items()}
    da = {k.lower(): v for k, v in (profile.get("default_answers") or {}).items()}

    filled: list[str] = []
    if await _fill_field(page, [r"\bname\b", r"full name"], profile.get("full_name", "")):
        filled.append("name")
    if await _fill_field(page, [r"e-?mail"], profile.get("email", "")):
        filled.append("email")
    if await _fill_field(page, [r"phone"], profile.get("phone", "")):
        filled.append("phone")
    if await _fill_field(page, [r"linkedin"], profile.get("linkedin", "")):
        filled.append("linkedin")
    if await _fill_field(page, [r"github"], profile.get("github", "")):
        filled.append("github")
    if await _fill_field(page, [r"website|portfolio"], profile.get("website", "")):
        filled.append("website")
    if await _fill_field(page, [r"location|city"], profile.get("location", "")):
        filled.append("location")
    if await _upload_resume(page, profile.get("resume_path", "")):
        filled.append("resume")

    # Apply user-supplied / default answers to any matching labelled fields.
    for q, a in {**da, **answers}.items():
        if a and await _fill_field(page, [re.escape(q)], a):
            filled.append(q)

    await asyncio.sleep(1.0)
    missing = await _unanswered_required(page)
    if missing:
        _log(apply_url, "needs_input", "; ".join(missing)[:300])
        return {
            "status": "needs_user_input",
            "filled": filled,
            "questions": missing,
            "detail": "These required fields could not be filled from your profile. "
                      "Ask the user for each, then call auto_apply again with "
                      "extra_answers={question: answer}. Do not guess.",
        }

    do_submit = AUTOSUBMIT or confirm
    if not do_submit:
        return {"status": "preview", "filled": filled,
                "detail": "Form is complete but autosubmit is off. Call again with "
                          "confirm=true to submit."}

    submit = None
    for sel in ("button[type='submit']",
                "button:has-text('Submit Application')",
                "button:has-text('Submit')"):
        loc = page.locator(sel).first
        try:
            await loc.wait_for(state="visible", timeout=3000)
            if await loc.is_enabled():
                submit = loc
                break
        except (PWTimeout, PWError):
            continue
    if submit is None:
        _log(apply_url, "error", "submit button not found")
        return {"status": "error", "filled": filled,
                "detail": "Form filled but the Submit button was not found/enabled. "
                          "Ask the user to check the Chrome window."}
    await submit.click()
    await asyncio.sleep(4.0)

    body = ""
    try:
        body = (await page.locator("body").inner_text()).lower()
    except PWError:
        pass
    success = any(s in body for s in (
        "application submitted", "thanks for applying", "thank you for applying",
        "we've received your application", "successfully submitted"))
    if success:
        _log(apply_url, "submitted", ", ".join(filled))
        await _pause()
        return {"status": "submitted", "filled": filled,
                "applied_today": _applied_today(), "daily_cap": DAILY_CAP}
    _log(apply_url, "uncertain", "no confirmation text detected")
    return {"status": "ambiguous", "filled": filled,
            "detail": "Clicked submit but no confirmation was detected. The user "
                      "should check the Chrome window to confirm whether it sent."}


@mcp.tool()
async def application_log(limit: int = 25) -> dict[str, Any]:
    """Return recent application attempts (audit trail) and today's count."""
    rows: list[dict[str, str]] = []
    if LOG_PATH.exists():
        with LOG_PATH.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    return {"status": "ok", "applied_today": _applied_today(), "daily_cap": DAILY_CAP,
            "recent": rows[-max(1, min(limit, 200)):]}


def main() -> None:
    """Console entry point: run the server over stdio (for MCP clients)."""
    mcp.run()


if __name__ == "__main__":
    main()
