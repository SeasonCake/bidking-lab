"""Summary-conditioned v3 posterior shadow sampler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.ground_truth import SessionTruth, prepare_session_sampler
from bidking_lab.inference.map_likelihood import QuantileSummary
from bidking_lab.inference.v3.constraints import ConstraintSet
from bidking_lab.inference.v3.summary import BucketFeasibleSummary, FeasibleSummaryReport
from bidking_lab.inference.v3.truth import decision_truth_from_session_truth


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
    match_scope = "strict"
    if n_total <= 0:
        diagnostics.append("no_prior_samples")
    if n_total > 0 and not strict_matched and summary.feasible:
        diagnostics.append("no_strict_summary_matched_samples")
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
        if matched:
            match_scope = "q6_projection"
            diagnostics.append("q6_projection_fallback")
        else:
            diagnostics.append("no_q6_projection_matched_samples")
    elif not summary.feasible:
        matched = ()
    q6_counts: list[int] = []
    q6_cells: list[int] = []
    q6_values: list[int] = []
    total_cells: list[int] = []
    total_values: list[int] = []
    formal_decision_values: list[int] = []
    tail_replacement_decision_values: list[int] = []
    q6_formal_decision_values: list[int] = []
    q6_tail_replacement_decision_values: list[int] = []
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
    q6_present_rate = (
        sum(1 for count in q6_counts if count > 0) / len(q6_counts)
        if q6_counts
        else None
    )
    return V3PosteriorReport(
        map_id=int(map_id),
        map_name=map_name,
        n_total=n_total,
        n_matched=len(matched),
        n_strict_matched=len(strict_matched),
        match_scope=match_scope,
        q6_present_rate=q6_present_rate,
        total_cells=_quantiles(total_cells),
        total_value=_quantiles(total_values),
        formal_decision_value=_quantiles(formal_decision_values),
        tail_replacement_decision_value=_quantiles(tail_replacement_decision_values),
        q6_count=_quantiles(q6_counts),
        q6_cells=_quantiles(q6_cells),
        q6_value=_quantiles(q6_values),
        q6_formal_decision_value=_quantiles(q6_formal_decision_values),
        q6_tail_replacement_decision_value=_quantiles(
            q6_tail_replacement_decision_values
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
