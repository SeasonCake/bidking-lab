"""Hard constraint compiler for v3 diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from bidking_lab.inference.v3.events import EvidenceEvent


@dataclass(frozen=True)
class HardNumericConstraint:
    target: str
    value: int | float
    event_id: str
    source_kind: str
    source_id: str
    sort_id: int | None


@dataclass(frozen=True)
class ConstraintConflict:
    target: str
    first: HardNumericConstraint
    second: HardNumericConstraint


@dataclass
class ConstraintSet:
    numeric: dict[str, HardNumericConstraint] = field(default_factory=dict)
    item_anchor_events: list[EvidenceEvent] = field(default_factory=list)
    shape_anchor_events: list[EvidenceEvent] = field(default_factory=list)
    quality_floor_events: list[EvidenceEvent] = field(default_factory=list)
    conflicts: list[ConstraintConflict] = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.conflicts


def _numeric_payload_value(event: EvidenceEvent) -> int | float | None:
    payload = event.payload or {}
    value: Any
    if "value" in payload:
        value = payload["value"]
    elif "result" in payload:
        value = payload["result"]
    else:
        return None
    if isinstance(value, bool) or value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not numeric.is_integer():
        return numeric
    return int(numeric)


def _is_numeric_target(target: str) -> bool:
    return target.startswith("session.") or target.startswith("bucket.")


def compile_hard_constraints(events: Iterable[EvidenceEvent]) -> ConstraintSet:
    """Compile hard v3 events into a first-pass constraint set.

    This is deliberately conservative: it compiles exact numeric constraints and
    records anchor-bearing events, but it does not yet allocate grid shapes or
    items. That later compiler must consume the anchor events directly.
    """

    out = ConstraintSet()
    for event in events:
        target_set = set(event.targets)
        if "item_anchors" in target_set or "category_anchors" in target_set:
            out.item_anchor_events.append(event)
        if "shape_anchors" in target_set:
            out.shape_anchor_events.append(event)
        if "quality_floors" in target_set:
            out.quality_floor_events.append(event)
        if event.strength != "hard":
            continue
        value = _numeric_payload_value(event)
        if value is None:
            continue
        for target in event.targets:
            if not _is_numeric_target(target):
                continue
            constraint = HardNumericConstraint(
                target=target,
                value=value,
                event_id=event.event_id,
                source_kind=event.source_kind,
                source_id=event.source_id,
                sort_id=event.sort_id,
            )
            current = out.numeric.get(target)
            if current is not None and current.value != value:
                out.conflicts.append(
                    ConstraintConflict(
                        target=target,
                        first=current,
                        second=constraint,
                    )
                )
                continue
            out.numeric[target] = constraint
    return out


__all__ = (
    "ConstraintConflict",
    "ConstraintSet",
    "HardNumericConstraint",
    "compile_hard_constraints",
)
