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

__all__ = (
    "ACTION_RESULT_SPECS",
    "ConstraintConflict",
    "ConstraintSet",
    "PUBLIC_INFO_SPECS",
    "SKILL_REVEAL_SPECS",
    "EvidenceCoverageReport",
    "EvidenceEvent",
    "EvidenceSpec",
    "HardNumericConstraint",
    "ItemAnchor",
    "QualityFloorAnchor",
    "ShapeAnchor",
    "action_result_spec",
    "audit_fatbeans_events",
    "audit_fatbeans_paths",
    "compile_hard_constraints",
    "events_from_fatbeans",
    "public_info_semantic",
    "public_info_semantics_dict",
    "public_info_spec",
    "skill_reveal_spec",
)
