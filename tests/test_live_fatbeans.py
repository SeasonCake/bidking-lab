from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from bidking_lab.live.fatbeans import (
    FatbeansActionResult,
    FatbeansCaptureEvents,
    FatbeansObservedItem,
    FatbeansPublicInfo,
    FatbeansStateEvent,
    latest_player_bids,
    live_batches_from_fatbeans_capture,
    live_batches_from_fatbeans_events,
    live_batches_from_fatbeans_capture_payload,
    load_fatbeans_packets_from_rows,
    parse_fatbeans_capture,
    parse_fatbeans_capture_payload,
)
from bidking_lab.live import (
    FieldUpdate,
    LayoutEstimatePolicy,
    estimate_warehouse_from_layout,
    grid_footprint,
    final_truth_from_events,
    layout_evidence_from_batches,
    layout_grid_view,
    layout_replay_stages,
    layout_risk_label,
    GridItemObservation,
    LiveSessionState,
    LiveObservationBatch,
    apply_observation_batch,
    live_state_to_session_obs,
)


FATBEANS_SAMPLE_DIR = (
    Path(__file__).resolve().parents[1] / "data" / "samples" / "fatbeans"
)

PROJECT4_CAPTURE = FATBEANS_SAMPLE_DIR / "bid_king_project4.json"


def test_grid_footprint_decodes_fatbeans_local_and_shape() -> None:
    footprint = grid_footprint(94, "33")

    assert footprint is not None
    assert (footprint.row, footprint.col) == (10, 5)
    assert (footprint.width, footprint.height) == (3, 3)
    assert (footprint.bottom_row, footprint.right_col) == (12, 7)


def test_grid_footprint_treats_missing_local_as_zero() -> None:
    footprint = grid_footprint(None, "23")

    assert footprint is not None
    assert (footprint.row, footprint.col) == (1, 1)
    assert (footprint.bottom_row, footprint.right_col) == (3, 2)


def test_layout_evidence_prefers_pre_settlement_grid_and_reports_risk() -> None:
    batches = (
        LiveObservationBatch(
            source="packet",
            phase="reading",
            sequence=1,
            grid_items=(
                # Top-left default local 0: rows 1-3, cols 1-2.
                GridItemObservation(
                    cells=6,
                    source="packet",
                    confidence="exact",
                    quality=5,
                    shape_key="23",
                    local_index=None,
                ),
                # Sparse deep tail: rows 15-17, cols 1-2.
                GridItemObservation(
                    cells=6,
                    source="packet",
                    confidence="exact",
                    quality=5,
                    shape_key="23",
                    local_index=140,
                ),
            ),
        ),
        LiveObservationBatch(
            source="packet",
            phase="settled",
            sequence=2,
            grid_items=(
                GridItemObservation(
                    cells=1,
                    source="packet",
                    confidence="exact",
                    quality=1,
                    shape_key="11",
                    local_index=0,
                ),
            ),
        ),
    )

    evidence = layout_evidence_from_batches(batches)

    assert evidence is not None
    assert evidence.sequence == 1
    assert evidence.max_row == 17
    assert evidence.total_cells == 12
    assert evidence.bounding_cells == 170
    assert evidence.bottom_tail_item_count == 1
    assert evidence.sparsity_ratio > 0.9
    assert layout_risk_label(evidence).startswith("低")

    estimate = estimate_warehouse_from_layout(evidence)
    assert estimate.min_reasonable_cells == 12
    assert estimate.p50_guess is None
    assert estimate.p90_guess is None
    assert estimate.confidence == "低"
    assert not estimate.locked


def test_layout_estimate_policy_can_be_swapped_for_sample_fitting() -> None:
    batch = LiveObservationBatch(
        source="packet",
        phase="reading",
        sequence=3,
        grid_items=(
            GridItemObservation(
                cells=16,
                source="packet",
                confidence="exact",
                quality=5,
                shape_key="44",
                local_index=0,
            ),
            GridItemObservation(
                cells=1,
                source="packet",
                confidence="exact",
                quality=2,
                shape_key="11",
                local_index=39,
            ),
        ),
    )
    evidence = layout_evidence_from_batches((batch,))
    assert evidence is not None

    default = estimate_warehouse_from_layout(evidence)
    fitted = estimate_warehouse_from_layout(
        evidence,
        policy=LayoutEstimatePolicy(
            name="sample-fit-test",
            medium_p50_margin=5,
        ),
    )

    assert default.policy_name == "conservative-v0"
    assert default.p50_guess == 20
    assert fitted.policy_name == "sample-fit-test"
    assert fitted.p50_guess == 35
    assert fitted.p90_guess == 40


def test_layout_grid_view_is_frontend_neutral() -> None:
    batch = LiveObservationBatch(
        source="packet",
        phase="reading",
        sequence=7,
        grid_items=(
            GridItemObservation(
                cells=4,
                source="packet",
                confidence="exact",
                item_id=12345,
                quality=4,
                shape_key="22",
                local_index=23,
            ),
        ),
    )
    evidence = layout_evidence_from_batches((batch,))

    assert evidence is not None
    view = layout_grid_view(evidence)

    assert view.sequence == 7
    assert view.rows == 4
    assert view.columns == 10
    assert "已放置 1 件 / 4 格" in view.summary
    assert len(view.items) == 1
    item = view.items[0]
    assert (item.row, item.col, item.width, item.height) == (3, 4, 2, 2)
    assert item.quality == 4
    assert item.label == "Q4\n12345"
    assert "shape=2x2" in item.tooltip
    assert item.z_index == 10


