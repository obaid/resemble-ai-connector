#!/usr/bin/env python3
"""Live smoke test against Resemble API (requires RESEMBLE_API_KEY)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from resemble_mcp.client import ResembleClient, ResembleError  # noqa: E402


def main() -> int:
    if not os.environ.get("RESEMBLE_API_KEY"):
        print("FAIL: RESEMBLE_API_KEY not set", file=sys.stderr)
        return 2
    client = ResembleClient(timeout=180.0)
    print("== account ==")
    acct = client.get_account()
    print(json.dumps({"success": acct.get("success"), "keys": list(acct.keys())[:8]}, indent=2))

    print("== list detect agents ==")
    agents = client.list_detect_agents()
    items = agents.get("items") or []
    print(f"count={agents.get('count')} n={len(items)}")
    assert items, "expected at least one Detect Agent"
    for i in items:
        print(f"- {i.get('uuid')}: {i.get('name')}")

    # Cheap Detect: public sample image URL (small)
    sample = os.environ.get(
        "RESEMBLE_SMOKE_URL",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    )
    print(f"== create_detection wait url={sample} ==")
    try:
        det = client.create_detection(url=sample, wait=True, intelligence=False)
        item = det.get("item") or {}
        print(
            json.dumps(
                {
                    "success": det.get("success"),
                    "uuid": item.get("uuid"),
                    "status": item.get("status"),
                    "media_type": item.get("media_type"),
                    "image_label": (item.get("image_metrics") or {}).get("label"),
                    "audio_label": (item.get("metrics") or {}).get("label"),
                },
                indent=2,
            )
        )
        assert det.get("success") is True
        assert item.get("uuid")
    except ResembleError as exc:
        print(f"Detect smoke skipped/failed: {exc}")
        if exc.status in {402, 403}:
            print("Continuing because agents list succeeded (billing/access).")
        else:
            raise

    print("SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
