"""Capture BidKing TCP packets directly with WinDivert.

This is the legal fallback when Fatbeans WebHook is unavailable. It does not
depend on Fatbeans export/WebHook membership: packets are sniffed locally,
attributed to BidKing.exe using the Windows TCP table, converted into the same
Fatbeans export-row shape, then fed to the existing live monitor artifact path.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter, deque
from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
for path in (SCRIPTS, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_fatbeans_webhook_monitor import (  # noqa: E402
    FatbeansWebhookMonitor,
    WebhookMonitorConfig,
    _acquire_lock,
)
from bidking_lab.live.fatbeans import (  # noqa: E402
    FatbeansFrame,
    _parse_direct_action_response,
    _parse_send_event,
    _parse_state_event,
    _parse_status_event,
)
from bidking_lab.live.monitor import load_monitor_tables  # noqa: E402


FlowKey = tuple[str, int, str, int]
StreamKey = tuple[str, str, int, str, int]
GAME_SEND_MESSAGE_IDS = {0x0022, 0x0026}
GAME_STATE_MESSAGE_IDS = {0x0021, 0x0025, 0x0027, 0x002D}
SESSION_ID_RE = re.compile(r"^\d{4}:\d+$")
MAX_FRAME_BYTES = 1_000_000


def _process_is_elevated() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _normalize_ip(value: Any) -> str:
    text = str(value or "")
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return text
    if getattr(ip, "ipv4_mapped", None) is not None:
        return str(ip.ipv4_mapped)
    return str(ip)


def _endpoint(value: Any) -> tuple[str, int] | None:
    if value in (None, (), ""):
        return None
    try:
        ip = getattr(value, "ip")
        port = getattr(value, "port")
    except AttributeError:
        try:
            ip, port = value
        except (TypeError, ValueError):
            return None
    try:
        return _normalize_ip(ip), int(port)
    except (TypeError, ValueError):
        return None


def _process_name_for_pid(pid: int | None) -> str | None:
    if pid is None:
        return None
    try:
        import psutil

        return psutil.Process(int(pid)).name()
    except Exception:  # noqa: BLE001 - process can exit while inspecting
        return None


def _matches_process_name(actual: Any, expected: str) -> bool:
    return str(actual or "").casefold() == expected.casefold()


def _is_loopback_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class FlowMatch:
    direction: str
    pid: int | None
    process_name: str
    local: tuple[str, int]
    remote: tuple[str, int]


def _flow_direction_map(process_name: str) -> dict[FlowKey, FlowMatch]:
    """Return packet 4-tuple -> SEND/REV for current BidKing TCP flows."""
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError("psutil is required for process-aware capture") from exc

    flows: dict[FlowKey, FlowMatch] = {}
    for conn in psutil.net_connections(kind="tcp"):
        if conn.pid is None:
            continue
        actual_name = _process_name_for_pid(conn.pid)
        if not _matches_process_name(actual_name, process_name):
            continue
        local = _endpoint(conn.laddr)
        remote = _endpoint(conn.raddr)
        if local is None or remote is None:
            continue
        local_ip, local_port = local
        remote_ip, remote_port = remote
        flows[(local_ip, local_port, remote_ip, remote_port)] = FlowMatch(
            direction="SEND",
            pid=conn.pid,
            process_name=actual_name or process_name,
            local=local,
            remote=remote,
        )
        flows[(remote_ip, remote_port, local_ip, local_port)] = FlowMatch(
            direction="REV",
            pid=conn.pid,
            process_name=actual_name or process_name,
            local=local,
            remote=remote,
        )
    return flows


def _flow_is_capture_target(
    match: FlowMatch,
    *,
    server_ports: set[int],
    include_loopback: bool,
) -> bool:
    remote_ip, remote_port = match.remote
    local_ip, local_port = match.local
    if server_ports and (remote_port in server_ports or local_port in server_ports):
        return True
    if include_loopback:
        return True
    return not _is_loopback_ip(remote_ip) and not _is_loopback_ip(local_ip)


class FlowIndex:
    def __init__(
        self,
        *,
        process_name: str,
        refresh_seconds: float,
        server_ports: set[int] | None = None,
        include_loopback: bool = False,
    ) -> None:
        self.process_name = process_name
        self.refresh_seconds = max(0.05, refresh_seconds)
        self.server_ports = set(server_ports or ())
        self.include_loopback = include_loopback
        self._flows: dict[FlowKey, FlowMatch] = {}
        self._last_refresh = 0.0

    def refresh_if_due(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self._last_refresh >= self.refresh_seconds:
            flows = _flow_direction_map(self.process_name)
            self._flows = {
                key: match
                for key, match in flows.items()
                if _flow_is_capture_target(
                    match,
                    server_ports=self.server_ports,
                    include_loopback=self.include_loopback,
                )
            }
            self._last_refresh = now

    def match(self, key: FlowKey) -> FlowMatch | None:
        self.refresh_if_due()
        match = self._flows.get(key)
        if match is not None:
            return match
        # The first packet can race ahead of the TCP table refresh.
        self.refresh_if_due(force=True)
        return self._flows.get(key)

    def active_flow_count(self) -> int:
        self.refresh_if_due()
        return len(self._flows) // 2

    def flow_signature(self) -> tuple[FlowKey, ...]:
        self.refresh_if_due()
        return tuple(sorted(self._flows.keys()))


def _packet_payload(packet: Any) -> bytes:
    payload = getattr(packet, "payload", b"") or b""
    if isinstance(payload, memoryview):
        return payload.tobytes()
    return bytes(payload)


def _packet_key(packet: Any) -> FlowKey | None:
    try:
        return (
            _normalize_ip(getattr(packet, "src_addr")),
            int(getattr(packet, "src_port")),
            _normalize_ip(getattr(packet, "dst_addr")),
            int(getattr(packet, "dst_port")),
        )
    except (TypeError, ValueError):
        return None


def _capture_time() -> str:
    now = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)) + (
        f".{int((now % 1) * 1000):03d}"
    )


def _packet_to_fatbeans_row(
    packet: Any,
    *,
    sort_id: int,
    flow_index: FlowIndex,
) -> dict[str, Any] | None:
    payload = _packet_payload(packet)
    if not payload:
        return None
    key = _packet_key(packet)
    if key is None:
        return None
    match = flow_index.match(key)
    if match is None:
        return None
    src_ip, src_port, dst_ip, dst_port = key
    return {
        "SortID": int(sort_id),
        "Direct": match.direction,
        "Protocol": "Tcp",
        "SrcIP": src_ip,
        "SrcPort": src_port,
        "DstIP": dst_ip,
        "DstPort": dst_port,
        "CaptureTime": _capture_time(),
        "Data": base64.b64encode(payload).decode("ascii"),
        "DataLength": len(payload),
        "PID": match.pid,
        "ProcessName": match.process_name,
        "Source": "WinDivert",
    }


@dataclass(frozen=True)
class GameFrame:
    template_row: Mapping[str, Any]
    raw: bytes
    direction: str
    message_id: int
    session_id: str
    is_state: bool
    is_status: bool = False


@dataclass(frozen=True)
class FrameGateEmit:
    rows: tuple[dict[str, Any], ...]
    reset_session: bool = False


def _valid_session_id(value: str | None) -> bool:
    return bool(value and SESSION_ID_RE.match(value))


def _frame_message_id(direction: str, raw: bytes) -> int | None:
    if direction == "SEND" and len(raw) >= 12:
        return int.from_bytes(raw[8:12], "big")
    if direction == "REV" and len(raw) >= 16:
        return int.from_bytes(raw[12:16], "big")
    return None


def _frame_packet_tag(direction: str, raw: bytes) -> int | None:
    if direction == "SEND" and len(raw) >= 8:
        return int.from_bytes(raw[4:8], "big")
    if direction == "REV" and len(raw) >= 12:
        return int.from_bytes(raw[8:12], "big")
    return None


class GameFrameGate:
    """Turn TCP payload chunks into game-session frame rows.

    The raw BidKing connection also carries heartbeat and non-auction UI frames.
    The live parser only needs bid/action sends and round/settlement state
    pushes, so this gate keeps complete frames with known session ids and drops
    the rest before they reach the monitor artifact builder.
    """

    def __init__(self) -> None:
        self._buffers: dict[StreamKey, bytearray] = {}
        self._current_session_id: str | None = None
        self._current_session_settled = False
        self._pending_next_session_frames: deque[GameFrame] = deque(maxlen=8)
        self._next_sort_id = 1
        self.dropped_bytes = 0
        self.ignored_frames = 0
        self.accepted_frames = 0
        self.ignored_reasons: Counter[str] = Counter()
        self._ignored_samples: deque[dict[str, Any]] = deque(maxlen=8)

    def _note_ignore(
        self,
        reason: str,
        *,
        sample: Mapping[str, Any] | None = None,
    ) -> None:
        self.ignored_frames += 1
        self.ignored_reasons[reason] += 1
        if sample is not None:
            stored = dict(sample)
            stored["reason"] = reason
            self._ignored_samples.append(stored)

    def ignored_reasons_dict(self) -> dict[str, int]:
        return dict(sorted(self.ignored_reasons.items()))

    @property
    def ignored_samples(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._ignored_samples)

    def ignored_samples_dict(self) -> list[dict[str, Any]]:
        return [dict(sample) for sample in self._ignored_samples]

    @staticmethod
    def _packet_key_from_stream_key(stream_key: StreamKey) -> FlowKey:
        direction, local_ip, local_port, remote_ip, remote_port = stream_key
        if direction == "SEND":
            return (local_ip, local_port, remote_ip, remote_port)
        return (remote_ip, remote_port, local_ip, local_port)

    def _ignored_frame_sample(
        self,
        row: Mapping[str, Any],
        *,
        direction: str,
        raw: bytes,
        message_id: int | None,
        frame_session_id: str | None = None,
    ) -> dict[str, Any]:
        sample = {
            "direction": direction,
            "sort_id": int(row.get("SortID") or 0),
            "capture_time": str(row.get("CaptureTime") or ""),
            "src": f"{_normalize_ip(row.get('SrcIP'))}:{int(row.get('SrcPort') or 0)}",
            "dst": f"{_normalize_ip(row.get('DstIP'))}:{int(row.get('DstPort') or 0)}",
            "packet_tag": _frame_packet_tag(direction, raw),
            "message_id": (
                f"0x{message_id:04x}" if message_id is not None else None
            ),
            "raw_length": len(raw),
            "raw_prefix": raw[:16].hex(),
            "active_session_id": self._current_session_id,
        }
        if frame_session_id is not None:
            sample["frame_session_id"] = frame_session_id
        return sample

    def reset_stream_buffers(
        self,
        *,
        keep_flow_keys: Iterable[FlowKey] | None = None,
        clear_session: bool = False,
    ) -> None:
        if keep_flow_keys is None:
            self._buffers.clear()
        else:
            keep_keys = set(keep_flow_keys)
            if keep_keys:
                self._buffers = {
                    stream_key: buffer
                    for stream_key, buffer in self._buffers.items()
                    if self._packet_key_from_stream_key(stream_key) in keep_keys
                }
            else:
                self._buffers.clear()
        self.dropped_bytes = 0
        if clear_session:
            self._current_session_id = None
            self._current_session_settled = False
            self._pending_next_session_frames.clear()
            self._next_sort_id = 1

    @property
    def active_session_id(self) -> str | None:
        return self._current_session_id

    def feed_row(self, row: Mapping[str, Any]) -> FrameGateEmit:
        direction = str(row.get("Direct") or "").upper()
        if direction not in ("SEND", "REV"):
            return FrameGateEmit(())
        stream_key = self._stream_key(row, direction)
        try:
            payload = base64.b64decode(row.get("Data") or "", validate=True)
        except Exception:  # noqa: BLE001 - malformed packet boundary
            return FrameGateEmit(())
        if not payload:
            return FrameGateEmit(())

        frames = self._extract_frames(stream_key, direction, payload)
        emitted: list[dict[str, Any]] = []
        reset_session = False
        for raw in frames:
            game_frame, ignore_reason, ignore_sample = self._classify_frame(
                row,
                direction,
                raw,
            )
            if game_frame is None:
                if ignore_reason == "rev_tool_pending_next_session":
                    continue
                self._note_ignore(
                    ignore_reason or "unclassified",
                    sample=ignore_sample,
                )
                continue
            should_emit, should_reset = self._should_emit(game_frame)
            if should_reset:
                reset_session = True
                emitted.clear()
                self._buffers.clear()
                self._next_sort_id = 1
                emitted.extend(
                    self._flush_pending_next_session_frames(game_frame.session_id)
                )
            if should_emit:
                emitted.append(self._row_from_game_frame(game_frame))
                self.accepted_frames += 1
            else:
                self._note_ignore(
                    "send_wrong_session",
                    sample=self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=game_frame.message_id,
                        frame_session_id=game_frame.session_id,
                    ),
                )
        return FrameGateEmit(tuple(emitted), reset_session=reset_session)

    def _stream_key(self, row: Mapping[str, Any], direction: str) -> StreamKey:
        src_ip = _normalize_ip(row.get("SrcIP"))
        dst_ip = _normalize_ip(row.get("DstIP"))
        try:
            src_port = int(row.get("SrcPort") or 0)
            dst_port = int(row.get("DstPort") or 0)
        except (TypeError, ValueError):
            src_port = 0
            dst_port = 0
        if direction == "SEND":
            local_ip, local_port = src_ip, src_port
            remote_ip, remote_port = dst_ip, dst_port
        else:
            local_ip, local_port = dst_ip, dst_port
            remote_ip, remote_port = src_ip, src_port
        return (direction, local_ip, local_port, remote_ip, remote_port)

    def _extract_frames(
        self,
        stream_key: StreamKey,
        direction: str,
        payload: bytes,
    ) -> list[bytes]:
        buffer = self._buffers.setdefault(stream_key, bytearray())
        buffer.extend(payload)
        frames: list[bytes] = []
        while len(buffer) >= 4:
            frame_len = int.from_bytes(buffer[:4], "big")
            min_len = 12 if direction == "SEND" else 16
            if frame_len < min_len or frame_len > MAX_FRAME_BYTES:
                del buffer[0]
                self.dropped_bytes += 1
                continue
            if len(buffer) < frame_len:
                break
            frames.append(bytes(buffer[:frame_len]))
            del buffer[:frame_len]
        return frames

    def _classify_frame(
        self,
        row: Mapping[str, Any],
        direction: str,
        raw: bytes,
    ) -> tuple[GameFrame | None, str | None, dict[str, Any] | None]:
        message_id = _frame_message_id(direction, raw)
        if message_id is None:
            return (
                None,
                "no_message_id",
                self._ignored_frame_sample(
                    row,
                    direction=direction,
                    raw=raw,
                    message_id=None,
                ),
            )
        frame = FatbeansFrame(
            index=0,
            direction=direction,  # type: ignore[arg-type]
            sort_id=int(row.get("SortID") or 0),
            capture_time=str(row.get("CaptureTime") or ""),
            raw=raw,
        )
        if direction == "SEND" and message_id in GAME_SEND_MESSAGE_IDS:
            event = _parse_send_event(frame)
            if event is None:
                return (
                    None,
                    "send_parse_failed",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                    ),
                )
            if not _valid_session_id(event.session_id):
                return (
                    None,
                    "send_bad_session",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                        frame_session_id=event.session_id,
                    ),
                )
            return GameFrame(
                template_row=row,
                raw=raw,
                direction=direction,
                message_id=message_id,
                session_id=event.session_id or "",
                is_state=False,
            ), None, None
        if (
            direction == "REV"
            and _frame_packet_tag(direction, raw) == 0
            and message_id == 0x0077
        ):
            status = _parse_status_event(frame)
            if status is None:
                return (
                    None,
                    "rev_status_parse_failed",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                    ),
                )
            if not _valid_session_id(status.session_id):
                return (
                    None,
                    "rev_status_bad_session",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                        frame_session_id=status.session_id,
                    ),
                )
            return GameFrame(
                template_row=row,
                raw=raw,
                direction=direction,
                message_id=message_id,
                session_id=status.session_id or "",
                is_state=False,
                is_status=True,
            ), None, None
        if (
            direction == "REV"
            and _frame_packet_tag(direction, raw) == 0
            and message_id in GAME_STATE_MESSAGE_IDS
            and message_id != 0x0027
        ):
            state = _parse_state_event(frame)
            if state is None:
                return (
                    None,
                    "rev_state_parse_failed",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                    ),
                )
            if not _valid_session_id(state.session_id):
                return (
                    None,
                    "rev_state_bad_session",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                        frame_session_id=state.session_id,
                    ),
                )
            if (
                state.map_id is None
                and state.round_index is None
                and not state.inventory_items
                and not state.bids
                and not state.action_results
                and not state.public_infos
                and not state.skill_reveals
            ):
                return (
                    None,
                    "rev_state_empty",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                        frame_session_id=state.session_id,
                    ),
                )
            return GameFrame(
                template_row=row,
                raw=raw,
                direction=direction,
                message_id=message_id,
                session_id=state.session_id or "",
                is_state=True,
            ), None, None
        if (
            direction == "REV"
            and _frame_packet_tag(direction, raw) == 0
            and message_id == 0x0027
        ):
            result = _parse_direct_action_response(frame)
            if result is None:
                return (
                    None,
                    "rev_tool_parse_failed",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                    ),
                )
            if not _valid_session_id(self._current_session_id):
                return (
                    None,
                    "rev_tool_no_active_session",
                    self._ignored_frame_sample(
                        row,
                        direction=direction,
                        raw=raw,
                        message_id=message_id,
                    ),
                )
            if self._current_session_settled:
                self._pending_next_session_frames.append(
                    GameFrame(
                        template_row=row,
                        raw=raw,
                        direction=direction,
                        message_id=message_id,
                        session_id="",
                        is_state=True,
                    )
                )
                return (
                    None,
                    "rev_tool_pending_next_session",
                    None,
                )
            return GameFrame(
                template_row=row,
                raw=raw,
                direction=direction,
                message_id=message_id,
                session_id=self._current_session_id or "",
                is_state=True,
            ), None, None
        return (
            None,
            "rev_not_game_frame",
            self._ignored_frame_sample(
                row,
                direction=direction,
                raw=raw,
                message_id=message_id,
            ),
        )

    def _should_emit(self, frame: GameFrame) -> tuple[bool, bool]:
        if frame.is_status:
            reset = (
                self._current_session_id is not None
                and self._current_session_id != frame.session_id
            )
            self._current_session_id = frame.session_id
            if reset:
                self._current_session_settled = False
            return True, reset
        if frame.is_state:
            reset = (
                self._current_session_id is not None
                and self._current_session_id != frame.session_id
            )
            self._current_session_id = frame.session_id
            if reset:
                self._current_session_settled = False
            if frame.message_id == 0x002D:
                self._current_session_settled = True
            return True, reset
        if self._current_session_id is None:
            self._current_session_id = frame.session_id
            self._current_session_settled = False
            return True, False
        if self._current_session_id == frame.session_id:
            return True, False
        if (
            self._current_session_id is not None
            and (frame.message_id == 0x0022 or self._current_session_settled)
        ):
            self._current_session_id = frame.session_id
            self._current_session_settled = False
            return True, True
        return False, False

    def _flush_pending_next_session_frames(self, session_id: str) -> list[dict[str, Any]]:
        if not self._pending_next_session_frames:
            return []
        rows: list[dict[str, Any]] = []
        while self._pending_next_session_frames:
            frame = self._pending_next_session_frames.popleft()
            rows.append(
                self._row_from_game_frame(
                    GameFrame(
                        template_row=frame.template_row,
                        raw=frame.raw,
                        direction=frame.direction,
                        message_id=frame.message_id,
                        session_id=session_id,
                        is_state=frame.is_state,
                        is_status=frame.is_status,
                    )
                )
            )
        return rows

    def _row_from_game_frame(self, frame: GameFrame) -> dict[str, Any]:
        row = dict(frame.template_row)
        row["SortID"] = self._next_sort_id
        row["Data"] = base64.b64encode(frame.raw).decode("ascii")
        row["DataLength"] = len(frame.raw)
        row["Source"] = "WinDivertFrameGate"
        row["MessageID"] = f"0x{frame.message_id:04x}"
        row["SessionID"] = frame.session_id
        self._next_sort_id += 1
        return row


def _should_schedule_monitor_process(row: Mapping[str, Any]) -> bool:
    return row.get("Direct") == "REV" and row.get("MessageID") != "0x0077"


def _default_filter(server_ports: list[int], *, broad: bool) -> str:
    if broad or not server_ports:
        return "tcp and tcp.PayloadLength > 0"
    parts = []
    for port in server_ports:
        parts.append(f"tcp.SrcPort == {int(port)}")
        parts.append(f"tcp.DstPort == {int(port)}")
    return "tcp and tcp.PayloadLength > 0 and (" + " or ".join(parts) + ")"


def _write_source_status(
    log_dir: Path,
    *,
    process_name: str,
    filter_text: str,
    active_flows: int,
    accepted_packets: int,
    sniffed_packets: int = 0,
    raw_packets: int = 0,
    ignored_frames: int = 0,
    dropped_bytes: int = 0,
    ignored_reasons: Mapping[str, int] | None = None,
    ignored_samples: Iterable[Mapping[str, Any]] | None = None,
    active_session_id: str | None = None,
) -> None:
    path = log_dir / "capture_source_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": time.time(),
        "source": "windivert",
        "process_name": process_name,
        "filter": filter_text,
        "active_flows": active_flows,
        "sniffed_packets": sniffed_packets,
        "accepted_frames": accepted_packets,
        "accepted_packets": accepted_packets,
        "raw_packets": raw_packets,
        "ignored_frames": ignored_frames,
        "dropped_bytes": dropped_bytes,
        "ignored_reasons": dict(ignored_reasons or ()),
        "ignored_samples": [
            dict(sample) for sample in (ignored_samples or ())
        ],
        "active_session_id": active_session_id,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture BidKing packets with WinDivert and feed live overlay.",
    )
    parser.add_argument("--log-dir", default=str(ROOT / "data" / "logs" / "live"))
    parser.add_argument("--raw-dir", default=None)
    parser.add_argument("--tables-dir", default=None)
    parser.add_argument("--process-name", default="BidKing.exe")
    parser.add_argument(
        "--server-port",
        type=int,
        action="append",
        default=None,
        help="Restrict capture to known server port. Repeatable.",
    )
    parser.add_argument(
        "--broad",
        action="store_true",
        help=(
            "Capture all TCP payload packets in sniff mode, then keep only "
            "flows owned by --process-name. Use this for UU/VPN/TUN/proxy cases "
            "where the real port is unknown."
        ),
    )
    parser.add_argument("--filter", default=None, help="Override WinDivert filter")
    parser.add_argument("--flow-refresh-seconds", type=float, default=0.25)
    parser.add_argument(
        "--include-loopback",
        action="store_true",
        help="Also keep BidKing.exe loopback flows. Off by default because local control flows are not game frames.",
    )
    parser.add_argument("--status-seconds", type=float, default=2.0)
    parser.add_argument("--debounce-seconds", type=float, default=1.0)
    parser.add_argument("--min-inference-interval-seconds", type=float, default=2.0)
    parser.add_argument("--n-trials", type=int, default=500)
    parser.add_argument("--roi-trials", type=int, default=250)
    parser.add_argument("--shadow-trials", type=int, default=None)
    parser.add_argument(
        "--full-shadow-trials",
        type=int,
        default=20,
        help="Shadow trials for full/archive snapshots (fast uses 1).",
    )
    parser.add_argument(
        "--skip-debug-shadows",
        action="store_true",
        help="Skip profile_b5 debug shadow (default unless --enable-debug-shadows).",
    )
    parser.add_argument(
        "--fast-n-trials",
        type=int,
        default=10,
        help=(
            "Trials for non-force live snapshots. Use 0 to disable fast "
            "snapshots and run full inference on every update."
        ),
    )
    parser.add_argument(
        "--enable-debug-shadows",
        action="store_true",
        help="Run profile_b5 debug shadow during live inference (off by default).",
    )
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument(
        "--formal-mode",
        default=os.environ.get("BIDKING_LIVE_FORMAL_MODE", "v3_practical"),
        choices=("v3_practical", "v2"),
        help=(
            "Formal live bid source. Defaults to BIDKING_LIVE_FORMAL_MODE "
            "or v3_practical."
        ),
    )
    parser.add_argument("--no-lock", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        import pydivert
    except ImportError:
        print(
            "[error] pydivert is not installed. Install it with: "
            f'"{sys.executable}" -m pip install pydivert',
            file=sys.stderr,
        )
        print(f"[env] python={sys.executable}", file=sys.stderr)
        return 2
    sniff_flag = getattr(getattr(pydivert, "Flag", object), "SNIFF", None)
    if sniff_flag is None:
        print(
            "[error] installed pydivert does not expose Flag.SNIFF; "
            "upgrade with: python -m pip install -U pydivert",
            file=sys.stderr,
        )
        return 2

    log_dir = Path(args.log_dir)
    raw_dir = Path(args.raw_dir) if args.raw_dir else log_dir / "raw"
    if not args.no_lock:
        try:
            _acquire_lock(log_dir)
        except RuntimeError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 2
    tables = load_monitor_tables(tables_dir=args.tables_dir)
    monitor = FatbeansWebhookMonitor(
        config=WebhookMonitorConfig(
            log_dir=log_dir,
            raw_dir=raw_dir,
            process_name=args.process_name,
            server_ports=tuple(args.server_port or ()),
            n_trials=args.n_trials,
            roi_trials=args.roi_trials,
            shadow_trials=args.shadow_trials,
            full_shadow_trials=max(1, int(args.full_shadow_trials)),
            run_debug_shadows=bool(args.enable_debug_shadows)
            and not args.skip_debug_shadows,
            seed=args.seed,
            formal_mode=args.formal_mode,
            debounce_seconds=args.debounce_seconds,
            min_inference_interval_seconds=args.min_inference_interval_seconds,
            fast_n_trials=args.fast_n_trials if args.fast_n_trials > 0 else None,
            file_name="windivert_live.json",
            source_name="windivert",
            packet_count_key="windivert_frames",
        ),
        tables=tables,
    )
    monitor.start()
    flow_index = FlowIndex(
        process_name=args.process_name,
        refresh_seconds=args.flow_refresh_seconds,
        server_ports=set(args.server_port or [10000]),
        include_loopback=args.include_loopback,
    )
    flow_index.refresh_if_due(force=True)
    frame_gate = GameFrameGate()

    server_ports = args.server_port or [10000]
    filter_text = args.filter or _default_filter(server_ports, broad=args.broad)
    _write_source_status(
        log_dir,
        process_name=args.process_name,
        filter_text=filter_text,
        active_flows=flow_index.active_flow_count(),
        accepted_packets=0,
        sniffed_packets=0,
        raw_packets=0,
        ignored_frames=0,
        dropped_bytes=0,
        active_session_id=None,
        ignored_samples=(),
    )
    print(f"[listen] Python: {sys.executable}", flush=True)
    print(f"[listen] process_elevated={_process_is_elevated()}", flush=True)
    print(f"[listen] WinDivert filter: {filter_text}", flush=True)
    print(
        f"[listen] process={args.process_name} active_flows={flow_index.active_flow_count()} "
        f"log_dir={log_dir}",
        flush=True,
    )
    sort_id = 1
    accepted = 0
    sniffed_packets = 0
    raw_packets = 0
    last_status = 0.0
    last_flow_signature: tuple[FlowKey, ...] = ()
    last_parse_warn = 0.0
    try:
        with pydivert.WinDivert(filter_text, flags=sniff_flag) as handle:
            for packet in handle:
                sniffed_packets += 1
                row = _packet_to_fatbeans_row(
                    packet,
                    sort_id=sort_id,
                    flow_index=flow_index,
                )
                now = time.monotonic()
                if row is not None:
                    raw_packets += 1
                    sort_id += 1
                    emitted = frame_gate.feed_row(row)
                    if emitted.reset_session:
                        monitor.reset_rows()
                    for game_row in emitted.rows:
                        monitor.accept_row(
                            game_row,
                            schedule_process=_should_schedule_monitor_process(
                                game_row
                            ),
                        )
                        accepted += 1
                    if args.verbose:
                        print(
                            f"[packet] raw={raw_packets} emitted={accepted} "
                            f"{row['Direct']} {row['SrcIP']}:{row['SrcPort']} "
                            f"-> {row['DstIP']}:{row['DstPort']} len={row['DataLength']}",
                            flush=True,
                        )
                if now - last_status >= args.status_seconds:
                    active = flow_index.active_flow_count()
                    flow_signature = flow_index.flow_signature()
                    if flow_signature and flow_signature != last_flow_signature:
                        frame_gate.reset_stream_buffers(
                            keep_flow_keys=flow_signature,
                            clear_session=False,
                        )
                        last_flow_signature = flow_signature
                        print(
                            f"[listen] bid flow changed ({active} active); "
                            "prune stale frame buffers, keep active session",
                            flush=True,
                        )
                    elif (
                        accepted == 0
                        and raw_packets >= 80
                        and frame_gate.ignored_frames >= 40
                        and now - last_parse_warn >= 15.0
                    ):
                        frame_gate.reset_stream_buffers(clear_session=True)
                        last_parse_warn = now
                        print(
                            "[warn] raw packets seen but no game frames parsed; "
                            f"reset buffers ignored={frame_gate.ignored_reasons_dict()}",
                            flush=True,
                        )
                    _write_source_status(
                        log_dir,
                        process_name=args.process_name,
                        filter_text=filter_text,
                        active_flows=active,
                        accepted_packets=accepted,
                        sniffed_packets=sniffed_packets,
                        raw_packets=raw_packets,
                        ignored_frames=frame_gate.ignored_frames,
                        dropped_bytes=frame_gate.dropped_bytes,
                        ignored_reasons=frame_gate.ignored_reasons_dict(),
                        ignored_samples=frame_gate.ignored_samples_dict(),
                        active_session_id=frame_gate.active_session_id,
                    )
                    if args.verbose:
                        print(
                            f"[status] active_flows={active} accepted={accepted}",
                            flush=True,
                        )
                    last_status = now
    except KeyboardInterrupt:
        print("[stop] interrupted", flush=True)
    except PermissionError:
        elevated = _process_is_elevated()
        print(
            "[error] WinDivert capture requires an elevated PowerShell/admin process. "
            f"process_elevated={elevated}",
            file=sys.stderr,
        )
        if elevated:
            print(
                "[error] Process is elevated but WinDivert still denied. "
                "Try: python -m pip install -U pydivert ; reboot ; "
                "disable other packet capture tools.",
                file=sys.stderr,
            )
        return 2
    finally:
        monitor.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
