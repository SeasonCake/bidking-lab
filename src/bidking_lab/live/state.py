"""Reducer and adapter for live observation batches."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from bidking_lab.inference.display import Reading, parse_reading
from bidking_lab.inference.observation import (
    HUGE_BAND_RANGE,
    QualityBucketObs,
    SessionObs,
)
from bidking_lab.live.types import (
    AuctionPhase,
    FieldUpdate,
    GridItemObservation,
    LiveObservationBatch,
    ObservationSource,
    SourceConfidence,
    event_requests_recompute,
    source_priority,
)


_CONFIDENCE_PRIORITY: dict[SourceConfidence, int] = {
    "low": 10,
    "medium": 20,
    "high": 30,
    "exact": 40,
}


@dataclass(frozen=True)
class ObservedField:
    """Current winning value for one logical field path."""

    value: Any
    source: ObservationSource
    confidence: SourceConfidence
    observed_at_ms: int | None = None
    sequence: int | None = None


@dataclass(frozen=True)
class LiveSessionState:
    """Merged realtime observations before conversion to ``SessionObs``."""

    phase: AuctionPhase = "unknown"
    fields: dict[tuple[str, ...], ObservedField] = field(default_factory=dict)
    grid_items: tuple[GridItemObservation, ...] = ()
    version: int = 0
    dirty: bool = False


def _observed_from_update(update: FieldUpdate) -> ObservedField:
    return ObservedField(
        value=update.value,
        source=update.source,
        confidence=update.confidence,
        observed_at_ms=update.observed_at_ms,
        sequence=update.sequence,
    )


def _is_newer(new: ObservedField, old: ObservedField) -> bool:
    if new.sequence is not None and old.sequence is not None:
        return new.sequence >= old.sequence
    if new.observed_at_ms is not None and old.observed_at_ms is not None:
        return new.observed_at_ms >= old.observed_at_ms
    return True


def should_replace_field(old: ObservedField | None, new: ObservedField) -> bool:
    """Return whether ``new`` should replace ``old`` for one field path."""
    if old is None:
        return True

    new_source = source_priority(new.source)
    old_source = source_priority(old.source)
    if new_source != old_source:
        return new_source > old_source

    if _is_newer(new, old):
        return True

    new_conf = _CONFIDENCE_PRIORITY[new.confidence]
    old_conf = _CONFIDENCE_PRIORITY[old.confidence]
    return new_conf > old_conf


def apply_observation_batch(
    state: LiveSessionState,
    batch: LiveObservationBatch,
) -> LiveSessionState:
    """Merge one observation batch into live state."""
    fields = dict(state.fields)
    changed = False

    for update in batch.field_updates:
        new_field = _observed_from_update(update)
        old_field = fields.get(update.path)
        if should_replace_field(old_field, new_field):
            if old_field != new_field:
                changed = True
            fields[update.path] = new_field

    grid_items = state.grid_items
    if batch.grid_items:
        grid_items = tuple(batch.grid_items)
        changed = True

    phase = state.phase
    if batch.phase != "unknown" and batch.phase != state.phase:
        phase = batch.phase
        changed = True

    if not changed:
        return state
    return LiveSessionState(
        phase=phase,
        fields=fields,
        grid_items=grid_items,
        version=state.version + 1,
        dirty=state.dirty or event_requests_recompute(batch.event_kind),
    )


def mark_ready(state: LiveSessionState) -> LiveSessionState:
    """Mark current state as having a fresh inference result."""
    if not state.dirty:
        return state
    return replace(state, dirty=False)


def summarize_field_sources(
    state: LiveSessionState,
    *,
    limit: int = 20,
) -> tuple[dict[str, Any], ...]:
    """Return compact rows for UI/debug display of field provenance."""
    rows: list[dict[str, Any]] = []
    for path, observed in sorted(state.fields.items()):
        rows.append(
            {
                "field": ".".join(path),
                "value": observed.value,
                "source": observed.source,
                "confidence": observed.confidence,
            }
        )
        if len(rows) >= limit:
            break
    return tuple(rows)


def _field_value(state: LiveSessionState, path: tuple[str, ...]) -> Any:
    field_value = state.fields.get(path)
    if field_value is None:
        return None
    return field_value.value


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_reading(value: Any) -> Reading | None:
    if value is None or value == "":
        return None
    if isinstance(value, Reading):
        return value
    try:
        return parse_reading(str(value))
    except ValueError:
        return None


def _bucket_from_fields(
    state: LiveSessionState,
    quality: int,
) -> QualityBucketObs | None:
    root = ("bucket", str(quality))
    total_cells = _as_int(_field_value(state, root + ("total_cells",)))
    count = _as_int(_field_value(state, root + ("count",)))
    value_sum = _as_int(_field_value(state, root + ("value_sum",)))
    avg_value = _as_float(_field_value(state, root + ("avg_value",)))
    avg_cells = _as_reading(_field_value(state, root + ("avg_cells",)))
    huge_band_raw = _field_value(state, root + ("huge_band",)) or "none"
    huge_band = huge_band_raw if huge_band_raw in HUGE_BAND_RANGE else "none"
    huge_cells_override = _as_int(
        _field_value(state, root + ("huge_cells_override",))
    ) or 0
    value_range = _field_value(state, root + ("value_range",))

    has_any = (
        total_cells is not None
        or count is not None
        or (value_sum is not None and value_sum > 0)
        or avg_value is not None
        or avg_cells is not None
        or huge_band != "none"
        or value_range is not None
    )
    if not has_any:
        return None

    return QualityBucketObs(
        quality=quality,
        avg_cells=avg_cells,
        total_cells=total_cells,
        count=count,
        value_sum=value_sum if value_sum is not None and value_sum > 0 else None,
        avg_value=avg_value,
        value_range=value_range,
        huge_band=huge_band,
        huge_cells_override=huge_cells_override,
    )


def live_state_to_session_obs(state: LiveSessionState) -> SessionObs | None:
    """Convert live state into inference ``SessionObs`` when possible."""
    map_id = _as_int(_field_value(state, ("session", "map_id")))
    hero = _field_value(state, ("session", "hero"))
    if map_id is None or hero not in ("ethan", "aisha"):
        return None

    buckets: dict[int, QualityBucketObs] = {}
    for quality in (1, 2, 3, 4, 5, 6):
        bucket = _bucket_from_fields(state, quality)
        if bucket is not None:
            buckets[quality] = bucket

    return SessionObs(
        map_id=map_id,
        hero=hero,
        warehouse_total_cells=_as_int(
            _field_value(state, ("session", "warehouse_total_cells")),
        ),
        warehouse_total_cells_approx=_as_int(
            _field_value(state, ("session", "warehouse_total_cells_approx")),
        ),
        total_item_count=_as_int(
            _field_value(state, ("session", "total_item_count")),
        ),
        buckets=buckets,
    )


__all__ = (
    "LiveSessionState",
    "ObservedField",
    "apply_observation_batch",
    "live_state_to_session_obs",
    "mark_ready",
    "should_replace_field",
    "summarize_field_sources",
)
