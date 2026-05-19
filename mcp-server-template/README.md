# MCP server template

A minimal copy-and-rename starter for a new MCP server. Mirrors the layout of
the other servers in this repo so they all install the same way and plug into
Claude Desktop the same way.

Don't install this folder as-is — copy it first, rename, then iterate.

## What's in it

```
mcp-server-template/
├── pyproject.toml                       # installable; console script = mcp-server-template
├── requirements.txt
├── README.md
└── src/mcp_server_template/
    ├── __init__.py
    ├── __main__.py                       # python -m mcp_server_template
    └── server.py                         # FastMCP server with two example tools
```

`server.py` includes one example tool (`echo`), a `status` health-check tool,
an `INSTRUCTIONS` string given to the AI, and a `main()` console entry point.
Tool docstrings, status conventions, and a confirm-before-side-effects
pattern follow the same shape the LinkedIn and Ashby servers use.

## Make a new server from this template

From the repo root, run this with your name (kebab-case; `-mcp` will be
appended automatically):

```bash
new=your-thing                                    # e.g. github-tracker
pkg=${new//-/_}_mcp                               # python package name
folder=${new}-mcp                                 # folder + project name

cp -r mcp-server-template "$folder"
mv "$folder/src/mcp_server_template" "$folder/src/$pkg"

# rewrite identifiers in code + config (works on macOS and Linux)
find "$folder" -type f \( -name '*.py' -o -name '*.toml' -o -name '*.md' \) \
  -exec sed -i.bak \
    -e "s/mcp_server_template/$pkg/g" \
    -e "s/mcp-server-template/$folder/g" {} +
find "$folder" -name '*.bak' -delete

pip install -e "./$folder"
```

After that:

1. Edit `$folder/src/$pkg/server.py` — replace `echo` with your real tools,
   write a meaningful `INSTRUCTIONS` string, fill in `status()`.
2. Update `$folder/README.md` and the `description` field in
   `$folder/pyproject.toml`.
3. Add a row for the new server to the repo-root `README.md` index.
4. Add a block under `mcpServers` in your Claude Desktop config:

   ```jsonc
   "your-thing": {
     "command": "your-thing-mcp"
   }
   ```

   Restart Claude Desktop and talk to it.

## Conventions worth keeping

- Every tool returns a dict with a `status` field: `"ok"`, `"needs_user_input"`,
  `"ambiguous"`, `"preview"`, or `"error"`. The AI is instructed to ask the
  user (not guess) on anything other than `"ok"`/`"preview"`.
- Side-effectful tools (send, submit, delete, post) take `confirm: bool = False`
  and return a `"preview"` until called again with `confirm=true`.
- Keep an append-only CSV audit log of anything the server actually did.
- Tool docstrings are the AI's documentation — write them as instructions:
  *when* to call it, *what* it returns, *when to stop and ask the user*.