def test_known_quality_grid_items_become_bucket_lower_bounds() -> None:
    state = LiveSessionState()
    batch = LiveObservationBatch(
        source="packet",
        event_kind="tool_revealed",
        phase="reading",
        sequence=1,
        field_updates=(
            FieldUpdate(
                path=("session", "map_id"),
                value=2401,
                source="packet",
                confidence="exact",
                sequence=1,
            ),
            FieldUpdate(
                path=("session", "hero"),
                value="aisha",
                source="packet",
                confidence="exact",
                sequence=1,
            ),
        ),
        grid_items=(
            GridItemObservation(
                cells=9,
                source="packet",
                confidence="exact",
                quality=3,
                shape_key="33",
                local_index=94,
            ),
            GridItemObservation(
                cells=4,
                source="packet",
                confidence="exact",
                quality=4,
                shape_key="22",
                local_index=23,
            ),
            GridItemObservation(
                cells=6,
                source="packet",
                confidence="exact",
                quality=None,
                shape_key="23",
                local_index=40,
            ),
        ),
    )

    session = live_state_to_session_obs(apply_observation_batch(state, batch))

    assert session is not None
    assert session.buckets[3].total_cells_min == 9
    assert session.buckets[3].count_min == 1
    assert session.buckets[4].total_cells_min == 4
    assert session.buckets[4].count_min == 1
    assert session.visible_outline_item_count_min == 3
    assert session.visible_outline_total_cells_min == 19
    assert session.unknown_outline_item_count == 1
    assert session.unknown_outline_total_cells == 6


