# Resemble AI → Grok Bot / Muse MCP Connector — Research Brief

**Researched:** 2026-09-23 (PT)  
**Sources:** https://docs.resemble.ai/llms.txt + linked `.md` pages (cached under `docs-cache/`), OpenAPI at docs site, Glama listing for `https://mcp.resemble.ai/mcp`, GitHub `resemble-ai/resemble-mcp` README  
**Audience:** Implement Muse/Grok Bot connector for Obaid (Resemble Trust Chrome extension + Resemble product)

---

## 1. Product surface map

| Surface | What it does | Auth | Base / key endpoints |
| --- | --- | --- | --- |
| **Deepfake Detection** | Async (or Prefer:wait) authenticity analysis for audio/image/video | Bearer API key | `https://app.resemble.ai/api/v2` — `POST /detect`, `GET /detect/{uuid}`, `GET /detect`, `DELETE /detect/{uuid}`, `POST /detect/batch`, `GET /detect/batch/{uuid}` |
| **Streaming Detect** | Real-time audio deepfake over WebSocket | Bearer | `wss://stream.resemble.ai` |
| **Secure Uploads** | Private media → short-lived JWT for Detect/Intelligence | Bearer | `POST /secure_uploads` → pass `media_token` |
| **Detect Agents** | 6 managed investigators; SSE run + persisted history | Bearer; plan must include Agents (`403` otherwise) | `GET /agents`, `POST /agents/{uuid}/run` (SSE), `GET /agents/{uuid}/runs`, `GET /agents/{uuid}/runs/{run_id}` |
| **Detect Intelligence (Q&A)** | NL questions on a *completed* detection | Bearer | `POST /detects/{uuid}/intelligence`, `GET /detects/{uuid}/intelligence/{question_uuid}` |
| **Intelligence (media analysis)** | Structured multimodal analysis (transcript, claims, etc.) | Bearer | Intelligence create/list/get under `/detect/intelligence*` (also flag `intelligence=true` on Detect) |
| **Audio Source Tracing** | Likely TTS/platform origin when audio labeled fake | Bearer | Nested on Detect (`audio_source_tracing=true`) + list/get tracing endpoints |
| **Identity (beta)** | Enroll person/brand; multimodal search | Bearer; preview program | `POST /identity`, `POST /identity/search`, attachments CRUD |
| **Watermarking** | Apply + detect Perth (+ SynthID aux); also `detect_watermark=true` on Detect | Bearer; watermark access required (`403`) | `POST /watermark/apply`, `GET /watermark/apply/{uuid}/result`, `POST /watermark/detect`, `GET /watermark/detect/{uuid}/result` |
| **Signal** | Fraud/abuse content scoring | Bearer; Signal plan | `POST /signal`, list/delete, custom categories, settings |
| **Text Detection** | AI-written text classifier | Bearer | `POST /text_detect`, `GET /text_detect/{uuid}` |
| **Agent Detection** *(website visitors)* | Person vs AI-agent traffic; publishable `pk_live_…` in page + API for sites/sessions/analytics | Publishable key in browser; **team API key** for management/analytics | Telemetry `…/agent_detection/telemetry`; management tools already on official remote MCP |
| **TTS / STS** | Synthesis | Bearer | **Different host:** `https://f.cluster.resemble.ai` — `/synthesize`, streaming HTTP/WS |
| **Voice clone / design / STT / enhancement / projects / clips** | Production voice pipeline | Bearer | `https://app.resemble.ai/api/v2` voices, recordings, speech-to-text, audio_enhancements, projects, clips |
| **Billing** | Plans, wallet | Bearer | `https://app.resemble.ai/billing/api/v1` |

### Auth model (all REST)

- **Header:** `Authorization: Bearer <API_KEY>`
- **Key source:** Account → API (OpenAPI notes `https://app.resemble.ai/hub/api`)
- **Scopes:** Docs do **not** expose OAuth-style scopes. Access is **one key + plan entitlements** (e.g. Detect Agents → `403`, Watermark → `403`, Signal → plan). Treat “scopes” as product entitlements, not header claims.
- Optional sync: `Prefer: wait` on Detect / watermark detect.

### Rate limits

- Default public REST: **~40 requests/second per API token**
- Documented exception: Audio Enhancement **10 req/min**
- Detect Agents consume **run allowance** (official remote MCP surfaces `free_runs_remaining` / `entitled`; public list-agents doc emphasizes plan access + billing `402`)

### Errors (common)

