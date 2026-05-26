"""Source-agnostic observation contracts for realtime monitoring.

These types are deliberately small. They reserve room for packet-capture
signals without tying the inference engine to ProtoHub, OCR, Streamlit, or
any specific transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ObservationSource = Literal["manual", "ocr", "packet", "derived"]
SourceConfidence = Literal["low", "medium", "high", "exact"]
AuctionPhase = Literal[
    "unknown",
    "map_select",
    "reading",
    "bidding",
    "settled",
]
LiveEventKind = Literal[
    "manual_update",
    "ocr_update",
    "session_started",
    "round_changed",
    "tool_revealed",
    "public_info_changed",
    "session_settled",
    "heartbeat",
]


_SOURCE_PRIORITY: dict[ObservationSource, int] = {
    "derived": 10,
    "ocr": 20,
    "manual": 30,
    "packet": 40,
}
_RECOMPUTE_EVENTS: frozenset[LiveEventKind] = frozenset(
    {
        "manual_update",
        "ocr_update",
        "session_started",
        "round_changed",
        "tool_revealed",
        "public_info_changed",
        "session_settled",
    }
)


def source_priority(source: ObservationSource) -> int:
    """Return merge priority for conflicting updates.

    Packet observations are highest because they should come from game state
    rather than screen text. Manual remains above OCR so the user can override
    recognition mistakes.
    """
    return _SOURCE_PRIORITY[source]


def event_requests_recompute(event_kind: LiveEventKind) -> bool:
    """Return whether a batch can change inference recommendations."""
    return event_kind in _RECOMPUTE_EVENTS


@dataclass(frozen=True)
class FieldUpdate:
    """One observed field update from manual UI, OCR, packet, or derived logic.

    ``path`` is a stable logical path, not a Streamlit widget key. Examples:
    ``("session", "warehouse_total_cells")`` or
    ``("bucket", "4", "avg_cells")``.
    """

    path: tuple[str, ...]
    value: Any
    source: ObservationSource
    confidence: SourceConfidence
    observed_at_ms: int | None = None
    sequence: int | None = None


@dataclass(frozen=True)
class GridItemObservation:
    """One visible/known warehouse item footprint.

    This is the reserved interface for future Ethan / packet-capture data:
    it can represent unknown-quality outlines, known-quality items, or exact
    item ids without forcing every case into ``QualityBucketObs`` too early.
    """

    cells: int
    source: ObservationSource
    confidence: SourceConfidence
    item_id: int | None = None
    quality: int | None = None
    shape_key: str | None = None
    value: int | None = None
    observed_at_ms: int | None = None


@dataclass(frozen=True)
class LiveObservationBatch:
    """A batch of observations from one discrete game or UI event.

    ``heartbeat`` batches may carry transport metadata, but do not make
    inference results stale. Emit a semantic event when game facts change.
    """

    source: ObservationSource
    event_kind: LiveEventKind = "manual_update"
    phase: AuctionPhase = "unknown"
    field_updates: tuple[FieldUpdate, ...] = ()
    grid_items: tuple[GridItemObservation, ...] = ()
    sequence: int | None = None
    observed_at_ms: int | None = None