@pytest.mark.parametrize(
    ("action_id", "category"),
    [
        (100157, 107),
        (100160, 110),
    ],
)
def test_category_outline_action_becomes_soft_category_observation(
    action_id: int,
    category: int,
) -> None:
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(),
        statuses=(),
        states=(
            FatbeansStateEvent(
                sort_id=7,
                capture_time="",
                message_id=0x0025,
                session_id="s1",
                map_id=2401,
                round_index=1,
                action_results=(
                    FatbeansActionResult(
                        action_id=action_id,
                        result=None,
                        result_field=None,
                        observed_items=(
                            FatbeansObservedItem(
                                local_index=0,
                                runtime_id=11,
                                item_id=None,
                                quality=None,
                                value=None,
                                shape_code=13,
                                cells=None,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    batches = live_batches_from_fatbeans_events(events)
    state = LiveSessionState()
    seed = LiveObservationBatch(
        source="manual",
        event_kind="manual_update",
        field_updates=(
            FieldUpdate(
                path=("session", "hero"),
                value="aisha",
                source="manual",
                confidence="exact",
            ),
        ),
    )
    state = apply_observation_batch(state, seed)
    for batch in batches:
        state = apply_observation_batch(state, batch)

    assert batches[0].grid_items[0].category == category
    session = live_state_to_session_obs(state)

    assert session is not None
    assert session.category_items[0].category == category
    assert session.category_items[0].cells == 3


def test_category_outline_merges_with_existing_runtime_item() -> None:
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(),
        statuses=(),
        states=(
            FatbeansStateEvent(
                sort_id=7,
                capture_time="",
                message_id=0x0025,
                session_id="s1",
                map_id=2401,
                round_index=1,
                public_infos=(
                    FatbeansPublicInfo(
                        info_id=200050,
                        map_id=2401,
                        value=2,
                        value_field=11,
                        observed_items=(
                            FatbeansObservedItem(
                                local_index=10,
                                runtime_id=11,
                                item_id=1103006,
                                quality=3,
                                value=3240,
                                shape_code=21,
                                cells=2,
                            ),
                        ),
                    ),
                ),
                action_results=(
                    FatbeansActionResult(
                        action_id=100160,
                        result=None,
                        result_field=None,
                        observed_items=(
                            FatbeansObservedItem(
                                local_index=10,
                                runtime_id=11,
                                item_id=None,
                                quality=None,
                                value=None,
                                shape_code=21,
                                cells=None,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    batch = live_batches_from_fatbeans_events(events)[0]

    assert len(batch.grid_items) == 1
    assert batch.grid_items[0].item_id == 1103006
    assert batch.grid_items[0].category == 110


def test_fatbeans_loader_skips_non_tcp_rows_with_http_payload_metadata() -> None:
    packets = load_fatbeans_packets_from_rows(
        [
            {
                "SortID": 1,
                "Protocol": "Https",
                "Direct": "SEND",
                "SrcIP": "127.0.0.1",
                "SrcPort": 1,
                "DstIP": "104.153.233.180",
                "DstPort": 443,
                "DataLength": 1781,
                "Data": "",
                "Url": "https://api.backblazeb2.com/b2api/v2/b2_authorize_account",
            },
            {
                "SortID": 2,
                "Protocol": "Tcp",
                "Direct": "SEND",
                "SrcIP": "127.0.0.1",
                "SrcPort": 20062,
                "DstIP": "8.133.195.27",
                "DstPort": 10000,
                "CaptureTime": "2026-05-28T13:28:55",
                "DataLength": 12,
                "Data": "AAAAAAAAAAAAAAAA",
            },
        ]
    )

    assert len(packets) == 1
    assert packets[0].sort_id == 2
    assert packets[0].src == "127.0.0.1:20062"


@pytest.mark.skipif(
    not PROJECT4_CAPTURE.exists(),
    reason="local Fatbeans project4 capture is not committed",
)
def test_fatbeans_project4_extracts_known_round_facts() -> None:
    events = parse_fatbeans_capture(PROJECT4_CAPTURE)

    assert len(events.packets) == 97
    assert len(events.frames) == 83
    assert [send.value for send in events.sends if send.kind == "bid"] == [
        290000,
        290000,
        290000,
    ]
    assert [send.value for send in events.sends if send.kind == "action"] == [
        100105,
        100104,
        100124,
    ]

    first_state = next(state for state in events.states if state.sort_id == 34)
    assert first_state.session_id == "2401:1274127923736451"
    assert first_state.map_id == 2401
    assert first_state.round_index == 1
    assert {bid.name: bid.current_value for bid in first_state.bids} == {
        "设计师lcjeremy": 153299,
        "加菲_Barista": 290000,
        "梦色幻想": 288888,
        "折翼的奇美拉": 220000,
    }
    assert [(r.action_id, r.result) for r in first_state.action_results] == [
        (100105, 48)
    ]
    assert first_state.public_infos[0].info_id == 200014
    assert first_state.public_infos[0].value == pytest.approx(2.965517, abs=1e-6)

    second_state = next(state for state in events.states if state.sort_id == 69)
    assert [(r.action_id, r.result) for r in second_state.action_results] == [
        (100105, 48),
        (100104, 8),
    ]
    assert [(info.info_id, info.value) for info in second_state.public_infos] == [
        (200014, pytest.approx(2.965517, abs=1e-6)),
        (200033, pytest.approx(3765.0, abs=1e-6)),
    ]

    settled = next(state for state in events.states if state.sort_id == 102)
    assert settled.settlement_loss_units == 16566
    assert [(r.action_id, r.result) for r in settled.action_results] == [
        (100105, 48),
        (100104, 8),
        (100124, 45778),
    ]
    assert latest_player_bids(events.states) == {
        "设计师lcjeremy": 417779,
        "加菲_Barista": 290000,
        "梦色幻想": 188888,
        "折翼的奇美拉": 220000,
    }


@pytest.mark.skipif(
    not PROJECT4_CAPTURE.exists(),
    reason="local Fatbeans project4 capture is not committed",
)
def test_fatbeans_project4_converts_supported_fields_to_live_batches() -> None:
    batches = live_batches_from_fatbeans_capture(PROJECT4_CAPTURE)
    updates = {
        update.path: update.value
        for batch in batches
        for update in batch.field_updates
    }

    assert updates[("session", "map_id")] == 2401
    assert updates[("session", "round")] == 2
    assert updates[("session", "hero")] == "ethan"
    assert updates[("bucket", "3", "total_cells")] == 48
    assert updates[("bucket", "4", "value_sum")] == 45778
    assert all(batch.source == "packet" for batch in batches)


@pytest.mark.skipif(
    not PROJECT4_CAPTURE.exists(),
    reason="local Fatbeans project4 capture is not committed",
)
def test_fatbeans_project4_payload_entrypoints_match_path_entrypoints() -> None:
    raw = PROJECT4_CAPTURE.read_bytes()

    from_path = parse_fatbeans_capture(PROJECT4_CAPTURE)
    from_payload = parse_fatbeans_capture_payload(raw)
    path_batches = live_batches_from_fatbeans_capture(PROJECT4_CAPTURE)
    payload_batches = live_batches_from_fatbeans_capture_payload(raw)

    assert len(from_payload.packets) == len(from_path.packets)
    assert len(from_payload.frames) == len(from_path.frames)
    assert len(from_payload.states) == len(from_path.states)
    assert payload_batches == path_batches


PACKAGE5_CAPTURE = FATBEANS_SAMPLE_DIR / "bid_king_packages_5.json"


@pytest.mark.skipif(
    not PACKAGE5_CAPTURE.exists(),
    reason="local Fatbeans package5 capture is not committed",
)
def test_fatbeans_package5_extracts_revealed_items_and_inventory() -> None:
    events = parse_fatbeans_capture(PACKAGE5_CAPTURE)

    assert len(events.packets) == 103
    assert len(events.frames) == 118
    assert [send.value for send in events.sends if send.kind == "action"] == [
        100136,
        100129,
        100105,
        100104,
        100112,
    ]

    first_state = next(state for state in events.states if state.sort_id == 72)
    treasure = first_state.action_results[0]
    assert treasure.action_id == 100136
    assert treasure.result is None
    assert [(item.runtime_id, item.quality) for item in treasure.observed_items] == [
        (1274127927583413, 4),
        (1274127927583400, 5),
        (1274127927583403, 4),
        (1274127927583386, 5),
    ]

    second_state = next(state for state in events.states if state.sort_id == 102)
    sampling = next(
        result for result in second_state.action_results
        if result.action_id == 100129
    )
    assert [(item.item_id, item.quality, item.value, item.cells) for item in sampling.observed_items] == [
        (1021005, 1, 207, 2),
        (1023009, 3, 1313, 1),
    ]
    assert sampling.result == 3

    settled = next(state for state in events.states if state.sort_id == 194)
    assert settled.round_no == 4
    assert len(settled.inventory_items) == 42
    assert sum(item.cells for item in settled.inventory_items) == 114
    purple_avg = next(
        result for result in settled.action_results
        if result.action_id == 100112
    )
    assert purple_avg.result == pytest.approx(2.3076923, abs=1e-6)
    by_runtime = {item.runtime_id: item for item in settled.inventory_items}
    assert by_runtime[1274127927583413].item_id == 1024001
    assert by_runtime[1274127927583413].cells == 4
    assert by_runtime[1274127927583400].item_id == 1045007
    assert by_runtime[1274127927583400].cells == 6


@pytest.mark.skipif(
    not PACKAGE5_CAPTURE.exists(),
    reason="local Fatbeans package5 capture is not committed",
)
def test_fatbeans_package5_live_batches_include_inventory_constraints() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE5_CAPTURE)
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
    for batch in batches:
        state = apply_observation_batch(state, batch)

    session = live_state_to_session_obs(state)

    assert session is not None
    assert session.map_id == 2408
    assert session.warehouse_total_cells == 114
    assert session.total_item_count == 42
    assert session.buckets[1].total_cells == 3
    assert session.buckets[1].count == 2
    assert session.buckets[3].total_cells == 26
    assert session.buckets[4].total_cells == 30
    assert session.buckets[4].count == 13
    assert session.buckets[4].avg_cells is not None
    assert session.buckets[4].avg_cells.raw.startswith("2.307692")
    assert session.buckets[5].total_cells == 42
    assert session.buckets[6].total_cells == 9
    assert len(state.grid_items) == 42


PACKAGE6_CAPTURE = FATBEANS_SAMPLE_DIR / "bid_king_packages6.json"


@pytest.mark.skipif(
    not PACKAGE6_CAPTURE.exists(),
    reason="local Fatbeans package6 capture is not committed",
)
def test_fatbeans_package6_extracts_skill_public_and_inventory_facts() -> None:
    events = parse_fatbeans_capture(PACKAGE6_CAPTURE)

    assert len(events.packets) == 70
    assert len(events.frames) == 74
    assert [send.value for send in events.sends if send.kind == "action"] == [
        100129
    ]

    first_state = next(state for state in events.states if state.sort_id == 61)
    assert [(reveal.skill_id, len(reveal.observed_items)) for reveal in first_state.skill_reveals] == [
        (1001034, 6),
        (1001033, 13),
    ]

    third_state = next(state for state in events.states if state.sort_id == 116)
    public_reveal = next(
        info for info in third_state.public_infos
        if info.info_id == 200026
    )
    assert [(item.runtime_id, item.quality) for item in public_reveal.observed_items] == [
        (1274127940693032, 4),
        (1274127940693022, 5),
        (1274127940693030, 2),
    ]

    settled = next(state for state in events.states if state.sort_id == 146)
    sampling = settled.action_results[0]
    assert sampling.action_id == 100129
    assert [
        (item.item_id, item.quality, item.value, item.shape_code, item.cells)
        for item in sampling.observed_items
    ] == [
        (1025001, 5, 49920, 22, 4),
        (1071004, 1, 137, 11, 1),
    ]

    assert len(settled.inventory_items) == 53
    assert sum(item.cells for item in settled.inventory_items) == 137
    counts = Counter(item.quality for item in settled.inventory_items)
    cells = Counter()
    for item in settled.inventory_items:
        cells[item.quality] += item.cells
    assert counts == {1: 6, 2: 13, 3: 14, 4: 9, 5: 7, 6: 4}
    assert cells == {1: 11, 2: 24, 3: 28, 4: 32, 5: 29, 6: 13}


@pytest.mark.skipif(
    not PACKAGE6_CAPTURE.exists(),
    reason="local Fatbeans package6 capture is not committed",
)
def test_fatbeans_package6_live_batches_include_skill_shapes() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE6_CAPTURE)
    first = next(batch for batch in batches if batch.sequence == 61)
    third = next(batch for batch in batches if batch.sequence == 116)
    settled = next(batch for batch in batches if batch.sequence == 146)

    assert len(first.grid_items) == 19
    assert sum(item.cells for item in first.grid_items) == 35
    assert len(third.grid_items) == 42
    assert sum(item.cells for item in third.grid_items) == 95
    assert len(settled.grid_items) == 53
    assert sum(item.cells for item in settled.grid_items) == 137


@pytest.mark.skipif(
    not PACKAGE6_CAPTURE.exists(),
    reason="local Fatbeans package6 capture is not committed",
)
def test_fatbeans_package6_aisha_reveals_pin_bucket_cells_and_counts() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE6_CAPTURE)
    first = next(batch for batch in batches if batch.sequence == 61)
    third = next(batch for batch in batches if batch.sequence == 116)
    first_updates = {update.path: update.value for update in first.field_updates}
    third_updates = {update.path: update.value for update in third.field_updates}

    assert first_updates[("bucket", "1", "total_cells")] == 11
    assert first_updates[("bucket", "1", "count")] == 6
    assert first_updates[("bucket", "2", "total_cells")] == 24
    assert first_updates[("bucket", "2", "count")] == 13
    assert third_updates[("bucket", "3", "total_cells")] == 28
    assert third_updates[("bucket", "3", "count")] == 14
    assert third_updates[("bucket", "4", "total_cells")] == 32
    assert third_updates[("bucket", "4", "count")] == 9


PACKAGE7_CAPTURE = FATBEANS_SAMPLE_DIR / "bid_king_packages7.json"
PACKAGE8_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package8.json"
PACKAGE9_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package_9_with_whole_bucket_perspective.json"
PACKAGE10_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package10.json"
PACKAGE11_CAPTURE = (
    FATBEANS_SAMPLE_DIR
    / "bidking_package11_with_4itemsinspection_bucketperspective_ethansskill.json"
)
PACKAGE12_CAPTURE = (
    FATBEANS_SAMPLE_DIR
    / "bidking_package12_wholebucktperspection_scan_publicinfo_basicitems_aisha.json"
)
PACKAGE13_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package13_eye_of_clarity_ethan.json"
PACKAGE14_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package14_aisha.json"
PACKAGE15_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package15_ethan.json"
PACKAGE16_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package16_ethan.json"
PACKAGE17_CAPTURE = FATBEANS_SAMPLE_DIR / "bidking_package17_eye_of_clarity_ethan.json"


def _shape_cells(shape_code: int | None) -> int:
    if shape_code is None:
        return 0
    return (shape_code // 10) * (shape_code % 10)


@pytest.mark.skipif(
    not PACKAGE7_CAPTURE.exists(),
    reason="local Fatbeans package7 capture is not committed",
)
def test_fatbeans_package7_extracts_aisha_and_settlement_inventory() -> None:
    events = parse_fatbeans_capture(PACKAGE7_CAPTURE)

    assert [send.value for send in events.sends if send.kind == "action"] == [
        100129,
        100136,
    ]
    settled = next(state for state in events.states if state.inventory_items)

    assert settled.map_id == 2401
    assert settled.round_index == 2
    assert len(settled.inventory_items) == 33
    assert sum(item.cells for item in settled.inventory_items) == 85
    counts = Counter(item.quality for item in settled.inventory_items)
    cells = Counter()
    for item in settled.inventory_items:
        cells[item.quality] += item.cells
    assert counts == {1: 8, 2: 7, 3: 8, 4: 4, 5: 5, 6: 1}
    assert cells == {1: 18, 2: 11, 3: 27, 4: 9, 5: 19, 6: 1}


@pytest.mark.skipif(
    not PACKAGE7_CAPTURE.exists(),
    reason="local Fatbeans package7 capture is not committed",
)
def test_fatbeans_package7_live_batches_include_aisha_reveal_constraints() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE7_CAPTURE)
    state = apply_observation_batch(
        LiveSessionState(),
        LiveObservationBatch(
            source="manual",
            field_updates=(
                FieldUpdate(
                    path=("session", "hero"),
                    value="aisha",
                    source="manual",
                    confidence="exact",
                ),
            ),
        ),
    )
    for batch in batches:
        state = apply_observation_batch(state, batch)
    session = live_state_to_session_obs(state)

    assert session is not None
    assert session.map_id == 2401
    assert session.buckets[1].count == 8
    assert session.buckets[1].total_cells == 18
    assert session.buckets[2].count == 7
    assert session.buckets[2].total_cells == 11
    assert session.buckets[3].count == 8
    assert session.buckets[3].total_cells == 27


@pytest.mark.skipif(
    not PACKAGE8_CAPTURE.exists(),
    reason="local Fatbeans package8 capture is not committed",
)
def test_fatbeans_package8_extracts_digital_outline_item_and_inventory() -> None:
    events = parse_fatbeans_capture(PACKAGE8_CAPTURE)

    assert [send.value for send in events.sends if send.kind == "action"] == [
        100136,
        100129,
        100157,
    ]
    settled = next(state for state in events.states if state.inventory_items)
    digital_outline = next(
        result for result in settled.action_results
        if result.action_id == 100157
    )

    assert [(item.shape_code, item.cells) for item in digital_outline.observed_items] == [
        (13, None),
        (11, None),
        (11, None),
    ]
    assert len(settled.inventory_items) == 37
    assert sum(item.cells for item in settled.inventory_items) == 101
    counts = Counter(item.quality for item in settled.inventory_items)
    cells = Counter()
    for item in settled.inventory_items:
        cells[item.quality] += item.cells
    assert counts == {1: 5, 2: 3, 3: 14, 4: 8, 5: 4, 6: 3}
    assert cells == {1: 7, 2: 4, 3: 44, 4: 35, 5: 7, 6: 4}


@pytest.mark.skipif(
    not PACKAGE8_CAPTURE.exists(),
    reason="local Fatbeans package8 capture is not committed",
)
def test_fatbeans_package8_live_batches_include_aisha_reveal_constraints() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE8_CAPTURE)
    third = next(batch for batch in batches if batch.sequence == 59)
    updates = {update.path: update.value for update in third.field_updates}

    assert updates[("bucket", "1", "total_cells")] == 7
    assert updates[("bucket", "1", "count")] == 5
    assert updates[("bucket", "2", "total_cells")] == 4
    assert updates[("bucket", "2", "count")] == 3
    assert updates[("bucket", "3", "total_cells")] == 44
    assert updates[("bucket", "3", "count")] == 14
    assert updates[("bucket", "4", "total_cells")] == 35
    assert updates[("bucket", "4", "count")] == 8


@pytest.mark.skipif(
    not PACKAGE9_CAPTURE.exists(),
    reason="local Fatbeans package9 capture is not committed",
)
def test_fatbeans_package9_whole_bucket_perspective_matches_inventory_cells() -> None:
    events = parse_fatbeans_capture(PACKAGE9_CAPTURE)
    settled = next(state for state in events.states if state.inventory_items)
    perspective = next(
        result for result in settled.action_results
        if result.action_id == 100100
    )

    assert len(perspective.observed_items) == len(settled.inventory_items) == 41
    assert sum(_shape_cells(item.shape_code) for item in perspective.observed_items) == 101
    assert sum(item.cells for item in settled.inventory_items) == 101


@pytest.mark.skipif(
    not PACKAGE10_CAPTURE.exists(),
    reason="local Fatbeans package10 capture is not committed",
)
def test_fatbeans_package10_skips_https_noise_and_extracts_settlement() -> None:
    events = parse_fatbeans_capture(PACKAGE10_CAPTURE)
    settled = next(state for state in events.states if state.inventory_items)

    assert [send.value for send in events.sends if send.kind == "action"] == [
        100105,
        100104,
        100129,
    ]
    assert len(settled.inventory_items) == 38
    assert sum(item.cells for item in settled.inventory_items) == 121
    random_inspection = next(
        result for result in settled.action_results
        if result.action_id == 100129
    )
    assert [
        (item.item_id, item.quality, item.value, item.shape_code)
        for item in random_inspection.observed_items
    ] == [
        (1034007, 4, 4428, 12),
        (1083011, 3, 14659, 53),
    ]


@pytest.mark.skipif(
    not PACKAGE10_CAPTURE.exists(),
    reason="local Fatbeans package10 capture is not committed",
)
def test_fatbeans_package10_map_public_purple_outlines_join_ethan_shapes() -> None:
    events = parse_fatbeans_capture(PACKAGE10_CAPTURE)
    first_state = next(state for state in events.states if state.sort_id == 28)
    public_purple = next(
        info for info in first_state.public_infos
        if info.info_id == 200001
    )
    opening_ethan = next(
        reveal for reveal in first_state.skill_reveals
        if reveal.skill_id == 1002081
    )

    assert {item.quality for item in opening_ethan.observed_items} == {None}
    assert len(public_purple.observed_items) == 13
    assert {item.quality for item in public_purple.observed_items} == {4}
    assert sum(_shape_cells(item.shape_code) for item in public_purple.observed_items) == 39

    batches = live_batches_from_fatbeans_capture(PACKAGE10_CAPTURE)
    first_batch = next(batch for batch in batches if batch.sequence == 28)
    first_updates = {update.path: update.value for update in first_batch.field_updates}
    purple_items = [item for item in first_batch.grid_items if item.quality == 4]

    assert first_updates[("bucket", "4", "total_cells")] == 39
    assert first_updates[("bucket", "4", "count")] == 13
    assert len(purple_items) == 13
    assert sum(item.cells for item in purple_items) == 39

    state = LiveSessionState()
    state = apply_observation_batch(state, first_batch)
    session = live_state_to_session_obs(state)

    assert session is not None
    assert session.buckets[4].total_cells == 39
    assert session.buckets[4].count == 13
    assert session.visible_outline_item_count_min == 27
    assert session.visible_outline_total_cells_min == 96
    assert session.unknown_outline_item_count == 14
    assert session.unknown_outline_total_cells == 57


@pytest.mark.skipif(
    not PACKAGE11_CAPTURE.exists(),
    reason="local Fatbeans package11 capture is not committed",
)
def test_fatbeans_package11_ethan_skill_matches_whole_bucket_perspective() -> None:
    events = parse_fatbeans_capture(PACKAGE11_CAPTURE)
    pre_settlement = next(state for state in events.states if state.sort_id == 80)
    settled = next(state for state in events.states if state.inventory_items)
    final_skill = next(
        reveal for reveal in pre_settlement.skill_reveals
        if reveal.skill_id == 1002085
    )
    perspective = next(
        result for result in settled.action_results
        if result.action_id == 100100
    )

    skill_shapes = {
        item.runtime_id: item.shape_code for item in final_skill.observed_items
    }
    perspective_shapes = {
        item.runtime_id: item.shape_code for item in perspective.observed_items
    }

    assert skill_shapes == perspective_shapes
    assert len(skill_shapes) == len(settled.inventory_items) == 32
    assert sum(_shape_cells(shape) for shape in skill_shapes.values()) == 79
    assert sum(item.cells for item in settled.inventory_items) == 79


@pytest.mark.skipif(
    not PACKAGE11_CAPTURE.exists(),
    reason="local Fatbeans package11 capture is not committed",
)
def test_fatbeans_package11_baoguang_quality_joins_ethan_shapes() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE11_CAPTURE)
    first = next(batch for batch in batches if batch.sequence == 19)
    cells_by_quality = Counter()
    count_by_quality = Counter()
    for item in first.grid_items:
        if item.quality is None:
            continue
        cells_by_quality[item.quality] += item.cells
        count_by_quality[item.quality] += 1

    assert count_by_quality[3] == 3
    assert cells_by_quality[3] == 6
    assert count_by_quality[4] == 1
    assert cells_by_quality[4] == 2


@pytest.mark.skipif(
    not PACKAGE11_CAPTURE.exists(),
    reason="local Fatbeans package11 capture is not committed",
)
def test_fatbeans_package11_full_ethan_outline_pins_live_warehouse() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE11_CAPTURE)
    fourth = next(batch for batch in batches if batch.sequence == 80)
    updates = {update.path: update.value for update in fourth.field_updates}

    assert updates[("session", "warehouse_total_cells")] == 79
    assert updates[("session", "total_item_count")] == 32
    assert len(fourth.grid_items) == 32
    assert sum(item.cells for item in fourth.grid_items) == 79


@pytest.mark.skipif(
    not PACKAGE12_CAPTURE.exists(),
    reason="local Fatbeans package12 capture is not committed",
)
def test_fatbeans_package12_aisha_full_perspective_pins_warehouse() -> None:
    events = parse_fatbeans_capture(PACKAGE12_CAPTURE)
    third = next(state for state in events.states if state.sort_id == 79)
    inspection = next(
        result for result in third.action_results
        if result.action_id == 100128
    )
    assert [
        (item.local_index, item.item_id, item.quality, item.shape_code)
        for item in inspection.observed_items
    ] == [(2, 1063002, 3, 12)]

    second = next(state for state in events.states if state.sort_id == 61)
    random_inspection = next(
        result for result in second.action_results
        if result.action_id == 100129
    )
    assert {
        (item.local_index, item.item_id, item.quality, item.shape_code)
        for item in random_inspection.observed_items
    } == {
        (38, 1021004, 1, 21),
        (92, 1085003, 5, 32),
    }

    batches = live_batches_from_fatbeans_capture(PACKAGE12_CAPTURE)
    fourth = next(batch for batch in batches if batch.sequence == 98)
    updates = {update.path: update.value for update in fourth.field_updates}

    assert updates[("bucket", "1", "total_cells")] == 6
    assert updates[("bucket", "1", "count")] == 3
    assert updates[("bucket", "2", "total_cells")] == 11
    assert updates[("bucket", "2", "count")] == 4
    assert updates[("bucket", "3", "total_cells")] == 41
    assert updates[("bucket", "3", "count")] == 15
    assert updates[("bucket", "4", "total_cells")] == 27
    assert updates[("bucket", "4", "count")] == 10
    assert updates[("session", "warehouse_total_cells")] == 123
    assert updates[("session", "total_item_count")] == 42
    assert len(fourth.grid_items) == 42
    assert sum(item.cells for item in fourth.grid_items) == 123


@pytest.mark.skipif(
    not PACKAGE13_CAPTURE.exists(),
    reason="local Fatbeans package13 capture is not committed",
)
def test_fatbeans_package13_mirror_eye_joins_ethan_outlines() -> None:
    events = parse_fatbeans_capture(PACKAGE13_CAPTURE)
    settled = next(state for state in events.states if state.inventory_items)
    first = next(state for state in events.states if state.sort_id == 48)
    mirror = next(
        result for result in first.action_results
        if result.action_id == 100134
    )
    known_outline = next(
        reveal for reveal in first.skill_reveals
        if reveal.skill_id == 1002082
    )

    assert len(mirror.observed_items) == len(known_outline.observed_items) == 58
    assert len(settled.inventory_items) == 58
    assert sum(_shape_cells(item.shape_code) for item in known_outline.observed_items) == 216
    assert sum(item.cells for item in settled.inventory_items) == 216

    batches = live_batches_from_fatbeans_capture(PACKAGE13_CAPTURE)
    first_batch = next(batch for batch in batches if batch.sequence == 48)
    updates = {update.path: update.value for update in first_batch.field_updates}
    cells_by_quality = Counter()
    count_by_quality = Counter()
    for item in first_batch.grid_items:
        count_by_quality[item.quality] += 1
        cells_by_quality[item.quality] += item.cells
    local_quality_shapes = {
        (item.local_index, item.quality, item.shape_key)
        for item in first_batch.grid_items
    }

    assert updates[("session", "warehouse_total_cells")] == 216
    assert updates[("session", "total_item_count")] == 58
    assert count_by_quality == {1: 1, 2: 13, 3: 12, 4: 20, 5: 7, 6: 5}
    assert cells_by_quality == {1: 1, 2: 37, 3: 29, 4: 75, 5: 37, 6: 37}
    assert (83, 1, "11") in local_quality_shapes
    assert (86, 6, "34") in local_quality_shapes


@pytest.mark.skipif(
    not PACKAGE14_CAPTURE.exists(),
    reason="local Fatbeans package14 capture is not committed",
)
def test_fatbeans_package14_aisha_coordinates_match_user_marks() -> None:
    events = parse_fatbeans_capture(PACKAGE14_CAPTURE)
    second = next(state for state in events.states if state.sort_id == 58)
    random_inspection = next(
        result for result in second.action_results
        if result.action_id == 100129
    )
    public_highest_area = next(
        info for info in second.public_infos
        if info.info_id == 200050
    )

    assert {
        (item.local_index, item.item_id, item.quality, item.shape_code)
        for item in random_inspection.observed_items
    } == {
        (69, 1041009, 1, 11),  # 泡泡水弹: row 7, col 10.
        (75, 1015001, 5, 21),  # 章丘铁锅: row 8, col 6.
    }
    assert [
        (item.local_index, item.item_id, item.quality, item.shape_code)
        for item in public_highest_area.observed_items
    ] == [(94, 1093009, 3, 33)]  # 蓝纹奶酪: rows 10-12, cols 5-7.


@pytest.mark.skipif(
    not PACKAGE15_CAPTURE.exists(),
    reason="local Fatbeans package15 capture is not committed",
)
def test_fatbeans_package15_baoguang_runtime_joins_ethan_shapes() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE15_CAPTURE)
    first = next(batch for batch in batches if batch.sequence == 19)
    local_quality_shapes = {
        (item.local_index, item.quality, item.shape_key, item.cells)
        for item in first.grid_items
    }

    assert (3, 4, "11", 1) in local_quality_shapes
    assert (4, 1, "11", 1) in local_quality_shapes
    assert (114, 6, "22", 4) in local_quality_shapes

    events = parse_fatbeans_capture(PACKAGE15_CAPTURE)
    second = next(state for state in events.states if state.sort_id == 38)
    random_inspection = next(
        result for result in second.action_results
        if result.action_id == 100129
    )
    assert {
        (item.local_index, item.item_id, item.quality, item.shape_code)
        for item in random_inspection.observed_items
    } == {
        (100, 1032005, 2, 22),  # 印花雨伞.
        (23, 1062004, 2, 22),  # 玛瑙棋.
    }


@pytest.mark.skipif(
    not PACKAGE16_CAPTURE.exists(),
    reason="local Fatbeans package16 capture is not committed",
)
def test_fatbeans_package16_baoguang_runtime_beats_quality_local_index() -> None:
    events = parse_fatbeans_capture(PACKAGE16_CAPTURE)
    settled = next(state for state in events.states if state.inventory_items)
    wall_fragment = next(
        item for item in settled.inventory_items
        if item.item_id == 1105004
    )
    shape_by_runtime = {
        item.runtime_id: (item.local_index, item.shape_code)
        for state in events.states
        for reveal in state.skill_reveals
        for item in reveal.observed_items
    }
    quality_by_runtime = {
        item.runtime_id: (item.local_index, item.quality)
        for state in events.states
        for result in state.action_results
        if result.action_id == 100136
        for item in result.observed_items
    }

    assert shape_by_runtime[wall_fragment.runtime_id] == (None, 23)
    assert quality_by_runtime[wall_fragment.runtime_id] == (10, 5)

    batches = live_batches_from_fatbeans_capture(PACKAGE16_CAPTURE)
    first = next(batch for batch in batches if batch.sequence == 51)
    assert (None, 5, "23", 6) in {
        (item.local_index, item.quality, item.shape_key, item.cells)
        for item in first.grid_items
    }


@pytest.mark.skipif(
    not PACKAGE17_CAPTURE.exists(),
    reason="local Fatbeans package17 capture is not committed",
)
def test_fatbeans_package17_mirror_eye_full_outline_and_scroll_rows() -> None:
    batches = live_batches_from_fatbeans_capture(PACKAGE17_CAPTURE)
    second = next(batch for batch in batches if batch.sequence == 45)
    live_state = LiveSessionState()
    for batch in batches:
        live_state = apply_observation_batch(live_state, batch)
        if batch.sequence == second.sequence:
            break
    session = live_state_to_session_obs(live_state)
    updates = {update.path: update.value for update in second.field_updates}
    cells_by_quality = Counter()
    count_by_quality = Counter()
    local_quality_shapes = {
        (item.local_index, item.quality, item.shape_key, item.cells)
        for item in second.grid_items
    }
    for item in second.grid_items:
        count_by_quality[item.quality] += 1
        cells_by_quality[item.quality] += item.cells

    assert updates[("session", "warehouse_total_cells")] == 157
    assert updates[("session", "total_item_count")] == 50
    assert count_by_quality == {1: 6, 2: 12, 3: 10, 4: 16, 5: 5, 6: 1}
    assert cells_by_quality == {1: 10, 2: 23, 3: 24, 4: 70, 5: 26, 6: 4}
    assert (60, 5, "61", 6) in local_quality_shapes  # 满分斯诺克纪念球杆.
    assert (105, 4, "33", 9) in local_quality_shapes  # 赛车座椅.
    assert (140, 5, "23", 6) in local_quality_shapes  # 单兵水下推进器.
    assert (None, 4, "11", 1) in local_quality_shapes  # 智能手表 at local 0.
    assert session is not None
    assert session.visible_outline_bottom_row_min == 17


@pytest.mark.skipif(
    not PACKAGE17_CAPTURE.exists(),
    reason="local Fatbeans package17 capture is not committed",
)
def test_fatbeans_package17_layout_replay_scores_against_settlement() -> None:
    events = parse_fatbeans_capture(PACKAGE17_CAPTURE)
    final_truth = final_truth_from_events(events)
    stages = layout_replay_stages(events)

    assert final_truth is not None
    assert final_truth.total_cells == 157
    assert final_truth.total_items == 50
    assert [(stage.sort_id, stage.layout.total_cells) for stage in stages] == [
        (26, 66),
        (45, 157),
        (60, 157),
        (74, 157),
    ]
    assert stages[0].known_cell_ratio == pytest.approx(66 / 157)
    assert stages[1].known_cell_ratio == 1
    assert stages[1].bounding_cell_error == 13
    locked = estimate_warehouse_from_layout(
        stages[1].layout,
        final_total_cells=stages[1].final_total_cells,
    )
    assert locked.locked
    assert locked.p50_guess == 157
