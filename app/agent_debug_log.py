"""NDJSON debug logger for agent instrumentation (session 834063)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

_LOG = Path(__file__).resolve().parent.parent.parent / "debug-834063.log"
_SESSION = "834063"
_ENABLED = os.environ.get("BIDKING_AGENT_DEBUG", "").strip().lower() in (
    "1", "true", "yes",
)


def agent_debug_log(
    *,
    location: str,
    message: str,
    data: dict | None = None,
    hypothesis_id: str = "",
    run_id: str = "pre-fix",
) -> None:
    if not _ENABLED:
        return
    # #region agent log
    try:
        payload = {
            "sessionId": _SESSION,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with _LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion
