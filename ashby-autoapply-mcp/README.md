# Ashby Auto-Apply MCP

An MCP server that lets Claude find jobs on Ashby company boards and apply to
them in **your own already-open, already-logged-in Chrome**, driven by a
`profile.json` you control.

Tell Claude *"find backend roles matching my profile and apply"* and it
queries Ashby's public posting API across the company boards you configured,
shows you the matches, then fills + uploads your résumé + submits each
application. It **auto-submits only when every required field is confidently
filled**; anything it can't answer from your profile (free-text, EEO,
work-authorization nuance, screening questions) is handed back so Claude asks
you instead of guessing.

It never sees or stores any password. You launch Chrome with remote
debugging and stay logged in; the server attaches over the Chrome DevTools
Protocol and drives that visible window. You watch it happen.

```
ashby-autoapply-mcp/
├── pyproject.toml                    # installable; console script: ashby-autoapply-mcp
├── requirements.txt
├── README.md
├── profile.example.json             # copy -> ~/.ashby-mcp/profile.json, fill it
├── companies.example.json           # copy -> ~/.ashby-mcp/companies.json, edit
└── src/ashby_autoapply_mcp/
    ├── __init__.py
    ├── __main__.py                   # python -m ashby_autoapply_mcp
    └── server.py                     # the MCP server (tools live here)
```

## Important truths up front

- **Ashby has no global job search.** Discovery is limited to the company
  board slugs you put in `companies.json`. The seed list is a starting point,
  not guaranteed correct — run `verify_companies` and prune it.
- **I cannot read your LinkedIn or CV.** LinkedIn is behind an auth wall and
  the server has no file access to your CV. Your details live in
  `profile.json` (your name and LinkedIn URL are pre-filled in the example;
  fill the rest). That file drives both job filtering and form filling.
- **Auto-fill is best-effort.** Ashby forms are dynamic and vary per company.
  Standard fields + résumé upload are handled; unrecognised required
  questions are returned to you, never guessed. The first real runs need
  watching — the form selectors in `server.py` (`_fill_field`,
  `_upload_resume`, `_unanswered_required`) are the fragile parts.
- **This cannot be tested end-to-end here.** No GUI Chrome / live Ashby forms
  in a cloud sandbox. The job-discovery filtering logic is unit-tested; the
  browser submission path is unverified against live Ashby.
- Mass auto-applying with a weak profile produces low-quality applications
  that cost you reputation and waste recruiters' time. Keep the profile
  sharp, keep the daily cap low, read the log.

## Install

```bash
cd ashby-autoapply-mcp
pip install -e .
python -m playwright install        # one-time
```

## Configure

```bash
mkdir -p ~/.ashby-mcp
cp profile.example.json   ~/.ashby-mcp/profile.json     # then fill every FILL_ME
cp companies.example.json ~/.ashby-mcp/companies.json   # then edit the slugs
```

`profile.json` needs at minimum `full_name`, `email`, and a real
`resume_path` (absolute path to your CV file). `target_titles`, `keywords`,
`locations`, `remote_only` drive discovery; `default_answers` pre-fill common
screening questions.

## Start Chrome with remote debugging

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir="$HOME/.linkedin-bot-chrome"
# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.linkedin-bot-chrome"
```
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 --user-data-dir="$env:USERPROFILE\.linkedin-bot-chrome"
```

(Reusing the same debug profile as the LinkedIn server is fine — both attach
to port 9222.)

## Connect to Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```jsonc
{
  "mcpServers": {
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

If the console script isn't on PATH, use
`"command": "/abs/path/to/python", "args": ["-m", "ashby_autoapply_mcp"]`.

## Tools

| Tool | What it does |
|---|---|
| `ashby_status` | Checks Chrome + profile.json + résumé + companies. Call first. |
| `verify_companies` | Pings each board's API; reports valid vs bad slugs. |
| `find_jobs` | Filters Ashby boards by your profile; returns matches to choose from. |
| `get_job` | One posting's full description so you can decide. |
| `auto_apply` | Fills + uploads résumé + submits (when complete). Asks on unknowns. |
| `application_log` | Audit trail + today's count vs cap. |

`auto_apply` returns `needs_user_input` with the exact `questions` it
couldn't answer. Claude asks you, then calls `auto_apply` again with
`extra_answers={question: answer}`. Submission only happens with everything
filled (`ASHBY_MCP_AUTOSUBMIT=1`, your choice) or `confirm=true`.

### Env vars

| Var | Default | Meaning |
|---|---|---|
| `ASHBY_MCP_CDP_URL` | `http://127.0.0.1:9222` | Your debug Chrome endpoint |
| `ASHBY_MCP_AUTOSUBMIT` | `1` | Submit when complete; set `0` to require confirm |
| `ASHBY_MCP_DAILY_CAP` | `15` | Max submitted applications per day |
| `ASHBY_MCP_DIR` | `~/.ashby-mcp` | Config/log directory |
| `ASHBY_MCP_PROFILE` / `_COMPANIES` / `_LOG` | under the dir above | Override paths |
| `ASHBY_MCP_MIN_DELAY` / `_MAX_DELAY` | `5` / `12` | Seconds to wait after a submit |
