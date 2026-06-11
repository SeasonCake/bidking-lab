"""Tests for the audit-only activity shadow prior builder."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from bidking_lab.extract.bid_map_table import load_bid_map_table
from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.item_table import load_item_table
from bidking_lab.simulation.basic_mc import flatten_pool


def _load_build_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "build_activity_shadow_prior.py"
    spec = importlib.util.spec_from_file_location("build_activity_shadow_prior", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_activity_shadow_prior_is_audit_only_and_keeps_official_refs_empty() -> None:
    module = _load_build_module()
    payload = module.build_shadow_prior(Path(__file__).resolve().parents[1])

    assert payload["status"] == "shadow_only_not_formal_prior"
    assert payload["do_not_merge_into_items_droppable"] is True
    assert payload["fit_model"]["name"] == "q6_log_value_weight_plus_similarity_v0"

    targets = {entry["item_id"]: entry for entry in payload["targets"]}
    assert set(targets) == {1016007, 1036006, 1036007, 1036008, 1076007}
    assert all(not entry["official_drop_refs"] for entry in targets.values())
    assert targets[1036006]["fit_confidence"] == "low_value_extrapolation"
    assert targets[1076007]["activity_text_eligible"] is False
    assert targets[1076007]["eligible_map_families"] == []
    assert targets[1036007]["estimated_leaf_weight"] > 0

    guard = payload["impact_guard"]
    assert guard["formal_use_allowed"] is False
    assert guard["drop_rate_validation_allowed"] is False
    high_tier = guard["activity_family_impact"]["high_tier_activity_scenes"]
    assert high_tier["recommendation"] == "keep_read_only_until_official_or_sample_confirmed"
    assert high_tier["weighted_mean_value_if_used"] < 1_000_000
    assert high_tier["max_value_item"]["item_id"] == 1036006
    assert high_tier["max_value_item"]["weight_share"] < 0.05


def test_activity_shadow_targets_stay_out_of_formal_map_prior() -> None:
    module = _load_build_module()
    repo_root = Path(__file__).resolve().parents[1]
    target_ids = set(module.TARGET_ITEM_IDS)

    droppable_path = repo_root / "data" / "processed" / "items_droppable.json"
    droppable = json.loads(droppable_path.read_text(encoding="utf-8"))
    assert target_ids.isdisjoint({int(row["item_id"]) for row in droppable})

    tables_dir = repo_root / "data" / "raw" / "tables"
    items = load_item_table(tables_dir / "Item.txt")
    drops = load_drop_table(tables_dir / "Drop.txt")
    maps = load_bid_map_table(tables_dir / "BidMap.txt")
    formal_ids: set[int] = set()
    for bid_map in maps.values():
        formal_ids.update(flatten_pool(bid_map.drop_pool_id, drops, items).item_ids)

    assert target_ids.isdisjoint(formal_ids)
    assert 1012005 in formal_ids
