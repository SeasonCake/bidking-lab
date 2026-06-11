from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _field_varint(field_no: int, value: int) -> bytes:
    return _varint((field_no << 3) | 0) + _varint(value)


def _field_bytes(field_no: int, value: bytes) -> bytes:
    return _varint((field_no << 3) | 2) + _varint(len(value)) + value


def _send_frame(
    message_id: int,
    *,
    session: str = "2401:1274127880525303",
    value: int = 123456,
) -> bytes:
    body = _field_varint(1, 1285603971496202)
    body += _field_bytes(2, session.encode("utf-8"))
    body += _field_varint(3, value)
    frame_len = 12 + len(body)
    return (
        frame_len.to_bytes(4, "big")
        + b"\x32\xd2\x55\x5f"
        + message_id.to_bytes(4, "big")
        + body
    )


def _rev_state_frame(
    message_id: int = 0x0025,
    *,
    session: str = "2401:1274127880525303",
    map_id: int = 2401,
    round_no: int | None = 1,
) -> bytes:
    payload = _field_bytes(1, session.encode("utf-8"))
    payload += _field_varint(2, map_id)
    if round_no is not None:
        payload += _field_varint(3, round_no)
    if message_id in (0x0021, 0x0025):
        body = _field_bytes(1, payload)
    elif message_id == 0x002D:
        body = _field_varint(1, 393075406931726)
        body += _field_bytes(2, payload)
    else:
        raise ValueError(f"unsupported state message id: {message_id}")
    frame_len = 16 + len(body)
    return (
        frame_len.to_bytes(4, "big")
        + b"\x32\xd2\x55\x60"
        + b"\x00\x00\x00\x00"
        + message_id.to_bytes(4, "big")
        + body
    )


def _rev_action_response_frame(
    *,
    action_id: int = 100105,
    result: int = 48,
    result_field: int = 14,
    packet_tag: int = 0,
) -> bytes:
    payload = _field_varint(4, action_id)
    payload += _field_varint(result_field, result)
    body = _field_bytes(2, payload)
    frame_len = 16 + len(body)
    return (
        frame_len.to_bytes(4, "big")
        + b"\x32\xd2\x55\x60"
        + packet_tag.to_bytes(4, "big")
        + (0x0027).to_bytes(4, "big")
        + body
    )


def _rev_status_frame(
    *,
    session: str = "2401:1274127880525303",
) -> bytes:
    body = _field_varint(1, 436506118628741)
    body += _field_bytes(2, session.encode("utf-8"))
    frame_len = 16 + len(body)
    return (
        frame_len.to_bytes(4, "big")
        + b"\x32\xd2\x55\x61"
        + b"\x00\x00\x00\x00"
        + (0x0077).to_bytes(4, "big")
        + body
    )


def _row(direction: str, payload: bytes, *, sort_id: int = 1) -> dict[str, object]:
    return {
        "SortID": sort_id,
        "Direct": direction,
        "Protocol": "Tcp",
        "SrcIP": "8.133.195.27" if direction == "REV" else "198.18.0.1",
        "SrcPort": 10000 if direction == "REV" else 60213,
        "DstIP": "198.18.0.1" if direction == "REV" else "8.133.195.27",
        "DstPort": 60213 if direction == "REV" else 10000,
        "CaptureTime": "2026-06-02 12:00:00.000",
        "Data": base64.b64encode(payload).decode("ascii"),
        "DataLength": len(payload),
        "PID": 1234,
        "ProcessName": "BidKing.exe",
        "Source": "WinDivert",
    }


