# LinkedIn outreach for Claude (MCP server)

Talk to Claude in plain language — *"find fintech product managers in London
and send them a short intro from me"* — and Claude drives **your own
already-open, already-logged-in Chrome** to search LinkedIn, message people
you're connected to, or send a connection request with a personalized note to
people you're not. Claude asks you before anything is sent, and asks
questions whenever something is unclear instead of guessing.

There are two pieces in this repo:

| File | What it is |
|---|---|
| `linkedin_mcp_server.py` | **The MCP server** — the thing you want. Connects to Claude. |
| `linkedin_bot.py` | Optional standalone CSV script (older, manual-list approach). |

It never sees or stores your password. You launch Chrome with remote
debugging and log into LinkedIn by hand; the server attaches over the Chrome
DevTools Protocol and drives that visible window. You watch it happen.

## Read this first

Automating LinkedIn violates LinkedIn's User Agreement and can get your
account **rate-limited, restricted, or permanently banned**. You accept that
risk. Also, on **free** LinkedIn accounts the number of connection requests
that can include a personalized note is heavily limited (Premium gets more),
and there are weekly invite caps. The server surfaces LinkedIn's own limit
messages back to Claude so it can tell you, rather than failing silently.

Keep volume low, keep messages genuinely personal, watch it run.

## Setup

```bash
pip install -r requirements.txt
python -m playwright install        # one-time
```

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

## 2. Connect the server to Claude Desktop

Edit Claude Desktop's config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```jsonc
{
  "mcpServers": {
    "linkedin-outreach": {
      "command": "python",
      "args": ["/ABSOLUTE/PATH/TO/linkedin_mcp_server.py"],
      "env": {
        "LINKEDIN_MCP_CDP_URL": "http://127.0.0.1:9222",
        "LINKEDIN_MCP_DAILY_MSG_CAP": "25",
        "LINKEDIN_MCP_WEEKLY_INVITE_CAP": "80"
      }
    }
  }
}
```

Use the absolute path to `python` from where you installed the requirements
(e.g. a venv's `python`). Restart Claude Desktop. Any other MCP-capable app
works the same way — point it at `python linkedin_mcp_server.py` over stdio.

## 3. Just talk to Claude

> "Check LinkedIn is ready. Then find 10 heads of growth at Series B fintechs
> in the UK. For each, if I'm connected send: *'Hi {name} — really liked your
> take on activation; would love to compare notes sometime.'* If I'm not
> connected, send a connection request with a one-line version of that. Show
> me each one before sending and ask me if anything's unclear."

What Claude does with the tools:

1. `linkedin_status` — confirms Chrome is attached and you're logged in.
2. `search_people` — runs the search, shows you the matches. You pick.
3. `reach_out` (preview) — for each person it reports whether it will **DM**
   (you're connected) or send a **connection request + note** (you're not),
   and the exact text. **Nothing is sent yet.**
4. You approve → Claude calls `reach_out` again with `confirm=true`.
5. `activity_log` — anytime, to see what was done and caps remaining.

## How the safety model works

- **Two-step send.** Every `reach_out` with `confirm=false` does nothing and
  returns a preview. Sending requires a second, explicit `confirm=true` call.
  Claude is instructed to show you the preview and get your approval first.
- **It asks instead of guessing.** If a page is a login/captcha wall, the
  layout is unrecognized, or it can't tell whether to message vs connect, the
  tool returns `needs_user_input`/`ambiguous` and Claude asks you a question.
- **Caps + audit log.** Daily message cap and weekly invite cap (env-tunable)
  are enforced from `~/.linkedin-mcp/activity_log.csv`, which records every
  action with a timestamp.
- **Note length.** Connection notes over 300 chars are rejected so Claude
  shortens them rather than having LinkedIn truncate.

### Tunable env vars

| Var | Default | Meaning |
|---|---|---|
| `LINKEDIN_MCP_CDP_URL` | `http://127.0.0.1:9222` | Your debug Chrome endpoint |
| `LINKEDIN_MCP_DAILY_MSG_CAP` | `25` | Max DMs sent per day |
| `LINKEDIN_MCP_WEEKLY_INVITE_CAP` | `80` | Max connection invites per 7 days |
| `LINKEDIN_MCP_MIN_DELAY` / `_MAX_DELAY` | `6` / `16` | Seconds to wait after a send |
| `LINKEDIN_MCP_LOG` | `~/.linkedin-mcp/activity_log.csv` | Audit log path |

## Honest limitations

- LinkedIn changes its HTML constantly. Search-result parsing and the
  Connect/Message/Send selectors (`_profile_state`, `_send_dm`,
  `_send_invite`, `search_people` in `linkedin_mcp_server.py`) are the fragile
  parts and may need occasional tweaks. The server fails loudly (asks you)
  rather than doing the wrong thing.
- This was built to run on your machine with your real Chrome and LinkedIn
  session. It cannot be exercised end-to-end in a headless/cloud environment,
  so the browser-driving paths are unverified against live LinkedIn — watch
  the first real run closely.
- Free-account invite-note limits and LinkedIn's commercial-use search limit
  are LinkedIn-side; the server reports them but cannot bypass them.

---

### Optional: standalone CSV script (`linkedin_bot.py`)

If you ever want a no-AI, fixed-list run instead: dry-runs by default, and
`--send` prompts per message. See `recipients.example.csv`. This is the older
approach you said you didn't want — kept only as a fallback.

```bash
python linkedin_bot.py --recipients recipients.csv          # preview only
python linkedin_bot.py --recipients recipients.csv --send    # confirm each
```
