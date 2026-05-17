"""Background MC hint runs for Streamlit (thread + cancel on input change)."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Callable

READING_FP_KEYS: tuple[str, ...] = (
    "map_id", "hero", "warehouse_cells", "total_item_count",
    "wg_cells", "white_cells", "white_count", "green_cells", "green_count",
    "blue_cells", "blue_count",
    "purple_cells", "purple_count", "purple_value", "purple_avg_value",
    "purple_huge_band", "purple_avg_raw",
    "gold_cells", "gold_count", "gold_value", "gold_avg_value",
    "gold_huge_band", "gold_avg_raw",
    "red_cells_total", "red_value_lo", "red_value_hi", "red_huge_band",
    "red_confirmed_none", "small_warehouse_confirmed",
)


def inference_fingerprint(
    state: dict[str, Any],
    mc: dict[str, Any],
    *,
    seed_stable: bool = True,
) -> str:
    """Fingerprint for cancel/stale detection.

    When ``seed_stable`` is False, ``seed`` is omitted so an unlocked random
  seed does not cancel background MC on every Streamlit rerun.
    """
    payload = {k: state.get(k) for k in READING_FP_KEYS}
    mc_payload = dict(mc)
    if not seed_stable:
        mc_payload.pop("seed", None)
    payload["_mc"] = mc_payload
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def start_background_hint(
    *,
    state: dict[str, Any],
    mc: dict[str, Any],
    compute_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None],
    mc_fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start a daemon thread; returns the shared result box dict."""
    fp_mc = mc_fingerprint if mc_fingerprint is not None else mc
    fp = inference_fingerprint(state, fp_mc)

    box: dict[str, Any] = {
        "status": "running",
        "fp": fp,
        "gen": 0,
        "result": None,
        "error": None,
    }
    cancel = threading.Event()
    box["cancel"] = cancel

    state_snap = dict(state)

    def _worker() -> None:
        try:
            if cancel.is_set():
                box["status"] = "cancelled"
                return
            result = compute_fn(state_snap, mc)
            if cancel.is_set():
                box["status"] = "cancelled"
                return
            box["result"] = result
            box["status"] = "done" if result is not None else "skipped"
        except Exception as exc:  # noqa: BLE001
            box["error"] = str(exc)
            box["status"] = "error"

    threading.Thread(target=_worker, daemon=True).start()
    return box


_BOX_KEY = "_bg_infer_box"


def sync_background_hint(
    session_state: Any,
    *,
    state: dict[str, Any],
    mc: dict[str, Any],
    mc_fingerprint: dict[str, Any] | None = None,
) -> str:
    """Cancel stale runs; promote finished results. Returns status string."""
    box = session_state.get(_BOX_KEY)
    if not box:
        return "idle"

    fp_mc = mc_fingerprint if mc_fingerprint is not None else mc
    current_fp = inference_fingerprint(state, fp_mc)
    if box.get("status") == "running" and box.get("fp") != current_fp:
        cancel = box.get("cancel")
        if cancel is not None:
            cancel.set()
        box["status"] = "cancelled"
        session_state["_hint_bundle"] = None
        return "cancelled"

    if box.get("status") == "done" and box.get("fp") == current_fp:
        session_state["_hint_bundle"] = box.get("result")
        session_state[_BOX_KEY] = None
        return "done"

    if box.get("status") in ("cancelled", "error", "skipped"):
        session_state[_BOX_KEY] = None
        return str(box["status"])

    if box.get("status") == "running":
        return "running"

    return "idle"


def request_background_hint(session_state: Any) -> None:
    session_state["_request_bg_hint"] = True
