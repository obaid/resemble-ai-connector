"""Thin HTTP client for Resemble Detect + Detect Agents APIs."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

API_BASE = os.environ.get("RESEMBLE_API_BASE", "https://app.resemble.ai/api/v2").rstrip("/")


class ResembleError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class ResembleClient:
    def __init__(self, api_key: str | None = None, *, timeout: float = 120.0):
        key = api_key or os.environ.get("RESEMBLE_API_KEY") or os.environ.get("RESEMBLE_TOKEN")
        if not key:
            raise ResembleError(
                "Missing RESEMBLE_API_KEY. Set it in the MCP server env or Plugins → Configure."
            )
        self._headers = {"Authorization": f"Bearer {key}"}
        self._timeout = timeout

    def _raise(self, resp: httpx.Response) -> None:
        try:
            body: Any = resp.json()
        except Exception:
            body = resp.text
        msg = None
        if isinstance(body, dict):
            msg = body.get("message") or body.get("error") or body.get("errors")
        raise ResembleError(
            f"Resemble API {resp.status_code}: {msg or resp.text[:500]}",
            status=resp.status_code,
            body=body,
        )

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{API_BASE}{path}", headers=self._headers, params=params)
            if resp.status_code >= 400:
                self._raise(resp)
            return resp.json()

    def post_json(self, path: str, payload: dict[str, Any], *, prefer_wait: bool = False) -> Any:
        headers = dict(self._headers)
        headers["Content-Type"] = "application/json"
        if prefer_wait:
            headers["Prefer"] = "wait"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(f"{API_BASE}{path}", headers=headers, json=payload)
            if resp.status_code >= 400:
                self._raise(resp)
            return resp.json()

    def post_multipart(
        self,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        prefer_wait: bool = False,
        stream: bool = False,
    ) -> Any:
        headers = dict(self._headers)
        if prefer_wait:
            headers["Prefer"] = "wait"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{API_BASE}{path}",
                headers=headers,
                data=data or {},
                files=files,
            )
            if resp.status_code >= 400:
                self._raise(resp)
            if stream:
                return resp.text
            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                return resp.json()
            return resp.text

    def list_detect_agents(self) -> Any:
        return self.get_json("/agents")

    def list_detect_agent_runs(self, agent_uuid: str) -> Any:
        return self.get_json(f"/agents/{agent_uuid}/runs")

    def get_detect_agent_run(self, agent_uuid: str, run_id: str) -> Any:
        return self.get_json(f"/agents/{agent_uuid}/runs/{run_id}")

    def run_detect_agent(
        self,
        agent_uuid: str,
        *,
        url: str | None = None,
        file_path: str | None = None,
        query: str | None = None,
        check_urls: str | None = None,
        max_sse_chars: int = 120_000,
    ) -> dict[str, Any]:
        if bool(url) == bool(file_path):
            raise ResembleError("Provide exactly one of url or file_path.")
        data: dict[str, Any] = {}
        if url:
            data["url"] = url
        if query:
            data["query"] = query
        if check_urls:
            data["check_urls"] = check_urls
        files = None
        file_handle = None
        try:
            if file_path:
                p = Path(file_path).expanduser().resolve()
                if not p.is_file():
                    raise ResembleError(f"file_path not found: {p}")
                file_handle = p.open("rb")
                files = {"file": (p.name, file_handle)}
            raw = self.post_multipart(
                f"/agents/{agent_uuid}/run",
                data=data,
                files=files,
                stream=True,
            )
        finally:
            if file_handle is not None:
                file_handle.close()

        events = parse_sse(raw if isinstance(raw, str) else str(raw))
        run_id = None
        final_verdict = None
        tokens: list[str] = []
        errors: list[Any] = []
        for ev in events:
            et = ev.get("type")
            if et == "run_started":
                run_id = ev.get("run_id")
            elif et == "token" and ev.get("text"):
                tokens.append(str(ev["text"]))
            elif et == "final_verdict":
                final_verdict = ev
            elif et in {"error", "failed"}:
                errors.append(ev)
        transcript = "".join(tokens)
        if len(transcript) > max_sse_chars:
            transcript = transcript[:max_sse_chars] + "…[truncated]"
        intelligence = None
        if isinstance(final_verdict, dict) and final_verdict.get("intelligence"):
            intel = final_verdict["intelligence"]
            if isinstance(intel, str):
                try:
                    intelligence = json.loads(intel)
                except json.JSONDecodeError:
                    intelligence = intel
            else:
                intelligence = intel
        return {
            "run_id": run_id,
            "agent_uuid": agent_uuid,
            "final_verdict": final_verdict,
            "intelligence": intelligence,
            "transcript_excerpt": transcript,
            "errors": errors,
            "event_count": len(events),
        }

    def create_detection(
        self,
        *,
        url: str | None = None,
        file_path: str | None = None,
        wait: bool = True,
        intelligence: bool = False,
        detect_watermark: bool = False,
        audio_source_tracing: bool = False,
        use_reverse_search: bool = False,
        zero_retention_mode: bool = False,
        modality: str | None = None,
        face_only: bool = False,
        signal: bool = False,
        infer_from_intelligence: bool = False,
    ) -> Any:
        if bool(url) == bool(file_path):
            raise ResembleError("Provide exactly one of url or file_path.")
        flags = {
            "intelligence": intelligence,
            "detect_watermark": detect_watermark,
            "audio_source_tracing": audio_source_tracing,
            "use_reverse_search": use_reverse_search,
            "zero_retention_mode": zero_retention_mode,
            "face_only": face_only,
            "signal": signal,
            "infer_from_intelligence": infer_from_intelligence,
        }
        # Only send true flags / non-empty modality — false booleans can confuse validation.
        payload: dict[str, Any] = {k: True for k, v in flags.items() if v}
        if modality:
            payload["modality"] = modality
        if url:
            payload["url"] = url
            return self.post_json("/detect", payload, prefer_wait=wait)
        p = Path(file_path).expanduser().resolve()  # type: ignore[arg-type]
        if not p.is_file():
            raise ResembleError(f"file_path not found: {p}")
        data = {k: ("true" if v is True else v) for k, v in payload.items()}
        with p.open("rb") as fh:
            return self.post_multipart(
                "/detect",
                data=data,
                files={"file": (p.name, fh)},
                prefer_wait=wait,
            )

    def get_detection(self, uuid: str, *, experts: bool = False) -> Any:
        params = {"experts": "true"} if experts else None
        return self.get_json(f"/detect/{uuid}", params=params)

    def ask_detect_intelligence(self, detect_uuid: str, question: str) -> Any:
        return self.post_json(
            f"/detects/{detect_uuid}/intelligence",
            {"query": question},
        )

    def get_detect_intelligence_answer(self, detect_uuid: str, question_uuid: str) -> Any:
        return self.get_json(f"/detects/{detect_uuid}/intelligence/{question_uuid}")


    def secure_upload(self, file_path: str) -> Any:
        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            raise ResembleError(f"file_path not found: {p}")
        with p.open("rb") as fh:
            return self.post_multipart(
                "/secure_uploads",
                files={"file": (p.name, fh)},
            )

    def get_account(self) -> Any:
        return self.get_json("/account")


def parse_sse(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in raw.split("\n\n"):
        data_lines = []
        for line in block.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        blob = "\n".join(data_lines).strip()
        if not blob or blob == "[DONE]":
            continue
        try:
            events.append(json.loads(blob))
        except json.JSONDecodeError:
            events.append({"type": "raw", "text": blob})
    return events
