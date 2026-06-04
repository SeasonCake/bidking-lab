"""Summary-conditioned v3 posterior shadow sampler."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.ground_truth import SessionTruth, prepare_session_sampler
from bidking_lab.inference.map_likelihood import QuantileSummary
from bidking_lab.inference.v3.constraints import ConstraintSet, ItemAnchor, ShapeAnchor
from bidking_lab.inference.v3.summary import BucketFeasibleSummary, FeasibleSummaryReport
from bidking_lab.inference.v3.truth import decision_truth_from_session_truth

_DEFAULT_PRACTICAL_P50_GUARD_QUANTILE = 0.60
_HIGH_TAIL_PRACTICAL_P50_GUARD_QUANTILE = 0.65
_LOW_TAIL_PRACTICAL_P50_GUARD_QUANTILE = 0.55
_HIGH_TAIL_MAP_IDS = frozenset((2404, 2501, 2503, 2506, 2601))
_LOW_TAIL_MAP_IDS = frozenset((2407, 2410, 2505, 2507, 2508))


@dataclass(frozen=True)
class V3PosteriorReport:
    map_id: int
    map_name: str
    n_total: int
    n_matched: int
    n_strict_matched: int
    match_scope: str
    q6_present_rate: float | None
    total_cells: QuantileSummary | None
    total_value: QuantileSummary | None
    formal_decision_value: QuantileSummary | None
    tail_replacement_decision_value: QuantileSummary | None
    q6_count: QuantileSummary | None
    q6_cells: QuantileSummary | None
    q6_value: QuantileSummary | None
    q6_formal_decision_value: QuantileSummary | None
    q6_tail_replacement_decision_value: QuantileSummary | None
    diagnostics: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.n_matched > 0

    @property
    def strict_ready(self) -> bool:
        return self.n_strict_matched > 0

    @property
    def match_rate(self) -> float:
        if self.n_total <= 0:
            return 0.0
        return self.n_matched / self.n_total

    @property
    def strict_match_rate(self) -> float:
        if self.n_total <= 0:
            return 0.0
        return self.n_strict_matched / self.n_total

    def to_flat_dict(self, *, prefix: str = "v3_post_") -> dict[str, Any]:
        out = {
            f"{prefix}available": True,
            f"{prefix}ready": self.ready,
            f"{prefix}strict_ready": self.strict_ready,
            f"{prefix}affects_bid": False,
            f"{prefix}map_id": self.map_id,
            f"{prefix}map_name": self.map_name,
            f"{prefix}match_scope": self.match_scope,
            f"{prefix}n_total": self.n_total,
            f"{prefix}n_matched": self.n_matched,
            f"{prefix}n_strict_matched": self.n_strict_matched,
            f"{prefix}match_rate": round(self.match_rate, 6),
            f"{prefix}strict_match_rate": round(self.strict_match_rate, 6),
            f"{prefix}q6_present_rate": (
                round(self.q6_present_rate, 6)
                if self.q6_present_rate is not None
                else None
            ),
            f"{prefix}diagnostics": ";".join(self.diagnostics),
        }
        out.update(_quantile_flat(f"{prefix}total_cells", self.total_cells))
        out.update(_quantile_flat(f"{prefix}total_value", self.total_value))
        out.update(_quantile_flat(f"{prefix}formal_decision_value", self.formal_decision_value))
        out.update(_quantile_flat(
            f"{prefix}tail_replacement_decision_value",
            self.tail_replacement_decision_value,
        ))
        out.update(_quantile_flat(f"{prefix}q6_count", self.q6_count))
        out.update(_quantile_flat(f"{prefix}q6_cells", self.q6_cells))
        out.update(_quantile_flat(f"{prefix}q6_value", self.q6_value))
        out.update(_quantile_flat(
            f"{prefix}q6_formal_decision_value",
            self.q6_formal_decision_value,
        ))
        out.update(_quantile_flat(
            f"{prefix}q6_tail_replacement_decision_value",
            self.q6_tail_replacement_decision_value,
        ))
        return out


def _quantile_flat(name: str, summary: QuantileSummary | None) -> dict[str, Any]:
    return {
        f"{name}_p10": round(summary.p10, 6) if summary is not None else None,
        f"{name}_p50": round(summary.p50, 6) if summary is not None else None,
        f"{name}_p90": round(summary.p90, 6) if summary is not None else None,
    }


def _quantiles(values: Sequence[int | float]) -> QuantileSummary | None:
    if not values:
        return None
    arr = np.asarray(tuple(values), dtype=np.float64)
    return QuantileSummary(
        p10=float(np.quantile(arr, 0.10)),
        p50=float(np.quantile(arr, 0.50)),
        p90=float(np.quantile(arr, 0.90)),
    )


def _quantile_value(values: Sequence[int | float], probability: float) -> float | None:
    if not values:
        return None
    arr = np.asarray(tuple(values), dtype=np.float64)
    return float(np.quantile(arr, probability))


def _weighted_quantiles(
    values: Sequence[int | float],
    weights: Sequence[float] | None,
    *,
    p50_tail_guard: bool = False,
    p90_tail_guard: bool = False,
    p50_guard_quantile: float = _DEFAULT_PRACTICAL_P50_GUARD_QUANTILE,
) -> QuantileSummary | None:
    if weights is None:
        return _quantiles(values)
    if not values:
        return None
    pairs = sorted(
        (float(value), float(weight))
        for value, weight in zip(values, weights, strict=True)
        if math.isfinite(float(weight)) and float(weight) > 0.0
    )
    if not pairs:
        return None
    arr = np.asarray([value for value, _ in pairs], dtype=np.float64)
    w = np.asarray([weight for _, weight in pairs], dtype=np.float64)
    total = float(w.sum())
    if total <= 0.0 or not math.isfinite(total):
        return None
    cumulative = np.cumsum(w)

    def pick(probability: float) -> float:
        index = int(np.searchsorted(cumulative, probability * total, side="left"))
        return float(arr[min(index, len(arr) - 1)])

    p50 = pick(0.50)
    p90 = pick(0.90)
    if p50_tail_guard or p90_tail_guard:
        unweighted = _quantiles(values)
        if p50_tail_guard and unweighted is not None:
            practical_p50 = _quantile_value(values, p50_guard_quantile)
            p50 = max(
                p50,
                practical_p50 if practical_p50 is not None else unweighted.p50,
            )
        if p90_tail_guard and unweighted is not None:
            p90 = max(p90, unweighted.p90)
    return QuantileSummary(p10=pick(0.10), p50=p50, p90=p90)


def _practical_p50_guard_quantile(map_id: int) -> float:
    if int(map_id) in _HIGH_TAIL_MAP_IDS:
        return _HIGH_TAIL_PRACTICAL_P50_GUARD_QUANTILE
    if int(map_id) in _LOW_TAIL_MAP_IDS:
        return _LOW_TAIL_PRACTICAL_P50_GUARD_QUANTILE
    return _DEFAULT_PRACTICAL_P50_GUARD_QUANTILE


def _guard_quantiles(
    summary: QuantileSummary | None,
    *,
    floor: int | float | None = None,
    exact: int | float | None = None,
) -> QuantileSummary | None:
    if summary is None:
        return None
    if exact is not None:
        value = float(exact)
        return QuantileSummary(p10=value, p50=value, p90=value)
    if floor is None:
        return summary
    value = float(floor)
    if value <= 0:
        return summary
    return QuantileSummary(
        p10=max(summary.p10, value),
        p50=max(summary.p50, value),
        p90=max(summary.p90, value),
    )


def sample_truth_bank(
    map_id: int,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    n_trials: int,
    seed: int = 0,
) -> tuple[SessionTruth, ...]:
    """Sample reusable prior truths for one map."""

    sampler = prepare_session_sampler(
        int(map_id),
        maps=maps,
        drops=drops,
        items=items,
    )
    rng = np.random.default_rng(int(seed) + int(map_id))
    return tuple(sampler.sample(rng=rng) for _ in range(max(0, int(n_trials))))


def _bucket_fields(truth: SessionTruth, quality: int) -> tuple[int, int, int]:
    bucket = truth.buckets.get(quality)
    if bucket is None:
        return 0, 0, 0
    return int(bucket.count), int(bucket.total_cells), int(bucket.value_sum)


def _truth_total_count(truth: SessionTruth) -> int:
    return sum(int(bucket.count) for bucket in truth.buckets.values())


def _truth_items(truth: SessionTruth) -> tuple[Item, ...]:
    return tuple(item for bucket in truth.buckets.values() for item in bucket.items)


def _bucket_matches(
    truth: SessionTruth,
    bucket: BucketFeasibleSummary,
) -> bool:
    count, cells, value = _bucket_fields(truth, bucket.quality)
    if bucket.count_exact is not None and count != int(bucket.count_exact):
        return False
    if bucket.cells_exact is not None and cells != int(bucket.cells_exact):
        return False
    if bucket.value_exact is not None and value != int(bucket.value_exact):
        return False
    if count < int(bucket.count_floor):
        return False
    if cells < int(bucket.cells_floor):
        return False
    if value < int(bucket.value_floor):
        return False
    return True


def _bucket_has_constraints(bucket: BucketFeasibleSummary | None) -> bool:
    if bucket is None:
        return False
    return any(
        value is not None
        for value in (bucket.count_exact, bucket.cells_exact, bucket.value_exact)
    ) or any(
        int(value) > 0
        for value in (bucket.count_floor, bucket.cells_floor, bucket.value_floor)
    )


def _bucket_has_value_constraint(bucket: BucketFeasibleSummary | None) -> bool:
    if bucket is None:
        return False
    return bucket.value_exact is not None or int(bucket.value_floor) > 0


def truth_matches_feasible_summary(
    truth: SessionTruth,
    summary: FeasibleSummaryReport,
) -> bool:
    if not summary.feasible:
        return False
    if (
        summary.session_total_count_exact is not None
        and _truth_total_count(truth) != int(summary.session_total_count_exact)
    ):
        return False
    if (
        summary.session_total_cells_exact is not None
        and int(truth.warehouse_total_cells) != int(summary.session_total_cells_exact)
    ):
        return False
    return all(_bucket_matches(truth, bucket) for bucket in summary.buckets)


def _likelihood_scale(target: int | float, *, base: float, ratio: float) -> float:
    return max(float(base), abs(float(target)) * float(ratio))


def _exact_log_likelihood(
    value: int | float,
    target: int | float | None,
    *,
    base_scale: float,
    ratio_scale: float,
    importance: float,
) -> float:
    if target is None:
        return 0.0
    diff = abs(float(value) - float(target))
    if diff <= 0.0:
        return 0.0
    scale = _likelihood_scale(target, base=base_scale, ratio=ratio_scale)
    return -float(importance) * (diff / scale) ** 2


def _floor_log_likelihood(
    value: int | float,
    floor: int | float | None,
    *,
    base_scale: float,
    ratio_scale: float,
    importance: float,
) -> float:
    if floor is None:
        return 0.0
    deficit = max(0.0, float(floor) - float(value))
    if deficit <= 0.0:
        return 0.0
    scale = _likelihood_scale(floor, base=base_scale, ratio=ratio_scale)
    return -float(importance) * (deficit / scale) ** 2


def _bucket_log_likelihood(
    truth: SessionTruth,
    bucket: BucketFeasibleSummary,
) -> float:
    count, cells, value = _bucket_fields(truth, bucket.quality)
    q6_boost = 1.45 if int(bucket.quality) == 6 else 1.0
    return sum((
        _exact_log_likelihood(
            count,
            bucket.count_exact,
            base_scale=1.0,
            ratio_scale=0.30,
            importance=1.65 * q6_boost,
        ),
        _exact_log_likelihood(
            cells,
            bucket.cells_exact,
            base_scale=5.0,
            ratio_scale=0.22,
            importance=1.35 * q6_boost,
        ),
        _exact_log_likelihood(
            value,
            bucket.value_exact,
            base_scale=90_000.0,
            ratio_scale=0.30,
            importance=0.85 * q6_boost,
        ),
        _floor_log_likelihood(
            count,
            bucket.count_floor,
            base_scale=1.0,
            ratio_scale=0.35,
            importance=1.30 * q6_boost,
        ),
        _floor_log_likelihood(
            cells,
            bucket.cells_floor,
            base_scale=5.0,
            ratio_scale=0.25,
            importance=1.05 * q6_boost,
        ),
        _floor_log_likelihood(
            value,
            bucket.value_floor,
            base_scale=90_000.0,
            ratio_scale=0.35,
            importance=0.70 * q6_boost,
        ),
    ))


def _shape_dimensions(shape_key: str | int | None) -> tuple[int, int] | None:
    if shape_key in (None, ""):
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


def _item_area(item: Item) -> int:
    return int(item.shape_w) * int(item.shape_h)


def _item_matches_categories(item: Item, categories: tuple[int, ...]) -> bool:
    if not categories:
        return True
    item_categories = {int(category) for category in item.tags}
    return any(int(category) in item_categories for category in categories)


def _item_anchor_weight(anchor: ItemAnchor) -> float:
    weight = 0.0
    if anchor.item_id is not None:
        weight += 3.0
    if anchor.value is not None:
        weight += 2.0
    if anchor.categories:
        weight += 1.5
    if anchor.shape_key is not None or anchor.cells is not None:
        weight += 1.0
    if anchor.quality is not None:
        weight += 0.5
    return max(weight, 0.5)


def _shape_anchor_weight(anchor: ShapeAnchor) -> float:
    weight = 1.0
    if anchor.quality is not None:
        weight += 0.5
    if anchor.item_id is not None:
        weight += 1.5
    return weight


def _item_matches_item_anchor(item: Item, anchor: ItemAnchor) -> bool:
    if anchor.item_id is not None and int(item.item_id) != int(anchor.item_id):
        return False
    if anchor.quality is not None and int(item.quality) != int(anchor.quality):
        return False
    if anchor.value is not None and int(item.value) != int(anchor.value):
        return False
    if anchor.cells is not None and _item_area(item) != int(anchor.cells):
        return False
    dims = _shape_dimensions(anchor.shape_key)
    if dims is not None and (int(item.shape_w), int(item.shape_h)) != dims:
        return False
    if not _item_matches_categories(item, anchor.categories):
        return False
    return True


def _item_matches_shape_anchor(item: Item, anchor: ShapeAnchor) -> bool:
    if anchor.item_id is not None and int(item.item_id) != int(anchor.item_id):
        return False
    if anchor.quality is not None and int(item.quality) != int(anchor.quality):
        return False
    if _item_area(item) != int(anchor.cells):
        return False
    dims = _shape_dimensions(anchor.shape_key)
    if dims is not None and (int(item.shape_w), int(item.shape_h)) != dims:
        return False
    return True


def _consume_best_match(
    items: tuple[Item, ...],
    used: set[int],
    predicate: Any,
) -> bool:
    for index, item in enumerate(items):
        if index in used:
            continue
        if predicate(item):
            used.add(index)
            return True
    return False


def _anchor_log_likelihood(
    truth: SessionTruth,
    constraints: ConstraintSet | None,
) -> float:
    if constraints is None:
        return 0.0
    items = _truth_items(truth)
    if not items:
        return 0.0
    used: set[int] = set()
    miss_weight = 0.0
    total_weight = 0.0
    for anchor in constraints.item_anchors.values():
        weight = _item_anchor_weight(anchor)
        total_weight += weight
        matched = _consume_best_match(
            items,
            used,
            lambda item, anchor=anchor: _item_matches_item_anchor(item, anchor),
        )
        if not matched:
            miss_weight += weight
    for anchor in constraints.shape_anchors.values():
        if anchor.key in constraints.item_anchors:
            continue
        weight = _shape_anchor_weight(anchor)
        total_weight += weight
        matched = _consume_best_match(
            items,
            used,
            lambda item, anchor=anchor: _item_matches_shape_anchor(item, anchor),
        )
        if not matched:
            miss_weight += weight
    if total_weight <= 0.0:
        return 0.0
    miss_ratio = miss_weight / total_weight
    return -min(18.0, 0.75 * miss_weight + 3.0 * miss_ratio * miss_ratio)


def _anchor_likelihood_weights(
    truths: Sequence[SessionTruth],
    constraints: ConstraintSet | None,
    *,
    temperature: float = 4.0,
    relative_floor: float = 1e-8,
) -> tuple[tuple[float, ...] | None, float]:
    if constraints is None or not truths:
        return None, 0.0
    if not constraints.item_anchors and not constraints.shape_anchors:
        return None, 0.0
    log_weights = np.asarray(
        [_anchor_log_likelihood(truth, constraints) for truth in truths],
        dtype=np.float64,
    )
    finite = np.isfinite(log_weights)
    if not finite.any():
        return None, 0.0
    max_log = float(log_weights[finite].max())
    relative = np.zeros(len(log_weights), dtype=np.float64)
    relative[finite] = np.exp(
        (log_weights[finite] - max_log) / max(float(temperature), 1e-9)
    )
    keep = relative >= max(float(relative_floor), 0.0)
    if not keep.any():
        return None, 0.0
    weights = relative[keep]
    if len(weights) != len(truths):
        return None, 0.0
    total = float(weights.sum())
    if total <= 0.0:
        return None, 0.0
    ess = float(total * total / float(np.square(weights).sum()))
    return tuple(float(weight) for weight in weights), ess


def _summary_log_likelihood(
    truth: SessionTruth,
    summary: FeasibleSummaryReport,
    *,
    constraints: ConstraintSet | None = None,
) -> float:
    total_count = _truth_total_count(truth)
    total_cells = int(truth.warehouse_total_cells)
    total_value = int(truth.total_value())
    score = sum((
        _exact_log_likelihood(
            total_count,
            summary.session_total_count_exact,
            base_scale=2.0,
            ratio_scale=0.12,
            importance=1.20,
        ),
        _exact_log_likelihood(
            total_cells,
            summary.session_total_cells_exact,
            base_scale=8.0,
            ratio_scale=0.12,
            importance=1.35,
        ),
        _floor_log_likelihood(
            total_count,
            summary.known_count_floor,
            base_scale=2.0,
            ratio_scale=0.20,
            importance=0.80,
        ),
        _floor_log_likelihood(
            total_cells,
            summary.known_cells_floor,
            base_scale=8.0,
            ratio_scale=0.20,
            importance=0.80,
        ),
        _floor_log_likelihood(
            total_value,
            summary.known_value_floor,
            base_scale=120_000.0,
            ratio_scale=0.35,
            importance=0.55,
        ),
    ))
    for bucket in summary.buckets:
        score += _bucket_log_likelihood(truth, bucket)
    score += _anchor_log_likelihood(truth, constraints)
    return score


def _summary_likelihood_matches(
    truths: Sequence[SessionTruth],
    summary: FeasibleSummaryReport,
    constraints: ConstraintSet | None,
    *,
    relative_floor: float = 1e-8,
    temperature: float = 4.0,
) -> tuple[tuple[SessionTruth, ...], tuple[float, ...], float]:
    if not truths:
        return (), (), 0.0
    log_weights = np.asarray(
        [
            _summary_log_likelihood(truth, summary, constraints=constraints)
            for truth in truths
        ],
        dtype=np.float64,
    )
    finite = np.isfinite(log_weights)
    if not finite.any():
        return (), (), 0.0
    max_log = float(log_weights[finite].max())
    relative = np.zeros(len(log_weights), dtype=np.float64)
    relative[finite] = np.exp(
        (log_weights[finite] - max_log) / max(float(temperature), 1e-9)
    )
    keep = relative >= max(float(relative_floor), 0.0)
    if not keep.any():
        keep[int(np.argmax(relative))] = True
    weights = relative[keep]
    total = float(weights.sum())
    ess = float(total * total / float(np.square(weights).sum())) if total > 0 else 0.0
    matched = tuple(truth for truth, use in zip(truths, keep, strict=True) if bool(use))
    return matched, tuple(float(weight) for weight in weights), ess


def _bucket_conditioned_truths(
    truths: Sequence[SessionTruth],
    bucket: BucketFeasibleSummary | None,
) -> tuple[SessionTruth, ...]:
    if not _bucket_has_constraints(bucket):
        return ()
    assert bucket is not None
    return tuple(truth for truth in truths if _bucket_matches(truth, bucket))


def estimate_q6_posterior_from_truths(
    *,
    map_id: int,
    map_name: str,
    summary: FeasibleSummaryReport,
    truths: Sequence[SessionTruth],
    constraints: ConstraintSet | None = None,
    replacement_values: Mapping[tuple[int, int, int], int] | None = None,
) -> V3PosteriorReport:
    diagnostics: list[str] = []
    n_total = len(truths)
    if not summary.feasible:
        diagnostics.append("summary_infeasible")
    strict_matched = tuple(
        truth
        for truth in truths
        if truth_matches_feasible_summary(truth, summary)
    )
    matched = strict_matched
    matched_weights: tuple[float, ...] | None = None
    match_scope = "strict"
    if strict_matched:
        matched_weights, effective_n = _anchor_likelihood_weights(
            strict_matched,
            constraints,
        )
        if matched_weights is not None:
            diagnostics.append("anchor_likelihood_weighted")
            diagnostics.append(f"anchor_likelihood_effective_samples={effective_n:.3f}")
    if n_total <= 0:
        diagnostics.append("no_prior_samples")
    if n_total > 0 and not strict_matched and summary.feasible:
        diagnostics.append("no_strict_summary_matched_samples")
        matched, matched_weights, effective_n = _summary_likelihood_matches(
            truths,
            summary,
            constraints,
        )
        if matched:
            match_scope = "summary_likelihood"
            diagnostics.append("summary_likelihood_fallback")
            diagnostics.append(
                f"summary_likelihood_effective_samples={effective_n:.3f}"
            )
        else:
            diagnostics.append("no_summary_likelihood_samples")
            q6_summary = summary.bucket(6)
            q6_projection = FeasibleSummaryReport(
                session_total_count_exact=None,
                session_total_cells_exact=None,
                known_count_floor=0,
                known_cells_floor=0,
                known_value_floor=0,
                buckets=(q6_summary,) if q6_summary is not None else (),
            )
            matched = tuple(
                truth
                for truth in truths
                if truth_matches_feasible_summary(truth, q6_projection)
            )
            matched_weights = None
            if matched:
                match_scope = "q6_projection"
                diagnostics.append("q6_projection_fallback")
            else:
                diagnostics.append("no_q6_projection_matched_samples")
    elif not summary.feasible:
        matched = ()
        matched_weights = None
    q6_counts: list[int] = []
    q6_cells: list[int] = []
    q6_values: list[int] = []
    total_cells: list[int] = []
    total_values: list[int] = []
    formal_decision_values: list[int] = []
    tail_replacement_decision_values: list[int] = []
    q6_formal_decision_values: list[int] = []
    q6_tail_replacement_decision_values: list[int] = []
    q6_summary = summary.bucket(6)
    for truth in matched:
        count, cells, value = _bucket_fields(truth, 6)
        q6_counts.append(count)
        q6_cells.append(cells)
        q6_values.append(value)
        total_cells.append(int(truth.warehouse_total_cells))
        total_values.append(int(truth.total_value()))
        if constraints is not None:
            decision = decision_truth_from_session_truth(
                truth,
                constraints=constraints,
                replacement_values=replacement_values or {},
            )
            formal_decision_values.append(decision.formal_decision_value)
            tail_replacement_decision_values.append(
                decision.tail_replacement_decision_value
            )
            q6_formal_decision_values.append(decision.q6_formal_decision_value)
            q6_tail_replacement_decision_values.append(
                decision.q6_tail_replacement_decision_value
            )
    total_cells_for_quantiles = total_cells
    total_values_for_quantiles = total_values
    formal_decision_values_for_quantiles = formal_decision_values
    tail_replacement_decision_values_for_quantiles = tail_replacement_decision_values
    q6_counts_for_quantiles = q6_counts
    q6_cells_for_quantiles = q6_cells
    q6_values_for_quantiles = q6_values
    q6_formal_decision_values_for_quantiles = q6_formal_decision_values
    q6_tail_replacement_values_for_quantiles = q6_tail_replacement_decision_values
    total_weights_for_quantiles = matched_weights
    q6_count_cell_weights_for_quantiles = matched_weights
    q6_value_weights_for_quantiles = matched_weights
    if match_scope == "summary_likelihood" and _bucket_has_constraints(q6_summary):
        q6_conditioned = _bucket_conditioned_truths(truths, q6_summary)
        if q6_conditioned:
            conditioned_weights, effective_n = _anchor_likelihood_weights(
                q6_conditioned,
                constraints,
            )
            diagnostics.append(
                f"q6_bucket_conditioned_samples={len(q6_conditioned)}"
            )
            if conditioned_weights is not None:
                diagnostics.append(
                    "q6_bucket_conditioned_anchor_likelihood_weighted"
                )
                diagnostics.append(
                    f"q6_bucket_conditioned_effective_samples={effective_n:.3f}"
                )
            conditioned_counts: list[int] = []
            conditioned_cells: list[int] = []
            conditioned_values: list[int] = []
            conditioned_q6_formal_values: list[int] = []
            conditioned_q6_tail_values: list[int] = []
            for truth in q6_conditioned:
                count, cells, value = _bucket_fields(truth, 6)
                conditioned_counts.append(count)
                conditioned_cells.append(cells)
                conditioned_values.append(value)
                if constraints is not None:
                    decision = decision_truth_from_session_truth(
                        truth,
                        constraints=constraints,
                        replacement_values=replacement_values or {},
                    )
                    conditioned_q6_formal_values.append(
                        decision.q6_formal_decision_value
                    )
                    conditioned_q6_tail_values.append(
                        decision.q6_tail_replacement_decision_value
                    )
            q6_counts_for_quantiles = conditioned_counts
            q6_cells_for_quantiles = conditioned_cells
            conditioned_weights_for_quantiles = conditioned_weights or tuple(
                1.0 for _ in conditioned_counts
            )
            q6_count_cell_weights_for_quantiles = conditioned_weights_for_quantiles
            condition_q6_value = _bucket_has_value_constraint(q6_summary)
            if condition_q6_value:
                q6_values_for_quantiles = conditioned_values
                q6_value_weights_for_quantiles = conditioned_weights_for_quantiles
            if condition_q6_value and conditioned_q6_formal_values:
                q6_formal_decision_values_for_quantiles = (
                    conditioned_q6_formal_values
                )
                q6_tail_replacement_values_for_quantiles = conditioned_q6_tail_values
            if (
                condition_q6_value
                and conditioned_values
                and total_values
                and len(q6_values) == len(total_values)
            ):
                total_cells_for_quantiles = [
                    max(0, total - q6_total) + conditioned_cells[
                        index % len(conditioned_cells)
                    ]
                    for index, (total, q6_total) in enumerate(
                        zip(total_cells, q6_cells, strict=True)
                    )
                ]
                total_values_for_quantiles = [
                    max(0, total - q6_total) + conditioned_values[
                        index % len(conditioned_values)
                    ]
                    for index, (total, q6_total) in enumerate(
                        zip(total_values, q6_values, strict=True)
                    )
                ]
            if (
                condition_q6_value
                and conditioned_q6_formal_values
                and formal_decision_values
                and len(q6_formal_decision_values) == len(formal_decision_values)
            ):
                diagnostics.append("q6_bucket_conditioned_formal_adjustment")
                formal_decision_values_for_quantiles = [
                    max(0, total - q6_total) + conditioned_q6_formal_values[
                        index % len(conditioned_q6_formal_values)
                    ]
                    for index, (total, q6_total) in enumerate(
                        zip(
                            formal_decision_values,
                            q6_formal_decision_values,
                            strict=True,
                        )
                    )
                ]
                tail_replacement_decision_values_for_quantiles = [
                    max(0, total - q6_total) + conditioned_q6_tail_values[
                        index % len(conditioned_q6_tail_values)
                    ]
                    for index, (total, q6_total) in enumerate(
                        zip(
                            tail_replacement_decision_values,
                            q6_tail_replacement_decision_values,
                            strict=True,
                        )
                    )
                ]
    q6_present_rate = (
        sum(1 for count in q6_counts_for_quantiles if count > 0)
        / len(q6_counts_for_quantiles)
        if q6_counts_for_quantiles
        else None
    )
    if q6_counts_for_quantiles and q6_count_cell_weights_for_quantiles is not None:
        weight_total = sum(q6_count_cell_weights_for_quantiles)
        q6_present_rate = (
            sum(
                weight
                for count, weight in zip(
                    q6_counts_for_quantiles,
                    q6_count_cell_weights_for_quantiles,
                    strict=True,
                )
                if count > 0
            )
            / weight_total
            if weight_total > 0
            else None
        )
    tail_guard = matched_weights is not None
    q6_count_exact = q6_summary.count_exact if q6_summary is not None else None
    q6_cells_exact = q6_summary.cells_exact if q6_summary is not None else None
    q6_value_exact = q6_summary.value_exact if q6_summary is not None else None
    q6_count_floor = q6_summary.count_floor if q6_summary is not None else 0
    q6_cells_floor = q6_summary.cells_floor if q6_summary is not None else 0
    q6_value_floor = q6_summary.value_floor if q6_summary is not None else 0
    p50_guard_quantile = _practical_p50_guard_quantile(int(map_id))
    if tail_guard:
        diagnostics.append(f"practical_p50_guard_quantile={p50_guard_quantile:.2f}")
    return V3PosteriorReport(
        map_id=int(map_id),
        map_name=map_name,
        n_total=n_total,
        n_matched=len(matched),
        n_strict_matched=len(strict_matched),
        match_scope=match_scope,
        q6_present_rate=q6_present_rate,
        total_cells=_guard_quantiles(
            _weighted_quantiles(
                total_cells_for_quantiles,
                total_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=summary.known_cells_floor,
            exact=summary.session_total_cells_exact,
        ),
        total_value=_guard_quantiles(
            _weighted_quantiles(
                total_values_for_quantiles,
                total_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=summary.known_value_floor,
        ),
        formal_decision_value=_guard_quantiles(
            _weighted_quantiles(
                formal_decision_values_for_quantiles,
                total_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=summary.known_value_floor,
        ),
        tail_replacement_decision_value=_guard_quantiles(
            _weighted_quantiles(
                tail_replacement_decision_values_for_quantiles,
                total_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=summary.known_value_floor,
        ),
        q6_count=_guard_quantiles(
            _weighted_quantiles(
                q6_counts_for_quantiles,
                q6_count_cell_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=q6_count_floor,
            exact=q6_count_exact,
        ),
        q6_cells=_guard_quantiles(
            _weighted_quantiles(
                q6_cells_for_quantiles,
                q6_count_cell_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=q6_cells_floor,
            exact=q6_cells_exact,
        ),
        q6_value=_guard_quantiles(
            _weighted_quantiles(
                q6_values_for_quantiles,
                q6_value_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=q6_value_floor,
            exact=q6_value_exact,
        ),
        q6_formal_decision_value=_guard_quantiles(
            _weighted_quantiles(
                q6_formal_decision_values_for_quantiles,
                q6_value_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=q6_value_floor,
        ),
        q6_tail_replacement_decision_value=_guard_quantiles(
            _weighted_quantiles(
                q6_tail_replacement_values_for_quantiles,
                q6_value_weights_for_quantiles,
                p50_tail_guard=tail_guard,
                p90_tail_guard=tail_guard,
                p50_guard_quantile=p50_guard_quantile,
            ),
            floor=q6_value_floor,
        ),
        diagnostics=tuple(diagnostics),
    )


def empty_posterior_flat_dict(*, prefix: str = "v3_post_") -> dict[str, Any]:
    out = {
        f"{prefix}available": False,
        f"{prefix}ready": False,
        f"{prefix}strict_ready": False,
        f"{prefix}affects_bid": False,
        f"{prefix}map_id": None,
        f"{prefix}map_name": None,
        f"{prefix}match_scope": None,
        f"{prefix}n_total": None,
        f"{prefix}n_matched": None,
        f"{prefix}n_strict_matched": None,
        f"{prefix}match_rate": None,
        f"{prefix}strict_match_rate": None,
        f"{prefix}q6_present_rate": None,
        f"{prefix}diagnostics": None,
    }
    for name in (
        "total_cells",
        "total_value",
        "formal_decision_value",
        "tail_replacement_decision_value",
        "q6_count",
        "q6_cells",
        "q6_value",
        "q6_formal_decision_value",
        "q6_tail_replacement_decision_value",
    ):
        out.update(_quantile_flat(f"{prefix}{name}", None))
    return out


__all__ = (
    "V3PosteriorReport",
    "empty_posterior_flat_dict",
    "estimate_q6_posterior_from_truths",
    "sample_truth_bank",
    "truth_matches_feasible_summary",
)
