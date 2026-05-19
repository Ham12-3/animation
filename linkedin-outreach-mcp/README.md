# LinkedIn Outreach MCP

An MCP server that lets Claude (Desktop, or any MCP-capable app) do LinkedIn
outreach by driving **your own already-open, already-logged-in Chrome**.

Talk to Claude in plain language — *"find fintech product managers in London
and send them a short intro from me"* — and it searches LinkedIn, DMs people
you're connected to, or sends a connection request with a personalized note
to people you're not. It previews every send for your approval and asks you
questions whenever something is unclear instead of guessing.

It never sees or stores your password. You launch Chrome with remote
debugging and log into LinkedIn by hand; the server attaches over the Chrome
DevTools Protocol and drives that visible window. You watch it happen.

```
linkedin-outreach-mcp/
├── pyproject.toml                       # installable package + console script
├── requirements.txt                     # plain pip-install path
├── src/linkedin_outreach_mcp/
│   ├── __init__.py
│   ├── __main__.py                      # python -m linkedin_outreach_mcp
│   └── server.py                        # the MCP server (tools live here)
└── standalone/                          # optional, no-AI fallback
    ├── linkedin_bot.py                  # fixed-CSV-list script
    └── recipients.example.csv
```

## Read this first

Automating LinkedIn violates LinkedIn's User Agreement and can get your
account **rate-limited, restricted, or permanently banned**. You accept that
risk. On **free** accounts, connection requests that include a personalized
note are heavily limited (Premium gets more), plus there are weekly invite
caps. The server surfaces LinkedIn's own limit messages back to Claude so it
can tell you, rather than failing silently. Keep volume low, keep messages
genuinely personal, watch it run.

## Install

From this folder:

```bash
pip install -e .
python -m playwright install     # one-time, pulls Playwright's browser driver
```

(`pip install -r requirements.txt` also works if you'd rather not install the
package; then run it with `python -m linkedin_outreach_mcp`.)

## 1. Start Chrome with remote debugging

Quit Chrome completely, then launch it with a debug port and a dedicated
profile folder (so your normal profile is untouched):

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir="$HOME/.linkedin-bot-chrome"

# Linux
google-chrome --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.linkedin-bot-chrome"
```
```powershell
# Windows PowerShell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 --user-data-dir="$env:USERPROFILE\.linkedin-bot-chrome"
```

In that window, go to linkedin.com and **log in by hand** (including 2FA).
The session persists in that profile folder, so this is a one-time thing.

## 2. Connect it to Claude Desktop

Edit Claude Desktop's config:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```jsonc
{
  "mcpServers": {
    "linkedin-outreach": {
      "command": "linkedin-outreach-mcp",
      "env": {
        "LINKEDIN_MCP_CDP_URL": "http://127.0.0.1:9222",
        "LINKEDIN_MCP_DAILY_MSG_CAP": "25",
        "LINKEDIN_MCP_WEEKLY_INVITE_CAP": "80"
      }
    }
  }
}
```

`command` can be the installed `linkedin-outreach-mcp` console script, or use
the explicit interpreter form if it's not on PATH:

```jsonc
"command": "/abs/path/to/python",
"args": ["-m", "linkedin_outreach_mcp"]
```

Restart Claude Desktop. Any other MCP-capable app works the same way over
stdio.

## 3. Just talk to Claude

> "Check LinkedIn is ready. Then find 10 heads of growth at Series B fintechs
> in the UK. If I'm connected, DM them: *'Hi {name} — liked your take on
> activation; would love to compare notes.'* If not, send a connection
> request with a one-line version. Show me each before sending; ask me if
> anything's unclear."

Tools the server exposes:

| Tool | What it does |
|---|---|
| `linkedin_status` | Confirms Chrome is attached and you're logged in. Call first. |
| `search_people` | Runs a People search; returns matches for you to pick. |
| `get_profile` | Reports name, degree, and can_message / can_connect / pending. |
| `reach_out` | Auto-picks DM vs connection-request-with-note. Two-step: preview, then `confirm=true`. |
| `activity_log` | Audit trail + caps remaining. |

## Safety model

- **Two-step send.** `reach_out` with `confirm=false` does nothing and
  returns a preview. Sending needs a second `confirm=true` call. Claude is
  instructed to show you the preview and get approval first.
- **Asks instead of guessing.** Login/captcha wall, unknown layout, or
  unclear contact path → returns `needs_user_input`/`ambiguous` and Claude
  asks you.
- **Caps + audit log.** Daily message and weekly invite caps (env-tunable)
  enforced from `~/.linkedin-mcp/activity_log.csv`, which records every
  action with a timestamp.
- **Note length.** Notes over 300 chars are rejected so Claude shortens them.

### Tunable env vars

| Var | Default | Meaning |
|---|---|---|
| `LINKEDIN_MCP_CDP_URL` | `http://127.0.0.1:9222` | Your debug Chrome endpoint |
| `LINKEDIN_MCP_DAILY_MSG_CAP` | `25` | Max DMs per day |
| `LINKEDIN_MCP_WEEKLY_INVITE_CAP` | `80` | Max invites per 7 days |
| `LINKEDIN_MCP_MIN_DELAY` / `_MAX_DELAY` | `6` / `16` | Seconds to wait after a send |
| `LINKEDIN_MCP_LOG` | `~/.linkedin-mcp/activity_log.csv` | Audit log path |

## Honest limitations

- LinkedIn changes its HTML constantly. Search-result parsing and the
  Connect/Message/Send selectors (`_profile_state`, `_send_dm`,
  `_send_invite`, `search_people` in `src/linkedin_outreach_mcp/server.py`)
  are the fragile parts and may need occasional tweaks. The server fails
  loudly (asks you) rather than doing the wrong thing.
- Built to run on your machine with your real Chrome and LinkedIn session;
  it can't be exercised end-to-end in a headless/cloud environment, so the
  browser-driving paths are unverified against live LinkedIn — watch the
  first real run closely.
- Free-account invite-note limits and LinkedIn's commercial-use search limit
  are LinkedIn-side; the server reports them but cannot bypass them.

## Optional: standalone CSV script

`standalone/linkedin_bot.py` is a no-AI fixed-list fallback. Dry-runs by
default; `--send` prompts per message.

```bash
cd standalone
python linkedin_bot.py --recipients recipients.csv          # preview only
python linkedin_bot.py --recipients recipients.csv --send    # confirm each
```
