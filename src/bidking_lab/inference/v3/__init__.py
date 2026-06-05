"""v3 inference scaffolding.

The initial v3 package is diagnostic-only. It records evidence semantics and
coverage before any posterior or live decision path is moved off v2.
"""

from bidking_lab.inference.v3.coverage import (
    EvidenceCoverageReport,
    audit_fatbeans_events,
    audit_fatbeans_paths,
)
from bidking_lab.inference.v3.calibration import (
    PriorCalibrationEntry,
    V3PriorCalibrationReport,
    calibrate_posterior_report,
    empty_prior_calibration_flat_dict,
    entry_from_mapping,
    load_prior_calibration_entries,
    propose_prior_calibration,
)
from bidking_lab.inference.v3.constraints import (
    ConstraintConflict,
    ConstraintSet,
    HardNumericConstraint,
    ItemAnchor,
    QualityFloorAnchor,
    ShapeAnchor,
    SoftNumericConstraint,
    compile_hard_constraints,
)
from bidking_lab.inference.v3.events import EvidenceEvent, events_from_fatbeans
from bidking_lab.inference.v3.evidence_registry import (
    ACTION_RESULT_SPECS,
    PUBLIC_INFO_SPECS,
    SKILL_REVEAL_SPECS,
    EvidenceSpec,
    action_result_spec,
    public_info_semantic,
    public_info_semantics_dict,
    public_info_spec,
    skill_reveal_spec,
)
from bidking_lab.inference.v3.posterior import (
    V3PosteriorReport,
    empty_posterior_flat_dict,
    estimate_q6_posterior_from_truths,
    sample_truth_bank,
    truth_matches_feasible_summary,
)
from bidking_lab.inference.v3.priors import (
    QualityPriorReport,
    SessionPriorReport,
    ordinary_shape_replacement_values,
    summarize_drop_prior,
)
from bidking_lab.inference.v3.summary import (
    BucketFeasibleSummary,
    FeasibleSummaryReport,
    compile_feasible_summary,
    empty_feasible_summary_flat_dict,
)
from bidking_lab.inference.v3.truth import (
    DecisionTruthReport,
    QualityTruthReport,
    SettlementTruthReport,
    decision_truth_from_fatbeans,
    decision_truth_from_session_truth,
    empty_decision_truth_flat_dict,
    empty_truth_flat_dict,
    settlement_truth_from_fatbeans,
)

__all__ = (
    "ACTION_RESULT_SPECS",
    "BucketFeasibleSummary",
    "ConstraintConflict",
    "ConstraintSet",
    "DecisionTruthReport",
    "PUBLIC_INFO_SPECS",
    "SKILL_REVEAL_SPECS",
    "EvidenceCoverageReport",
    "EvidenceEvent",
    "EvidenceSpec",
    "FeasibleSummaryReport",
    "HardNumericConstraint",
    "ItemAnchor",
    "PriorCalibrationEntry",
    "QualityFloorAnchor",
    "QualityPriorReport",
    "QualityTruthReport",
    "ShapeAnchor",
    "SoftNumericConstraint",
    "SessionPriorReport",
    "SettlementTruthReport",
    "V3PosteriorReport",
    "V3PriorCalibrationReport",
    "action_result_spec",
    "audit_fatbeans_events",
    "audit_fatbeans_paths",
    "calibrate_posterior_report",
    "compile_hard_constraints",
    "compile_feasible_summary",
    "decision_truth_from_fatbeans",
    "decision_truth_from_session_truth",
    "empty_decision_truth_flat_dict",
    "empty_feasible_summary_flat_dict",
    "empty_posterior_flat_dict",
    "empty_prior_calibration_flat_dict",
    "empty_truth_flat_dict",
    "entry_from_mapping",
    "estimate_q6_posterior_from_truths",
    "events_from_fatbeans",
    "load_prior_calibration_entries",
    "ordinary_shape_replacement_values",
    "propose_prior_calibration",
    "public_info_semantic",
    "public_info_semantics_dict",
    "public_info_spec",
    "sample_truth_bank",
    "settlement_truth_from_fatbeans",
    "skill_reveal_spec",
    "summarize_drop_prior",
    "truth_matches_feasible_summary",
)
