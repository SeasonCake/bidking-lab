import importlib.util
from pathlib import Path
from types import SimpleNamespace

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropEntry, DropPool
from bidking_lab.extract.item_table import Item


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_capacity_table_audit.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_capacity_table_audit",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _item(item_id: int = 1001) -> Item:
    return Item(
        item_id=item_id,
        name=f"item_{item_id}",
        description="",
        name_key=f"item_{item_id}",
        desc_key=f"item_{item_id}_desc",
        quality=4,
        quality_color="",
        value=10_000,
        shape_w=2,
        shape_h=2,
        tags=[],
        allowed_shelves=[],
        icon_name="",
        model_name="",
        raw_row=[],
    )


def _tables(
    *,
    items_per_session_max: int = 44,
    raw_row: list[str] | None = None,
) -> SimpleNamespace:
    item = _item()
    return SimpleNamespace(
        maps={
            2601: BidMap(
                map_id=2601,
                name="direct_capacity_map",
                description="",
                category=101,
                auction_mode="open",
                sub_pool_weights=[],
                rounds_total=5,
                entry_fee_silver=0,
                starting_budget_silver=100_000,
                drop_pool_id=9001,
                items_per_session_min=22,
                items_per_session_max=items_per_session_max,
                value_tier_ui="",
                mode_flag=4,
                bid_price_ladder=[],
                round_category_hints=[],
                raw_row=raw_row or [],
            )
        },
        drops={
            9001: DropPool(
                pool_id=9001,
                name="pool",
                description="",
                pool_type=2,
                entries=[
                    DropEntry(
                        category=101,
                        item_id=item.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    )
                ],
            )
        },
        items={item.item_id: item},
    )


def test_capacity_table_audit_marks_truth_above_sampler_possible_max() -> None:
    module = _load_module()
    details = [
        {
            "file": "sample.json#prebid_r1",
            "map_id": 2601,
            "hero_map_evidence_profile": "aisha|2601|shape+layout",
            "item_count_capacity": {
                "total_count_source": "exact",
                "total_count_target": 65,
                "truth_item_count": 65,
                "prior_items_per_session_min": 22,
                "prior_items_per_session_max": 44,
                "target_prior_max_delta": 21,
                "truth_prior_max_delta": 21,
                "target_truth_delta": 0,
                "cases": ["direct_prior_max_conflict"],
                "flags": [
                    "target_count_above_prior_max",
                    "truth_count_above_prior_max",
                ],
            },
        }
    ]

    result = module.summarize_capacity_table_audit(
        details,
        tables=_tables(),
        selected_case="direct_prior_max_conflict",
    )

    assert len(result) == 1
    row = result[0]
    assert row["map_id"] == "2601"
    assert row["status"] == "table_possible_max_below_truth"
    assert row["table_impossible_rows"] == 1
    assert row["round_cap_impossible_rows"] == 0
    assert row["bidmap_raw_column_count"] == 0
    assert row["bidmap_drop_ref_column_index"] == 16
    assert row["bidmap_raw_round_cap_max"] is None
    assert row["bidmap_items_per_session_max"] == 44
    assert row["sampler_max_count_per_draw"] == 1
    assert row["sampler_possible_item_count_max"] == 44
    assert row["capacity_cases"] == {"direct_prior_max_conflict": 1}
    assert row["target_truth_delta_counts"] == {
        "below": 0,
        "match": 1,
        "above": 0,
    }


