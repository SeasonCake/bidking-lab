"""v3 inference scaffolding.

The initial v3 package is diagnostic-only. It records evidence semantics and
coverage before any posterior or live decision path is moved off v2.
"""

from bidking_lab.inference.v3.coverage import (
    EvidenceCoverageReport,
    audit_fatbeans_events,
    audit_fatbeans_paths,
)
from bidking_lab.inference.v3.constraints import (
    ConstraintConflict,
    ConstraintSet,
    HardNumericConstraint,
    ItemAnchor,
    QualityFloorAnchor,
    ShapeAnchor,
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
from bidking_lab.inference.v3.priors import (
    QualityPriorReport,
    SessionPriorReport,
    ordinary_shape_replacement_values,
    summarize_drop_prior,
)
from bidking_lab.inference.v3.truth import (
    DecisionTruthReport,
    QualityTruthReport,
    SettlementTruthReport,
    decision_truth_from_fatbeans,
    empty_decision_truth_flat_dict,
    empty_truth_flat_dict,
    settlement_truth_from_fatbeans,
)

__all__ = (
    "ACTION_RESULT_SPECS",
    "ConstraintConflict",
    "ConstraintSet",
    "DecisionTruthReport",
    "PUBLIC_INFO_SPECS",
    "SKILL_REVEAL_SPECS",
    "EvidenceCoverageReport",
    "EvidenceEvent",
    "EvidenceSpec",
    "HardNumericConstraint",
    "ItemAnchor",
    "QualityFloorAnchor",
    "QualityPriorReport",
    "QualityTruthReport",
    "ShapeAnchor",
    "SessionPriorReport",
    "SettlementTruthReport",
    "action_result_spec",
    "audit_fatbeans_events",
    "audit_fatbeans_paths",
    "compile_hard_constraints",
    "decision_truth_from_fatbeans",
    "empty_decision_truth_flat_dict",
    "empty_truth_flat_dict",
    "events_from_fatbeans",
    "ordinary_shape_replacement_values",
    "public_info_semantic",
    "public_info_semantics_dict",
    "public_info_spec",
    "settlement_truth_from_fatbeans",
    "skill_reveal_spec",
    "summarize_drop_prior",
)
