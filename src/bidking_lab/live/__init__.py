"""Live observation interfaces for future realtime monitoring.

This package intentionally contains only source-agnostic data contracts for
now. OCR, manual UI input, and future packet capture should all emit the same
observation events before anything is merged into ``SessionObs``.
"""

from bidking_lab.live.types import (
    AuctionPhase,
    FieldUpdate,
    GridItemObservation,
    LiveEventKind,
    LiveObservationBatch,
    ObservationSource,
    SourceConfidence,
    event_requests_recompute,
    source_priority,
)
from bidking_lab.live.state import (
    LiveSessionState,
    ObservedField,
    apply_observation_batch,
    live_session_matches_context,
    live_state_to_session_obs,
    mark_ready,
    should_replace_field,
    summarize_blocked_field_updates,
    summarize_field_sources,
    summarize_selected_field_sources,
)
from bidking_lab.live.legacy import (
    legacy_obs_fields,
    live_batch_from_legacy_obs,
)

__all__ = (
    "AuctionPhase",
    "FieldUpdate",
    "GridItemObservation",
    "LiveEventKind",
    "LiveObservationBatch",
    "ObservationSource",
    "SourceConfidence",
    "LiveSessionState",
    "ObservedField",
    "apply_observation_batch",
    "live_session_matches_context",
    "live_state_to_session_obs",
    "mark_ready",
    "should_replace_field",
    "summarize_blocked_field_updates",
    "summarize_field_sources",
    "summarize_selected_field_sources",
    "legacy_obs_fields",
    "live_batch_from_legacy_obs",
    "event_requests_recompute",
    "source_priority",
)
