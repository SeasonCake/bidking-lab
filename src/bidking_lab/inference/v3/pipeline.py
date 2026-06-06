"""Shared v3 shadow inference pipeline.

Archive evaluation and live monitoring should prepare source-specific inputs,
then call this module for the actual v3 report chain. Keeping the chain here
prevents posterior, CCV, residual, calibration, and underestimate shadow fields
from drifting between paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from bidking_lab.inference.ground_truth import SessionTruth
from bidking_lab.inference.v3.calibration import (
    PriorCalibrationEntry,
    V3PriorCalibrationReport,
    calibrate_posterior_report,
)
from bidking_lab.inference.v3.constraints import ConstraintSet
from bidking_lab.inference.v3.formal_value_sampler import (
    V3FormalValueSamplerReport,
    sample_formal_value_report,
)
from bidking_lab.inference.v3.posterior import (
    V3PosteriorReport,
    empty_posterior_flat_dict,
    estimate_component_count_cell_value_posterior_from_truths,
    estimate_count_cell_value_posterior_from_truths,
    estimate_q6_posterior_from_truths,
    estimate_residual_count_cell_value_posterior_from_truths,
)
from bidking_lab.inference.v3.residual_gate import (
    V3ResidualGateReport,
    gate_residual_posterior_report,
)
from bidking_lab.inference.v3.residual_targets import (
    V3ResidualTargetCandidateReport,
    assess_q6_residual_targets,
)
from bidking_lab.inference.v3.settlement_count_prior import (
    SettlementCountPriorEntry,
    V3SettlementCountPriorReport,
    assess_settlement_count_prior,
)
from bidking_lab.inference.v3.summary import FeasibleSummaryReport
from bidking_lab.inference.v3.tail_value_review import (
    TailValueReviewEntry,
    V3TailValueReviewReport,
    review_tail_value_posterior_report,
)
from bidking_lab.inference.v3.underestimate_repair import (
    UnderestimateRepairEntry,
    V3UnderestimateRepairReport,
    repair_underestimate_posterior_report,
)


@dataclass(frozen=True)
class V3CcvOptions:
    count_cell_tail_guard: bool = True
    value_tail_guard: bool = True
    condition_temperature: float | None = None
    relative_floor: float | None = None
    component_likelihood: bool = False
    component_move_cells: bool = True


@dataclass(frozen=True)
class V3ShadowPipelineReport:
    posterior: V3PosteriorReport
    ccv_posterior: V3PosteriorReport
    ccv_component_posterior: V3PosteriorReport | None
    residual_posterior: V3PosteriorReport
    residual_gate: V3ResidualGateReport
    residual_targets: V3ResidualTargetCandidateReport
    calibration: V3PriorCalibrationReport
    underestimate: V3UnderestimateRepairReport
    tail_review: V3TailValueReviewReport
    formal_value: V3FormalValueSamplerReport
    settlement_count_prior: V3SettlementCountPriorReport

    def to_flat_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        out.update(self.posterior.to_flat_dict())
        out.update(self.ccv_posterior.to_flat_dict(prefix="v3_ccv_"))
        if self.ccv_component_posterior is None:
            out.update(empty_posterior_flat_dict(prefix="v3_ccvc_"))
        else:
            out.update(
                self.ccv_component_posterior.to_flat_dict(prefix="v3_ccvc_")
            )
        out.update(self.residual_posterior.to_flat_dict(prefix="v3_resid_"))
        out.update(self.residual_gate.to_flat_dict())
        out.update(self.residual_targets.to_flat_dict())
        out.update(self.calibration.to_flat_dict())
        out.update(self.underestimate.to_flat_dict())
        out.update(self.tail_review.to_flat_dict())
        out.update(self.formal_value.to_flat_dict())
        out.update(self.settlement_count_prior.to_flat_dict())
        return out


def estimate_shadow_pipeline(
    *,
    map_id: int,
    map_name: str,
    summary: FeasibleSummaryReport,
    truths: Sequence[SessionTruth],
    constraints: ConstraintSet | None = None,
    replacement_values: Mapping[tuple[int, int, int], int] | None = None,
    calibration_entry: PriorCalibrationEntry | None = None,
    underestimate_entry: UnderestimateRepairEntry | None = None,
    tail_review_entry: TailValueReviewEntry | None = None,
    settlement_count_prior_entry: SettlementCountPriorEntry | None = None,
    hero: str | None = None,
    ccv_options: V3CcvOptions | None = None,
    prior_fields: Mapping[str, Any] | None = None,
) -> V3ShadowPipelineReport:
    posterior = estimate_q6_posterior_from_truths(
        map_id=int(map_id),
        map_name=str(map_name or ""),
        summary=summary,
        truths=truths,
        constraints=constraints,
        replacement_values=replacement_values or {},
    )
    ccv_kwargs: dict[str, Any] = {}
    if ccv_options is not None:
        ccv_kwargs["count_cell_tail_guard"] = ccv_options.count_cell_tail_guard
        ccv_kwargs["value_tail_guard"] = ccv_options.value_tail_guard
        if ccv_options.condition_temperature is not None:
            ccv_kwargs["condition_temperature"] = ccv_options.condition_temperature
        if ccv_options.relative_floor is not None:
            ccv_kwargs["relative_floor"] = ccv_options.relative_floor
    ccv_posterior = estimate_count_cell_value_posterior_from_truths(
        map_id=int(map_id),
        map_name=str(map_name or ""),
        summary=summary,
        truths=truths,
        constraints=constraints,
        replacement_values=replacement_values or {},
        baseline=posterior,
        **ccv_kwargs,
    )
    ccv_component_posterior = (
        estimate_component_count_cell_value_posterior_from_truths(
            map_id=int(map_id),
            map_name=str(map_name or ""),
            summary=summary,
            truths=truths,
            constraints=constraints,
            replacement_values=replacement_values or {},
            baseline=posterior,
            move_cells=ccv_options.component_move_cells,
        )
        if ccv_options is not None and ccv_options.component_likelihood
        else None
    )
    residual_posterior = estimate_residual_count_cell_value_posterior_from_truths(
        map_id=int(map_id),
        map_name=str(map_name or ""),
        summary=summary,
        truths=truths,
        constraints=constraints,
        replacement_values=replacement_values or {},
        baseline=posterior,
    )
    residual_gate = gate_residual_posterior_report(
        posterior,
        residual_posterior,
        calibration_entry,
    )
    residual_targets = assess_q6_residual_targets(summary)
    calibration = calibrate_posterior_report(posterior, calibration_entry)
    underestimate = repair_underestimate_posterior_report(
        posterior,
        underestimate_entry,
        hero=hero,
    )
    tail_review = review_tail_value_posterior_report(
        posterior,
        tail_review_entry,
        hero=hero,
    )
    formal_value = sample_formal_value_report(
        posterior,
        summary=summary,
        prior_fields=prior_fields,
    )
    settlement_count_prior = assess_settlement_count_prior(
        entry=settlement_count_prior_entry,
        map_id=int(map_id),
        summary=summary,
        prior_fields=prior_fields,
    )
    return V3ShadowPipelineReport(
        posterior=posterior,
        ccv_posterior=ccv_posterior,
        ccv_component_posterior=ccv_component_posterior,
        residual_posterior=residual_posterior,
        residual_gate=residual_gate,
        residual_targets=residual_targets,
        calibration=calibration,
        underestimate=underestimate,
        tail_review=tail_review,
        formal_value=formal_value,
        settlement_count_prior=settlement_count_prior,
    )


__all__ = (
    "V3CcvOptions",
    "V3ShadowPipelineReport",
    "estimate_shadow_pipeline",
)
