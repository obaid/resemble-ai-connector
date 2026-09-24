"""Resemble authenticity MCP server (stdio) for Grok Bot and Muse."""
from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import ResembleClient, ResembleError

mcp = FastMCP(
    "resemble-ai",
    instructions=(
        "Resemble AI media-authenticity connector. Use Detect Agents for managed "
        "investigations (social, news, documents, evidence, ID, web) and Detect for "
        "deepfake scoring of audio/image/video. Prefer public HTTPS urls. Summarize "
        "verdicts for the user; do not dump raw SSE transcripts unless asked."
    ),
)


def _ok(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def _err(exc: Exception) -> str:
    if isinstance(exc, ResembleError):
        return json.dumps(
            {"error": str(exc), "status": exc.status, "body": exc.body},
            indent=2,
            default=str,
        )
    return json.dumps({"error": str(exc)}, indent=2)


@mcp.tool()
def resemble_list_detect_agents() -> str:
    """List Resemble Detect Agents available to this API key (managed authenticity investigators)."""
    try:
        data = ResembleClient().list_detect_agents()
        items = data.get("items") or []
        slim = [
            {
                "uuid": i.get("uuid"),
                "name": i.get("name"),
                "tier": i.get("tier"),
                "description": i.get("description") or i.get("tagline"),
                "activated": i.get("activated"),
                "capabilities": i.get("capabilities"),
            }
            for i in items
        ]
        return _ok({"success": data.get("success", True), "count": len(slim), "agents": slim})
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def resemble_run_investigation(
    agent_uuid: str,
    url: str = "",
    file_path: str = "",
    query: str = "",
    check_urls: str = "",
) -> str:
    """Run a Detect Agent investigation on a public media/page URL or local file.

    Prefer url. agent_uuid comes from resemble_list_detect_agents (e.g. investigate_social_content,
    verify_breaking_news, verify_document, website_check). Optional query is the investigation objective.
    Consumes the SSE stream and returns run_id, final verdict/intelligence, and a transcript excerpt.
    """
    try:
        result = ResembleClient(timeout=300.0).run_detect_agent(
            agent_uuid,
            url=url or None,
            file_path=file_path or None,
            query=query or None,
            check_urls=check_urls or None,
        )
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def resemble_list_investigation_runs(agent_uuid: str) -> str:
    """List recent investigation runs for a Detect Agent."""
    try:
        return _ok(ResembleClient().list_detect_agent_runs(agent_uuid))
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def resemble_get_investigation_run(agent_uuid: str, run_id: str) -> str:
    """Fetch a persisted Detect Agent investigation run by run_id."""
    try:
        return _ok(ResembleClient().get_detect_agent_run(agent_uuid, run_id))
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def resemble_create_detection(
    url: str = "",
    file_path: str = "",
    wait: bool = True,
    intelligence: bool = False,
    detect_watermark: bool = False,
    audio_source_tracing: bool = False,
    use_reverse_search: bool = False,
    zero_retention_mode: bool = False,
    modality: str = "",
    face_only: bool = False,
    signal: bool = False,
    infer_from_intelligence: bool = False,
) -> str:
    """Submit a deepfake detection job for audio, image, or video.

    Provide exactly one of url (public HTTPS) or file_path. wait=True sends Prefer: wait so the
    response includes a completed verdict when possible. Optional intelligence / watermark /
    source-tracing / reverse-search flags map to the Detect API.
    """
    try:
        result = ResembleClient(timeout=300.0).create_detection(
            url=url or None,
            file_path=file_path or None,
            wait=wait,
            intelligence=intelligence,
            detect_watermark=detect_watermark,
            audio_source_tracing=audio_source_tracing,
            use_reverse_search=use_reverse_search,
            zero_retention_mode=zero_retention_mode,
            modality=modality or None,
            face_only=face_only,
            signal=signal,
            infer_from_intelligence=infer_from_intelligence,
        )
        return _ok(result)
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def resemble_get_detection(uuid: str, experts: bool = False) -> str:
    """Get a deepfake detection result by UUID. Set experts=true for all completed Intelligence results."""
    try:
        return _ok(ResembleClient().get_detection(uuid, experts=experts))
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def resemble_ask_detection_question(detect_uuid: str, question: str) -> str:
    """Ask a natural-language question about a completed Detect report (Detect Intelligence)."""
    try:
        return _ok(ResembleClient().ask_detect_intelligence(detect_uuid, question))
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def resemble_get_detection_answer(detect_uuid: str, question_uuid: str) -> str:
    """Poll the answer for a Detect Intelligence question."""
    try:
        return _ok(ResembleClient().get_detect_intelligence_answer(detect_uuid, question_uuid))
    except Exception as exc:
        return _err(exc)




@mcp.tool()
def resemble_secure_upload(file_path: str) -> str:
    """Upload private media to Resemble and return a short-lived media_token (1 hour) for Detect."""
    try:
        return _ok(ResembleClient().secure_upload(file_path))
    except Exception as exc:
        return _err(exc)

@mcp.tool()
def resemble_account() -> str:
    """Sanity-check the API key by fetching the Resemble account profile."""
    try:
        return _ok(ResembleClient().get_account())
    except Exception as exc:
        return _err(exc)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
