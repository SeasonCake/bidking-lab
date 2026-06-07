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
