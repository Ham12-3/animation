"""Smoke-test every MCP server in this repo.

For each server it:
  * checks the server module file exists and compiles,
  * imports the package and lists its registered MCP tools,
  * (Ashby only) exercises filter_jobs with a small fixture.

Exits non-zero on any failure. Run via `make test`.
"""

from __future__ import annotations

import asyncio
import importlib
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVERS: list[tuple[str, str]] = [
    ("linkedin-outreach-mcp", "linkedin_outreach_mcp"),
    ("ashby-autoapply-mcp", "ashby_autoapply_mcp"),
    ("mcp-server-template", "mcp_server_template"),
]


def main() -> int:
    failures: list[str] = []

    for folder, pkg in SERVERS:
        src = ROOT / folder / "src" / pkg / "server.py"
        if not src.exists():
            failures.append(f"{folder}: missing {src}")
            continue
        try:
            py_compile.compile(str(src), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{folder}: compile failed - {exc}")
            continue
        try:
            mod = importlib.import_module(pkg)
            tools = asyncio.run(mod.mcp.list_tools())
        except Exception as exc:
            failures.append(f"{folder}: import/list_tools failed - {exc}")
            continue
        print(f"  {folder:<26} tools: {[t.name for t in tools]}")

    try:
        from ashby_autoapply_mcp import filter_jobs
        sample = [{
            "title": "Backend Engineer", "location": "London, UK",
            "isRemote": False, "isListed": True, "secondaryLocations": [],
        }]
        assert filter_jobs(sample, ["Backend Engineer"], [], "London", False), \
            "expected a match"
        assert not filter_jobs(sample, ["Designer"], [], "London", False), \
            "expected no match"
        print("  ashby-autoapply-mcp        filter_jobs unit check OK")
    except Exception as exc:
        failures.append(f"filter_jobs sanity: {exc}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
