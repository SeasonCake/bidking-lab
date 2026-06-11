"""Build an audit-only fitted prior for v308 activity-only items.

The v308 World Cup items are valid Item.txt rows, but the local Drop.txt has
no numeric weights for them. This script produces a separate JSON artifact with
explicit evidence and a simple similarity/regression estimate. It must not be
merged into the formal Drop prior without sample or table confirmation.
"""

from __future__ import annotations

import io
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap, load_bid_map_table
from bidking_lab.extract.drop_table import DropEntry, DropPool, load_drop_table
from bidking_lab.extract.item_table import Item, load_item_table
from bidking_lab.simulation.basic_mc import POOL_REFERENCE_CATEGORY, is_physical_loot_item


TARGET_ITEM_IDS = (1016007, 1036006, 1036007, 1036008, 1076007)
WORLD_CUP_LIMITED_ITEM_IDS = (1016007, 1036006, 1036007, 1036008)

ELIGIBLE_MAP_FAMILIES: dict[int, list[str]] = {
    1036007: [
        "abandoned_warehouse",
        "shipping_container",
        "high_tier_activity_scenes",
    ],
    1016007: ["shipping_container", "high_tier_activity_scenes"],
    1036006: ["high_tier_activity_scenes"],
    1036008: ["high_tier_activity_scenes"],
    1076007: [],
}

FAMILY_LABELS = {
    "abandoned_warehouse": "activity text: abandoned warehouse",
    "shipping_container": "activity text: shipping container",
    "high_tier_activity_scenes": (
        "activity text: vacant villa / ship sealed cabin / secret auction / "
        "deep-sea shipwreck / secluded villa"
    ),
}


@dataclass(frozen=True)
class BasisItem:
    item_id: int
    name: str
    cells: int
    value: int
    value_ratio: float
    median_leaf_weight: float
    ref_count: int
    tags: tuple[int, ...]
    ref_categories: tuple[int, ...]


def _ensure_utf8_stdio() -> None:
    if sys.platform != "win32":
        return
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _quality_categories(item: Item) -> set[int]:
    categories = {int(tag) for tag in item.tags if 101 <= int(tag) <= 110}
    prefix = int(item.item_id) // 10000
    if 101 <= prefix <= 110:
        categories.add(prefix)
    return categories


def _map_reachable_leaf_refs(
    *,
    maps: dict[int, BidMap],
    drops: dict[int, DropPool],
    items: dict[int, Item],
) -> tuple[dict[int, list[tuple[int, int, int]]], set[int], set[int]]:
    by_item: dict[int, list[tuple[int, int, int]]] = {}
    missing_items: set[int] = set()
    missing_pools: set[int] = set()
    visited: set[int] = set()

    def walk(pool_id: int) -> None:
        if pool_id in visited:
            return
        visited.add(pool_id)
        pool = drops.get(pool_id)
        if pool is None:
            missing_pools.add(pool_id)
            return
        for entry in pool.entries:
            if entry.category == POOL_REFERENCE_CATEGORY:
                walk(entry.item_id)
                continue
            item = items.get(entry.item_id)
            if item is None:
                missing_items.add(entry.item_id)
                continue
            if is_physical_loot_item(item):
                by_item.setdefault(entry.item_id, []).append(
                    (pool_id, entry.category, entry.weight)
                )

    for bid_map in maps.values():
        walk(bid_map.drop_pool_id)
    return by_item, missing_items, missing_pools


def _all_drop_refs(drops: dict[int, DropPool]) -> dict[int, list[dict[str, int]]]:
    refs: dict[int, list[dict[str, int]]] = {}
    for pool in drops.values():
        for entry in pool.entries:
            if entry.category == POOL_REFERENCE_CATEGORY:
                continue
            refs.setdefault(entry.item_id, []).append(
                {
                    "pool_id": pool.pool_id,
                    "category": entry.category,
                    "n_min": entry.n_min,
                    "n_max": entry.n_max,
                    "weight": entry.weight,
                }
            )
    return refs