| HTTP | Typical meaning |
| --- | --- |
| 400 | Bad params, empty file, invalid modality, watermark bool, oversized for watermark path |
| 401 | Missing/invalid API key |
| 402 | Billing / credits |
| 403 | Product not entitled (Agents, Watermark, etc.) |
| 404 | Detect/agent/run not found |
| 422 | Missing file/url; Identity video search; Detect Intelligence before completion |

Response shape: `{ "success": true|false, "message"?: "...", "item"|"items"?: ... }`

---

## 2. Locked end-to-end agent use case (ONE)

### **Trust Media Authenticity Pipeline**

> Given suspicious media (public HTTPS URL **or** private file via Secure Upload), run Resemble Detect with provenance signals (watermark, optional audio source tracing, intelligence), poll to a terminal verdict, optionally ask Detect Intelligence follow-ups, and escalate ambiguous/high-stakes cases to a managed **Detect Agent** investigation (`investigate_social_content` or `verify_breaking_news`).

**Why this (not TTS) for Obaid**

1. Directly mirrors **Resemble Trust** Chrome extension work (page media → authenticity).
2. Docs homepage leads with Safety & Detection / Detect Agents; TTS is a separate synthesis cluster.
3. Official product MCP already prioritizes Detect/Agents/Watermark — market signal that authenticity is the agent-first surface.
4. Secure Upload + zero-retention are Trust-relevant (private user media) and **under-covered** by the public action MCP (URL-centric).
5. TTS is valuable later as a second connector; first connector should compound Trust + Detect product knowledge.

**Happy path (agent logic)**

1. If local/private file → `secure_upload` → `media_token` (1h TTL).
2. Else use public `url`.
3. `detect_create` with `intelligence=true`, `detect_watermark=true`, and for audio `audio_source_tracing=true`; prefer async + poll (or `Prefer: wait` with bounded timeout).
4. `detect_get` until `status` ∈ {`completed`,`failed`} (remember watermark child can keep parent `processing`).
5. Optional: `ask_detect_intelligence` / poll answer for user questions.
6. If score borderline, news/social context, or user asks for investigation → `list_detect_agents` → `run_detect_agent` → on timeout `get_detect_agent_run`.
7. Present: Detect `label`/`aggregated_score` (authenticity claim basis), watermark/C2PA, agent `verdict` as narrative assessment only.

---

## 3. Locked use case — implementable contract

### Env / headers

| Name | Required | Notes |
| --- | --- | --- |
| `RESEMBLE_API_KEY` | Yes | Bearer token; never ship to browser (Agent Detection uses `pk_live_…` separately) |
| `RESEMBLE_API_BASE` | No | Default `https://app.resemble.ai/api/v2` |
| `Prefer: wait` | Optional per-call | Sync Detect/watermark; still set client `max_wait` |

No documented per-endpoint API key scopes.

### Exact endpoints for the pipeline

#### A. Secure upload (private media)

- **`POST /secure_uploads`** multipart `file`
- **Response:** `{ success, token }` JWT, **expires 1 hour**, single-purpose
- **Failure:** oversized/empty → 400; auth → 401

#### B. Submit detection

- **`POST /detect`**
- **Body (exactly one source):** `url` *or* `media_token` *or* multipart `file` (≤150 MB; watermark path tighter: 25 MB audio/image, 100 MB video)
- **Useful fields:**  
  `intelligence`, `detect_watermark`, `wait_for_intelligence`, `infer_from_intelligence`, `audio_source_tracing`, `visualize`, `frame_length` (1–4), `modality` (`audio`|`video`|`all` for video), `face_only`, `use_reverse_search` (image), `use_ood_detector` (audio), `zero_retention_mode`, `callback_url`, `signal`
- **Async response:** `{ success, item: { uuid, status: "processing", ... } }`
- **With `Prefer: wait`:** terminal Detect (+ watermark if requested); intelligence may still process

**Shapes that matter (completed audio):**

```json
{
  "success": true,
  "item": {
    "uuid": "...",
    "status": "completed",
    "media_type": "audio",
    "metrics": {
      "label": "fake|real|...",
      "score": ["0.9", "..."],
      "consistency": "0.85",
      "aggregated_score": "0.80"
    },
    "watermark": { "status": "completed|failed|pending", "metrics": { "has_watermark": {}, "synthid": false } },
    "intelligence": { "uuid": "...", "status": "completed|processing|failed", "description": "..." },
    "audio_source_tracing": { "label": "resemble_ai|elevenlabs|...", "error_message": null },
    "c2pa_manifest": { "validation_state": "Valid|NotPresent|Unavailable" },
    "zero_retention_mode": false,
    "url": "...",
    "filename": "..."
  }
}
```

