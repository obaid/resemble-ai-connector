---
name: install-resemble-connector
description: Install or configure the Resemble AI authenticity connector for Grok Bot or Muse. Use when the user asks how to add Resemble MCP, set RESEMBLE_API_KEY, or wire this plugin into Muse/Grok Bot.
---

# Install Resemble connector

Canonical bot-facing steps live in the repo root: [instructions.md](../../instructions.md). Prefer that file over inventing a custom path.

## Human one-liner

> Add Resemble MCP so that you can investigate media authenticity by following https://github.com/obaid/resemble-ai-connector/blob/main/instructions.md

## Grok Bot (summary)

1. Get `RESEMBLE_API_KEY` (secure secret flow; Account → API at app.resemble.ai).
2. Add MCP: command `uvx`, args `--from` `git+https://github.com/obaid/resemble-ai-connector.git` `resemble-mcp`, env `RESEMBLE_API_KEY`.
3. Smoke with `resemble_list_detect_agents` (or `resemble_account`).
4. Do the user’s requested authenticity job.

Fallback if `uvx` is unavailable: remote `https://mcp.resemble.ai/mcp` with `Authorization: Bearer ${RESEMBLE_API_KEY}`.

## Muse (summary)

1. `pip install` from this git URL (or `pip install -e .` from a clone).
2. Merge `muse/mcp.stdio.example.json`; set `RESEMBLE_API_KEY`.
3. Append `muse/AGENTS.md.snippet`.
4. Restart; smoke with `resemble_list_detect_agents`.

## Variables

- `RESEMBLE_API_KEY` (required) — Bearer token
- Optional `RESEMBLE_API_BASE` — default `https://app.resemble.ai/api/v2`
