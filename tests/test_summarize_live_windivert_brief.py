from __future__ import annotations

import json
from types import SimpleNamespace

import scripts.summarize_live_windivert_brief as module
from scripts.summarize_live_windivert_brief import summarize


def test_summarize_live_windivert_brief_groups_by_round() -> None:
    rows = [
        {
            "ts": 1,
            "source": "windivert",
            "file": "windivert_live.json",
            "hero": "ethan",
            "map_id": 2401,
            "round": 1,
            "action_round": 2,
            "posterior_samples": 0,
            "posterior_total_samples": 20,
            "final_decision_value": 300_000,
            "decision_value_p90": 250_000,
            "decision_value_p50_error": -100_000,
            "final_q6_value": 180_000,
            "final_q6_decision_value": 180_000,
            "v2_q6_decision_value_p90": 120_000,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_space_pressure_p90": 0.2,
            "v2_q6_space_overflow_rate": 0,
            "q6_top_size_band": "q6_top_large",
            "random_sample_avg_signal_values": "n=3:avg=124892.00",
            "public_constraint_key": "max_quality",
            "evidence_profile_key": "public:random_avg+layout",
            "information_density_band": "low",
            "shape_target_count": 1,
            "category_target_count": 1,
            "category_exclusion_count": 0,
            "anchor_count": 1,
            "posterior_diagnostics": (
                "public_random_sample_value_floor:355942;"
                "public_random_sample_value_floor_mode:hard:pass=3/7:min=3"
            ),
            "q6_residual_boost_shadow_active": True,
            "q6_residual_boost_shadow_covered_after": True,
            "warehouse_p50_error": -45,
            "monitor_n_trials": 20,
        },
        {
            "ts": 2,
            "source": "windivert",
            "file": "windivert_live.json",
            "hero": "gabriela",
            "map_id": 2501,
            "round": 4,
            "action_round": 4,
            "posterior_samples": 10,
            "final_decision_value": 320_000,
            "decision_value_p90": 400_000,
            "decision_value_p50_error": 20_000,
            "final_q6_value": 0,
            "warehouse_p50_error": 8,
            "inference_profile": {"n_trials": 10},
            "size_bucket_active": True,
        },
    ]
    summary = summarize(rows)
    assert summary["total_rows"] == 2
    assert summary["source_counts"] == {"windivert": 2}
    assert summary["by_observed_round"]["R1"]["rows"] == 1
    assert summary["by_action_round"]["R2"]["rows"] == 1
    assert summary["by_action_round"]["R2"]["p50_under_rate"] == 1.0
    assert summary["by_action_round"]["R2"]["p90_coverage"] == 0.0
    assert summary["by_action_round"]["R2"]["median_n_trials"] == 20
    assert summary["by_round"]["R4+"]["median_matched"] == 10
    assert summary["by_q6_truth"]["q6>0"]["rows"] == 1
    assert summary["by_q6_truth"]["q6=0"]["rows"] == 1
    assert summary["by_random_avg"]["signal"]["rows"] == 1
    assert summary["by_random_avg"]["none"]["rows"] == 1
    assert summary["by_random_floor_mode"]["hard"]["rows"] == 1
    assert summary["by_random_floor_mode"]["none"]["rows"] == 1
    assert summary["by_q6_shadow"]["covered"]["rows"] == 1
    assert summary["by_q6_shadow"]["none"]["rows"] == 1
    assert summary["by_warehouse_error"]["under<-20"]["rows"] == 1
    assert summary["by_warehouse_error"]["within±20"]["rows"] == 1
    assert summary["by_primary_error"]["q6_tail_value"]["rows"] == 1
    assert summary["by_primary_error"]["p90_covered"]["rows"] == 1
    assert summary["by_diagnostic_tag"]["q6_truth"]["rows"] == 1
    assert summary["by_diagnostic_tag"]["random_avg_signal"]["rows"] == 1
    assert summary["by_diagnostic_tag"]["warehouse_under<-20"]["rows"] == 1
    assert summary["by_hero"]["ethan"]["rows"] == 1
    assert summary["by_evidence_profile"]["public:random_avg+layout"]["rows"] == 1
    assert summary["by_public_constraint"]["max_quality"]["rows"] == 1
    assert summary["by_information_density"]["low"]["rows"] == 1
    assert summary["by_constraint_density"]["medium_3_5"]["rows"] == 1
    assert summary["by_sample_space"]["zero_match"]["rows"] == 1
    assert summary["by_space_pressure"]["low_space_pressure"]["rows"] == 1
    assert summary["by_tail"]["q6_top_large"]["rows"] == 1
    assert summary["top_p90_misses"][0]["primary_error"] == "q6_tail_value"


