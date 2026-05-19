# LinkedIn messaging via your own Chrome

A small tool that attaches to **your already-open, already-logged-in Chrome**
and sends LinkedIn messages from a list — with a human in the loop.

It does **not** log in for you, does **not** ask for or store your password,
and does **not** launch a hidden browser. You drive a real Chrome window; the
script just automates the clicks while you watch.

## Read this first

LinkedIn's User Agreement prohibits automated messaging and scraping.
Using this can get your account **rate-limited, restricted, or permanently
banned**, regardless of how careful you are. You accept that risk.

To keep risk low:

- Keep the daily cap small (default 20; honestly, lower is safer).
- Write personal messages — generic blasts are what gets flagged.
- Stay at the keyboard and watch it run. Use the default per-message
  confirmation, not `--yes`.
- Only message people you actually have a reason to message.

This is for your own account and your own outreach. Don't use it to spam.

## Setup

```bash
pip install -r requirements.txt
python -m playwright install   # one-time; pulls Playwright's driver
```

## 1. Start Chrome with remote debugging

Quit Chrome completely first, then launch it with a debugging port and a
dedicated profile folder (so it doesn't disturb your normal profile):

**macOS**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.linkedin-bot-chrome"
```

**Linux**
```bash
google-chrome --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.linkedin-bot-chrome"
```

**Windows (PowerShell)**
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:USERPROFILE\.linkedin-bot-chrome"
```

In that Chrome window, go to linkedin.com and **log in normally** (including
any 2FA). The session stays in that profile folder, so you only do this once.

## 2. Build your recipient list

Copy `recipients.example.csv` to `recipients.csv` and edit it. Columns:

- `profile_url` (required) — the person's LinkedIn profile URL.
- `first_name` (optional) — used for the `{first_name}` placeholder.
- `message` (optional) — per-person message. If blank, the `--message`
  template is used.

## 3. Dry-run (default, sends nothing)

```bash
python linkedin_bot.py --recipients recipients.csv
```

This prints exactly what it *would* send for each person and writes a
`dry-run` row to `sent_log.csv`. Nothing is sent.

## 4. Send, confirming each one

```bash
python linkedin_bot.py --recipients recipients.csv --send
```

For each person it opens the profile, opens the message box, types the
message, and asks `Send this message? [y/N]` before clicking Send. It waits
a randomized delay between sends and stops at the daily cap.

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--cdp-url` | `http://localhost:9222` | Where your debug Chrome is listening |
| `--recipients` | `recipients.csv` | Input CSV |
| `--message` | `Hi {first_name}, great to connect on LinkedIn!` | Fallback template |
| `--send` | off | Actually send (otherwise dry-run) |
| `--yes` | off | Skip the per-message prompt (auto-send — higher risk) |
| `--daily-cap` | `20` | Max real sends per calendar day |
| `--min-delay` / `--max-delay` | `45` / `90` | Seconds to wait after each send |
| `--log` | `sent_log.csv` | Append-only audit log |

## Notes & limits

- The daily cap is enforced from `sent_log.csv`, so keep that file around.
- LinkedIn changes its HTML often. If the Message box or Send button stops
  being found, the selectors in `linkedin_bot.py` (`open_message_box`,
  `click_send`) are where to adjust.
- People you aren't connected to may not show a Message button; those are
  logged as `skipped`.
- This was built to run on your machine; it can't be tested in a headless
  CI/cloud environment because it needs your real Chrome and LinkedIn session.
