"""Practical v3 advisory synthesis.

This layer is intentionally shadow-only. It converts existing v3 lanes into a
single practical advisory surface for archive/live review, without changing the
formal bid path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bidking_lab.inference.map_likelihood import QuantileSummary
from bidking_lab.inference.v3.capacity_source_expansion import (
    V3CapacitySourceExpansionReport,
)
from bidking_lab.inference.v3.formal_value_sampler import (
    V3FormalValueSamplerReport,
)
from bidking_lab.inference.v3.posterior import (
    V3PosteriorReport,
    empty_posterior_flat_dict,
)
from bidking_lab.inference.v3.settlement_count_prior import (
    V3SettlementCountPriorReport,
)
from bidking_lab.inference.v3.tail_value_review import V3TailValueReviewReport
from bidking_lab.inference.v3.underestimate_repair import (
    V3UnderestimateRepairReport,
)

_Q6_PRIOR_FLOOR_MIN_VALUE_GAP = 100_000.0
_TAIL_REPLACEMENT_MIN_P90_GAP = 50_000.0
_RANDOM_AVG_VALUE_SIGNAL_FLOOR = 20_000.0
_RANDOM_AVG_VALUE_MIN_P50_GAP = 100_000.0
_RANDOM_AVG_VALUE_MIN_P90_GAP = 50_000.0


@dataclass(frozen=True)
class V3PracticalAdvisoryReport:
    baseline: V3PosteriorReport | None
    advisory: V3PosteriorReport | None
    source: str
    mode: str
    status: str
    recommendation: str
    confidence: str
    source_lanes: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    reason: str = ""

    @property
    def available(self) -> bool:
        return True

    @property
    def ready(self) -> bool:
        return self.baseline is not None and self.baseline.ready

    @property
    def active(self) -> bool:
        return False

    @property
    def affects_bid(self) -> bool:
        return False

    @property
    def candidate(self) -> bool:
        return self.ready and self.status not in {
            "not_ready",
            "baseline_passthrough",
        }

    def to_flat_dict(self, *, prefix: str = "v3_practical_") -> dict[str, Any]:
        out = (
            empty_posterior_flat_dict(prefix=prefix)
            if self.advisory is None
            else self.advisory.to_flat_dict(prefix=prefix)
        )
        baseline_formal = _formal(self.baseline)
        advisory_formal = _formal(self.advisory)
        baseline_q6_formal = _q6_formal(self.baseline)
        advisory_q6_formal = _q6_formal(self.advisory)
        out.update(
            {
                f"{prefix}available": self.available,
                f"{prefix}ready": self.ready,
                f"{prefix}affects_bid": self.affects_bid,
                f"{prefix}active": self.active,
                f"{prefix}candidate": self.candidate,
                f"{prefix}source": self.source,
                f"{prefix}mode": self.mode,
                f"{prefix}status": self.status,
                f"{prefix}recommendation": self.recommendation,
                f"{prefix}confidence": self.confidence,
                f"{prefix}source_lanes": "+".join(self.source_lanes),
                f"{prefix}risk_flags": "+".join(self.risk_flags),
                f"{prefix}reason": self.reason,
                f"{prefix}baseline_formal_decision_value_p50": _q(
                    baseline_formal,
                    "p50",
                ),
                f"{prefix}baseline_formal_decision_value_p90": _q(
                    baseline_formal,
                    "p90",
                ),
                f"{prefix}delta_formal_decision_value_p50": _delta(
                    advisory_formal,
                    baseline_formal,
                    "p50",
                ),
                f"{prefix}delta_formal_decision_value_p90": _delta(
                    advisory_formal,
                    baseline_formal,
                    "p90",
                ),
                f"{prefix}baseline_q6_formal_decision_value_p50": _q(
                    baseline_q6_formal,
                    "p50",
                ),
                f"{prefix}baseline_q6_formal_decision_value_p90": _q(
                    baseline_q6_formal,
                    "p90",
                ),
                f"{prefix}delta_q6_formal_decision_value_p50": _delta(
                    advisory_q6_formal,
                    baseline_q6_formal,
                    "p50",
                ),
                f"{prefix}delta_q6_formal_decision_value_p90": _delta(
                    advisory_q6_formal,
                    baseline_q6_formal,
                    "p90",
                ),
            }
        )
        return out


def advise_practical_report(
    posterior: V3PosteriorReport | None,
    *,
    formal_value: V3FormalValueSamplerReport | None = None,
    underestimate: V3UnderestimateRepairReport | None = None,
    tail_review: V3TailValueReviewReport | None = None,
    settlement_count_prior: V3SettlementCountPriorReport | None = None,
    capacity_source_expansion: V3CapacitySourceExpansionReport | None = None,
    evidence_events: tuple[Any, ...] = (),
) -> V3PracticalAdvisoryReport:
    if posterior is None or not posterior.ready:
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=posterior,
            source="none",
            mode="not_ready",
            status="not_ready",
            recommendation="no_advice",
            confidence="none",
            reason="baseline_not_ready",
        )

    lanes: list[str] = []
    risks: list[str] = []
    reasons: list[str] = []

    if formal_value is not None and formal_value.candidate:
        lanes.append("formal_value")
        risks.append("value_floor_candidate")
        reasons.append(formal_value.gate_reason)
    elif formal_value is not None and formal_value.mixed_value_floor_watch:
        lanes.append("formal_value")
        risks.append("mixed_value_floor_guard")
        reasons.append(formal_value.gate_reason)
    elif (
        formal_value is not None
        and "capacity_cells_drift" in formal_value.stress_classes
    ):
        lanes.append("formal_value")
        risks.append("capacity_cells_drift")
        reasons.append(formal_value.gate_reason)

    q6_prior_floor = _q6_prior_floor_watch(
        posterior,
        formal_value,
    )
    if q6_prior_floor is not None:
        lanes.append("formal_value")
        lanes.append("prior_q6_floor")
        risks.append("q6_prior_floor_watch")
        reasons.append(q6_prior_floor[1])

    tail_replacement_watch = _tail_replacement_p90_watch(posterior)
    if tail_replacement_watch is not None:
        lanes.append("tail_replacement")
        risks.append("tail_replacement_p90_watch")
        reasons.append(tail_replacement_watch[1])

    random_avg_watch = _random_avg_value_floor_watch(
        posterior,
        evidence_events=evidence_events,
    )
    if random_avg_watch is not None:
        lanes.append("random_avg_value")
        risks.append("random_avg_value_floor_watch")
        reasons.append(random_avg_watch[1])

    if underestimate is not None and underestimate.candidate:
        lanes.append("underestimate")
        risks.append("underestimate_repair_candidate")
        if underestimate.entry is not None:
            reasons.append(underestimate.entry.gate_reason)

    if tail_review is not None and tail_review.candidate:
        lanes.append("tail_review")
        risks.append("tail_value_candidate")
        if tail_review.entry is not None:
            reasons.append(tail_review.entry.gate_reason)
    if tail_review is not None and tail_review.hurt_guard:
        lanes.append("tail_review")
        risks.append("tail_value_hurt_guard")
        if tail_review.entry is not None:
            reasons.append(tail_review.entry.gate_reason)

    if settlement_count_prior is not None and settlement_count_prior.candidate:
        lanes.append("settlement_count_prior")
        risks.append("settlement_count_prior_candidate")
        reasons.append(settlement_count_prior.gate_reason)
    if settlement_count_prior is not None and settlement_count_prior.missing_table:
        lanes.append("settlement_count_prior")
        risks.append("missing_settlement_count_table")
        reasons.append(settlement_count_prior.gate_reason)

    cse_fields = (
        capacity_source_expansion.to_flat_dict()
        if capacity_source_expansion is not None
        else {}
    )
    if bool(cse_fields.get("v3_cse_pressure_candidate")):
        lanes.append("capacity_source_expansion")
        risks.append("capacity_source_pressure")
        if capacity_source_expansion is not None:
            reasons.append(capacity_source_expansion.gate_reason)
    elif capacity_source_expansion is not None and capacity_source_expansion.candidate:
        lanes.append("capacity_source_expansion")
        risks.append("capacity_source_candidate")
        reasons.append(capacity_source_expansion.gate_reason)

    if formal_value is not None and formal_value.candidate:
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=formal_value.posterior,
            source="formal_value",
            mode="value_floor_watch",
            status="watch_raise_candidate",
            recommendation="raise_watch",
            confidence="medium",
            source_lanes=_dedupe(lanes),
            risk_flags=_dedupe(risks),
            reason=_join_reasons(reasons),
        )
    if underestimate is not None and underestimate.candidate:
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=underestimate.posterior,
            source="underestimate",
            mode="bounded_underestimate_repair",
            status="watch_raise_candidate",
            recommendation="raise_watch",
            confidence="medium_low",
            source_lanes=_dedupe(lanes),
            risk_flags=_dedupe(risks),
            reason=_join_reasons(reasons),
        )
    if q6_prior_floor is not None:
        advisory, _reason = q6_prior_floor
        combined_random_avg = _random_avg_value_floor_watch(
            advisory,
            evidence_events=evidence_events,
        )
        if combined_random_avg is not None:
            advisory, random_reason, _random_raise_watch = combined_random_avg
            if random_reason not in reasons:
                reasons.append(random_reason)
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=advisory,
            source="q6_prior_floor",
            mode="q6_prior_floor_watch",
            status="watch_q6_prior_floor",
            recommendation="raise_watch",
            confidence="low_medium",
            source_lanes=_dedupe(lanes),
            risk_flags=_dedupe(risks),
            reason=_join_reasons(reasons),
        )
    if random_avg_watch is not None:
        advisory, _reason, random_raise_watch = random_avg_watch
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=advisory,
            source="random_avg_value",
            mode="random_avg_value_floor_watch",
            status=(
                "watch_random_avg_value_floor"
                if random_raise_watch
                else "watch_random_avg_value_p50_floor"
            ),
            recommendation="raise_watch" if random_raise_watch else "ceiling_watch",
            confidence="medium_low",
            source_lanes=_dedupe(lanes),
            risk_flags=_dedupe(risks),
            reason=_join_reasons(reasons),
        )
    if tail_replacement_watch is not None:
        advisory, _reason = tail_replacement_watch
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=advisory,
            source="tail_replacement",
            mode="tail_replacement_p90_watch",
            status="watch_tail_replacement_p90",
            recommendation="raise_watch",
            confidence="low",
            source_lanes=_dedupe(lanes),
            risk_flags=_dedupe(risks),
            reason=_join_reasons(reasons),
        )
    if any(
        flag in risks
        for flag in (
            "capacity_source_pressure",
            "capacity_cells_drift",
            "mixed_value_floor_guard",
            "missing_settlement_count_table",
        )
    ):
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=posterior,
            source="risk_watch",
            mode="capacity_or_value_guard",
            status="watch_risk_no_numeric_shift",
            recommendation="raise_watch",
            confidence="low",
            source_lanes=_dedupe(lanes),
            risk_flags=_dedupe(risks),
            reason=_join_reasons(reasons),
        )
    if "tail_value_candidate" in risks:
        return V3PracticalAdvisoryReport(
            baseline=posterior,
            advisory=posterior,
            source="risk_watch",
            mode="tail_or_source_watch",
            status="watch_no_numeric_shift",
            recommendation="ceiling_watch",
            confidence="low",
            source_lanes=_dedupe(lanes),
            risk_flags=_dedupe(risks),
            reason=_join_reasons(reasons),
        )
    return V3PracticalAdvisoryReport(
        baseline=posterior,
        advisory=posterior,
        source="baseline",
        mode="baseline",
        status="baseline_passthrough",
        recommendation="baseline_reference",
        confidence="baseline",
        source_lanes=_dedupe(lanes),
        risk_flags=_dedupe(risks),
        reason=(
            "broad_risk_recorded_no_action"
            if risks
            else "no_practical_v3_risk"
        ),
    )


def empty_practical_advisory_flat_dict(
    *,
    prefix: str = "v3_practical_",
) -> dict[str, Any]:
    return V3PracticalAdvisoryReport(
        baseline=None,
        advisory=None,
        source="none",
        mode="not_ready",
        status="not_ready",
        recommendation="no_advice",
        confidence="none",
        reason="missing_baseline",
    ).to_flat_dict(prefix=prefix)


def _formal(report: V3PosteriorReport | None) -> QuantileSummary | None:
    return report.formal_decision_value if report is not None else None


def _q6_formal(report: V3PosteriorReport | None) -> QuantileSummary | None:
    return report.q6_formal_decision_value if report is not None else None


def _q(summary: QuantileSummary | None, attr: str) -> float | None:
    if summary is None:
        return None
    return round(float(getattr(summary, attr)), 6)


def _delta(
    advisory: QuantileSummary | None,
    baseline: QuantileSummary | None,
    attr: str,
) -> float | None:
    if advisory is None or baseline is None:
        return None
    return round(float(getattr(advisory, attr)) - float(getattr(baseline, attr)), 6)


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed


def _raise_p90_by_delta(
    summary: QuantileSummary | None,
    delta: float,
) -> QuantileSummary | None:
    if summary is None or delta <= 0.0:
        return summary
    return QuantileSummary(
        p10=float(summary.p10),
        p50=float(summary.p50),
        p90=float(summary.p90) + float(delta),
    )


def _floor_p90(
    summary: QuantileSummary | None,
    floor: float,
) -> QuantileSummary | None:
    if summary is None or floor <= 0.0:
        return summary
    return QuantileSummary(
        p10=float(summary.p10),
        p50=float(summary.p50),
        p90=max(float(summary.p90), float(floor)),
    )


def _floor_p50_p90(
    summary: QuantileSummary | None,
    floor: float,
) -> QuantileSummary | None:
    if summary is None or floor <= 0.0:
        return summary
    floor_value = float(floor)
    return QuantileSummary(
        p10=float(summary.p10),
        p50=max(float(summary.p50), floor_value),
        p90=max(float(summary.p90), floor_value),
    )


def _q6_prior_floor_watch(
    posterior: V3PosteriorReport,
    formal_value: V3FormalValueSamplerReport | None,
) -> tuple[V3PosteriorReport, str] | None:
    prior_fields = formal_value.prior_fields if formal_value is not None else None
    if not prior_fields:
        return None
    prior_q6_value = _float_or_none(prior_fields.get("v3_prior_q6_expected_value"))
    q6_formal = posterior.q6_formal_decision_value
    formal = posterior.formal_decision_value
    if prior_q6_value is None or q6_formal is None or formal is None:
        return None
    q6_gap = max(0.0, float(prior_q6_value) - float(q6_formal.p90))
    if q6_gap < _Q6_PRIOR_FLOOR_MIN_VALUE_GAP:
        return None
    diagnostics = tuple(posterior.diagnostics) + (
        "practical_q6_prior_floor_watch",
        f"practical_q6_prior_expected_value={prior_q6_value:.6f}",
        f"practical_q6_prior_p90_gap={q6_gap:.6f}",
    )
    advisory = V3PosteriorReport(
        map_id=posterior.map_id,
        map_name=posterior.map_name,
        n_total=posterior.n_total,
        n_matched=posterior.n_matched,
        n_strict_matched=posterior.n_strict_matched,
        match_scope=posterior.match_scope,
        q6_present_rate=posterior.q6_present_rate,
        total_cells=posterior.total_cells,
        total_value=_raise_p90_by_delta(posterior.total_value, q6_gap),
        formal_decision_value=_raise_p90_by_delta(formal, q6_gap),
        tail_replacement_decision_value=_raise_p90_by_delta(
            posterior.tail_replacement_decision_value,
            q6_gap,
        ),
        q6_count=posterior.q6_count,
        q6_cells=posterior.q6_cells,
        q6_value=_floor_p90(posterior.q6_value, prior_q6_value),
        q6_formal_decision_value=_floor_p90(q6_formal, prior_q6_value),
        q6_tail_replacement_decision_value=_floor_p90(
            posterior.q6_tail_replacement_decision_value,
            prior_q6_value,
        ),
        diagnostics=diagnostics,
    )
    reason = (
        "q6_prior_floor_shadow_only:"
        f"expected={prior_q6_value:.0f}:p90_gap={q6_gap:.0f}"
    )
    return advisory, reason


def _random_avg_value_observations(
    evidence_events: tuple[Any, ...],
) -> tuple[tuple[int, float], ...]:
    observations: list[tuple[int, float]] = []
    for event in evidence_events:
        targets = set(getattr(event, "targets", ()) or ())
        semantic = str(getattr(event, "semantic", "") or "")
        if "random_avg_value" not in targets and not (
            semantic.startswith("random_") and semantic.endswith("_avg_value")
        ):
            continue
        raw_count = semantic.removeprefix("random_").split("_", 1)[0]
        try:
            sample_count = int(raw_count)
        except (TypeError, ValueError):
            continue
        payload = getattr(event, "payload", None) or {}
        value = _float_or_none(payload.get("value", payload.get("result")))
        if value is None or value < _RANDOM_AVG_VALUE_SIGNAL_FLOOR:
            continue
        observations.append((sample_count, float(value)))
    return tuple(observations)


def _random_avg_value_floor_watch(
    posterior: V3PosteriorReport,
    *,
    evidence_events: tuple[Any, ...],
) -> tuple[V3PosteriorReport, str, bool] | None:
    observations = _random_avg_value_observations(evidence_events)
    if not observations:
        return None
    formal = posterior.formal_decision_value
    if formal is None:
        return None
    floor = max(float(count) * value for count, value in observations)
    p50_gap = max(0.0, floor - float(formal.p50))
    p90_gap = max(0.0, floor - float(formal.p90))
    if (
        p50_gap < _RANDOM_AVG_VALUE_MIN_P50_GAP
        and p90_gap < _RANDOM_AVG_VALUE_MIN_P90_GAP
    ):
        return None
    raise_watch = p90_gap >= _RANDOM_AVG_VALUE_MIN_P90_GAP
    diagnostics = tuple(posterior.diagnostics) + (
        "practical_random_avg_value_floor_watch",
        f"practical_random_avg_value_floor={floor:.6f}",
        f"practical_random_avg_value_p50_gap={p50_gap:.6f}",
        f"practical_random_avg_value_p90_gap={p90_gap:.6f}",
    )
    advisory = V3PosteriorReport(
        map_id=posterior.map_id,
        map_name=posterior.map_name,
        n_total=posterior.n_total,
        n_matched=posterior.n_matched,
        n_strict_matched=posterior.n_strict_matched,
        match_scope=posterior.match_scope,
        q6_present_rate=posterior.q6_present_rate,
        total_cells=posterior.total_cells,
        total_value=_floor_p50_p90(posterior.total_value, floor),
        formal_decision_value=_floor_p50_p90(formal, floor),
        tail_replacement_decision_value=_floor_p50_p90(
            posterior.tail_replacement_decision_value,
            floor,
        ),
        q6_count=posterior.q6_count,
        q6_cells=posterior.q6_cells,
        q6_value=posterior.q6_value,
        q6_formal_decision_value=posterior.q6_formal_decision_value,
        q6_tail_replacement_decision_value=(
            posterior.q6_tail_replacement_decision_value
        ),
        diagnostics=diagnostics,
    )
    labels = ",".join(f"n={count}:avg={value:.0f}" for count, value in observations)
    reason = (
        "random_avg_value_floor_shadow_only:"
        f"floor={floor:.0f}:p50_gap={p50_gap:.0f}:"
        f"p90_gap={p90_gap:.0f}:samples={labels}"
    )
    return advisory, reason, raise_watch


def _tail_replacement_p90_watch(
    posterior: V3PosteriorReport,
) -> tuple[V3PosteriorReport, str] | None:
    formal = posterior.formal_decision_value
    replacement = posterior.tail_replacement_decision_value
    if formal is None or replacement is None:
        return None
    gap = max(0.0, float(replacement.p90) - float(formal.p90))
    if gap < _TAIL_REPLACEMENT_MIN_P90_GAP:
        return None
    diagnostics = tuple(posterior.diagnostics) + (
        "practical_tail_replacement_p90_watch",
        f"practical_tail_replacement_p90_gap={gap:.6f}",
    )
    advisory = V3PosteriorReport(
        map_id=posterior.map_id,
        map_name=posterior.map_name,
        n_total=posterior.n_total,
        n_matched=posterior.n_matched,
        n_strict_matched=posterior.n_strict_matched,
        match_scope=posterior.match_scope,
        q6_present_rate=posterior.q6_present_rate,
        total_cells=posterior.total_cells,
        total_value=posterior.total_value,
        formal_decision_value=_floor_p90(formal, float(replacement.p90)),
        tail_replacement_decision_value=replacement,
        q6_count=posterior.q6_count,
        q6_cells=posterior.q6_cells,
        q6_value=posterior.q6_value,
        q6_formal_decision_value=posterior.q6_formal_decision_value,
        q6_tail_replacement_decision_value=(
            posterior.q6_tail_replacement_decision_value
        ),
        diagnostics=diagnostics,
    )
    reason = f"tail_replacement_p90_shadow_only:p90_gap={gap:.0f}"
    return advisory, reason


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


def _join_reasons(reasons: list[str]) -> str:
    return ";".join(_dedupe([reason for reason in reasons if reason]))


__all__ = (
    "V3PracticalAdvisoryReport",
    "advise_practical_report",
    "empty_practical_advisory_flat_dict",
)
