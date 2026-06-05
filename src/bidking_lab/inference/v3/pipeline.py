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
from bidking_lab.inference.v3.posterior import (
    V3PosteriorReport,
    estimate_count_cell_value_posterior_from_truths,
    estimate_q6_posterior_from_truths,
    estimate_residual_count_cell_value_posterior_from_truths,
)
from bidking_lab.inference.v3.residual_gate import (
    V3ResidualGateReport,
    gate_residual_posterior_report,
)
from bidking_lab.inference.v3.summary import FeasibleSummaryReport
from bidking_lab.inference.v3.underestimate_repair import (
    UnderestimateRepairEntry,
    V3UnderestimateRepairReport,
    repair_underestimate_posterior_report,
)


@dataclass(frozen=True)
class V3ShadowPipelineReport:
    posterior: V3PosteriorReport
    ccv_posterior: V3PosteriorReport
    residual_posterior: V3PosteriorReport
    residual_gate: V3ResidualGateReport
    calibration: V3PriorCalibrationReport
    underestimate: V3UnderestimateRepairReport

    def to_flat_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        out.update(self.posterior.to_flat_dict())
        out.update(self.ccv_posterior.to_flat_dict(prefix="v3_ccv_"))
        out.update(self.residual_posterior.to_flat_dict(prefix="v3_resid_"))
        out.update(self.residual_gate.to_flat_dict())
        out.update(self.calibration.to_flat_dict())
        out.update(self.underestimate.to_flat_dict())
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
    hero: str | None = None,
) -> V3ShadowPipelineReport:
    posterior = estimate_q6_posterior_from_truths(
        map_id=int(map_id),
        map_name=str(map_name or ""),
        summary=summary,
        truths=truths,
        constraints=constraints,
        replacement_values=replacement_values or {},
    )
    ccv_posterior = estimate_count_cell_value_posterior_from_truths(
        map_id=int(map_id),
        map_name=str(map_name or ""),
        summary=summary,
        truths=truths,
        constraints=constraints,
        replacement_values=replacement_values or {},
        baseline=posterior,
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
    calibration = calibrate_posterior_report(posterior, calibration_entry)
    underestimate = repair_underestimate_posterior_report(
        posterior,
        underestimate_entry,
        hero=hero,
    )
    return V3ShadowPipelineReport(
        posterior=posterior,
        ccv_posterior=ccv_posterior,
        residual_posterior=residual_posterior,
        residual_gate=residual_gate,
        calibration=calibration,
        underestimate=underestimate,
    )


__all__ = (
    "V3ShadowPipelineReport",
    "estimate_shadow_pipeline",
)
