from __future__ import annotations

from bidking_lab.live import (
    FieldUpdate,
    GridItemObservation,
    LiveSessionState,
    LiveObservationBatch,
    apply_observation_batch,
    event_requests_recompute,
    live_state_to_session_obs,
    mark_ready,
    source_priority,
    summarize_blocked_field_updates,
    summarize_field_sources,
)


def test_source_priority_keeps_packet_above_manual_and_ocr() -> None:
    assert source_priority("packet") > source_priority("manual")
    assert source_priority("manual") > source_priority("ocr")
    assert source_priority("ocr") > source_priority("derived")


def test_only_semantic_events_request_recompute() -> None:
    for event_kind in (
        "manual_update",
        "ocr_update",
        "session_started",
        "round_changed",
        "tool_revealed",
        "public_info_changed",
        "session_settled",
    ):
        assert event_requests_recompute(event_kind) is True

    assert event_requests_recompute("heartbeat") is False


def test_live_observation_batch_can_hold_packet_grid_items() -> None:
    batch = LiveObservationBatch(
        source="packet",
        phase="reading",
        field_updates=(
            FieldUpdate(
                path=("session", "warehouse_total_cells"),
                value=123,
                source="packet",
                confidence="exact",
                sequence=7,
            ),
        ),
        grid_items=(
            GridItemObservation(
                cells=12,
                quality=None,
                source="packet",
                confidence="exact",
                shape_key="3x4",
            ),
        ),
        sequence=7,
    )

    assert batch.field_updates[0].path == ("session", "warehouse_total_cells")
    assert batch.grid_items[0].quality is None
    assert batch.grid_items[0].cells == 12


def test_reducer_prefers_packet_over_manual_and_ocr() -> None:
    state = LiveSessionState()
    state = apply_observation_batch(
        state,
        LiveObservationBatch(
            source="ocr",
            field_updates=(
                FieldUpdate(
                    path=("session", "warehouse_total_cells"),
                    value=120,
                    source="ocr",
                    confidence="medium",
                    sequence=1,
                ),
            ),
        ),
    )
    state = apply_observation_batch(
        state,
        LiveObservationBatch(
            source="manual",
            field_updates=(
                FieldUpdate(
                    path=("session", "warehouse_total_cells"),
                    value=123,
                    source="manual",
                    confidence="high",
                    sequence=2,
                ),
            ),
        ),
    )
    state = apply_observation_batch(
        state,
        LiveObservationBatch(
            source="packet",
            field_updates=(
                FieldUpdate(
                    path=("session", "warehouse_total_cells"),
                    value=126,
                    source="packet",
                    confidence="exact",
                    sequence=3,
                ),
            ),
        ),
    )

    field = state.fields[("session", "warehouse_total_cells")]
    assert field.value == 126
    assert field.source == "packet"
    assert state.version == 3
    assert state.dirty is True


def test_reducer_same_source_newer_sequence_wins() -> None:
    state = LiveSessionState()
    for seq, value in ((1, 60), (2, 72)):
        state = apply_observation_batch(
            state,
            LiveObservationBatch(
                source="packet",
                field_updates=(
                    FieldUpdate(
                        path=("session", "warehouse_total_cells"),
                        value=value,
                        source="packet",
                        confidence="exact",
                        sequence=seq,
                    ),
                ),
            ),
        )

    assert state.fields[("session", "warehouse_total_cells")].value == 72


def test_reducer_lower_priority_cannot_overwrite_higher_priority() -> None:
    state = apply_observation_batch(
        LiveSessionState(),
        LiveObservationBatch(
            source="packet",
            field_updates=(
                FieldUpdate(
                    path=("session", "map_id"),
                    value=2401,
                    source="packet",
                    confidence="exact",
                    sequence=1,
                ),
            ),
        ),
    )
    state = apply_observation_batch(
        state,
        LiveObservationBatch(
            source="ocr",
            field_updates=(
                FieldUpdate(
                    path=("session", "map_id"),
                    value=2402,
                    source="ocr",
                    confidence="high",
                    sequence=99,
                ),
            ),
        ),
    )

    assert state.fields[("session", "map_id")].value == 2401


