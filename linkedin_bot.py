#!/usr/bin/env python3
"""Drive YOUR own logged-in Chrome to send LinkedIn messages, with a human in the loop.

It does NOT log in for you and does NOT store credentials. You start Chrome
yourself with remote debugging enabled, log into LinkedIn by hand, and this
script attaches to that running window over the Chrome DevTools Protocol.

Read README.md before using. Automated LinkedIn messaging violates LinkedIn's
User Agreement and can get your account restricted or banned. Keep volume low,
keep messages personal, and watch it run.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Error as PWError
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright


@dataclass
class Recipient:
    profile_url: str
    first_name: str
    message: str


def load_recipients(path: Path, default_template: str) -> list[Recipient]:
    if not path.exists():
        sys.exit(f"Recipients file not found: {path}")
    out: list[Recipient] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "profile_url" not in reader.fieldnames:
            sys.exit("CSV must have a 'profile_url' column (see recipients.example.csv).")
        for row in reader:
            url = (row.get("profile_url") or "").strip()
            if not url:
                continue
            first = (row.get("first_name") or "").strip()
            template = (row.get("message") or "").strip() or default_template
            try:
                message = template.format(first_name=first or "there")
            except (KeyError, IndexError):
                # Unknown placeholder in the template -> send it literally
                # rather than crashing the whole run.
                message = template
            out.append(Recipient(profile_url=url, first_name=first, message=message))
    if not out:
        sys.exit("No recipients with a profile_url found in the CSV.")
    return out


def sent_today(log_path: Path) -> int:
    """How many messages we already recorded as sent today (for the daily cap)."""
    if not log_path.exists():
        return 0
    today = dt.date.today().isoformat()
    count = 0
    with log_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("status") == "sent" and (row.get("timestamp") or "").startswith(today):
                count += 1
    return count


def log_result(log_path: Path, profile_url: str, status: str, detail: str) -> None:
    new = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if new:
            writer.writerow(["timestamp", "profile_url", "status", "detail"])
        writer.writerow([dt.datetime.now().isoformat(timespec="seconds"), profile_url, status, detail])


def human_pause(lo: float, hi: float) -> None:
    time.sleep(random.uniform(lo, hi))


def open_message_box(page):
    """Click the profile's 'Message' button and return the compose editor locator.

    LinkedIn's DOM changes often, so we try a few strategies and fall back
    gracefully. Returns None if the person can't be messaged.
    """
    page.wait_for_load_state("domcontentloaded")
    human_pause(2.0, 4.0)

    clicked = False
    # Strategy 1: the primary "Message" button in the profile top card.
    for getter in (
        lambda: page.get_by_role("button", name=re.compile(r"^Message", re.I)),
        lambda: page.locator("button[aria-label^='Message']"),
        lambda: page.locator("a[aria-label^='Message']"),
    ):
        try:
            btn = getter().first
            btn.wait_for(state="visible", timeout=4000)
            btn.click()
            clicked = True
            break
        except (PWTimeout, PWError):
            continue

    if not clicked:
        return None

    human_pause(1.5, 3.0)
    for sel in (
        "div.msg-form__contenteditable[contenteditable='true']",
        "div[role='textbox'][contenteditable='true']",
        "div[aria-label*='Write a message'][contenteditable='true']",
    ):
        editor = page.locator(sel).first
        try:
            editor.wait_for(state="visible", timeout=4000)
            return editor
        except (PWTimeout, PWError):
            continue
    return None


def type_message(editor, text: str) -> None:
    editor.click()
    human_pause(0.4, 1.0)
    for chunk in text.split("\n"):
        editor.type(chunk, delay=random.uniform(20, 60))
        # Shift+Enter keeps a newline inside the LinkedIn compose box
        # instead of submitting the message.
        editor.press("Shift+Enter")
    human_pause(0.5, 1.2)


def click_send(page) -> bool:
    for getter in (
        lambda: page.locator("button.msg-form__send-button"),
        lambda: page.get_by_role("button", name=re.compile(r"^Send$", re.I)),
    ):
        try:
            btn = getter().first
            btn.wait_for(state="visible", timeout=4000)
            if btn.is_enabled():
                btn.click()
                return True
        except (PWTimeout, PWError):
            continue
    return False


def confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def run(args: argparse.Namespace) -> int:
    recipients = load_recipients(Path(args.recipients), args.message)
    log_path = Path(args.log)

    already = sent_today(log_path)
    remaining = max(0, args.daily_cap - already)
    mode = "DRY-RUN (nothing will be sent)" if not args.send else (
        "AUTO-SEND" if args.yes else "SEND with per-message confirmation"
    )
    print(f"Mode: {mode}")
    print(f"Recipients loaded: {len(recipients)}")
    print(f"Daily cap: {args.daily_cap} | already sent today: {already} | remaining: {remaining}\n")

    if args.send and remaining == 0:
        print("Daily cap already reached. Stopping.")
        return 0

    # Dry-run only previews; it never touches Chrome.
    if not args.send:
        for idx, r in enumerate(recipients, 1):
            print(f"[{idx}/{len(recipients)}] {r.profile_url}")
            print(f"    message: {r.message!r}")
            log_result(log_path, r.profile_url, "dry-run", "preview only")
        print(f"\nDry-run complete. {len(recipients)} message(s) previewed, none sent.")
        return 0

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp_url)
        except PWError as exc:
            sys.exit(
                f"Could not attach to Chrome at {args.cdp_url}: {exc}\n"
                "Start Chrome with remote debugging first (see README.md)."
            )
        if not browser.contexts:
            sys.exit("Connected to Chrome but found no browser context/tabs open.")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        processed = 0
        for idx, r in enumerate(recipients, 1):
            if processed >= remaining:
                print(f"\nReached daily cap of {args.daily_cap}. Stopping.")
                break

            print(f"[{idx}/{len(recipients)}] {r.profile_url}")
            print(f"    message: {r.message!r}")

            try:
                page.goto(r.profile_url, wait_until="domcontentloaded", timeout=30000)
            except (PWTimeout, PWError) as exc:
                print(f"    skip: could not open profile ({exc})")
                log_result(log_path, r.profile_url, "error", f"goto failed: {exc}")
                continue

            editor = open_message_box(page)
            if editor is None:
                print("    skip: no Message button / not connected.")
                log_result(log_path, r.profile_url, "skipped", "no message button")
                continue

            try:
                type_message(editor, r.message)
            except (PWTimeout, PWError) as exc:
                print(f"    skip: could not type message ({exc})")
                log_result(log_path, r.profile_url, "error", f"type failed: {exc}")
                continue

            if not args.yes and not confirm("    Send this message? [y/N] "):
                print("    not sent (you declined).")
                log_result(log_path, r.profile_url, "declined", "user declined")
                continue

            if click_send(page):
                processed += 1
                print("    sent.")
                log_result(log_path, r.profile_url, "sent", "ok")
            else:
                print("    skip: Send button not found/enabled.")
                log_result(log_path, r.profile_url, "error", "send button missing")

            human_pause(args.min_delay, args.max_delay)

    print("\nDone.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Send LinkedIn messages through your own attached Chrome (human-in-the-loop).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--cdp-url", default="http://localhost:9222",
                   help="DevTools endpoint of the Chrome you started with --remote-debugging-port.")
    p.add_argument("--recipients", default="recipients.csv",
                   help="CSV with columns: profile_url[,first_name][,message].")
    p.add_argument("--message",
                   default="Hi {first_name}, great to connect on LinkedIn!",
                   help="Default message template when a row has no 'message'. Supports {first_name}.")
    p.add_argument("--log", default="sent_log.csv", help="Append-only audit log of every action.")
    p.add_argument("--send", action="store_true",
                   help="Actually send. Without this flag it is a dry-run preview only.")
    p.add_argument("--yes", action="store_true",
                   help="With --send, skip the per-message y/N prompt (auto-send). Higher risk.")
    p.add_argument("--daily-cap", type=int, default=20,
                   help="Max messages actually sent per calendar day (tracked via the log).")
    p.add_argument("--min-delay", type=float, default=45.0,
                   help="Minimum seconds to wait after a successful send.")
    p.add_argument("--max-delay", type=float, default=90.0,
                   help="Maximum seconds to wait after a successful send.")
    return p


if __name__ == "__main__":
    sys.exit(run(build_parser().parse_args()))