def _module():
    path = ROOT / "scripts" / "run_windivert_live_monitor.py"
    spec = importlib.util.spec_from_file_location("run_windivert_live_monitor", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakePacket:
    src_addr = "127.0.0.1"
    src_port = 50123
    dst_addr = "8.133.195.27"
    dst_port = 10000
    payload = b"\x00\x00\x00\x04"


class FakeFlowIndex:
    def match(self, key):
        return types.SimpleNamespace(
            direction="SEND",
            pid=1234,
            process_name="BidKing.exe",
            local=("127.0.0.1", 50123),
            remote=("8.133.195.27", 10000),
        )


def test_default_filter_can_be_port_limited_or_broad() -> None:
    module = _module()

    assert module._default_filter([10000], broad=False) == (
        "tcp and tcp.PayloadLength > 0 and "
        "(tcp.SrcPort == 10000 or tcp.DstPort == 10000)"
    )
    assert module._default_filter([10000], broad=True) == (
        "tcp and tcp.PayloadLength > 0"
    )


def test_packet_to_fatbeans_row_uses_process_flow_direction() -> None:
    module = _module()

    row = module._packet_to_fatbeans_row(
        FakePacket(),
        sort_id=9,
        flow_index=FakeFlowIndex(),
    )

    assert row["SortID"] == 9
    assert row["Direct"] == "SEND"
    assert row["Protocol"] == "Tcp"
    assert row["SrcIP"] == "127.0.0.1"
    assert row["SrcPort"] == 50123
    assert row["DstPort"] == 10000
    assert row["DataLength"] == 4
    assert base64.b64decode(row["Data"]) == b"\x00\x00\x00\x04"
    assert row["ProcessName"] == "BidKing.exe"
    assert row["Source"] == "WinDivert"


def test_write_source_status_records_windivert_open_error(tmp_path: Path) -> None:
    module = _module()

    module._write_source_status(
        tmp_path,
        process_name="BidKing.exe",
        filter_text="tcp",
        active_flows=2,
        accepted_packets=0,
        sniffed_packets=0,
        raw_packets=0,
        ignored_frames=0,
        dropped_bytes=0,
        active_session_id=None,
        error_code="windivert_dependency_missing",
        error_message="[WinError 2]",
        error_hint="重新解压 full 包",
    )

    payload = json.loads(
        (tmp_path / "capture_source_status.json").read_text(encoding="utf-8")
    )
    assert payload["error_code"] == "windivert_dependency_missing"
    assert payload["error_message"] == "[WinError 2]"
    assert payload["error_hint"] == "重新解压 full 包"
    assert payload["active_flows"] == 2


def test_flow_direction_map_indexes_bidking_send_and_receive(
    monkeypatch,
) -> None:
    module = _module()

    fake_conn = types.SimpleNamespace(
        pid=1234,
        laddr=types.SimpleNamespace(ip="127.0.0.1", port=50123),
        raddr=types.SimpleNamespace(ip="8.133.195.27", port=10000),
    )
    fake_psutil = types.SimpleNamespace(
        net_connections=lambda kind: [fake_conn],
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    monkeypatch.setattr(
        module,
        "_process_name_for_pid",
        lambda pid: "BidKing.exe" if pid == 1234 else None,
    )

    flows = module._flow_direction_map("BidKing.exe")

    send = flows[("127.0.0.1", 50123, "8.133.195.27", 10000)]
    recv = flows[("8.133.195.27", 10000, "127.0.0.1", 50123)]
    assert send.direction == "SEND"
    assert recv.direction == "REV"
    assert send.pid == 1234


def test_flow_index_filters_loopback_but_keeps_server_port(
    monkeypatch,
) -> None:
    module = _module()
    flows = {
        ("127.0.0.1", 60215, "127.0.0.1", 60214): module.FlowMatch(
            direction="SEND",
            pid=1,
            process_name="BidKing.exe",
            local=("127.0.0.1", 60215),
            remote=("127.0.0.1", 60214),
        ),
        ("198.18.0.1", 60213, "8.133.195.27", 10000): module.FlowMatch(
            direction="SEND",
            pid=1,
            process_name="BidKing.exe",
            local=("198.18.0.1", 60213),
            remote=("8.133.195.27", 10000),
        ),
    }
    monkeypatch.setattr(module, "_flow_direction_map", lambda _name: flows)

    index = module.FlowIndex(
        process_name="BidKing.exe",
        refresh_seconds=60.0,
        server_ports={10000},
        include_loopback=False,
    )
    index.refresh_if_due(force=True)

    assert index.match(("127.0.0.1", 60215, "127.0.0.1", 60214)) is None
    assert (
        index.match(("198.18.0.1", 60213, "8.133.195.27", 10000)).direction
        == "SEND"
    )


def test_flow_index_can_include_loopback_flows(monkeypatch) -> None:
    module = _module()
    flows = {
        ("127.0.0.1", 15940, "127.0.0.1", 7897): module.FlowMatch(
            direction="SEND",
            pid=1,
            process_name="BidKing.exe",
            local=("127.0.0.1", 15940),
            remote=("127.0.0.1", 7897),
        ),
    }
    monkeypatch.setattr(module, "_flow_direction_map", lambda _name: flows)

    index = module.FlowIndex(
        process_name="BidKing.exe",
        refresh_seconds=60.0,
        server_ports={10000},
        include_loopback=True,
    )
    index.refresh_if_due(force=True)

    assert (
        index.match(("127.0.0.1", 15940, "127.0.0.1", 7897)).direction
        == "SEND"
    )


def test_game_frame_gate_accepts_status_frame_for_session_prewarm() -> None:
    module = _module()
    gate = module.GameFrameGate()

    emitted = gate.feed_row(_row("REV", _rev_status_frame()))

    assert len(emitted.rows) == 1
    assert emitted.reset_session is False
    assert emitted.rows[0]["MessageID"] == "0x0077"
    assert emitted.rows[0]["SessionID"] == "2401:1274127880525303"
    assert gate.active_session_id == "2401:1274127880525303"
    assert gate.ignored_frames == 0
    assert not module._should_schedule_monitor_process(emitted.rows[0])


def test_game_frame_gate_accepts_state_and_matching_session_sends() -> None:
    module = _module()
    gate = module.GameFrameGate()

    early_send = gate.feed_row(_row("SEND", _send_frame(0x0022), sort_id=1))
    state = gate.feed_row(_row("REV", _rev_state_frame(), sort_id=2))
    matching_send = gate.feed_row(_row("SEND", _send_frame(0x0026), sort_id=3))
    other_session_send = gate.feed_row(
        _row(
            "SEND",
            _send_frame(0x0026, session="2401:9999999999999999"),
            sort_id=4,
        )
    )

    assert len(early_send.rows) == 1
    assert early_send.rows[0]["MessageID"] == "0x0022"
    assert early_send.rows[0]["SessionID"] == "2401:1274127880525303"
    assert len(state.rows) == 1
    assert state.rows[0]["MessageID"] == "0x0025"
    assert state.rows[0]["SessionID"] == "2401:1274127880525303"
    assert state.rows[0]["Source"] == "WinDivertFrameGate"
    assert state.rows[0]["SortID"] == 2
    assert gate.active_session_id == "2401:1274127880525303"
    assert len(matching_send.rows) == 1
    assert matching_send.rows[0]["MessageID"] == "0x0026"
    assert matching_send.rows[0]["SortID"] == 3
    assert other_session_send.rows == ()
    assert gate.ignored_frames == 1


def test_game_frame_gate_uses_first_send_to_prewarm_direct_action_session() -> None:
    module = _module()
    gate = module.GameFrameGate()

    first_send = gate.feed_row(_row("SEND", _send_frame(0x0026), sort_id=1))
    action_response = gate.feed_row(
        _row("REV", _rev_action_response_frame(), sort_id=2)
    )

    assert len(first_send.rows) == 1
    assert first_send.rows[0]["MessageID"] == "0x0026"
    assert gate.active_session_id == "2401:1274127880525303"
    assert len(action_response.rows) == 1
    assert action_response.rows[0]["MessageID"] == "0x0027"
    assert action_response.rows[0]["SessionID"] == "2401:1274127880525303"


def test_game_frame_gate_accepts_session_started_state() -> None:
    module = _module()
    gate = module.GameFrameGate()

    started = gate.feed_row(
        _row("REV", _rev_state_frame(0x0021, round_no=None), sort_id=1)
    )
    first_send = gate.feed_row(_row("SEND", _send_frame(0x0022), sort_id=2))

    assert len(started.rows) == 1
    assert started.rows[0]["MessageID"] == "0x0021"
    assert started.rows[0]["SessionID"] == "2401:1274127880525303"
    assert gate.active_session_id == "2401:1274127880525303"
    assert len(first_send.rows) == 1
    assert first_send.rows[0]["MessageID"] == "0x0022"


def test_game_frame_gate_resets_on_new_bid_send_session() -> None:
    module = _module()
    gate = module.GameFrameGate()

    first_state = gate.feed_row(
        _row(
            "REV",
            _rev_state_frame(session="2401:1111111111111111"),
            sort_id=1,
        )
    )
    first_send = gate.feed_row(
        _row(
            "SEND",
            _send_frame(0x0022, session="2401:1111111111111111"),
            sort_id=2,
        )
    )
    new_bid_send = gate.feed_row(
        _row(
            "SEND",
            _send_frame(0x0022, session="2410:2222222222222222"),
            sort_id=3,
        )
    )
    new_action_send = gate.feed_row(
        _row(
            "SEND",
            _send_frame(0x0026, session="2410:2222222222222222"),
            sort_id=4,
        )
    )

    assert len(first_state.rows) == 1
    assert len(first_send.rows) == 1
    assert new_bid_send.reset_session is True
    assert len(new_bid_send.rows) == 1
    assert new_bid_send.rows[0]["SortID"] == 1
    assert new_bid_send.rows[0]["MessageID"] == "0x0022"
    assert new_bid_send.rows[0]["SessionID"] == "2410:2222222222222222"
    assert gate.active_session_id == "2410:2222222222222222"
    assert len(new_action_send.rows) == 1
    assert new_action_send.rows[0]["SortID"] == 2
    assert new_action_send.rows[0]["SessionID"] == "2410:2222222222222222"


def test_game_frame_gate_keeps_session_when_only_stream_buffers_reset() -> None:
    module = _module()
    gate = module.GameFrameGate()

    started = gate.feed_row(
        _row("REV", _rev_state_frame(0x0021, round_no=None), sort_id=1)
    )
    gate.reset_stream_buffers(clear_session=False)
    send_after_flow_change = gate.feed_row(
        _row("SEND", _send_frame(0x0022), sort_id=2)
    )

    assert len(started.rows) == 1
    assert gate.active_session_id == "2401:1274127880525303"
    assert len(send_after_flow_change.rows) == 1
    assert send_after_flow_change.rows[0]["MessageID"] == "0x0022"


def test_game_frame_gate_accepts_current_session_direct_action_response() -> None:
    module = _module()
    gate = module.GameFrameGate()

    early_response = gate.feed_row(
        _row("REV", _rev_action_response_frame(), sort_id=1)
    )
    started = gate.feed_row(
        _row("REV", _rev_state_frame(0x0021, round_no=None), sort_id=2)
    )
    direct_response = gate.feed_row(
        _row("REV", _rev_action_response_frame(), sort_id=3)
    )
    empty_ack = gate.feed_row(
        _row("REV", _rev_action_response_frame(packet_tag=1234), sort_id=4)
    )

    assert early_response.rows == ()
    assert len(started.rows) == 1
    assert len(direct_response.rows) == 1
    assert direct_response.rows[0]["MessageID"] == "0x0027"
    assert direct_response.rows[0]["SessionID"] == "2401:1274127880525303"
    assert direct_response.rows[0]["SortID"] == 2
    assert empty_ack.rows == ()
    assert gate.ignored_frames == 2


def test_game_frame_gate_carries_direct_action_after_settlement_to_next_session() -> None:
    module = _module()
    gate = module.GameFrameGate()

    started = gate.feed_row(
        _row("REV", _rev_state_frame(0x0021, round_no=None), sort_id=1)
    )
    settled = gate.feed_row(
        _row("REV", _rev_state_frame(0x002D, round_no=3), sort_id=2)
    )
    late_direct = gate.feed_row(
        _row("REV", _rev_action_response_frame(), sort_id=3)
    )
    next_bid = gate.feed_row(
        _row(
            "SEND",
            _send_frame(0x0022, session="2501:2222222222222222"),
            sort_id=4,
        )
    )

    assert len(started.rows) == 1
    assert len(settled.rows) == 1
    assert settled.rows[0]["MessageID"] == "0x002d"
    assert late_direct.rows == ()
    assert "rev_tool_after_settlement" not in gate.ignored_reasons_dict()
    assert next_bid.reset_session is True
    assert len(next_bid.rows) == 2
    assert next_bid.rows[0]["SortID"] == 1
    assert next_bid.rows[0]["MessageID"] == "0x0027"
    assert next_bid.rows[0]["SessionID"] == "2501:2222222222222222"
    assert next_bid.rows[1]["SortID"] == 2
    assert next_bid.rows[1]["MessageID"] == "0x0022"
    assert next_bid.rows[1]["SessionID"] == "2501:2222222222222222"


def test_game_frame_gate_accepts_next_session_action_send_after_settlement() -> None:
    module = _module()
    gate = module.GameFrameGate()

    gate.feed_row(_row("REV", _rev_state_frame(0x0021, round_no=None), sort_id=1))
    gate.feed_row(_row("REV", _rev_state_frame(0x002D, round_no=3), sort_id=2))
    next_action = gate.feed_row(
        _row(
            "SEND",
            _send_frame(0x0026, session="2501:2222222222222222"),
            sort_id=3,
        )
    )

    assert next_action.reset_session is True
    assert len(next_action.rows) == 1
    assert next_action.rows[0]["SortID"] == 1
    assert next_action.rows[0]["MessageID"] == "0x0026"
    assert next_action.rows[0]["SessionID"] == "2501:2222222222222222"
    assert gate.active_session_id == "2501:2222222222222222"


def test_game_frame_gate_reconstructs_split_frames() -> None:
    module = _module()
    gate = module.GameFrameGate()
    frame = _rev_state_frame()

    first = gate.feed_row(_row("REV", frame[:7], sort_id=1))
    second = gate.feed_row(_row("REV", frame[7:], sort_id=2))

    assert first.rows == ()
    assert len(second.rows) == 1
    assert second.rows[0]["DataLength"] == len(frame)


def test_game_frame_gate_keeps_split_buffers_per_tcp_flow() -> None:
    module = _module()
    gate = module.GameFrameGate()
    first_frame = _rev_state_frame(session="2401:1111111111111111")
    second_frame = _rev_state_frame(session="2401:2222222222222222")
    first_head = _row("REV", first_frame[:7], sort_id=1)
    first_tail = _row("REV", first_frame[7:], sort_id=3)
    second = _row("REV", second_frame, sort_id=2)
    second["DstPort"] = 60214

    assert gate.feed_row(first_head).rows == ()
    emitted_second = gate.feed_row(second)
    emitted_first = gate.feed_row(first_tail)

    assert len(emitted_second.rows) == 1
    assert emitted_second.rows[0]["SessionID"] == "2401:2222222222222222"
    assert len(emitted_first.rows) == 1
    assert emitted_first.rows[0]["SessionID"] == "2401:1111111111111111"
    assert emitted_first.reset_session is True


def test_game_frame_gate_prunes_stale_flow_buffers_but_keeps_active_flow() -> None:
    module = _module()
    gate = module.GameFrameGate()
    first_frame = _rev_state_frame(session="2401:1111111111111111")
    second_frame = _rev_state_frame(session="2401:2222222222222222")
    first_head = _row("REV", first_frame[:7], sort_id=1)
    first_tail = _row("REV", first_frame[7:], sort_id=3)
    second_head = _row("REV", second_frame[:7], sort_id=2)
    second_head["DstPort"] = 60214
    second_tail = _row("REV", second_frame[7:], sort_id=4)
    second_tail["DstPort"] = 60214

    assert gate.feed_row(first_head).rows == ()
    assert gate.feed_row(second_head).rows == ()
    gate.reset_stream_buffers(
        keep_flow_keys={
            ("8.133.195.27", 10000, "198.18.0.1", 60214),
        },
        clear_session=False,
    )

    emitted_first = gate.feed_row(first_tail)
    emitted_second = gate.feed_row(second_tail)

    assert emitted_first.rows == ()
    assert len(emitted_second.rows) == 1
    assert emitted_second.rows[0]["SessionID"] == "2401:2222222222222222"


def test_game_frame_gate_resets_on_new_state_session() -> None:
    module = _module()
    gate = module.GameFrameGate()

    first_state = gate.feed_row(
        _row(
            "REV",
            _rev_state_frame(session="2401:1111111111111111"),
            sort_id=1,
        )
    )
    first_send = gate.feed_row(
        _row(
            "SEND",
            _send_frame(0x0022, session="2401:1111111111111111"),
            sort_id=2,
        )
    )
    second_state = gate.feed_row(
        _row(
            "REV",
            _rev_state_frame(session="2405:2222222222222222", map_id=2405),
            sort_id=3,
        )
    )

    assert len(first_state.rows) == 1
    assert first_state.rows[0]["SortID"] == 1
    assert len(first_send.rows) == 1
    assert first_send.rows[0]["SortID"] == 2
    assert second_state.reset_session is True
    assert len(second_state.rows) == 1
    assert second_state.rows[0]["SortID"] == 1
    assert second_state.rows[0]["SessionID"] == "2405:2222222222222222"


def test_game_frame_gate_resets_on_new_status_session() -> None:
    module = _module()
    gate = module.GameFrameGate()

    first_state = gate.feed_row(
        _row(
            "REV",
            _rev_state_frame(session="2401:1111111111111111"),
            sort_id=1,
        )
    )
    next_status = gate.feed_row(
        _row(
            "REV",
            _rev_status_frame(session="2407:2222222222222222"),
            sort_id=2,
        )
    )
    next_state = gate.feed_row(
        _row(
            "REV",
            _rev_state_frame(session="2407:2222222222222222", map_id=2407),
            sort_id=3,
        )
    )

    assert len(first_state.rows) == 1
    assert next_status.reset_session is True
    assert len(next_status.rows) == 1
    assert next_status.rows[0]["SortID"] == 1
    assert next_status.rows[0]["MessageID"] == "0x0077"
    assert gate.active_session_id == "2407:2222222222222222"
    assert len(next_state.rows) == 1
    assert next_state.rows[0]["SortID"] == 2
    assert next_state.rows[0]["SessionID"] == "2407:2222222222222222"
