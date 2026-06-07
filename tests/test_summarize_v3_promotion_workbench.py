import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_promotion_workbench.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_promotion_workbench",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_workbench_marks_stop_loss_lanes() -> None:
    module = _load_module()

    result = module.summarize_workbench(
        {
            "overall_status": "not_ready",
            "blocked_gates": 2,
            "gate_dependencies": {
                "lane_status_counts": {
                    "settlement_bridge_support": {"blocked": 1, "watch": 1},
                    "table_activity_capacity": {"watch": 1},
                },
                "blocked_or_pending_gates": [
                    {
                        "gate": "settlement_count_guarded_bridge_stability",
                        "lane": "settlement_bridge_support",
                        "status": "blocked",
                    }
                ],
                "watch_gates": [
                    {
                        "gate": "settlement_count_guarded_bridge_holdout",
                        "lane": "settlement_bridge_support",
                        "status": "watch",
                    },
                    {
                        "gate": "capacity_source_expansion_shadow",
                        "lane": "table_activity_capacity",
                        "status": "watch",
                    },
                ],
            },
        }
    )

    lanes = {row["lane"]: row for row in result["lanes"]}
    assert result["next_mode"] == "build_shadow_formal_value_workbench"
    assert lanes["settlement_bridge_support"]["verdict"] == "stop_loss"
    assert lanes["settlement_bridge_support"]["blocked_gates"] == [
        "settlement_count_guarded_bridge_stability"
    ]
    assert lanes["table_activity_capacity"]["verdict"] == "watch_only"


def test_workbench_keeps_archive_quality_as_usable_watch() -> None:
    module = _load_module()

    result = module.summarize_workbench(
        {
            "overall_status": "not_ready",
            "blocked_gates": 0,
            "gate_dependencies": {
                "lane_status_counts": {
                    "archive_pipeline_quality": {"pass": 1, "watch": 1}
                },
                "blocked_or_pending_gates": [],
                "watch_gates": [
                    {
                        "gate": "archive_data_quality",
                        "lane": "archive_pipeline_quality",
                        "status": "watch",
                    }
                ],
            },
        }
    )

    assert result["lanes"][0]["lane"] == "archive_pipeline_quality"
    assert result["lanes"][0]["verdict"] == "usable_watch"