Image uses `image_metrics.label/score`; video uses `metrics` (audio) + `video_metrics` (visual) unless `modality` skips one.

#### C. Poll / resume

- **`GET /detect/{uuid}`** optional `?experts=true` (all completed intelligence results as array)
- **Failure:** 404 `{ success:false, message:"Detect not found" }`
- Poll while `status === "processing"`; treat watermark nested failure ≠ Detect failure

#### D. Detect Intelligence Q&A

- **`POST /detects/{uuid}/intelligence`** `{ "query": "..." }` → **202**, question `uuid`, `status: pending`
- **`GET /detects/{uuid}/intelligence/{question_uuid}`** until answer ready
- **422** if detection not completed; **404** if detect missing

#### E. Detect Agents escalation

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/agents` | Six presets; `uuid`/`preset_id` currently identical strings |
| POST | `/agents/{uuid}/run` | `multipart`: `file` **or** `url`, optional `query`, `evidence[]`, `check_urls`; **`Accept: text/event-stream`** |
| GET | `/agents/{uuid}/runs` | List |
| GET | `/agents/{uuid}/runs/{run_id}` | Full transcript after disconnect/timeout |

**Presets:** `investigate_social_content`, `review_insurance_claim`, `verify_breaking_news`, `verify_document`, `verify_evidence`, `verify_id`

**SSE events (critical):** `run_started` (`run_id`), `detect` / `tool_result` (label/score), `final_verdict` (`intelligence` may be JSON string), `done`, `error`

**Pre-stream errors:** 401 / 402 / 403 / 404 / 422 (no file/url)

**Truth rule (from official MCP + docs):** only Detect **`label`/`score`** ground authenticity claims; agent **`verdict`** is written assessment.

### Failure modes to handle in tools

1. Missing entitlement (`403` Agents/Watermark) — clear message to enable plan.
2. Billing (`402`) — stop and report.
3. Watermark size limits even with secure upload.
4. Token expiry (1h) — re-upload.
5. Long jobs / Prefer:wait client timeout — return uuid + instruct poll.
6. Intelligence still `processing` after Detect `completed`.
7. SSE client disconnect — run continues server-side; use `get_detect_agent_run`.
8. Zero retention — URLs null; do not expect re-download.
9. Probabilistic verdicts — never claim legal proof.
10. Agent Detection publishable key ≠ API key (do not confuse products).

---

## 4. Does Resemble already publish a public MCP?

**Yes — three distinct surfaces:**

| MCP | Transport | Purpose | Auth |
| --- | --- | --- | --- |
| `https://docs.resemble.ai/_mcp/server` | Docs site MCP | **Documentation** for AI clients | Docs only |
| GitHub `resemble-ai/resemble-mcp` | **stdio** (optional SSE) | Docs lookup + OpenAPI search tools (`resemble_docs_lookup`, `resemble_search`, …) | None (local docs) |
| **`https://mcp.resemble.ai/mcp`** | **Streamable HTTP** (also SSE at `/sse`) | **Actions:** Detect, Agents, watermark, text detect, Agent Detection sites/sessions, etc. Registry: `io.github.resemble-ai/resemble-mcp` | Resemble API key |

Official action MCP tools observed (Glama, ~18 tools):  
`detect_deepfake`, `get_detection`, `analyze_media`, `ask_about_detection`, `detect_watermark`, `apply_watermark`, `trace_audio_source`, `detect_ai_text`, `get_text_detection`, `list_detect_agents`, `run_detect_agent_investigation`, `get_detect_agent_run`, plus Agent Detection site/session/analytics cluster.

**Gaps vs Trust pipeline:** no first-class **secure_uploads** / `media_token` flow; no **Identity** enroll/search; Detect Agents SSE abstracted behind poll/timeout tools; Muse may still want a **curated Trust skill** even if it remotes to this server.

---

## 5. Plugin design brief (Muse / Grok Bot)

### Recommendation: transport

- **Primary: remote Streamable HTTP** (align with `mcp.resemble.ai`, Muse hosting, API key in server env — never in Chrome extension).
- **Optional stdio** only for local Obaid dev / offline docs pairing.
- **Do not** reinvent docs MCP; point coding agents at docs MCP / GitHub docs server separately.
- **Strategy:** Implement a **Trust-focused Muse connector** that either (a) proxies subset of official remote MCP + adds Secure Upload (+ Identity later), or (b) calls REST directly with the tool set below. Prefer (b) for Trust gaps; reuse official remote if Muse can multi-mount both.