def test_capacity_table_audit_adds_raw_inventory_diagnostics(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    sample = tmp_path / "sample.json"
    sample.write_text("[]", encoding="utf-8")

    inventory_items = (
        SimpleNamespace(runtime_id=101, item_id=1001, quality=4, cells=4),
        SimpleNamespace(runtime_id=102, item_id=1001, quality=4, cells=4),
    )
    state = SimpleNamespace(
        sort_id=10,
        message_id=0x002D,
        round_index=2,
        map_id=2601,
        inventory_items=inventory_items,
    )

    monkeypatch.setattr(
        module,
        "parse_fatbeans_capture",
        lambda path: SimpleNamespace(states=(state,)),
    )
    monkeypatch.setattr(
        module,
        "settlement_truth_from_fatbeans",
        lambda events, *, items: SimpleNamespace(item_count=2),
    )

    result = module.summarize_capacity_table_audit(
        [
            {
                "file": f"{sample}#prebid_r1",
                "map_id": 2601,
                "hero_map_evidence_profile": "aisha|2601|shape+layout",
                "item_count_capacity": {
                    "total_count_source": "exact",
                    "total_count_target": 2,
                    "truth_item_count": 2,
                    "prior_items_per_session_max": 1,
                    "truth_prior_max_delta": 1,
                    "target_truth_delta": 0,
                    "cases": ["direct_prior_max_conflict"],
                },
            }
        ],
        tables=_tables(),
        selected_case="direct_prior_max_conflict",
    )

    row = result[0]
    assert row["raw_inventory_status"] == "verified_latest_inventory"
    assert row["raw_inventory_file_count"] == 1
    assert row["raw_latest_inventory_item_count"]["max"] == 2
    assert row["raw_latest_inventory_truth_match_files"] == 1
    assert row["raw_detail_truth_latest_match_rows"] == 1
    assert row["raw_duplicate_runtime_id_count"]["max"] == 0
    assert row["raw_duplicate_runtime_item_pair_count"]["max"] == 0
    assert row["raw_duplicate_item_id_count"]["max"] == 1
    assert row["raw_missing_from_drop_universe_count"]["max"] == 0
    assert row["raw_known_temp_zodiac_count"]["max"] == 0
    assert row["raw_non_zodiac_missing_from_drop_universe_count"]["max"] == 0
    assert row["raw_drop_ref_excess_item_count"]["max"] == 0
    assert row["raw_drop_ref_excess_after_temp_zodiac_count"]["max"] == 0
    assert row["raw_round_cap_excess_item_count"]["max"] is None
    assert row["raw_round_cap_excess_after_temp_zodiac_count"]["max"] is None
    assert row["raw_latest_inventory_message_ids"] == {"0x002D": 1}
    assert row["raw_latest_inventory_quality_counts"] == {"4": 2}


def test_capacity_table_audit_filters_selected_case() -> None:
    module = _load_module()
    details = [
        {
            "file": "sample.json#prebid_r1",
            "map_id": 2601,
            "hero_map_evidence_profile": "aisha|2601|shape+layout",
            "item_count_capacity": {
                "total_count_source": "floor",
                "total_count_target": 40,
                "truth_item_count": 65,
                "prior_items_per_session_max": 44,
                "target_prior_max_delta": -4,
                "truth_prior_max_delta": 21,
                "target_truth_delta": -25,
                "cases": ["target_lower_bound_truth_above_prior"],
            },
        }
    ]

    assert (
        module.summarize_capacity_table_audit(
            details,
            tables=_tables(),
            selected_case="direct_prior_max_conflict",
        )
        == []
    )
    assert len(
        module.summarize_capacity_table_audit(
            details,
            tables=_tables(),
            selected_case="target_lower_bound_truth_above_prior",
        )
    ) == 1


def test_capacity_table_audit_quantifies_zodiac_adjusted_count_gap(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    sample = tmp_path / "sample.json"
    sample.write_text("[]", encoding="utf-8")

    inventory_items = (
        SimpleNamespace(runtime_id=101, item_id=1001, quality=4, cells=4),
        SimpleNamespace(runtime_id=102, item_id=1306006, quality=3, cells=4),
        SimpleNamespace(runtime_id=103, item_id=1001, quality=4, cells=4),
    )
    state = SimpleNamespace(
        sort_id=10,
        message_id=0x002D,
        round_index=2,
        map_id=2601,
        inventory_items=inventory_items,
    )

    monkeypatch.setattr(
        module,
        "parse_fatbeans_capture",
        lambda path: SimpleNamespace(states=(state,)),
    )
    monkeypatch.setattr(
        module,
        "settlement_truth_from_fatbeans",
        lambda events, *, items: SimpleNamespace(item_count=3),
    )

    raw_row = ["0"] * 23
    raw_row[14] = "[2,2,2,2,2]"
    raw_row[17] = "[9999,2601,1,1]"
    result = module.summarize_capacity_table_audit(
        [
            {
                "file": f"{sample}#prebid_r1",
                "map_id": 2601,
                "hero_map_evidence_profile": "aisha|2601|shape+layout",
                "item_count_capacity": {
                    "total_count_source": "exact",
                    "total_count_target": 3,
                    "truth_item_count": 3,
                    "prior_items_per_session_max": 1,
                    "truth_prior_max_delta": 2,
                    "target_truth_delta": 0,
                    "cases": ["direct_prior_max_conflict"],
                },
            }
        ],
        tables=_tables(items_per_session_max=1, raw_row=raw_row),
        selected_case="direct_prior_max_conflict",
    )

    row = result[0]
    assert row["raw_known_temp_zodiac_count"]["max"] == 1
    assert row["raw_non_zodiac_missing_from_drop_universe_count"]["max"] == 0
    assert row["raw_drop_ref_excess_item_count"]["max"] == 2
    assert row["raw_drop_ref_excess_after_temp_zodiac_count"]["max"] == 1
    assert row["raw_round_cap_excess_item_count"]["max"] == 1
    assert row["raw_round_cap_excess_after_temp_zodiac_count"]["max"] == 0
