"""Background hint thread bookkeeping."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

_APP = Path(__file__).resolve().parents[1] / "app"
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from bg_inference import (
    inference_fingerprint,
    start_background_hint,
    sync_background_hint,
)


def _fake_state(**kw):
    base = {
        "map_id": 1001,
        "hero": "ethan",
        "warehouse_cells": 120,
        "total_item_count": 0,
        "wg_cells": 10,
        "white_cells": 0,
        "white_count": 0,
        "green_cells": 0,
        "green_count": 0,
        "blue_cells": 0,
        "blue_count": 0,
        "purple_cells": 0,
        "purple_count": 0,
        "purple_value": 0,
        "purple_avg_value": 0,
        "purple_huge_band": "",
        "purple_avg_raw": "",
        "gold_cells": 0,
        "gold_count": 0,
        "gold_value": 0,
        "gold_avg_value": 0,
        "gold_huge_band": "",
        "gold_avg_raw": "",
        "red_cells_total": 0,
        "red_value_lo": 0,
        "red_value_hi": 0,
        "red_huge_band": "",
        "red_confirmed_none": False,
        "small_warehouse_confirmed": False,
    }
    base.update(kw)
    return base


def test_sync_promotes_done_result():
    ss: dict = {}
    state = _fake_state()
    mc = {"n_trials": 10, "seed": 1, "warehouse_tol": 8, "purple_tol": 4}
    box = {
        "status": "done",
        "fp": inference_fingerprint(state, mc),
        "result": {"ok": True},
        "error": None,
    }
    ss["_bg_infer_box"] = box
    assert sync_background_hint(ss, state=state, mc=mc) == "done"
    assert ss["_hint_bundle"] == {"ok": True}
    assert ss.get("_bg_infer_box") is None


def test_sync_cancels_on_fingerprint_mismatch():
    ss: dict = {}
    state = _fake_state()
    mc = {"n_trials": 10, "seed": 1, "warehouse_tol": 8, "purple_tol": 4}
    cancel = threading.Event()
    ss["_bg_infer_box"] = {
        "status": "running",
        "fp": "stale_fp",
        "cancel": cancel,
        "result": None,
        "error": None,
    }
    assert sync_background_hint(ss, state=state, mc=mc) == "cancelled"
    assert cancel.is_set()
    assert ss.get("_bg_infer_box") is None


def test_start_background_hint_completes():
    state = _fake_state()
    mc = {"n_trials": 10, "seed": 1, "warehouse_tol": 8, "purple_tol": 4}
    box = start_background_hint(
        state=state,
        mc=mc,
        compute_fn=lambda _s, _m: {"done": 1},
    )
    ss = {"_bg_infer_box": box}
    deadline = time.time() + 5
    while time.time() < deadline:
        status = sync_background_hint(ss, state=state, mc=mc)
        if status == "done":
            break
        time.sleep(0.05)
    assert status == "done"
    assert ss["_hint_bundle"] == {"done": 1}
