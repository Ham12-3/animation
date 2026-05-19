# MCP servers

This repository holds MCP servers, each self-contained in its own folder so
they can be installed and run independently. They all attach to the same
debugged Chrome instance, so one Chrome window can be driven by every server.

| Folder | What it is |
|---|---|
| [`linkedin-outreach-mcp/`](linkedin-outreach-mcp/) | **LinkedIn Outreach MCP** — Claude searches LinkedIn and sends DMs / noted connection requests by driving your own logged-in Chrome, with a human-in-the-loop preview. |
| [`ashby-autoapply-mcp/`](ashby-autoapply-mcp/) | **Ashby Auto-Apply MCP** — finds jobs on Ashby company boards (public posting API) and auto-applies in your own logged-in Chrome from a `profile.json` you control; asks you about anything it can't answer. |
| [`mcp-server-template/`](mcp-server-template/) | Copy-and-rename starter for a new MCP server. See its README for the rename steps. |

Each server has its own README with full setup + the tools it exposes. What
follows is the cross-cutting "wire it all up once" guide.

## 1. Install everything

```bash
pip install -e ./linkedin-outreach-mcp ./ashby-autoapply-mcp
python -m playwright install        # one-time, pulls Playwright's browser driver
```

This puts both console scripts (`linkedin-outreach-mcp` and
`ashby-autoapply-mcp`) on your PATH.

## 2. Start Chrome with remote debugging (one window for both servers)

Quit Chrome completely, then launch it with a debug port and a dedicated
profile folder. Log into LinkedIn (for the LinkedIn server) in that window;
the Ashby server doesn't need a login but uses the same window for the
Ashby application pages.

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

## 3. Configure the Ashby server (one-time)

```bash
mkdir -p ~/.ashby-mcp
cp ashby-autoapply-mcp/profile.example.json   ~/.ashby-mcp/profile.json
cp ashby-autoapply-mcp/companies.example.json ~/.ashby-mcp/companies.json
# then edit profile.json (email, phone, absolute resume_path, target_titles, ...)
# and companies.json (verify slugs by running the verify_companies tool)
```

The LinkedIn server has no config files; it reads only env vars (see its
README).

## 4. Wire both servers into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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
    },
    "ashby-autoapply": {
      "command": "ashby-autoapply-mcp",
      "env": {
        "ASHBY_MCP_CDP_URL": "http://127.0.0.1:9222",
        "ASHBY_MCP_DAILY_CAP": "15",
        "ASHBY_MCP_AUTOSUBMIT": "1"
      }
    }
  }
}
```

If `linkedin-outreach-mcp` / `ashby-autoapply-mcp` aren't found by Claude
Desktop (PATH issues), use the explicit interpreter form instead:

```jsonc
"command": "/abs/path/to/python",
"args":    ["-m", "linkedin_outreach_mcp"]
```

Restart Claude Desktop. You should see both servers connect, and the tools
from each become available in chat. Talk to Claude in plain language — each
server's README has example prompts.

## 5. Adding a new MCP server

Use [`mcp-server-template/`](mcp-server-template/). Copy it, rename, edit
`server.py`, then add a block to the `mcpServers` object above. Step-by-step
in the template's README.

## Honest reminders

- These servers drive your real Chrome and your real accounts. LinkedIn
  automation breaks LinkedIn's User Agreement; mass-applying with a weak
  profile harms your reputation. Keep volume low, keep content personal,
  watch what they do.
- Form selectors and search-result parsing on LinkedIn and Ashby change
  often. When something stops working, the README of each server points at
  the exact functions to tweak.
- The browser-driving paths could not be exercised in the cloud sandbox
  where this was built. The first real runs on your machine deserve close
  attention.