### Env vars

```bash
RESEMBLE_API_KEY=...          # required
RESEMBLE_API_BASE=https://app.resemble.ai/api/v2   # optional
RESEMBLE_DEFAULT_MAX_WAIT_SECONDS=120              # optional poll budget
RESEMBLE_ENABLE_AGENTS=true                        # gate costly SSE tools
```

### Tool list (v1 — Trust pipeline only)

| Tool | When to use |
| --- | --- |
| `resemble_secure_upload` | Local/private media must reach Detect without a public URL. Returns `media_token` (1h). |
| `resemble_detect_media` | Primary authenticity check. Pass `url` or `media_token`. Enable watermark/intelligence/source-tracing flags as needed. Polls or returns uuid on timeout. |
| `resemble_get_detection` | Resume/poll after timeout; refresh intelligence/watermark children. |
| `resemble_ask_about_detection` | User asks NL questions about a **completed** detect uuid. |
| `resemble_list_detect_agents` | Before investigation; pick preset; confirm Agents entitlement. |
| `resemble_run_detect_agent` | Escalate social/news/evidence/ID cases; consumes run allowance; SSE→summary. |
| `resemble_get_detect_agent_run` | After timeout/disconnect; reload transcript by `preset_id` + `run_id`. |

**Defer to v2:** Identity search/enroll, apply_watermark, text_detect, Signal, Agent Detection site tooling, TTS.

### Skill text (when-to-use)

```text
Use Resemble Trust tools when the user wants to verify whether audio, image, or video
is AI-generated/deepfake, check Resemble/SynthID watermarks or C2PA, trace synthetic
audio sources, or run a managed Detect Agent investigation (social, news, evidence, ID).

Workflow: secure_upload (if private) → detect_media → get_detection if still processing →
ask_about_detection for follow-ups → list/run Detect Agent for high-stakes or ambiguous cases.

Do NOT use these tools for text-to-speech, voice cloning, or generic media generation.
Do NOT treat agent narrative verdicts as the sole authenticity proof — cite Detect label/score.
Never put RESEMBLE_API_KEY in web pages; Agent Detection publishable keys are a different product.
```

### Naming / UX notes

- Prefix `resemble_` for Muse multi-connector clarity.
- Default `zero_retention_mode=false`; expose flag for Trust privacy demos.
- Cap `max_wait_seconds`; always return uuid for resume.
- For Chrome extension handoff: extension does capture/upload; Muse connector does API orchestration with the same key family used server-side.

### Out of scope for v1

- WebSocket streaming detect (`wss://stream.resemble.ai`) — hard for MCP tool semantics.
- Batch zip detect.
- Billing wallet tools.
- Synthesis cluster (`f.cluster.resemble.ai`).

---

## 6. Implementation accuracy checklist

- [x] Auth = Bearer only; base `app.resemble.ai/api/v2` for Detect path  
- [x] Detect create/get paths and Prefer:wait semantics  
- [x] Secure upload → `media_token`  
- [x] Detect Agents routes + six `preset_id`s + SSE  
- [x] Detect Intelligence path uses **`/detects/`** (plural) not `/detect/`  
- [x] Rate limit baseline 40 rps  
- [x] Public action MCP exists at `https://mcp.resemble.ai/mcp`  
- [x] Locked use case = Trust authenticity pipeline (Detect-first)  
- [x] Raw docs cached in `/workspace/resemble-connector/docs-cache/`

---

## Cache index (key snippets)

| File | Topic |
| --- | --- |
| `llms.txt` | Full docs index |
| `authentication.md` | Servers + Bearer |
| `rate-limits.md` | 40 rps |
| `detect_create.md` / `api-reference_deepfake-detection_create-detection.md` | Detect request/response |
| `detect_get.md` | Poll semantics |
| `detect_secure-uploads.md` | media_token |
| `detect_agents*.md` | Agents + SSE |
| `detect_detect-intelligence_*.md` | Q&A |
| `detect_identity*.md` | Beta identity |
| `detect_watermark*.md` | Watermark API |
| `detect_agent-detection.md` | Website Agent Detection (distinct) |
| `github-resemble-mcp-README.md` | Docs-only stdio MCP |
| `openapi.json` | Path inventory |

