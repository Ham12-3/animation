# MCP servers

This repository holds MCP servers, each self-contained in its own folder so
they can be installed and run independently.

| Folder | What it is |
|---|---|
| [`linkedin-outreach-mcp/`](linkedin-outreach-mcp/) | **LinkedIn Outreach MCP** — lets Claude search LinkedIn and send DMs / noted connection requests by driving your own logged-in Chrome, with a human-in-the-loop preview. |
| [`ashby-autoapply-mcp/`](ashby-autoapply-mcp/) | **Ashby Auto-Apply MCP** — finds jobs on Ashby company boards (public posting API) and auto-applies in your own logged-in Chrome from a `profile.json` you control; asks you about anything it can't answer. |

Each server is self-contained (its own `pyproject.toml` / `README.md`) and
attaches to the same debugged Chrome (port 9222). Add new MCP servers as
sibling folders here.
