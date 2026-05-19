#!/usr/bin/env python3
"""MCP server template - replace this docstring and the tools below.

This is a copy-and-rename starter. See README.md for the rename steps. The
sibling servers (linkedin-outreach-mcp, ashby-autoapply-mcp) are good
references for shape and conventions.

Conventions worth keeping:
  * Every tool returns a dict with a `status` field whose value is one of
    "ok" / "needs_user_input" / "ambiguous" / "preview" / "error". The
    instructions string below tells the AI to ask the user (not guess) on
    any status other than "ok"/"preview".
  * Side-effectful tools (sending, submitting, deleting) take a `confirm`
    argument and default to a preview so the AI surfaces a check to the user.
  * Keep an append-only CSV audit log of anything the server does.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

INSTRUCTIONS = """\
This server does <one-line description of what it does>.

Workflow you should follow:
1. Call status() first. If it isn't ready, tell the user the exact steps to
   fix and stop.
2. Call <discovery tool> with the user's criteria. Show the results; let the
   user pick. Never invent items.
3. For side-effectful actions, call the tool once WITHOUT confirm to preview
   what it will do, show the user, get explicit approval, then call again
   with confirm=true.

If any tool returns status "needs_user_input"/"ambiguous"/"error", do not
guess or retry blindly. Ask the user a clear question and wait.
"""

mcp = FastMCP("mcp-server-template", instructions=INSTRUCTIONS)


@mcp.tool()
async def status() -> dict[str, Any]:
    """Report whether the server has everything it needs to operate.

    Always call this first. Return any missing config / connections in
    `problems` so the AI can tell the user exactly what to fix.
    """
    problems: list[str] = []
    # TODO: check config files, external connections, credentials, etc.
    return {"status": "ready" if not problems else "not_ready", "problems": problems}


@mcp.tool()
async def echo(message: str) -> dict[str, Any]:
    """Example tool - replace with a real one.

    Each tool's docstring is the description the AI sees. Make it
    instructive: when to call it, what it returns, when to stop and ask
    the user instead.
    """
    return {"status": "ok", "echo": message}


def main() -> None:
    """Console entry point: run the server over stdio (for MCP clients)."""
    mcp.run()


if __name__ == "__main__":
    main()
