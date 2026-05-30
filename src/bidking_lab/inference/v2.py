"""Evidence-first inference v2 primitives.

The v1 live posterior samples a whole auction session and then rejects samples
that do not match observations. That works for low-information states, but it
breaks down once packet captures provide exact runtime/item facts. This module
keeps v2 separate so realtime code can compare both engines before switching.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
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
from bidking_lab.inference.observation import SessionObs

EvidenceStrength = Literal["hard", "soft"]


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
class ResidualProblem:
    """Map problem after exact known items have been anchored."""

    map_id: int
    map_name: str
    anchors: tuple[KnownItemAnchor, ...]
    known_item_count: int
    known_cells: int
    known_value: int
    anchor_item_counts: Mapping[int, int]
    diagnostics: tuple[str, ...] = ()


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


def build_residual_problem(
    map_id: int,
    store: EvidenceStore,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
) -> ResidualProblem:
    """Create a residual problem by forcing exact known items into every sample."""

    bid_map = maps[map_id]
    anchors = known_item_anchors(store, items=items)
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
    return ResidualProblem(
        map_id=map_id,
        map_name=bid_map.name,
        anchors=anchors,
        known_item_count=len(anchors),
        known_cells=sum(anchor.cells for anchor in anchors),
        known_value=sum(anchor.value for anchor in anchors),
        anchor_item_counts=dict(counts),
        diagnostics=tuple(diagnostics),
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

        total_draws = int(
            rng.integers(
                self._sampler.items_per_session_min,
                self._sampler.items_per_session_max + 1,
            )
        )
        residual_draws = max(0, total_draws - self.problem.known_item_count)
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
    )
    sampler = ConditionalSampler(problem, maps=maps, drops=drops, items=items)
    rng = np.random.default_rng(seed)
    values: list[int] = []
    cells: list[int] = []
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
        weight = category_observation_soft_score(truth, obs)
        values.append(truth.total_value())
        cells.append(truth.warehouse_total_cells)
        weights.append(weight)
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
        diagnostics=problem.diagnostics,
    )


__all__ = (
    "ConditionalSampler",
    "EvidenceFact",
    "EvidenceStore",
    "EvidenceStoreBuilder",
    "KnownItemAnchor",
    "PosteriorReport",
    "ResidualProblem",
    "RuntimeEvidence",
    "build_residual_problem",
    "estimate_posterior_v2",
    "evidence_store_from_fatbeans_events",
    "known_item_anchors",
)
