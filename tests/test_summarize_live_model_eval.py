from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _summary_module():
    path = ROOT / "scripts" / "summarize_live_model_eval.py"
    spec = importlib.util.spec_from_file_location("summarize_live_model_eval", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_summarize_dedupes_latest_row_by_file() -> None:
    module = _summary_module()

    summary = module.summarize(
        [
            {
                "ts": 1,
                "file": "a.json",
                "final_value": 100,
                "decision_value_p50_error": -90,
            },
            {
                "ts": 2,
                "file": "a.json",
                "final_value": 100,
                "decision_value_p50_error": -10,
            },
        ]
    )

    assert summary["raw_rows"] == 2
    assert summary["rows"] == 1
    assert summary["deduped_rows"] == 1
    assert summary["decision_value_mae"] == 10
