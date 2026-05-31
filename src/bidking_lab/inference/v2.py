"""Evidence-first inference v2 primitives.

The v1 live posterior samples a whole auction session and then rejects samples
that do not match observations. That works for low-information states, but it
breaks down once packet captures provide exact runtime/item facts. This module
keeps v2 separate so realtime code can compare both engines before switching.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Literal, Mapping, Sequence

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.ground_truth import (
    BucketTruth,
    SessionTruth,
    is_huge_item,
    prepare_session_sampler,
)
from bidking_lab.inference.map_likelihood import (
    QuantileSummary,
    category_observation_soft_score,
    truth_matches_obs,
)
from bidking_lab.inference.observation import CategoryItemObservation, SessionObs
from bidking_lab.simulation.robust_value import is_confusable_long_tail

EvidenceStrength = Literal["hard", "soft"]

_PUBLIC_AVG_VALUE_QUALITY: dict[int, int] = {
    200037: 5,  # 所有金色品质藏品的平均价值
}


@dataclass(frozen=True)
class EvidenceFact:
    """One non-item evidence fact retained for diagnostics."""

    kind: str
    key: str
    value: Any
    source: str
    strength: EvidenceStrength = "hard"
    sequence: int | None = None


@dataclass(frozen=True)
class RuntimeEvidence:
    """Merged facts for one runtime/local warehouse object."""

    runtime_id: int | None = None
    local_index: int | None = None
    item_id: int | None = None
    quality: int | None = None
    value: int | None = None
    shape_key: str | None = None
    cells: int | None = None
    categories: tuple[int, ...] = ()
    sources: tuple[str, ...] = ()

    @property
    def evidence_key(self) -> str:
        if self.runtime_id is not None:
            return f"runtime:{self.runtime_id}"
        if self.local_index is not None and self.shape_key is not None:
            return f"local:{self.local_index}:{self.shape_key}"
        return "anonymous"

    def merge(
        self,
        other: RuntimeEvidence,
    ) -> RuntimeEvidence:
        categories = tuple(dict.fromkeys((*self.categories, *other.categories)))
        sources = tuple(dict.fromkeys((*self.sources, *other.sources)))
        return RuntimeEvidence(
            runtime_id=self.runtime_id if self.runtime_id is not None else other.runtime_id,
            local_index=(
                self.local_index if self.local_index is not None else other.local_index
            ),
            item_id=self.item_id if self.item_id is not None else other.item_id,
            quality=self.quality if self.quality is not None else other.quality,
            value=self.value if self.value is not None else other.value,
            shape_key=self.shape_key if self.shape_key is not None else other.shape_key,
            cells=self.cells if self.cells is not None else other.cells,
            categories=categories,
            sources=sources,
        )


@dataclass(frozen=True)
class EvidenceStore:
    """Runtime-indexed evidence gathered from packet/public/tool sources."""

    by_runtime: Mapping[int, RuntimeEvidence]
    anonymous: tuple[RuntimeEvidence, ...] = ()
    facts: tuple[EvidenceFact, ...] = ()

    def runtime_items(self) -> tuple[RuntimeEvidence, ...]:
        return tuple(self.by_runtime.values())

    def items(self) -> tuple[RuntimeEvidence, ...]:
        return (*self.runtime_items(), *self.anonymous)


class EvidenceStoreBuilder:
    """Mutable builder that deduplicates item evidence by runtime/local key."""

    def __init__(self) -> None:
        self._by_runtime: dict[int, RuntimeEvidence] = {}
        self._by_local_shape: dict[tuple[int, str], RuntimeEvidence] = {}
        self._anonymous: list[RuntimeEvidence] = []
        self._facts: list[EvidenceFact] = []

    def add_fact(self, fact: EvidenceFact) -> None:
        self._facts.append(fact)

    def add_item(self, item: RuntimeEvidence) -> None:
        if item.runtime_id is not None:
            current = self._by_runtime.get(item.runtime_id)
            self._by_runtime[item.runtime_id] = (
                item if current is None else current.merge(item)
            )
            return
        if item.local_index is not None and item.shape_key is not None:
            key = (item.local_index, item.shape_key)
            current = self._by_local_shape.get(key)
            self._by_local_shape[key] = item if current is None else current.merge(item)
            return
        self._anonymous.append(item)

    def build(self) -> EvidenceStore:
        return EvidenceStore(
            by_runtime=dict(self._by_runtime),
            anonymous=(*self._by_local_shape.values(), *self._anonymous),
            facts=tuple(self._facts),
        )


@dataclass(frozen=True)
class KnownItemAnchor:
    """Exact item evidence that every v2 sample must contain."""

    key: str
    item_id: int
    quality: int
    cells: int
    value: int
    local_index: int | None = None
    runtime_id: int | None = None
    categories: tuple[int, ...] = ()
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnownFootprint:
    """One trusted shape-bearing layout footprint."""

    key: str
    local_index: int
    shape_key: str
    cells: int
    row: int
    col: int
    width: int
    height: int
    bottom_row: int
    right_col: int
    item_id: int | None = None
    quality: int | None = None


@dataclass(frozen=True)
class LayoutFeasibility:
    """Lightweight layout feasibility diagnostics for v2 samples."""

    footprint_count: int
    occupied_cells: int
    item_cells: int
    overlap_cells: int
    overflow_count: int
    bottom_row: int | None
    bounding_cells: int
    score: float
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResidualProblem:
    """Map problem after exact known items have been anchored."""

    map_id: int
    map_name: str
    anchors: tuple[KnownItemAnchor, ...]
    known_item_count: int
    known_cells: int
    known_value: int
    anchor_item_counts: Mapping[int, int]
    bucket_targets: Mapping[int, "ResidualBucketTarget"]
    category_targets: tuple[CategoryItemObservation, ...]
    layout: LayoutFeasibility
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResidualBucketTarget:
    """Per-quality target after known anchors are accounted for."""

    quality: int
    total_cells_exact: int | None = None
    count_exact: int | None = None
    total_cells_floor: int | None = None
    count_floor: int | None = None
    value_floor: int | None = None
    value_exact: int | None = None
    avg_value: float | None = None


@dataclass(frozen=True)
class PosteriorReport:
    """Unified posterior summary produced by the v2 conditional sampler."""

    map_id: int
    map_name: str
    n_total: int
    n_matched: int
    total_cells: QuantileSummary | None
    total_value: QuantileSummary | None
    anchor_count: int
    known_cells: int
    known_value: int
    layout_score: float
    decision_value: QuantileSummary | None = None
    q6_match_rate: float | None = None
    q6_value: QuantileSummary | None = None
    layout_diagnostics: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()


def _shape_cells(shape_key: str | None) -> int | None:
    if shape_key is None:
        return None
    try:
        code = int(shape_key)
    except (TypeError, ValueError):
        return None
    w = code // 10
    h = code % 10
    if w <= 0 or h <= 0:
        return None
    return w * h


def _shape_dimensions(shape_key: str | None) -> tuple[int, int] | None:
    if shape_key is None:
        return None
    try:
        code = int(shape_key)
    except (TypeError, ValueError):
        return None
    width = code // 10
    height = code % 10
    if width <= 0 or height <= 0:
        return None
    return width, height


def _observed_item_to_runtime_evidence(
    item: Any,
    *,
    source: str,
    category: int | None = None,
) -> RuntimeEvidence | None:
    shape_code = getattr(item, "shape_code", None)
    shape_key = str(shape_code) if shape_code else None
    cells = getattr(item, "cells", None)
    if cells is None:
        cells = _shape_cells(shape_key)
    categories = (category,) if category is not None else ()
    return RuntimeEvidence(
        runtime_id=getattr(item, "runtime_id", None),
        local_index=getattr(item, "local_index", None),
        item_id=getattr(item, "item_id", None),
        quality=getattr(item, "quality", None),
        value=getattr(item, "value", None),
        shape_key=shape_key,
        cells=cells,
        categories=categories,
        sources=(source,),
    )


def evidence_store_from_fatbeans_events(
    events: Any,
    *,
    include_inventory: bool = False,
) -> EvidenceStore:
    """Build an EvidenceStore from parsed Fatbeans events.

    Inventory facts are excluded by default because realtime inference should
    not use settlement truth as pre-settlement evidence.
    """

    from bidking_lab.live.fatbeans import _CATEGORY_OUTLINE_ACTIONS

    builder = EvidenceStoreBuilder()
    for state in getattr(events, "states", ()) or ():
        sequence = getattr(state, "sort_id", None)
        for info in getattr(state, "public_infos", ()) or ():
            builder.add_fact(
                EvidenceFact(
                    kind="public_info",
                    key=str(getattr(info, "info_id", "")),
                    value=getattr(info, "value", None),
                    source="public",
                    sequence=sequence,
                )
            )
            for item in getattr(info, "observed_items", ()) or ():
                ev = _observed_item_to_runtime_evidence(
                    item,
                    source=f"public:{getattr(info, 'info_id', '')}",
                )
                if ev is not None:
                    builder.add_item(ev)
        for result in getattr(state, "action_results", ()) or ():
            action_id = getattr(result, "action_id", None)
            category = _CATEGORY_OUTLINE_ACTIONS.get(action_id)
            for item in getattr(result, "observed_items", ()) or ():
                ev = _observed_item_to_runtime_evidence(
                    item,
                    source=f"action:{action_id}",
                    category=category,
                )
                if ev is not None:
                    builder.add_item(ev)
        for reveal in getattr(state, "skill_reveals", ()) or ():
            for item in getattr(reveal, "observed_items", ()) or ():
                ev = _observed_item_to_runtime_evidence(
                    item,
                    source=f"skill:{getattr(reveal, 'skill_id', '')}",
                )
                if ev is not None:
                    builder.add_item(ev)
        if include_inventory:
            for item in getattr(state, "inventory_items", ()) or ():
                item_id = getattr(item, "item_id", None)
                ev = RuntimeEvidence(
                    runtime_id=getattr(item, "runtime_id", None),
                    item_id=item_id,
                    quality=getattr(item, "quality", None),
                    cells=getattr(item, "cells", None),
                    sources=("inventory",),
                )
                builder.add_item(ev)
    return builder.build()


def known_item_anchors(
    store: EvidenceStore,
    *,
    items: Mapping[int, Item],
) -> tuple[KnownItemAnchor, ...]:
    """Return exact item anchors from merged runtime evidence."""

    anchors: list[KnownItemAnchor] = []
    seen_keys: set[str] = set()
    for evidence in store.items():
        if evidence.item_id is None or evidence.item_id not in items:
            continue
        item = items[evidence.item_id]
        key = evidence.evidence_key
        if key in seen_keys:
            continue
        seen_keys.add(key)
        anchors.append(
            KnownItemAnchor(
                key=key,
                runtime_id=evidence.runtime_id,
                local_index=evidence.local_index,
                item_id=item.item_id,
                quality=evidence.quality or item.quality,
                cells=evidence.cells or item.shape_w * item.shape_h,
                value=evidence.value or item.value,
                categories=evidence.categories,
                sources=evidence.sources,
            )
        )
    return tuple(anchors)


def _unique_shape_item_anchors(
    map_id: int,
    store: EvidenceStore,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    existing_keys: set[str],
) -> tuple[KnownItemAnchor, ...]:
    sampler = prepare_session_sampler(map_id, maps=maps, drops=drops, items=items)
    candidates_by_key: dict[
        tuple[int, str, tuple[int, ...]],
        dict[int, Item],
    ] = {}
    for pool in sampler.pools:
        for item in pool.items:
            shape_key = f"{item.shape_w}{item.shape_h}"
            category_keys = [()]
            category_keys.extend((tag,) for tag in item.tags)
            for category_key in category_keys:
                key = (item.quality, shape_key, category_key)
                candidates_by_key.setdefault(key, {})[item.item_id] = item

    anchors: list[KnownItemAnchor] = []
    seen_keys = set(existing_keys)
    for evidence in store.items():
        if evidence.item_id is not None:
            continue
        if evidence.quality is None or evidence.shape_key is None:
            continue
        lookup_keys = [
            (int(evidence.quality), evidence.shape_key, (category,))
            for category in evidence.categories
        ]
        lookup_keys.append((int(evidence.quality), evidence.shape_key, ()))
        matched_item: Item | None = None
        for lookup_key in lookup_keys:
            candidates = candidates_by_key.get(lookup_key, {})
            if len(candidates) == 1:
                matched_item = next(iter(candidates.values()))
                break
        if matched_item is None:
            continue
        key = evidence.evidence_key
        if key in seen_keys:
            continue
        seen_keys.add(key)
        anchors.append(
            KnownItemAnchor(
                key=key,
                runtime_id=evidence.runtime_id,
                local_index=evidence.local_index,
                item_id=matched_item.item_id,
                quality=matched_item.quality,
                cells=evidence.cells or matched_item.shape_w * matched_item.shape_h,
                value=matched_item.value,
                categories=evidence.categories,
                sources=(*evidence.sources, "inferred:unique_shape"),
            )
        )
    return tuple(anchors)


def known_footprints(
    store: EvidenceStore,
    *,
    columns: int = 10,
) -> tuple[KnownFootprint, ...]:
    footprints: list[KnownFootprint] = []
    seen: set[str] = set()
    for evidence in store.items():
        if evidence.local_index is None or evidence.shape_key is None:
            continue
        if evidence.local_index < 0:
            continue
        dims = _shape_dimensions(evidence.shape_key)
        if dims is None:
            continue
        key = evidence.evidence_key
        if key in seen:
            continue
        seen.add(key)
        width, height = dims
        row = evidence.local_index // columns + 1
        col = evidence.local_index % columns + 1
        footprints.append(
            KnownFootprint(
                key=key,
                local_index=evidence.local_index,
                shape_key=evidence.shape_key,
                cells=evidence.cells or width * height,
                row=row,
                col=col,
                width=width,
                height=height,
                bottom_row=row + height - 1,
                right_col=col + width - 1,
                item_id=evidence.item_id,
                quality=evidence.quality,
            )
        )
    return tuple(footprints)


def layout_feasibility_from_store(
    store: EvidenceStore,
    *,
    columns: int = 10,
) -> LayoutFeasibility:
    footprints = known_footprints(store, columns=columns)
    if not footprints:
        return LayoutFeasibility(
            footprint_count=0,
            occupied_cells=0,
            item_cells=0,
            overlap_cells=0,
            overflow_count=0,
            bottom_row=None,
            bounding_cells=0,
            score=1.0,
        )
    occupied: set[tuple[int, int]] = set()
    overflow_count = 0
    item_cells = 0
    item_cells_in_grid = 0
    for footprint in footprints:
        item_cells += footprint.cells
        if footprint.right_col > columns:
            overflow_count += 1
        for row in range(footprint.row, footprint.bottom_row + 1):
            for col in range(footprint.col, footprint.right_col + 1):
                if 1 <= col <= columns:
                    item_cells_in_grid += 1
                    occupied.add((row, col))
    occupied_cells = len(occupied)
    overlap_cells = max(0, item_cells_in_grid - occupied_cells)
    bottom_row = max(footprint.bottom_row for footprint in footprints)
    diagnostics: list[str] = []
    score = 1.0
    if overflow_count:
        diagnostics.append(f"footprint_overflow:{overflow_count}")
        score *= max(0.25, 1.0 - 0.15 * overflow_count)
    if overlap_cells:
        diagnostics.append(f"footprint_overlap_cells:{overlap_cells}")
        score *= max(0.25, 1.0 - overlap_cells / max(1, item_cells))
    return LayoutFeasibility(
        footprint_count=len(footprints),
        occupied_cells=occupied_cells,
        item_cells=item_cells,
        overlap_cells=overlap_cells,
        overflow_count=overflow_count,
        bottom_row=bottom_row,
        bounding_cells=bottom_row * columns,
        score=score,
        diagnostics=tuple(diagnostics),
    )


def layout_feasibility_score(
    truth: SessionTruth,
    layout: LayoutFeasibility,
) -> float:
    if layout.footprint_count <= 0:
        return 1.0
    truth_count = sum(bucket.count for bucket in truth.buckets.values())
    if truth_count < layout.footprint_count:
        return 0.0
    if truth.warehouse_total_cells < layout.occupied_cells:
        return 0.0
    if layout.bottom_row is None or layout.bounding_cells <= 0:
        return layout.score

    minimum_dense_cells = max(0, (layout.bottom_row - 1) * 10)
    if minimum_dense_cells <= layout.occupied_cells:
        return layout.score
    if truth.warehouse_total_cells >= minimum_dense_cells:
        return layout.score
    gap = minimum_dense_cells - truth.warehouse_total_cells
    return layout.score * max(0.25, 1.0 - gap / max(1, minimum_dense_cells))


def _quality_evidence_floors(
    store: EvidenceStore,
) -> dict[int, tuple[int, int, int]]:
    count_by_quality: Counter[int] = Counter()
    cells_by_quality: Counter[int] = Counter()
    value_by_quality: Counter[int] = Counter()
    seen: set[str] = set()
    for evidence in store.items():
        if evidence.quality is None:
            continue
        key = evidence.evidence_key
        if key in seen:
            continue
        seen.add(key)
        quality = int(evidence.quality)
        count_by_quality[quality] += 1
        if evidence.cells is not None:
            cells_by_quality[quality] += int(evidence.cells)
        if evidence.value is not None:
            value_by_quality[quality] += int(evidence.value)
    return {
        quality: (count, cells_by_quality[quality], value_by_quality[quality])
        for quality, count in count_by_quality.items()
    }


def _public_avg_value_targets(store: EvidenceStore) -> dict[int, float]:
    targets: dict[int, float] = {}
    for fact in store.facts:
        if fact.kind != "public_info":
            continue
        try:
            info_id = int(fact.key)
            value = float(fact.value)
        except (TypeError, ValueError):
            continue
        quality = _PUBLIC_AVG_VALUE_QUALITY.get(info_id)
        if quality is None or value <= 0:
            continue
        targets[quality] = value
    return targets


def _item_matches_category_target(
    item: Item,
    target: CategoryItemObservation,
) -> bool:
    if target.category not in item.tags:
        return False
    if target.quality is not None and item.quality != target.quality:
        return False
    if target.cells is not None and item.shape_w * item.shape_h != target.cells:
        return False
    dims = _shape_dimensions(target.shape_key)
    if dims is not None and (item.shape_w, item.shape_h) != dims:
        return False
    return True


def build_residual_problem(
    map_id: int,
    store: EvidenceStore,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    obs: SessionObs | None = None,
) -> ResidualProblem:
    """Create a residual problem by forcing exact known items into every sample."""

    bid_map = maps[map_id]
    anchors = known_item_anchors(store, items=items)
    anchors = (
        *anchors,
        *_unique_shape_item_anchors(
            map_id,
            store,
            maps=maps,
            drops=drops,
            items=items,
            existing_keys={anchor.key for anchor in anchors},
        ),
    )
    sampler = prepare_session_sampler(map_id, maps=maps, drops=drops, items=items)
    pool_item_ids = {
        item.item_id
        for pool in sampler.pools
        for item in pool.items
    }
    missing = sorted({anchor.item_id for anchor in anchors} - pool_item_ids)
    diagnostics: list[str] = []
    if missing:
        diagnostics.append(
            "anchors_not_in_flattened_pool:" + ",".join(str(item_id) for item_id in missing)
        )
    counts = Counter(anchor.item_id for anchor in anchors)
    layout = layout_feasibility_from_store(store)
    bucket_targets: dict[int, ResidualBucketTarget] = {}
    category_targets: list[CategoryItemObservation] = []
    if obs is not None:
        category_targets = [
            target for target in obs.category_items
            if target.item_id is None
        ]
        for quality, bucket in obs.buckets.items():
            cells_exact = bucket.total_cells
            cells_floor = bucket.total_cells_min
            count_exact = bucket.count
            count_floor = bucket.count_min
            value_floor = (
                bucket.value_sum
                if bucket.value_sum is not None and bucket.value_sum > 0
                else None
            )
            avg_value = (
                bucket.avg_value
                if bucket.avg_value is not None and bucket.avg_value > 0
                else None
            )
            if avg_value is not None:
                count_floor = max(count_floor or 0, 1)
            if (
                cells_exact is None
                and cells_floor is None
                and count_exact is None
                and count_floor is None
                and value_floor is None
                and avg_value is None
            ):
                continue
            bucket_targets[quality] = ResidualBucketTarget(
                quality=quality,
                total_cells_exact=int(cells_exact) if cells_exact is not None else None,
                count_exact=int(count_exact) if count_exact is not None else None,
                total_cells_floor=int(cells_floor) if cells_floor is not None else None,
                count_floor=int(count_floor) if count_floor is not None else None,
                value_floor=int(value_floor) if value_floor is not None else None,
                value_exact=int(value_floor) if value_floor is not None else None,
                avg_value=float(avg_value) if avg_value is not None else None,
            )
    for quality, (count_floor, cells_floor, value_floor) in _quality_evidence_floors(store).items():
        current = bucket_targets.get(quality)
        target_cells = cells_floor if cells_floor > 0 else None
        target_count = count_floor
        target_value = value_floor if value_floor > 0 else None
        target_avg_value = None
        target_cells_exact = None
        target_count_exact = None
        if current is not None:
            if current.total_cells_floor is not None or target_cells is not None:
                target_cells = max(current.total_cells_floor or 0, target_cells or 0)
            target_count = max(current.count_floor or 0, target_count)
            if current.value_floor is not None or target_value is not None:
                target_value = max(current.value_floor or 0, target_value or 0)
            target_avg_value = current.avg_value
            target_value_exact = current.value_exact
            target_cells_exact = current.total_cells_exact
            target_count_exact = current.count_exact
        else:
            target_value_exact = None
        bucket_targets[quality] = ResidualBucketTarget(
            quality=quality,
            total_cells_exact=target_cells_exact,
            count_exact=target_count_exact,
            total_cells_floor=target_cells,
            count_floor=target_count,
            value_floor=target_value,
            value_exact=target_value_exact,
            avg_value=target_avg_value,
        )
    for quality, avg_value in _public_avg_value_targets(store).items():
        current = bucket_targets.get(quality)
        bucket_targets[quality] = ResidualBucketTarget(
            quality=quality,
            total_cells_exact=current.total_cells_exact if current else None,
            count_exact=current.count_exact if current else None,
            total_cells_floor=current.total_cells_floor if current else None,
            count_floor=max(current.count_floor or 0, 1) if current else 1,
            value_floor=current.value_floor if current else None,
            value_exact=current.value_exact if current else None,
            avg_value=avg_value,
        )
    if category_targets:
        for target in category_targets:
            if not any(
                _item_matches_category_target(item, target)
                for pool in sampler.pools
                for item in pool.items
            ):
                diagnostics.append(
                    "category_target_no_pool_match:"
                    f"{target.category}:{target.quality}:{target.shape_key}:{target.cells}"
                )
    return ResidualProblem(
        map_id=map_id,
        map_name=bid_map.name,
        anchors=anchors,
        known_item_count=len(anchors),
        known_cells=sum(anchor.cells for anchor in anchors),
        known_value=sum(anchor.value for anchor in anchors),
        anchor_item_counts=dict(counts),
        bucket_targets=bucket_targets,
        category_targets=tuple(category_targets),
        layout=layout,
        diagnostics=tuple((*diagnostics, *layout.diagnostics)),
    )


def _add_item_to_buckets(
    buckets: dict[int, BucketTruth],
    item: Item,
    *,
    count: int = 1,
) -> None:
    area = item.shape_w * item.shape_h
    bucket = buckets.setdefault(item.quality, BucketTruth(quality=item.quality))
    bucket.count += count
    bucket.total_cells += area * count
    bucket.value_sum += item.value * count
    if is_huge_item(item):
        bucket.huge_count += count
    bucket.items.extend([item] * count)


class ConditionalSampler:
    """Sample sessions while forcing KnownItemAnchor items to exist."""

    def __init__(
        self,
        problem: ResidualProblem,
        *,
        maps: Mapping[int, BidMap],
        drops: Mapping[int, DropPool],
        items: Mapping[int, Item],
    ) -> None:
        self.problem = problem
        self.items = items
        self._sampler = prepare_session_sampler(
            problem.map_id,
            maps=maps,
            drops=drops,
            items=items,
        )

    def sample(self, rng: np.random.Generator | None = None) -> SessionTruth:
        rng = rng or np.random.default_rng()
        buckets: dict[int, BucketTruth] = {}
        for anchor in self.problem.anchors:
            item = self.items.get(anchor.item_id)
            if item is not None:
                _add_item_to_buckets(buckets, item)

        if not self._sampler.pools:
            return self._truth_from_buckets(buckets)

        pool_idx = (
            int(rng.choice(len(self._sampler.pools), p=self._sampler.pool_weights))
            if len(self._sampler.pools) > 1
            else 0
        )
        pool = self._sampler.pools[pool_idx]
        if len(pool.probabilities) == 0:
            return self._truth_from_buckets(buckets)

        self._sample_category_targets(pool, buckets, rng)
        self._sample_bucket_targets(pool, buckets, rng)

        current_count = sum(bucket.count for bucket in buckets.values())
        draw_min = max(
            self._sampler.items_per_session_min,
            current_count,
            self.problem.layout.footprint_count,
        )
        draw_max = max(self._sampler.items_per_session_max, draw_min)
        total_draws = int(rng.integers(draw_min, draw_max + 1))
        residual_draws = max(0, total_draws - current_count)
        if residual_draws:
            sampled_idx = rng.choice(
                len(pool.probabilities),
                size=residual_draws,
                replace=True,
                p=pool.probabilities,
            )
            counts = rng.integers(
                pool.n_min[sampled_idx],
                pool.n_max[sampled_idx] + 1,
            )
            for pool_i, count in zip(sampled_idx, counts):
                _add_item_to_buckets(
                    buckets,
                    pool.items[int(pool_i)],
                    count=int(count),
                )
        return self._truth_from_buckets(buckets)

    def _sample_category_targets(
        self,
        pool: Any,
        buckets: dict[int, BucketTruth],
        rng: np.random.Generator,
    ) -> None:
        if not self.problem.category_targets:
            return
        for target in self.problem.category_targets:
            indexes = [
                idx for idx, item in enumerate(pool.items)
                if _item_matches_category_target(item, target)
            ]
            if not indexes:
                continue
            probs = pool.probabilities[indexes].astype(np.float64)
            total = float(probs.sum())
            if total <= 0:
                continue
            probs = probs / total
            repeats = max(1, int(target.count))
            for _ in range(repeats):
                local_i = int(rng.choice(len(indexes), p=probs))
                pool_i = int(indexes[local_i])
                _add_item_to_buckets(buckets, pool.items[pool_i])

    def _sample_bucket_targets(
        self,
        pool: Any,
        buckets: dict[int, BucketTruth],
        rng: np.random.Generator,
    ) -> None:
        if not self.problem.bucket_targets:
            return
        qualities = np.asarray([item.quality for item in pool.items], dtype=np.int64)
        for target in self.problem.bucket_targets.values():
            indexes = np.flatnonzero(qualities == target.quality)
            if len(indexes) == 0:
                continue
            if self._sample_exact_bucket_combo(pool, indexes, buckets, target, rng):
                if self._bucket_target_met(buckets.get(target.quality), target):
                    continue
            attempts = 0
            while not self._bucket_target_met(buckets.get(target.quality), target):
                attempts += 1
                if attempts > 200:
                    break
                feasible = self._feasible_target_indexes(
                    pool,
                    indexes,
                    buckets.get(target.quality),
                    target,
                )
                if len(feasible) == 0:
                    break
                probs = pool.probabilities[feasible].astype(np.float64)
                total = float(probs.sum())
                if total <= 0:
                    break
                probs = probs / total
                local_i = int(rng.choice(len(feasible), p=probs))
                pool_i = int(feasible[local_i])
                item = pool.items[pool_i]
                max_count = self._max_add_count_for_target(
                    buckets.get(target.quality),
                    target,
                    item,
                    int(pool.n_max[pool_i]),
                )
                if max_count < int(pool.n_min[pool_i]):
                    continue
                count = int(rng.integers(int(pool.n_min[pool_i]), max_count + 1))
                _add_item_to_buckets(buckets, item, count=count)

    def _sample_exact_bucket_combo(
        self,
        pool: Any,
        indexes: np.ndarray,
        buckets: dict[int, BucketTruth],
        target: ResidualBucketTarget,
        rng: np.random.Generator,
    ) -> bool:
        if target.count_exact is None or target.total_cells_exact is None:
            return False
        bucket = buckets.get(target.quality)
        current_count = bucket.count if bucket is not None else 0
        current_cells = bucket.total_cells if bucket is not None else 0
        remaining_count = int(target.count_exact - current_count)
        remaining_cells = int(target.total_cells_exact - current_cells)
        if remaining_count == 0 and remaining_cells == 0:
            return True
        if remaining_count < 0 or remaining_cells < 0:
            return False
        if remaining_count > 80 or remaining_cells > 320:
            return False

        options_by_delta: dict[tuple[int, int], list[tuple[int, int, float]]] = {}
        for pool_i in indexes:
            pool_i = int(pool_i)
            item = pool.items[pool_i]
            area = int(item.shape_w * item.shape_h)
            if area <= 0:
                continue
            min_count = int(pool.n_min[pool_i])
            max_count = int(pool.n_max[pool_i])
            for count in range(min_count, max_count + 1):
                added_cells = area * count
                if count <= remaining_count and added_cells <= remaining_cells:
                    key = (count, added_cells)
                    weight = float(pool.probabilities[pool_i])
                    options_by_delta.setdefault(key, []).append((pool_i, count, weight))
        if not options_by_delta:
            return False

        deltas = tuple(sorted(options_by_delta))

        @lru_cache(maxsize=None)
        def can_fill(count_left: int, cells_left: int) -> bool:
            if count_left == 0 and cells_left == 0:
                return True
            if count_left < 0 or cells_left < 0:
                return False
            for count, cells in deltas:
                if count <= count_left and cells <= cells_left:
                    if can_fill(count_left - count, cells_left - cells):
                        return True
            return False

        if not can_fill(remaining_count, remaining_cells):
            return False

        count_left = remaining_count
        cells_left = remaining_cells
        while count_left or cells_left:
            feasible = [
                (count, cells)
                for count, cells in deltas
                if count <= count_left
                and cells <= cells_left
                and can_fill(count_left - count, cells_left - cells)
            ]
            if not feasible:
                return False
            weights = np.asarray(
                [
                    sum(weight for _pool_i, _count, weight in options_by_delta[key])
                    for key in feasible
                ],
                dtype=np.float64,
            )
            total = float(weights.sum())
            if total <= 0:
                return False
            key = feasible[int(rng.choice(len(feasible), p=weights / total))]
            choices = options_by_delta[key]
            choice_weights = np.asarray(
                [weight for _pool_i, _count, weight in choices],
                dtype=np.float64,
            )
            choice_total = float(choice_weights.sum())
            if choice_total <= 0:
                return False
            pool_i, count, _weight = choices[
                int(rng.choice(len(choices), p=choice_weights / choice_total))
            ]
            _add_item_to_buckets(buckets, pool.items[pool_i], count=count)
            count_left -= count
            cells_left -= key[1]
        return True

    def _feasible_target_indexes(
        self,
        pool: Any,
        indexes: np.ndarray,
        bucket: BucketTruth | None,
        target: ResidualBucketTarget,
    ) -> np.ndarray:
        if target.count_exact is None and target.total_cells_exact is None:
            return indexes
        feasible: list[int] = []
        for pool_i in indexes:
            max_count = self._max_add_count_for_target(
                bucket,
                target,
                pool.items[int(pool_i)],
                int(pool.n_max[int(pool_i)]),
            )
            if max_count >= int(pool.n_min[int(pool_i)]):
                feasible.append(int(pool_i))
        return np.asarray(feasible, dtype=np.int64)

    @staticmethod
    def _max_add_count_for_target(
        bucket: BucketTruth | None,
        target: ResidualBucketTarget,
        item: Item,
        default_max: int,
    ) -> int:
        max_count = max(0, int(default_max))
        current_count = bucket.count if bucket is not None else 0
        current_cells = bucket.total_cells if bucket is not None else 0
        if target.count_exact is not None:
            max_count = min(max_count, max(0, target.count_exact - current_count))
        if target.total_cells_exact is not None:
            area = item.shape_w * item.shape_h
            if area <= 0:
                return 0
            max_count = min(
                max_count,
                max(0, (target.total_cells_exact - current_cells) // area),
            )
        return max_count

    @staticmethod
    def _bucket_target_met(
        bucket: BucketTruth | None,
        target: ResidualBucketTarget,
    ) -> bool:
        cells = bucket.total_cells if bucket is not None else 0
        count = bucket.count if bucket is not None else 0
        if target.total_cells_exact is not None:
            if cells != target.total_cells_exact:
                return False
        elif target.total_cells_floor is not None and cells < target.total_cells_floor:
            return False
        if target.count_exact is not None:
            if count != target.count_exact:
                return False
        elif target.count_floor is not None and count < target.count_floor:
            return False
        value = bucket.value_sum if bucket is not None else 0
        if target.value_floor is not None and value < target.value_floor:
            return False
        return True

    def _truth_from_buckets(self, buckets: dict[int, BucketTruth]) -> SessionTruth:
        return SessionTruth(
            map_id=self.problem.map_id,
            map_name=self.problem.map_name,
            warehouse_total_cells=sum(bucket.total_cells for bucket in buckets.values()),
            buckets=buckets,
        )


def _quantiles(values: Sequence[int], weights: Sequence[float]) -> QuantileSummary | None:
    if not values:
        return None
    arr = np.asarray(values, dtype=np.float64)
    if not weights or len(weights) != len(values):
        p10, p50, p90 = np.percentile(arr, [10, 50, 90])
        return QuantileSummary(p10=float(p10), p50=float(p50), p90=float(p90))
    w = np.asarray(weights, dtype=np.float64)
    valid = w > 0
    if not np.any(valid):
        return None
    arr = arr[valid]
    w = w[valid]
    order = np.argsort(arr)
    arr = arr[order]
    w = w[order]
    cumulative = np.cumsum(w)
    total = float(cumulative[-1])
    p10, p50, p90 = np.interp(
        [0.10 * total, 0.50 * total, 0.90 * total],
        cumulative,
        arr,
    )
    return QuantileSummary(p10=float(p10), p50=float(p50), p90=float(p90))


def value_evidence_score(
    truth: SessionTruth,
    problem: ResidualProblem,
) -> float:
    """Score value floor and average-value evidence for one sampled truth."""

    score = 1.0
    for target in problem.bucket_targets.values():
        bucket = truth.buckets.get(target.quality)
        if target.value_floor is not None:
            value = bucket.value_sum if bucket is not None else 0
            if value < target.value_floor:
                return 0.0
        if target.value_exact is not None:
            value = bucket.value_sum if bucket is not None else 0
            rel_err = abs(value - target.value_exact) / max(1.0, target.value_exact)
            if rel_err <= 0.05:
                factor = 1.0
            elif rel_err <= 0.25:
                factor = max(0.35, 1.0 - rel_err * 2)
            elif rel_err <= 0.75:
                factor = max(0.10, 1.0 - rel_err)
            else:
                factor = 0.05
            score *= factor
        if target.avg_value is None:
            continue
        if bucket is None or bucket.count <= 0:
            return 0.0
        actual = bucket.value_sum / bucket.count
        rel_err = abs(actual - target.avg_value) / max(1.0, target.avg_value)
        if rel_err <= 0.10:
            factor = 1.0
        elif rel_err <= 0.50:
            factor = max(0.20, 1.0 - rel_err)
        else:
            factor = 0.10
        score *= factor
    return score


def decision_value_for_truth(truth: SessionTruth, problem: ResidualProblem) -> int:
    """Return decision value after trimming unconfirmed small rare tails."""

    exact_anchor_ids = set(problem.anchor_item_counts)
    total = 0
    for bucket in truth.buckets.values():
        for item in bucket.items:
            if item.item_id not in exact_anchor_ids and is_confusable_long_tail(item):
                continue
            total += item.value
    return total


def _relax_exact_bucket_obs(obs: SessionObs) -> tuple[SessionObs, tuple[str, ...]]:
    relaxed_buckets = {}
    relaxed: list[str] = []
    for quality, bucket in obs.buckets.items():
        cells_min = bucket.total_cells_min
        count_min = bucket.count_min
        if bucket.total_cells is not None:
            cells_min = max(cells_min or 0, bucket.total_cells)
        if bucket.count is not None:
            count_min = max(count_min or 0, bucket.count)
        if bucket.total_cells is not None or bucket.count is not None:
            relaxed.append(
                f"q{quality}:count={bucket.count}:cells={bucket.total_cells}"
            )
        relaxed_buckets[quality] = replace(
            bucket,
            total_cells=None,
            count=None,
            total_cells_min=cells_min,
            count_min=count_min,
        )
    if not relaxed:
        return obs, ()
    return replace(obs, buckets=relaxed_buckets), (
        "relaxed_exact_bucket_targets:" + ";".join(relaxed),
    )


def _estimate_posterior_for_problem(
    problem: ResidualProblem,
    obs: SessionObs,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    n_trials: int = 3000,
    seed: int = 0,
    cells_tol: int = 2,
    count_tol: int = 1,
    value_rel_tol: float = 0.10,
    warehouse_tol: int = 8,
    total_item_count_tol: int = 0,
    extra_diagnostics: tuple[str, ...] = (),
) -> PosteriorReport:
    sampler = ConditionalSampler(problem, maps=maps, drops=drops, items=items)
    rng = np.random.default_rng(seed)
    values: list[int] = []
    decision_values: list[int] = []
    cells: list[int] = []
    q6_values: list[int] = []
    weights: list[float] = []
    trials = max(0, int(n_trials))
    for _ in range(trials):
        truth = sampler.sample(rng=rng)
        if not truth_matches_obs(
            truth,
            obs,
            cells_tol=cells_tol,
            count_tol=count_tol,
            value_rel_tol=value_rel_tol,
            warehouse_tol=warehouse_tol,
            total_item_count_tol=total_item_count_tol,
        ):
            continue
        layout_score = layout_feasibility_score(truth, problem.layout)
        if layout_score <= 0:
            continue
        value_score = value_evidence_score(truth, problem)
        if value_score <= 0:
            continue
        weight = category_observation_soft_score(truth, obs) * layout_score * value_score
        values.append(truth.total_value())
        decision_values.append(decision_value_for_truth(truth, problem))
        cells.append(truth.warehouse_total_cells)
        q6_bucket = truth.buckets.get(6)
        q6_values.append(q6_bucket.value_sum if q6_bucket is not None else 0)
        weights.append(weight)
    diagnostics = [*extra_diagnostics, *problem.diagnostics]
    q6_match_count = sum(1 for value in q6_values if value > 0)
    q6_match_rate = q6_match_count / len(q6_values) if q6_values else None
    if 6 not in problem.bucket_targets and q6_match_rate is not None and q6_match_rate < 0.10:
        diagnostics.append(f"q6_unconstrained_low_sample_rate:{q6_match_rate:.3f}")
    return PosteriorReport(
        map_id=problem.map_id,
        map_name=problem.map_name,
        n_total=trials,
        n_matched=len(values),
        total_cells=_quantiles(cells, weights),
        total_value=_quantiles(values, weights),
        anchor_count=problem.known_item_count,
        known_cells=problem.known_cells,
        known_value=problem.known_value,
        layout_score=problem.layout.score,
        decision_value=_quantiles(decision_values, weights),
        q6_match_rate=q6_match_rate,
        q6_value=_quantiles(q6_values, weights),
        layout_diagnostics=problem.layout.diagnostics,
        diagnostics=tuple(diagnostics),
    )


def estimate_posterior_v2(
    map_id: int,
    obs: SessionObs,
    store: EvidenceStore,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    n_trials: int = 3000,
    seed: int = 0,
    cells_tol: int = 2,
    count_tol: int = 1,
    value_rel_tol: float = 0.10,
    warehouse_tol: int = 8,
    total_item_count_tol: int = 0,
) -> PosteriorReport:
    """Estimate a posterior with exact item anchors forced into every trial."""

    problem = build_residual_problem(
        map_id,
        store,
        maps=maps,
        drops=drops,
        items=items,
        obs=obs,
    )
    strict = _estimate_posterior_for_problem(
        problem,
        obs,
        maps=maps,
        drops=drops,
        items=items,
        n_trials=n_trials,
        seed=seed,
        cells_tol=cells_tol,
        count_tol=count_tol,
        value_rel_tol=value_rel_tol,
        warehouse_tol=warehouse_tol,
        total_item_count_tol=total_item_count_tol,
    )
    if strict.n_matched > 0:
        return strict

    relaxed_obs, diagnostics = _relax_exact_bucket_obs(obs)
    if not diagnostics:
        return strict
    relaxed_problem = build_residual_problem(
        map_id,
        store,
        maps=maps,
        drops=drops,
        items=items,
        obs=relaxed_obs,
    )
    return _estimate_posterior_for_problem(
        relaxed_problem,
        relaxed_obs,
        maps=maps,
        drops=drops,
        items=items,
        n_trials=n_trials,
        seed=seed,
        cells_tol=cells_tol,
        count_tol=count_tol,
        value_rel_tol=value_rel_tol,
        warehouse_tol=warehouse_tol,
        total_item_count_tol=total_item_count_tol,
        extra_diagnostics=diagnostics,
    )


__all__ = (
    "ConditionalSampler",
    "EvidenceFact",
    "EvidenceStore",
    "EvidenceStoreBuilder",
    "KnownItemAnchor",
    "KnownFootprint",
    "LayoutFeasibility",
    "PosteriorReport",
    "ResidualBucketTarget",
    "ResidualProblem",
    "RuntimeEvidence",
    "build_residual_problem",
    "decision_value_for_truth",
    "estimate_posterior_v2",
    "evidence_store_from_fatbeans_events",
    "known_footprints",
    "known_item_anchors",
    "layout_feasibility_from_store",
    "layout_feasibility_score",
    "value_evidence_score",
)
