# Convenience targets for this repo's MCP servers.
#
#   make setup                          - install everything you need
#   make install                        - just the editable pip installs
#   make playwright                     - one-time browser-driver download
#   make test                           - smoke-test each server
#   make new-server NAME=your-thing     - scaffold a new MCP server folder
#   make claude-config                  - print a ready-to-paste Claude Desktop block
#   make clean                          - remove build/__pycache__ artifacts
#
# Override the interpreter with: make PY=.venv/bin/python install

PY  ?= python3
PIP := $(PY) -m pip

SERVERS := linkedin-outreach-mcp ashby-autoapply-mcp

.PHONY: help setup install playwright test new-server claude-config clean

help:
	@echo "Targets:"
	@echo "  make setup                          install all servers + playwright driver"
	@echo "  make install                        editable pip install of all real servers"
	@echo "  make playwright                     download Playwright's browser driver (one-time)"
	@echo "  make test                           compile + import + list tools for every server"
	@echo "  make new-server NAME=your-thing     scaffold a new MCP server from the template"
	@echo "  make claude-config                  print a Claude Desktop mcpServers block"
	@echo "  make clean                          remove build artifacts and __pycache__"
	@echo ""
	@echo "Override the interpreter with PY=, e.g.  make PY=.venv/bin/python install"

setup: install playwright

install:
	$(PIP) install -e ./linkedin-outreach-mcp -e ./ashby-autoapply-mcp

playwright:
	$(PY) -m playwright install

test:
	$(PY) scripts/smoke_test.py

# usage: make new-server NAME=your-thing
new-server:
	@if [ -z "$(NAME)" ]; then \
	  echo "Usage: make new-server NAME=<kebab-case-name>   (no -mcp suffix)"; exit 2; \
	fi
	@new="$(NAME)"; \
	pkg=$$(echo "$$new" | tr '-' '_')_mcp; \
	folder="$${new}-mcp"; \
	if [ -e "$$folder" ]; then echo "Refusing to overwrite existing $$folder"; exit 1; fi; \
	cp -r mcp-server-template "$$folder"; \
	mv "$$folder/src/mcp_server_template" "$$folder/src/$$pkg"; \
	find "$$folder" -type f \( -name '*.py' -o -name '*.toml' -o -name '*.md' \) \
	  -exec sed -i.bak \
	    -e "s/mcp_server_template/$$pkg/g" \
	    -e "s/mcp-server-template/$$folder/g" {} +; \
	find "$$folder" -name '*.bak' -delete; \
	$(PIP) install -e "./$$folder"; \
	echo ""; \
	echo "Created $$folder."; \
	echo "Next steps:"; \
	echo "  1. Edit $$folder/src/$$pkg/server.py - replace 'echo' with real tools."; \
	echo "  2. Update $$folder/README.md and the description in $$folder/pyproject.toml."; \
	echo "  3. Add a row to the root README.md table."; \
	echo "  4. Add to your Claude Desktop config:"; \
	echo "       \"$$new\": { \"command\": \"$$folder\" }"

claude-config:
	@echo '{'
	@echo '  "mcpServers": {'
	@echo '    "linkedin-outreach": {'
	@echo '      "command": "linkedin-outreach-mcp",'
	@echo '      "env": {'
	@echo '        "LINKEDIN_MCP_CDP_URL": "http://127.0.0.1:9222",'
	@echo '        "LINKEDIN_MCP_DAILY_MSG_CAP": "25",'
	@echo '        "LINKEDIN_MCP_WEEKLY_INVITE_CAP": "80"'
	@echo '      }'
	@echo '    },'
	@echo '    "ashby-autoapply": {'
	@echo '      "command": "ashby-autoapply-mcp",'
	@echo '      "env": {'
	@echo '        "ASHBY_MCP_CDP_URL": "http://127.0.0.1:9222",'
	@echo '        "ASHBY_MCP_DAILY_CAP": "15",'
	@echo '        "ASHBY_MCP_AUTOSUBMIT": "1"'
	@echo '      }'
	@echo '    }'
	@echo '  }'
	@echo '}'

clean:
	rm -rf build dist
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
