---
name: install-resemble-connector
description: Install or configure the Resemble AI authenticity connector for Grok Bot or Muse. Use when the user asks how to add Resemble MCP, set RESEMBLE_API_KEY, or wire this plugin into Muse/Grok Bot.
---

# Install Resemble connector

## Grok Bot
1. Ensure `RESEMBLE_API_KEY` is available (Account → API at app.resemble.ai).
2. Install this Agent Plugin from the marketplace once published, **or** ask the bot: add a custom MCP server `resemble-ai` with command `uvx` and args from `mcp.json`, env `RESEMBLE_API_KEY`.
3. For a local checkout on the bot computer: `pip install -e .` then command `resemble-mcp` (or `python -m resemble_mcp` with `PYTHONPATH=server`).
4. Confirm with `resemble_account` or `resemble_list_detect_agents`.

## Muse
1. Install the package into Muse's Python env: `pip install -e .`
2. Merge `muse/mcp.stdio.example.json` into Muse's MCP config (or run `muse-mcp-config` equivalents for your host), setting `RESEMBLE_API_KEY`.
3. Append `muse/AGENTS.md.snippet` to project agent instructions so Muse knows when to call Resemble tools.
4. Restart the host; smoke with `resemble_list_detect_agents`.

## Variables
- `RESEMBLE_API_KEY` (required) — Bearer token
- Optional `RESEMBLE_API_BASE` — default `https://app.resemble.ai/api/v2`
