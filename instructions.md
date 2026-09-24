# Install Resemble authenticity MCP (for Grok Bot / Muse)

**Audience:** another Grok Bot or Muse agent. A human will paste a short ask plus this URL. Follow these steps exactly; do not invent alternate install paths.

## One-line human ask (copy this)

> Add Resemble MCP so that you can investigate media authenticity by following https://github.com/obaid/resemble-ai-connector/blob/main/instructions.md

Replace “investigate media authenticity” with any concrete job (deepfake Detect, social investigation, etc.).

---

## What this connector does

Trust / media authenticity against Resemble’s API:

- List and run **Detect Agents** (social, news, documents, evidence, ID, web)
- **Deepfake Detect** on audio / image / video URLs
- Optional Detect Intelligence Q&A and secure upload

Repo: https://github.com/obaid/resemble-ai-connector

---

## Grok Bot — install steps (do these in order)

### 1. Check if already connected

Call your MCP status / plugin tools. If a server named `resemble-ai` (or tools starting with `resemble_`) is already available and authenticated, **skip to step 4**.

### 2. Get the API key

You need `RESEMBLE_API_KEY` (Bearer token from https://app.resemble.ai → Account → API).

- If the human did not give a key, ask once for it using your secure secret / credential flow (never ask them to paste a key into chat if you have a masked secret input).
- Do not invent or reuse another product’s key.

### 3. Add the MCP server

Prefer the **Trust tool pack** from this repo (stdio via `uvx`):

| Field | Value |
| --- | --- |
| name | `resemble-ai` |
| command | `uvx` |
| args | `--from` `git+https://github.com/obaid/resemble-ai-connector.git` `resemble-mcp` |
| env | `RESEMBLE_API_KEY` = the user’s key |

Confirm with the user only if your host requires an install confirmation UI; then call your add-MCP tool with those exact values.

**Fallback (official hosted MCP only):** if `uvx` cannot run on this host, add a remote server instead:

| Field | Value |
| --- | --- |
| name | `resemble-ai` |
| url | `https://mcp.resemble.ai/mcp` |
| headers | `Authorization: Bearer <RESEMBLE_API_KEY>` |

Note: the hosted MCP is Resemble’s public action server. Prefer `uvx` when available so Trust helpers from this repo (including secure upload) are present.

### 4. Smoke-check

Call, in order:

1. `resemble_account` **or** `resemble_list_detect_agents`
2. Tell the human it worked in one short sentence (e.g. how many Detect Agents you see).

If auth fails, ask them to regenerate the key at Account → API and retry step 3.

### 5. Then do the job they asked for

After the smoke-check, perform the capability from their sentence (the “so that you can ______” part). Prefer this workflow:

1. `resemble_list_detect_agents` — pick the matching agent when the task is an investigation.
2. `resemble_run_investigation` with a public HTTPS `url` and a clear `query`, **or**
3. `resemble_create_detection` with `url` and `wait=true` for raw deepfake scores.
4. Summarize label / recommended action / confidence. Do not invent scores.

Prefer public HTTPS media URLs. Do not upload private media unless the user asks.

---

## Muse — install steps

1. `pip install "resemble-ai-connector @ git+https://github.com/obaid/resemble-ai-connector.git"` (or clone + `pip install -e .`).
2. Merge [muse/mcp.stdio.example.json](muse/mcp.stdio.example.json) into Muse’s MCP config; set `RESEMBLE_API_KEY`.
3. Append [muse/AGENTS.md.snippet](muse/AGENTS.md.snippet) to agent instructions.
4. Restart Muse; call `resemble_list_detect_agents`; then do the user’s job.

---

## Manual CLI smoke (optional, humans)

```bash
git clone https://github.com/obaid/resemble-ai-connector.git
cd resemble-ai-connector
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
export RESEMBLE_API_KEY=...
python scripts/smoke_test.py   # expect SMOKE_OK
```

---

## Do not

- Do not open `github.com/xai-org/plugin-marketplace`.
- Do not embed the API key in a URL or commit it.
- Do not tell the user to dig through raw `mcp.json` args unless your host has no add-MCP tool.