def test_live_state_to_session_obs_builds_inference_observation() -> None:
    state = LiveSessionState()
    state = apply_observation_batch(
        state,
        LiveObservationBatch(
            source="manual",
            phase="reading",
            field_updates=(
                FieldUpdate(
                    path=("session", "map_id"),
                    value=2401,
                    source="manual",
                    confidence="exact",
                ),
                FieldUpdate(
                    path=("session", "hero"),
                    value="ethan",
                    source="manual",
                    confidence="exact",
                ),
                FieldUpdate(
                    path=("session", "warehouse_total_cells"),
                    value=60,
                    source="manual",
                    confidence="exact",
                ),
                FieldUpdate(
                    path=("bucket", "4", "avg_cells"),
                    value="2.50",
                    source="manual",
                    confidence="exact",
                ),
                FieldUpdate(
                    path=("bucket", "4", "value_sum"),
                    value=86_490,
                    source="manual",
                    confidence="high",
                ),
                FieldUpdate(
                    path=("bucket", "5", "total_cells"),
                    value=30,
                    source="packet",
                    confidence="exact",
                ),
            ),
        ),
    )

    obs = live_state_to_session_obs(state)

    assert obs is not None
    assert obs.map_id == 2401
    assert obs.hero == "ethan"
    assert obs.warehouse_capacity() == 60
    assert obs.buckets[4].avg_cells is not None
    assert obs.buckets[4].avg_cells.raw == "2.50"
    assert obs.buckets[4].value_sum == 86_490
    assert obs.buckets[5].total_cells == 30


def test_mark_ready_clears_dirty_without_changing_version() -> None:
    state = apply_observation_batch(
        LiveSessionState(),
        LiveObservationBatch(
            source="manual",
            field_updates=(
                FieldUpdate(
                    path=("session", "hero"),
                    value="ethan",
                    source="manual",
                    confidence="exact",
                ),
            ),
        ),
    )
    ready = mark_ready(state)

    assert ready.version == state.version
    assert ready.dirty is False


def test_summarize_field_sources_returns_stable_debug_rows() -> None:
    state = apply_observation_batch(
        LiveSessionState(),
        LiveObservationBatch(
            source="manual",
            field_updates=(
                FieldUpdate(
                    path=("session", "hero"),
                    value="ethan",
                    source="manual",
                    confidence="exact",
                ),
                FieldUpdate(
                    path=("bucket", "4", "avg_cells"),
                    value="2.90",
                    source="ocr",
                    confidence="high",
                ),
            ),
        ),
    )

    rows = summarize_field_sources(state)

    assert rows == (
        {
            "field": "bucket.4.avg_cells",
            "value": "2.90",
            "source": "ocr",
            "confidence": "high",
        },
        {
            "field": "session.hero",
            "value": "ethan",
            "source": "manual",
            "confidence": "exact",
        },
    )


def test_summarize_blocked_field_updates_reports_lower_priority_attempts() -> None:
    state = apply_observation_batch(
        LiveSessionState(),
        LiveObservationBatch(
            source="manual",
            field_updates=(
                FieldUpdate(
                    path=("bucket", "4", "value_sum"),
                    value=86_490,
                    source="manual",
                    confidence="exact",
                ),
            ),
        ),
    )
    batch = LiveObservationBatch(
        source="ocr",
        field_updates=(
            FieldUpdate(
                path=("bucket", "4", "value_sum"),
                value=80_000,
                source="ocr",
                confidence="high",
            ),
        ),
    )

    rows = summarize_blocked_field_updates(state, batch)
    updated = apply_observation_batch(state, batch)

    assert rows == (
        {
            "field": "bucket.4.value_sum",
            "attempted_value": 80_000,
            "attempted_source": "ocr",
            "kept_value": 86_490,
            "kept_source": "manual",
            "reason": "lower_priority_source",
        },
    )
    assert updated.fields[("bucket", "4", "value_sum")].value == 86_490


def test_heartbeat_metadata_update_does_not_make_inference_stale() -> None:
    ready = mark_ready(
        apply_observation_batch(
            LiveSessionState(),
            LiveObservationBatch(
                source="manual",
                field_updates=(
                    FieldUpdate(
                        path=("session", "hero"),
                        value="ethan",
                        source="manual",
                        confidence="exact",
                    ),
                ),
            ),
        )
    )

    heartbeat = apply_observation_batch(
        ready,
        LiveObservationBatch(
            source="packet",
            event_kind="heartbeat",
            field_updates=(
                FieldUpdate(
                    path=("transport", "last_seen_ms"),
                    value=1234,
                    source="packet",
                    confidence="exact",
                ),
            ),
        ),
    )

    assert heartbeat.version == ready.version + 1
    assert heartbeat.dirty is False