def _fit_q6_log_weight_model(
    *,
    items: dict[int, Item],
    map_refs_by_item: dict[int, list[tuple[int, int, int]]],
) -> dict[str, float | int]:
    rows: list[tuple[float, float]] = []
    for item_id, refs in map_refs_by_item.items():
        item = items[item_id]
        if item.quality != 6 or item.value <= 0:
            continue
        weights = [weight for _pool_id, _category, weight in refs]
        if not weights:
            continue
        rows.append((math.log(float(item.value)), math.log(float(median(weights)))))
    if len(rows) < 2:
        return {"intercept": 0.0, "slope": 0.0, "r2": 0.0, "training_count": len(rows)}
    x = np.array([row[0] for row in rows], dtype=np.float64)
    y = np.array([row[1] for row in rows], dtype=np.float64)
    design = np.vstack([np.ones_like(x), x]).T
    coef = np.linalg.lstsq(design, y, rcond=None)[0]
    pred = design @ coef
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 0.0 if ss_tot <= 0 else 1.0 - (ss_res / ss_tot)
    return {
        "intercept": float(coef[0]),
        "slope": float(coef[1]),
        "r2": r2,
        "training_count": len(rows),
    }


def _predict_log_model_weight(item: Item, model: dict[str, float | int]) -> float:
    if item.value <= 0:
        return 1.0
    intercept = float(model["intercept"])
    slope = float(model["slope"])
    return max(1.0, math.exp(intercept + slope * math.log(float(item.value))))


def _basis_items_for_target(
    target: Item,
    *,
    items: dict[int, Item],
    map_refs_by_item: dict[int, list[tuple[int, int, int]]],
) -> tuple[str, list[BasisItem]]:
    target_cells = target.shape_w * target.shape_h
    target_value = max(1, target.value)
    target_categories = _quality_categories(target)

    candidates: list[tuple[int, Item, int, float, bool, set[int], set[int], float, int]] = []
    for item_id, refs in map_refs_by_item.items():
        item = items[item_id]
        if item.quality != target.quality:
            continue
        cells = item.shape_w * item.shape_h
        ratio = float(item.value) / float(target_value)
        item_categories = _quality_categories(item)
        ref_categories = {category for _pool_id, category, _weight in refs}
        category_overlap = bool((item_categories | ref_categories) & target_categories)
        median_weight = float(median(weight for _pool_id, _category, weight in refs))
        candidates.append(
            (
                item_id,
                item,
                cells,
                ratio,
                category_overlap,
                item_categories,
                ref_categories,
                median_weight,
                len(refs),
            )
        )

    tiers = (
        (
            "strict_same_category_same_cells_value_0.5_2x",
            lambda c: c[4] and c[2] == target_cells and 0.5 <= c[3] <= 2.0,
        ),
        (
            "relaxed_same_category_cells_pm2_value_0.25_4x",
            lambda c: c[4] and abs(c[2] - target_cells) <= 2 and 0.25 <= c[3] <= 4.0,
        ),
        (
            "same_category_any_cells_value_0.25_4x",
            lambda c: c[4] and 0.25 <= c[3] <= 4.0,
        ),
        (
            "same_cells_any_category_value_0.25_4x",
            lambda c: c[2] == target_cells and 0.25 <= c[3] <= 4.0,
        ),
        ("same_category_any_value", lambda c: c[4]),
    )
    tier_name = "none"
    matched: list[tuple[int, Item, int, float, bool, set[int], set[int], float, int]] = []
    for name, predicate in tiers:
        matched = [candidate for candidate in candidates if predicate(candidate)]
        if matched:
            tier_name = name
            break

    matched.sort(key=lambda c: (abs(math.log(max(c[3], 1e-9))), abs(c[2] - target_cells), c[0]))
    basis: list[BasisItem] = []
    for item_id, item, cells, ratio, _overlap, item_categories, ref_categories, weight, ref_count in matched[:12]:
        basis.append(
            BasisItem(
                item_id=item_id,
                name=item.name,
                cells=cells,
                value=item.value,
                value_ratio=ratio,
                median_leaf_weight=weight,
                ref_count=ref_count,
                tags=tuple(sorted(item_categories)),
                ref_categories=tuple(sorted(ref_categories)),
            )
        )
    return tier_name, basis


