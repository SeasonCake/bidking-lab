from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]


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
