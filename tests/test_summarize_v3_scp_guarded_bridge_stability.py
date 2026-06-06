import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_scp_guarded_bridge_stability.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_scp_guarded_bridge_stability",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run(
    *,
    trials: int,
    seed: int,
    status: str = "watch",
    selected: dict[str, int] | None = None,
    applied_rows: int = 25,
    applied_hurts: list[str] | None = None,
) -> dict[str, object]:
    selected_counts = selected or {"2506": 2}
    return {
        "posterior_trials": trials,
        "posterior_seed": seed,
        "overall_status": status,
        "selected_group_fold_counts": selected_counts,
        "selected_group_support": [
            {
                "group": group,
                "selected_folds": selected_folds,
                "sessions": max(1, applied_rows // max(1, selected_folds)),
                "metric_rows": applied_rows,
                "candidate_rows": applied_rows,
                "applied_rows": applied_rows,
                "sample_limited_rows": 0,
            }
            for group, selected_folds in selected_counts.items()
        ],
        "candidate_only": {
            "candidate_rows": applied_rows,
            "applied_rows": applied_rows,
            "delta_formal_p50_mae": -1000,
            "delta_formal_p90_coverage": 0,
            "bridge_formal_p50_over_rate": 0.25,
        },
        "applied_hurts": applied_hurts or [],
    }


def test_guarded_bridge_stability_passes_exact_group_across_runs() -> None:
    module = _load_module()

    result = module.summarize_stability(
        [
            _run(trials=256, seed=0),
            _run(trials=256, seed=1),
            _run(trials=256, seed=7),
        ],
        required_selected_groups=("2506",),
        min_applied_rows=20,
    )

    assert result["overall_status"] == "watch"
    assert result["status_reasons"] == ["all_runs_stable"]
    assert result["watch_runs"] == 3
    assert result["stable_selected_groups"] == ["2506"]
    assert result["union_selected_groups"] == ["2506"]
    assert result["min_applied_rows"] == 25


def test_guarded_bridge_stability_blocks_hurt_run() -> None:
    module = _load_module()

    result = module.summarize_stability(
        [
            _run(trials=64, seed=0),
            _run(
                trials=64,
                seed=1,
                status="blocked_holdout_hurt",
                selected={"2501": 1, "2506": 2},
                applied_rows=62,
                applied_hurts=["2501"],
            ),
        ],
        required_selected_groups=("2506",),
        min_applied_rows=20,
    )

    assert result["overall_status"] == "blocked_applied_hurt"
    assert "applied_hurts_present" in result["status_reasons"]
    assert "selected_group_drift" in result["status_reasons"]
    assert result["hurt_group_counts"] == {"2501": 1}
    assert result["union_selected_groups"] == ["2501", "2506"]


def test_guarded_bridge_stability_blocks_low_support() -> None:
    module = _load_module()

    result = module.summarize_stability(
        [
            _run(trials=256, seed=0, applied_rows=9),
            _run(trials=256, seed=1, applied_rows=9),
            _run(trials=256, seed=7, applied_rows=9),
        ],
        required_selected_groups=("2506",),
        min_applied_rows=20,
    )

    assert result["overall_status"] == "blocked_low_support"
    assert result["status_reasons"] == ["low_applied_rows"]
    assert result["min_applied_rows"] == 9
    assert result["max_applied_rows"] == 9
    assert result["selected_group_support_gap"] == [
        {
            "group": "2506",
            "run_count": 3,
            "required_applied_rows": 20,
            "min_applied_rows": 9,
            "max_applied_rows": 9,
            "min_applied_gap": 11,
            "min_candidate_rows": 9,
            "min_metric_rows": 9,
            "min_sessions": 4,
            "runs": [
                {
                    "posterior_trials": 256,
                    "posterior_seed": 0,
                    "selected_folds": 2,
                    "sessions": 4,
                    "metric_rows": 9,
                    "candidate_rows": 9,
                    "applied_rows": 9,
                },
                {
                    "posterior_trials": 256,
                    "posterior_seed": 1,
                    "selected_folds": 2,
                    "sessions": 4,
                    "metric_rows": 9,
                    "candidate_rows": 9,
                    "applied_rows": 9,
                },
                {
                    "posterior_trials": 256,
                    "posterior_seed": 7,
                    "selected_folds": 2,
                    "sessions": 4,
                    "metric_rows": 9,
                    "candidate_rows": 9,
                    "applied_rows": 9,
                },
            ],
        }
    ]