def _confidence(match_tier: str, basis_count: int) -> str:
    if match_tier == "none" or basis_count == 0:
        return "none"
    if match_tier == "same_category_any_value":
        return "low_value_extrapolation"
    if match_tier.startswith("strict") and basis_count >= 3:
        return "medium"
    if match_tier.startswith("relaxed") and basis_count >= 3:
        return "medium_low"
    if basis_count >= 3:
        return "low"
    return "very_low"


def _activity_family_impact(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id = {int(entry["item_id"]): entry for entry in targets}
    impact: dict[str, dict[str, Any]] = {}
    for family in FAMILY_LABELS:
        entries = [
            by_id[item_id]
            for item_id, families in ELIGIBLE_MAP_FAMILIES.items()
            if family in families
        ]
        total_weight = sum(max(0, int(entry["estimated_leaf_weight"])) for entry in entries)
        weighted_value_sum = sum(
            max(0, int(entry["estimated_leaf_weight"])) * max(0, int(entry["value"]))
            for entry in entries
        )
        max_value_entry = max(entries, key=lambda entry: int(entry["value"]), default=None)
        max_weight_entry = max(
            entries,
            key=lambda entry: int(entry["estimated_leaf_weight"]),
            default=None,
        )
        low_confidence_entries = [
            entry
            for entry in entries
            if entry["fit_confidence"] in {"low", "very_low", "low_value_extrapolation", "none"}
        ]
        impact[family] = {
            "label": FAMILY_LABELS[family],
            "target_count": len(entries),
            "estimated_weight_sum": total_weight,
            "weighted_mean_value_if_used": (
                None if total_weight <= 0 else int(round(weighted_value_sum / total_weight))
            ),
            "max_value_item": None
            if max_value_entry is None
            else {
                "item_id": max_value_entry["item_id"],
                "name": max_value_entry["name"],
                "value": max_value_entry["value"],
                "estimated_leaf_weight": max_value_entry["estimated_leaf_weight"],
                "weight_share": None
                if total_weight <= 0
                else round(int(max_value_entry["estimated_leaf_weight"]) / total_weight, 4),
            },
            "max_weight_item": None
            if max_weight_entry is None
            else {
                "item_id": max_weight_entry["item_id"],
                "name": max_weight_entry["name"],
                "value": max_weight_entry["value"],
                "estimated_leaf_weight": max_weight_entry["estimated_leaf_weight"],
                "weight_share": None
                if total_weight <= 0
                else round(int(max_weight_entry["estimated_leaf_weight"]) / total_weight, 4),
            },
            "low_confidence_target_count": len(low_confidence_entries),
            "recommendation": "keep_read_only_until_official_or_sample_confirmed"
            if low_confidence_entries
            else "sample_confirm_before_formal_use",
        }
    return impact


def build_shadow_prior(repo_root: Path) -> dict[str, Any]:
    tables_in = repo_root / "data" / "raw" / "tables"
    raw_root = repo_root / "data" / "raw"
    items = load_item_table(tables_in / "Item.txt")
    drops = load_drop_table(tables_in / "Drop.txt")
    maps = load_bid_map_table(tables_in / "BidMap.txt")
    official_refs = _all_drop_refs(drops)
    map_refs_by_item, missing_items, missing_pools = _map_reachable_leaf_refs(
        maps=maps,
        drops=drops,
        items=items,
    )
    model = _fit_q6_log_weight_model(items=items, map_refs_by_item=map_refs_by_item)

    targets: list[dict[str, Any]] = []
    for item_id in TARGET_ITEM_IDS:
        item = items[item_id]
        match_tier, basis = _basis_items_for_target(
            item,
            items=items,
            map_refs_by_item=map_refs_by_item,
        )
        regression_weight = _predict_log_model_weight(item, model)
        neighbor_weight = float(median([basis_item.median_leaf_weight for basis_item in basis])) if basis else None
        if neighbor_weight is None or match_tier == "same_category_any_value":
            blended_weight = regression_weight
            fit_mode = "regression_only"
        else:
            blended_weight = math.exp((math.log(regression_weight) + math.log(neighbor_weight)) / 2.0)
            fit_mode = "geomean_regression_neighbor"
        activity_families = ELIGIBLE_MAP_FAMILIES[item_id]
        targets.append(
            {
                "item_id": item_id,
                "name": item.name,
                "quality": item.quality,
                "cells": item.shape_w * item.shape_h,
                "value": item.value,
                "tags": item.tags,
                "activity_text_eligible": item_id in WORLD_CUP_LIMITED_ITEM_IDS,
                "eligible_map_families": activity_families,
                "eligible_map_family_labels": [FAMILY_LABELS[fam] for fam in activity_families],
                "official_drop_refs": official_refs.get(item_id, []),
                "estimated_leaf_weight": int(round(blended_weight)),
                "fit_confidence": _confidence(match_tier, len(basis)),
                "fit_mode": fit_mode,
                "match_tier": match_tier,
                "fit_components": {
                    "q6_log_value_regression_weight": round(regression_weight, 3),
                    "neighbor_median_weight": None if neighbor_weight is None else round(neighbor_weight, 3),
                    "blended_weight": round(blended_weight, 3),
                },
                "matched_basis_items": [
                    {
                        "item_id": basis_item.item_id,
                        "name": basis_item.name,
                        "cells": basis_item.cells,
                        "value": basis_item.value,
                        "value_ratio": round(basis_item.value_ratio, 4),
                        "median_leaf_weight": round(basis_item.median_leaf_weight, 3),
                        "ref_count": basis_item.ref_count,
                        "tags": list(basis_item.tags),
                        "ref_categories": list(basis_item.ref_categories),
                    }
                    for basis_item in basis
                ],
            }
        )

    activity_edges: dict[str, list[dict[str, Any]]] = {}
    by_id = {entry["item_id"]: entry for entry in targets}
    for family in FAMILY_LABELS:
        family_entries = []
        for item_id, families in ELIGIBLE_MAP_FAMILIES.items():
            if family not in families:
                continue
            entry = by_id[item_id]
            family_entries.append(
                {
                    "item_id": item_id,
                    "name": entry["name"],
                    "estimated_leaf_weight": entry["estimated_leaf_weight"],
                    "fit_confidence": entry["fit_confidence"],
                }
            )
        activity_edges[family] = family_entries

    return {
        "schema": "bidking_activity_shadow_prior_v0",
        "status": "shadow_only_not_formal_prior",
        "do_not_merge_into_items_droppable": True,
        "fileVersion": (raw_root / "fileVersion").read_text(encoding="utf-8").strip()
        if (raw_root / "fileVersion").exists()
        else None,
        "source_evidence": {
            "official_drop_source_found": False,
            "official_drop_source_note": (
                "Target items have valid Item.txt rows, but current Drop.txt has no "
                "leaf refs for them. Activity text names eligible map families but "
                "does not provide numeric weights."
            ),
            "activity_text_key": "activity_des_10007",
            "missing_map_item_rows": sorted(missing_items),
            "missing_map_drop_pools": sorted(missing_pools),
        },
        "fit_model": {
            "name": "q6_log_value_weight_plus_similarity_v0",
            "regression": model,
            "notes": [
                "Regression is fit on current map-reachable q6 items with official Drop weights.",
                "Neighbor median prefers same category/tags, same cells, and nearby value.",
                "This artifact is for audit/replay experiments only.",
            ],
        },
        "impact_guard": {
            "formal_use_allowed": False,
            "drop_rate_validation_allowed": False,
            "reason": (
                "No official numeric Drop weights were found. Fitted weights are kept "
                "read-only so they cannot raise live bids or pass formal drop-rate validation."
            ),
            "activity_family_impact": _activity_family_impact(targets),
        },
        "activity_edges": activity_edges,
        "targets": targets,
    }


def main() -> int:
    _ensure_utf8_stdio()
    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "data" / "processed" / "activity_drop_shadow_prior.json"
    payload = build_shadow_prior(repo_root)
    _write_json(out_path, payload)
    print(f"wrote {out_path}")
    print(f"  targets: {len(payload['targets'])}")
    print(f"  status : {payload['status']}")
    for entry in payload["targets"]:
        print(
            f"  {entry['item_id']} {entry['name']}: "
            f"weight~{entry['estimated_leaf_weight']} "
            f"confidence={entry['fit_confidence']} official_refs={len(entry['official_drop_refs'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
