# resemble-ai-connector

Agent Plugin + MCP server for **Resemble AI media authenticity**. Works with **Grok Bot** (Cursor Agent Plugins) and **Muse** (stdio MCP).

## Use case

Give an assistant a complete authenticity workflow:

1. List managed **Detect Agents** (social, news, documents, evidence, ID, web).
2. Run an investigation against a public URL (SSE stream → verdict + `run_id`).
3. Optionally submit a **deepfake Detect** job for audio/image/video scores, watermark, source tracing, or intelligence.
4. Ask follow-up questions on a Detect report.

Docs: [docs.resemble.ai](https://docs.resemble.ai) · Auth: `Authorization: Bearer <API_KEY>` against `https://app.resemble.ai/api/v2`.

## Tools

| Tool | Purpose |
| --- | --- |
| `resemble_list_detect_agents` | List Detect Agents |
| `resemble_run_investigation` | Run agent on `url` or `file_path` |
| `resemble_list_investigation_runs` | Recent runs for an agent |
| `resemble_get_investigation_run` | Persisted run detail |
| `resemble_create_detection` | Deepfake Detect job |
| `resemble_get_detection` | Poll Detect result |
| `resemble_ask_detection_question` | Detect Intelligence Q&A |
| `resemble_get_detection_answer` | Poll Intelligence answer |
| `resemble_account` | API key sanity check |

## Install (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export RESEMBLE_API_KEY=...
resemble-mcp   # stdio MCP
```

Smoke test (no MCP host required):

```bash
python scripts/smoke_test.py
```

## MCP transports

| Host | Recommended config |
| --- | --- |
| **Grok Bot** | `mcp.json` → official Streamable HTTP `https://mcp.resemble.ai/mcp` with `Authorization: Bearer ${RESEMBLE_API_KEY}` |
| **Muse / local** | Install this package and use `mcp.stdio.json` (`resemble-mcp`) for Trust extras including `resemble_secure_upload` |

This repo’s stdio server implements the Trust authenticity workflow (Detect Agents + Detect + secure upload) against the public REST API. Grok Bot can also use Resemble’s hosted action MCP at the same API key.

## Grok Bot

This repo is an **Agent Plugins** package (`plugin.json` + `mcp.json` + `skills/`).

1. Set `RESEMBLE_API_KEY` under Plugins → Configure (or pass env when adding a custom server).
2. Install from marketplace after publish, **or** ask Grok Bot to add a custom stdio server using `mcp.json`.
3. Submit path for marketplace: https://cursor.com/marketplace/publish

`localhost` URLs on your laptop are not reachable from Grok Bot. Prefer `uvx --from git+… resemble-mcp` or install on the bot computer.

## Muse

1. `pip install -e .` into Muse’s environment.
2. Wire stdio MCP from `muse/mcp.stdio.example.json`.
3. Append `muse/AGENTS.md.snippet` to agent instructions.
4. Restart Muse / host and call `resemble_list_detect_agents`.

## Security

- Never commit `.env` or real keys.
- Prefer public HTTPS media URLs; use `zero_retention_mode` when Detect must not retain uploads.

## License

MIT
