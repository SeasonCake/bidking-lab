import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_settlement_count_prior_candidates.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_settlement_count_prior_candidates",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _item(item_id: int, *, cells: int = 4) -> SimpleNamespace:
    return SimpleNamespace(item_id=item_id, cells=cells)


def _state(map_id: int, item_ids: list[int]) -> SimpleNamespace:
    return SimpleNamespace(
        message_id=0x002D,
        round_index=5,
        map_id=map_id,
        inventory_items=tuple(_item(item_id) for item_id in item_ids),
    )


def _tables(*, include_map: bool = True) -> SimpleNamespace:
    raw_row = [""] * 23
    raw_row[14] = "[4,4,4]"
    raw_row[17] = "[9999,2601,1,2]"
    maps = {}
    if include_map:
        maps[2601] = SimpleNamespace(
            name="count_prior_map",
            drop_pool_id=2601,
            items_per_session_min=1,
            items_per_session_max=2,
            raw_row=raw_row,
        )
    return SimpleNamespace(maps=maps)


def _patch_parser(monkeypatch, module, states_by_name):
    monkeypatch.setattr(
        module,
        "parse_fatbeans_capture",
        lambda path: SimpleNamespace(states=(states_by_name[Path(path).name],)),
    )
    monkeypatch.setattr(
        module,
        "_latest_settlement_payload",
        lambda path: (None, None, {"settlement_frame_count": 0}),
    )


def test_settlement_count_prior_candidates_quantifies_table_residuals(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("[]", encoding="utf-8")
    second.write_text("[]", encoding="utf-8")
    _patch_parser(
        monkeypatch,
        module,
        {
            "first.json": _state(2601, [1001, 1002, 1306003]),
            "second.json": _state(2601, [1001, 1002, 1003, 1004, 1005, 1306004]),
        },
    )

    result = module.summarize_settlement_count_prior_candidates(
        [tmp_path],
        tables=_tables(),
        min_samples=2,
    )

    assert result["files"] == 2
    assert result["settlement_rows"] == 2
    assert result["overall"]["above_drop_ref_rows"] == 2
    assert result["overall"]["above_drop_ref_after_temp_zodiac_rows"] == 1
    assert result["overall"]["above_round_cap_rows"] == 1
    assert result["overall"]["above_round_cap_after_temp_zodiac_rows"] == 1
    assert result["overall"]["residual_modes"] == {
        "activity_extras_only_drop_ref_gap": 1,
        "round_cap_overflow_after_temp": 1,
    }
    assert result["overall"]["inventory_slot_headroom_after_temp_zodiac"]["n"] == 0
    assert result["overall"]["full_observed_action_rows"] == 0
    assert result["overall"]["public_total_rows"] == 0
    row = result["rows"][0]
    assert row["group"] == "2601"
    assert row["candidate_status"] == "observed_exceeds_table_caps_shadow_only"
    assert row["files"] == 2
    assert row["residual_modes"] == {
        "activity_extras_only_drop_ref_gap": 1,
        "round_cap_overflow_after_temp": 1,
    }
    assert row["bidmap_items_per_session_max"]["max"] == 2
    assert row["bidmap_raw_round_cap_max"]["max"] == 4
    assert row["inventory_count"]["max"] == 6
    assert row["non_temp_inventory_count"]["max"] == 5
    assert row["known_temp_zodiac_count"]["max"] == 1
    assert row["drop_ref_excess_after_temp_zodiac_count"]["max"] == 3
    assert row["round_cap_excess_after_temp_zodiac_count"]["max"] == 1

    residual_result = module.summarize_settlement_count_prior_candidates(
        [tmp_path],
        tables=_tables(),
        group_by="residual_mode",
        min_samples=1,
    )
    residual_rows = {row["group"]: row for row in residual_result["rows"]}
    assert set(residual_rows) == {
        "activity_extras_only_drop_ref_gap",
        "round_cap_overflow_after_temp",
    }
    assert (
        residual_rows["round_cap_overflow_after_temp"][
            "above_round_cap_after_temp_zodiac_rows"
        ]
        == 1
    )
    assert (
        residual_rows["activity_extras_only_drop_ref_gap"][
            "above_drop_ref_after_temp_zodiac_rows"
        ]
        == 0
    )


def test_settlement_count_prior_candidates_marks_missing_table_shadow_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    sample = tmp_path / "activity.json"
    sample.write_text("[]", encoding="utf-8")
    _patch_parser(
        monkeypatch,
        module,
        {"activity.json": _state(2521, [1001, 1002, 1003])},
    )

    result = module.summarize_settlement_count_prior_candidates(
        [sample],
        tables=_tables(include_map=False),
        min_samples=1,
    )

    assert result["overall"]["missing_table_rows"] == 1
    assert result["rows"][0]["group"] == "2521"
    assert result["rows"][0]["candidate_status"] == "missing_table_shadow_only"
    assert result["rows"][0]["table_statuses"] == {"missing_bidmap": 1}


def test_settlement_count_prior_candidates_rejects_unknown_group_by() -> None:
    module = _load_module()

    with pytest.raises(ValueError):
        module.summarize_settlement_count_prior_candidates(
            [],
            tables=_tables(),
            group_by="unknown",
        )