def test_summarize_live_windivert_brief_json_roundtrip() -> None:
    summary = summarize([])
    payload = json.loads(json.dumps(summary))
    assert payload["total_rows"] == 0


def test_load_archive_rows_replays_recent_complete_archive(
    tmp_path,
    monkeypatch,
) -> None:
    archive = tmp_path / "archive" / "complete"
    archive.mkdir(parents=True)
    capture = archive / "windivert_2026-06-04_complete_ethan_2401_session.json"
    capture.write_text("[]\n", encoding="utf-8")

    monkeypatch.setattr(module, "load_monitor_tables", lambda: "tables")

    def fake_build(path, **kwargs):
        assert path == capture
        assert kwargs["tables"] == "tables"
        assert kwargs["n_trials"] == 10
        assert kwargs["roi_trials"] == 0
        assert kwargs["shadow_trials"] == 1
        assert kwargs["run_debug_shadows"] is False
        return {
            "session_id": "2401:session",
            "model_eval": {
                "file": str(path.name),
                "round": 3,
                "action_round": 3,
                "decision_value_p50_error": -42,
                "monitor_n_trials": 10,
            },
        }

    monkeypatch.setattr(module, "build_monitor_artifact_from_file", fake_build)

    rows = module._load_archive_rows(
        tmp_path / "archive",
        since_ts=0,
        n_trials=10,
        roi_trials=0,
        shadow_trials=1,
        run_debug_shadows=False,
        window="full",
    )

    assert len(rows) == 1
    assert rows[0]["source"] == "windivert_archive"
    assert rows[0]["session_id"] == "2401:session"
    assert rows[0]["archive_path"] == str(capture)
    assert rows[0]["snapshot_mode"] == "archive_fast"


def test_load_archive_rows_can_emit_prebid_windows(
    tmp_path,
    monkeypatch,
) -> None:
    archive = tmp_path / "archive" / "complete"
    archive.mkdir(parents=True)
    capture = archive / "windivert_2026-06-04_complete_ethan_2401_session.json"
    capture.write_text("[]\n", encoding="utf-8")
    events = SimpleNamespace(
        packets=(SimpleNamespace(sort_id=1), SimpleNamespace(sort_id=2)),
        frames=(SimpleNamespace(sort_id=1), SimpleNamespace(sort_id=2)),
        sends=(SimpleNamespace(sort_id=2, kind="bid", value=580000),),
        states=(SimpleNamespace(sort_id=1),),
        statuses=(),
    )

    monkeypatch.setattr(module, "load_monitor_tables", lambda: "tables")
    monkeypatch.setattr(module, "parse_fatbeans_capture", lambda path: events)

    def fake_build_events(events_arg, **kwargs):
        if len(events_arg.packets) == 2:
            return {
                "session_id": "2401:session",
                "known_value_sum": 900000,
                "inventory_cells": 121,
                "final_q6_value": 600000,
            }
        return {
            "session_id": "2401:session",
            "round": None,
            "action_round": None,
        }

    def fake_model_eval_row(**kwargs):
        assert kwargs["final_value"] == 900000
        assert kwargs["final_cells"] == 121
        assert kwargs["truth_breakdown"]["final_q6_value"] == 600000
        return {
            "file": kwargs["file"],
            "round": None,
            "action_round": None,
            "decision_value_p50_error": -100000,
        }

    monkeypatch.setattr(module, "build_monitor_artifact_from_events", fake_build_events)
    monkeypatch.setattr(module, "_model_eval_row", fake_model_eval_row)

    rows = module._load_archive_rows(
        tmp_path / "archive",
        since_ts=0,
        n_trials=10,
        roi_trials=0,
        shadow_trials=1,
        run_debug_shadows=False,
        window="prebid",
    )

    assert len(rows) == 1
    assert rows[0]["source"] == "windivert_archive_prebid"
    assert rows[0]["eval_window"] == "pre_bid"
    assert rows[0]["eval_window_round"] == 1
    assert rows[0]["window_bid_value"] == 580000
    assert rows[0]["round"] == 1
    assert rows[0]["action_round"] == 1


def test_summarize_live_windivert_brief_dedupes_archive_by_session() -> None:
    rows = module._dedupe_rows(
        [
            {"source": "windivert", "session_id": "2401:a", "file": "live.json"},
            {
                "source": "windivert_archive",
                "session_id": "2401:a",
                "archive_path": "archive/complete/windivert_a.json",
            },
            {
                "source": "windivert_archive",
                "session_id": "2401:b",
                "archive_path": "archive/complete/windivert_b.json",
            },
        ]
    )

    assert [row["session_id"] for row in rows] == ["2401:a", "2401:b"]
