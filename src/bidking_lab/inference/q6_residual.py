"""Shared q6 residual sampler gates and evidence profile helpers."""

from __future__ import annotations

from typing import Any


RANDOM_SAMPLE_AVG_PROFILE_SIGNAL_FLOOR = 20_000.0
AISHA_BOTTOM_ROW_RISK_THRESHOLD = 16
AISHA_SHIPWRECK_DEEP_ROW_THRESHOLD = 13


SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_BOOST_PROFILES = frozenset(
    {
        ("aisha", "shipwreck", "shape+layout"),
        ("aisha", "shipwreck", "tool:category+shape+layout"),
        ("ethan", "shipwreck", "layout"),
        ("ethan", "shipwreck", "shape+layout"),
    }
)
AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES = frozenset(
    {
        ("aisha", "shipwreck", "shape+layout"),
        ("aisha", "shipwreck", "tool:category+shape+layout"),
    }
)
AISHA_HIDDEN_V1_Q6_RESIDUAL_PROFILES = frozenset(
    {
        ("aisha", "hidden", "shape+layout"),
    }
)
AISHA_VILLA_V1_Q6_RESIDUAL_PROFILES = frozenset(
    {
        ("aisha", "villa", "shape+layout"),
    }
)


def actionable_random_sample_avg_values(
    values: Any,
    *,
    signal_floor: float = RANDOM_SAMPLE_AVG_PROFILE_SIGNAL_FLOOR,
) -> tuple[tuple[int, float], ...]:
    """Keep random-sample averages strong enough to affect profile routing."""
    return tuple(
        (int(sample_count), float(value))
        for sample_count, value in (values or ())
        if float(value) >= signal_floor
    )


def aisha_bottom_row_risk(
    *,
    hero: str | None,
    map_family: str,
    bottom_row: int | None,
) -> bool:
    """Flag Aisha shipwreck layouts that extend into the lower grid."""
    return (
        str(hero or "").lower() == "aisha"
        and map_family == "shipwreck"
        and bottom_row is not None
        and int(bottom_row) >= AISHA_BOTTOM_ROW_RISK_THRESHOLD
    )


def evidence_profile_key_from_problem(
    problem: Any,
    *,
    random_sample_avg_signal_floor: float = RANDOM_SAMPLE_AVG_PROFILE_SIGNAL_FLOOR,
) -> str:
    """Return a stable evidence-profile key for batch and live q6 gates."""
    parts: list[str] = []
    diagnostics = ";".join(getattr(problem, "diagnostics", ()) or ())
    public_parts: list[str] = []
    if "public_max_quality:" in diagnostics:
        public_parts.append("max_quality")
    if "public_max_item_cells:" in diagnostics:
        public_parts.append("max_item_cells")
    if public_parts:
        parts.append(f"public:{'+'.join(public_parts)}")
    if actionable_random_sample_avg_values(
        getattr(problem, "random_sample_avg_values", ()),
        signal_floor=random_sample_avg_signal_floor,
    ):
        parts.append("public:random_avg")
    if len(getattr(problem, "category_targets", ()) or ()) > 0:
        parts.append("tool:category")
    if len(getattr(problem, "shape_targets", ()) or ()) > 0:
        parts.append("shape")
    if getattr(getattr(problem, "layout", None), "trusted_footprint_count", 0) > 0:
        parts.append("layout")
    return "+".join(parts) if parts else "basic"


def q6_residual_boost_for_profile(
    *,
    hero: str | None,
    map_family: str,
    evidence_profile_key: str,
    requested_boost: float,
    gate: str,
    bottom_row: int | None = None,
) -> float:
    """Return active q6 residual boost for a named profile gate."""
    if requested_boost <= 1.0:
        return 1.0
    if gate == "all":
        return requested_boost
    key = (str(hero or "").lower(), map_family, evidence_profile_key)
    if gate == "shipwreck_profile_v1":
        return (
            requested_boost
            if key in SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_BOOST_PROFILES
            else 1.0
        )
    if gate == "aisha_shipwreck_bottom_v1":
        return (
            requested_boost
            if key in AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES
            and bottom_row is not None
            and int(bottom_row) >= AISHA_BOTTOM_ROW_RISK_THRESHOLD
            else 1.0
        )
    if gate == "aisha_shipwreck_deep_v1":
        return (
            requested_boost
            if key in AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES
            and bottom_row is not None
            and int(bottom_row) >= AISHA_SHIPWRECK_DEEP_ROW_THRESHOLD
            else 1.0
        )
    return 1.0


def q6_residual_prior_floor_ratio_for_profile(
    *,
    hero: str | None,
    map_family: str,
    evidence_profile_key: str,
    requested_ratio: float,
    gate: str,
    bottom_row: int | None = None,
) -> float:
    """Return active q6 prior count/cells floor ratio for a named profile gate."""
    if requested_ratio <= 0:
        return 0.0
    if gate == "all":
        return requested_ratio
    key = (str(hero or "").lower(), map_family, evidence_profile_key)
    if gate == "shipwreck_profile_v1":
        return (
            requested_ratio
            if key in SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_BOOST_PROFILES
            else 0.0
        )
    if gate == "aisha_shipwreck_profile_v1":
        return (
            requested_ratio
            if key in AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES
            else 0.0
        )
    if gate == "aisha_shipwreck_bottom_v1":
        return (
            requested_ratio
            if key in AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES
            and bottom_row is not None
            and int(bottom_row) >= AISHA_BOTTOM_ROW_RISK_THRESHOLD
            else 0.0
        )
    if gate == "aisha_shipwreck_deep_v1":
        return (
            requested_ratio
            if key in AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES
            and bottom_row is not None
            and int(bottom_row) >= AISHA_SHIPWRECK_DEEP_ROW_THRESHOLD
            else 0.0
        )
    if gate == "aisha_hidden_v1":
        return (
            requested_ratio
            if key in AISHA_HIDDEN_V1_Q6_RESIDUAL_PROFILES
            else 0.0
        )
    if gate == "aisha_villa_shape_layout_v1":
        return (
            requested_ratio
            if key in AISHA_VILLA_V1_Q6_RESIDUAL_PROFILES
            else 0.0
        )
    if gate == "aisha_deep_or_hidden_v1":
        if (
            key in AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES
            and bottom_row is not None
            and int(bottom_row) >= AISHA_SHIPWRECK_DEEP_ROW_THRESHOLD
        ) or key in AISHA_HIDDEN_V1_Q6_RESIDUAL_PROFILES:
            return requested_ratio
        return 0.0
    return 0.0


__all__ = (
    "AISHA_HIDDEN_V1_Q6_RESIDUAL_PROFILES",
    "AISHA_SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_PROFILES",
    "AISHA_VILLA_V1_Q6_RESIDUAL_PROFILES",
    "AISHA_BOTTOM_ROW_RISK_THRESHOLD",
    "AISHA_SHIPWRECK_DEEP_ROW_THRESHOLD",
    "RANDOM_SAMPLE_AVG_PROFILE_SIGNAL_FLOOR",
    "SHIPWRECK_PROFILE_V1_Q6_RESIDUAL_BOOST_PROFILES",
    "actionable_random_sample_avg_values",
    "aisha_bottom_row_risk",
    "evidence_profile_key_from_problem",
    "q6_residual_boost_for_profile",
    "q6_residual_prior_floor_ratio_for_profile",
)
