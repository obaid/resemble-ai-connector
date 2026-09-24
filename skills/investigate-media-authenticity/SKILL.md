---
name: investigate-media-authenticity
description: Investigate whether audio, images, video, documents, or social/news media are authentic using Resemble Detect Agents and deepfake Detect. Use when the user asks about deepfakes, synthetic media, provenance, Detect Agents, or Resemble authenticity checks.
---

# Investigate media authenticity (Resemble)

## When to use
- Suspected deepfake / AI-generated media
- Trust & safety triage for social posts, news clips, IDs, documents, insurance evidence
- Follow-up questions on a Detect report

## Steps
1. Call `resemble_list_detect_agents` and choose the best `uuid` (examples: `investigate_social_content`, `verify_breaking_news`, `verify_document`, `verify_evidence`, `verify_id`, `website_check`).
2. Prefer a **public HTTPS URL**. Call `resemble_run_investigation` with `agent_uuid`, `url`, and a concrete `query`.
3. If the user wants a model score rather than a managed investigation, call `resemble_create_detection` with `url` and `wait=true`. Add `intelligence=true` when narrative/fraud context is needed; `detect_watermark=true` for Resemble/SynthID watermark checks; `audio_source_tracing=true` for likely TTS origin.
4. Persist identifiers (`run_id`, detection `uuid`) so you can call `resemble_get_investigation_run` / `resemble_get_detection` later.
5. Report a short verdict: recommended action or label, confidence/score, key evidence. Offer next steps (ask Detect Intelligence, re-run with another agent).

## Guardrails
- Do not fabricate scores or agent names.
- Do not put API keys in chat.
- Local `file_path` only when the file is already on the MCP host computer.
- 402/403 usually means billing or missing Detect Agents access — tell the user plainly.
