"""Inspect FatbeansCreater JSON packet exports.

The script is intentionally transport-level only: it reconstructs length-
prefixed application frames from Fatbeans packet fragments and prints metadata
that helps decide which frames are worth reverse-engineering next. It does not
connect to the game or modify traffic.
"""

from __future__ import annotations

import argparse
import base64
import collections
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


PRINTABLE_RE = re.compile(rb"[\x20-\x7e]{4,}")
INTERESTING_NEEDLES = (
    b"auction",
    b"shoucang",
    b"round",
    b"item",
    b"map",
    b"hero",
    b"2401:",
    b"_Barista",
)


@dataclass(frozen=True)
class Packet:
    sort_id: int
    direction: str
    src: str
    dst: str
    capture_time: str
    data: bytes


@dataclass(frozen=True)
class Frame:
    index: int
    direction: str
    offset: int
    sort_id: int
    capture_time: str
    raw: bytes

    @property
    def length(self) -> int:
        return len(self.raw)

    @property
    def header_len(self) -> int:
        return 12 if self.direction == "SEND" else 16

    @property
    def body(self) -> bytes:
        return self.raw[self.header_len :]

    @property
    def packet_tag_hex(self) -> str:
        if self.direction == "SEND":
            return self.raw[4:8].hex()
        return self.raw[8:12].hex()

    @property
    def message_id(self) -> int:
        if self.direction == "SEND":
            return int.from_bytes(self.raw[8:12], "big")
        return int.from_bytes(self.raw[12:16], "big")

    @property
    def message_id_hex(self) -> str:
        return f"0x{self.message_id:04x}"

    @property
    def server_seq(self) -> int | None:
        if self.direction == "SEND":
            return None
        return int.from_bytes(self.raw[4:8], "big")


def _direction(raw: Any) -> str:
    text = str(raw or "").upper()
    if text == "RECV":
        return "REV"
    return text


def load_packets(path: Path) -> list[Packet]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("Fatbeans export must be a JSON array")

    packets: list[Packet] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        payload = base64.b64decode(row.get("Data") or "")
        expected_len = int(row.get("DataLength") or 0)
        if len(payload) != expected_len:
            raise ValueError(
                f"DataLength mismatch at SortID={row.get('SortID')}: "
                f"decoded={len(payload)} expected={expected_len}"
            )
        packets.append(
            Packet(
                sort_id=int(row["SortID"]),
                direction=_direction(row.get("Direct")),
                src=f"{row.get('SrcIP')}:{row.get('SrcPort')}",
                dst=f"{row.get('DstIP')}:{row.get('DstPort')}",
                capture_time=str(row.get("CaptureTime") or ""),
                data=payload,
            )
        )
    return sorted(packets, key=lambda p: p.sort_id)


def reconstruct_frames(packets: Sequence[Packet], direction: str) -> list[Frame]:
    selected = [p for p in packets if p.direction == direction]
    stream = bytearray()
    segments: list[tuple[int, int, Packet]] = []
    for packet in selected:
        start = len(stream)
        stream.extend(packet.data)
        segments.append((start, len(stream), packet))

    frames: list[Frame] = []
    offset = 0
    segment_index = 0
    while offset < len(stream):
        if offset + 4 > len(stream):
            raise ValueError(f"{direction} stream has incomplete length at {offset}")
        frame_len = int.from_bytes(stream[offset : offset + 4], "big")
        if frame_len < 4 or offset + frame_len > len(stream):
            raise ValueError(
                f"{direction} invalid frame length {frame_len} at offset {offset}; "
                f"remaining={len(stream) - offset}"
            )
        while (
            segment_index + 1 < len(segments)
            and segments[segment_index][1] <= offset
        ):
            segment_index += 1
        packet = segments[segment_index][2]
        frames.append(
            Frame(
                index=len(frames),
                direction=direction,
                offset=offset,
                sort_id=packet.sort_id,
                capture_time=packet.capture_time,
                raw=bytes(stream[offset : offset + frame_len]),
            )
        )
        offset += frame_len
    return frames


def printable_strings(data: bytes, *, limit: int = 8) -> list[str]:
    out: list[str] = []
    for match in PRINTABLE_RE.findall(data):
        text = match.decode("utf-8", errors="replace")
        if len(text) > 160:
            text = text[:157] + "..."
        out.append(text)
        if len(out) >= limit:
            break
    return out


def extract_json_values(data: bytes) -> list[Any]:
    values: list[Any] = []
    decoder = json.JSONDecoder()
    for pos, byte in enumerate(data):
        if byte not in (ord("{"), ord("[")):
            continue
        try:
            text = data[pos:].decode("utf-8")
            value, _end = decoder.raw_decode(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        values.append(value)
        if len(values) >= 3:
            break
    return values


def read_varint(data: bytes, offset: int) -> tuple[int, int] | None:
    value = 0
    shift = 0
    pos = offset
    while pos < len(data) and shift <= 63:
        byte = data[pos]
        value |= (byte & 0x7F) << shift
        pos += 1
        if not byte & 0x80:
            return value, pos
        shift += 7
    return None


def summarize_protobuf_fields(data: bytes, *, limit: int = 16) -> list[str]:
    fields: list[str] = []
    offset = 0
    while offset < len(data) and len(fields) < limit:
        key = read_varint(data, offset)
        if key is None:
            break
        key_value, offset = key
        field_no = key_value >> 3
        wire_type = key_value & 0x07
        if field_no <= 0:
            break

        if wire_type == 0:
            parsed = read_varint(data, offset)
            if parsed is None:
                break
            value, offset = parsed
            fields.append(f"{field_no}:varint={value}")
        elif wire_type == 1:
            if offset + 8 > len(data):
                break
            fields.append(f"{field_no}:fixed64")
            offset += 8
        elif wire_type == 2:
            parsed_len = read_varint(data, offset)
            if parsed_len is None:
                break
            size, offset = parsed_len
            if offset + size > len(data):
                break
            chunk = data[offset : offset + size]
            preview = ""
            strings = printable_strings(chunk, limit=1)
            if strings:
                preview = f" {strings[0]!r}"
            fields.append(f"{field_no}:len={size}{preview}")
            offset += size
        elif wire_type == 5:
            if offset + 4 > len(data):
                break
            fields.append(f"{field_no}:fixed32")
            offset += 4
        else:
            fields.append(f"{field_no}:wire{wire_type}")
            break
    return fields


def parse_protobuf_fields(data: bytes, *, limit: int = 512) -> list[tuple[int, int, Any]]:
    """Best-effort protobuf wire parser for shallow field inspection."""
    fields: list[tuple[int, int, Any]] = []
    offset = 0
    while offset < len(data) and len(fields) < limit:
        key = read_varint(data, offset)
        if key is None:
            break
        key_value, offset = key
        field_no = key_value >> 3
        wire_type = key_value & 0x07
        if field_no <= 0:
            break

        if wire_type == 0:
            parsed = read_varint(data, offset)
            if parsed is None:
                break
            value, offset = parsed
            fields.append((field_no, wire_type, value))
        elif wire_type == 1:
            if offset + 8 > len(data):
                break
            fields.append((field_no, wire_type, data[offset : offset + 8]))
            offset += 8
        elif wire_type == 2:
            parsed_len = read_varint(data, offset)
            if parsed_len is None:
                break
            size, offset = parsed_len
            if offset + size > len(data):
                break
            fields.append((field_no, wire_type, data[offset : offset + size]))
            offset += size
        elif wire_type == 5:
            if offset + 4 > len(data):
                break
            fields.append((field_no, wire_type, data[offset : offset + 4]))
            offset += 4
        else:
            break
    return fields


def first_field(fields: Sequence[tuple[int, int, Any]], field_no: int) -> Any:
    for fn, _wt, value in fields:
        if fn == field_no:
            return value
    return None


def all_fields(fields: Sequence[tuple[int, int, Any]], field_no: int) -> list[Any]:
    return [value for fn, _wt, value in fields if fn == field_no]


def maybe_ascii(value: Any) -> str | None:
    if not isinstance(value, bytes):
        return None
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text or any(ord(ch) < 32 for ch in text):
        return None
    return text


def candidate_event_row(frame: Frame) -> dict[str, Any] | None:
    fields = parse_protobuf_fields(frame.body)
    if frame.direction == "SEND" and frame.message_id in (0x22, 0x26):
        return {
            "frame": frame.index,
            "sort": frame.sort_id,
            "time": frame.capture_time[11:23],
            "dir": frame.direction,
            "msg": frame.message_id_hex,
            "meaning": (
                "bid_candidate" if frame.message_id == 0x22
                else "tool_or_action_candidate"
            ),
            "session": maybe_ascii(first_field(fields, 2)) or "",
            "value": first_field(fields, 3),
            "details": "",
        }

    if frame.direction == "REV" and frame.packet_tag_hex == "00000000":
        if frame.message_id == 0x25:
            wrapper = first_field(fields, 1)
            nested = parse_protobuf_fields(wrapper) if isinstance(wrapper, bytes) else []
            return {
                "frame": frame.index,
                "sort": frame.sort_id,
                "time": frame.capture_time[11:23],
                "dir": frame.direction,
                "msg": frame.message_id_hex,
                "meaning": "round_state_push_candidate",
                "session": maybe_ascii(first_field(nested, 1)) or "",
                "value": f"map={first_field(nested, 2)} round={first_field(nested, 3)}",
                "details": (
                    f"field5={len(all_fields(nested, 5))} "
                    f"field6={len(all_fields(nested, 6))} "
                    f"field7={len(all_fields(nested, 7))} "
                    f"field8={len(all_fields(nested, 8))}"
                ),
            }
        if frame.message_id == 0x2D:
            snapshot = first_field(fields, 2)
            nested = parse_protobuf_fields(snapshot) if isinstance(snapshot, bytes) else []
            return {
                "frame": frame.index,
                "sort": frame.sort_id,
                "time": frame.capture_time[11:23],
                "dir": frame.direction,
                "msg": frame.message_id_hex,
                "meaning": "settlement_or_r5_push_candidate",
                "session": maybe_ascii(first_field(nested, 1)) or "",
                "value": (
                    f"map={first_field(nested, 2)} round={first_field(nested, 3)} "
                    f"v3={first_field(fields, 3)} v4={first_field(fields, 4)} "
                    f"v5={first_field(fields, 5)}"
                ),
                "details": (
                    f"field6_players_or_results={len(all_fields(fields, 6))} "
                    f"snapshot_field6={len(all_fields(nested, 6))}"
                ),
            }
    return None


def is_interesting(frame: Frame, *, large_threshold: int) -> bool:
    body = frame.body
    lower = body.lower()
    if frame.length >= large_threshold:
        return True
    if any(needle.lower() in lower for needle in INTERESTING_NEEDLES):
        return True
    if extract_json_values(body):
        return True
    return False


def endpoint_counts(packets: Iterable[Packet]) -> list[tuple[tuple[str, str], int]]:
    counter = collections.Counter((p.src, p.dst) for p in packets)
    return counter.most_common()


def render_report(
    path: Path,
    packets: Sequence[Packet],
    frames: Sequence[Frame],
    *,
    large_threshold: int,
    max_frames: int,
) -> str:
    lines: list[str] = []
    lines.append(f"# Fatbeans capture inspection: `{path.name}`")
    lines.append("")
    lines.append("## 中文摘要")
    lines.append("")
    lines.append(
        "这是 Fatbeans JSON 抓包导出的离线检查报告。报告只记录结构化统计、"
        "frame 索引、消息号和少量字符串预览，不需要把原始抓包文件提交到 Git。"
    )
    lines.append("")
    lines.append("结论：")
    lines.append("")
    lines.append(
        f"- 当前导出包含 `{len(packets)}` 条 packet；这代表已导出的筛选结果，"
        "不一定等于抓包工具底栏的全部捕获数量。"
    )
    lines.append(
        "- 全部 payload 已通过 Base64 长度校验，说明不是 UI 文本复制，也没有明显截断。"
    )
    lines.append(
        f"- 应用层可按 4 字节大端长度前缀重组成 `{len(frames)}` 条完整 frame。"
    )
    lines.append(
        "- `SEND msg=0x0022`、`SEND msg=0x0026`、"
        "`REV push msg=0x0025` 和 `REV push msg=0x002d` 是当前优先分析对象。"
    )
    lines.append(
        "- 下一步应验证这些 message id 和字段位置在更多样本中是否稳定，"
        "再把真实 packet 转为 normalized fixture / `LiveObservationBatch`。"
    )
    lines.append("")
    lines.append("简历/项目叙事价值：")
    lines.append("")
    lines.append(
        "- 这条链路覆盖 GUI 抓包、主 TCP 会话筛选、payload 校验、TCP 片段拼接、"
        "应用层 frame 重组、protobuf wire 字段探查和候选事件时间线生成。"
    )
    lines.append(
        "- 它把项目从 OCR/手填输入推进到 packet 观测层，同时保持只读、离线、"
        "非自动化边界。"
    )
    lines.append("")
    lines.append("## Capture Summary")
    lines.append("")
    lines.append(f"- packets: {len(packets)}")
    lines.append(
        f"- sort_id range: {min(p.sort_id for p in packets)}"
        f" .. {max(p.sort_id for p in packets)}"
    )
    lines.append(f"- time range: {packets[0].capture_time} .. {packets[-1].capture_time}")
    lines.append(f"- total payload bytes: {sum(len(p.data) for p in packets)}")
    direction_counts = collections.Counter(p.direction for p in packets)
    lines.append(f"- packet directions: {dict(direction_counts)}")
    lines.append("")
    lines.append("## Endpoints")
    lines.append("")
    for (src, dst), count in endpoint_counts(packets):
        lines.append(f"- `{src} -> {dst}`: {count}")

    lines.append("")
    lines.append("## Reconstructed Frames")
    lines.append("")
    frame_counts = collections.Counter(f.direction for f in frames)
    lines.append(f"- frames: {len(frames)}")
    lines.append(f"- frame directions: {dict(frame_counts)}")
    for direction in ("SEND", "REV"):
        subset = [f for f in frames if f.direction == direction]
        if not subset:
            continue
        msg_counts = collections.Counter(f.message_id_hex for f in subset)
        lines.append(
            f"- {direction}: {len(subset)} frames, "
            f"{sum(len(f.body) for f in subset)} body bytes"
        )
        common = ", ".join(f"{k} x{v}" for k, v in msg_counts.most_common(8))
        lines.append(f"  - common message ids: {common}")

    interesting = [
        frame for frame in frames
        if is_interesting(frame, large_threshold=large_threshold)
    ]
    lines.append("")
    lines.append("## Interesting Frames")
    lines.append("")
    lines.append(
        f"Showing up to {max_frames} frames with JSON/text markers or "
        f"length >= {large_threshold} bytes."
    )
    lines.append("")
    lines.append(
        "| frame | sort | time | dir | msg | tag | len | body | notes |"
    )
    lines.append("|---:|---:|---|---|---:|---|---:|---:|---|")
    for frame in interesting[:max_frames]:
        strings = printable_strings(frame.body, limit=3)
        json_values = extract_json_values(frame.body)
        proto = summarize_protobuf_fields(frame.body, limit=5)
        notes: list[str] = []
        if json_values:
            first = json_values[0]
            if isinstance(first, dict):
                notes.append("json keys=" + ",".join(list(first)[:6]))
            else:
                notes.append(f"json {type(first).__name__}")
        if strings:
            notes.append("str=" + " / ".join(s.replace("|", "\\|") for s in strings))
        if proto:
            notes.append("pb=" + "; ".join(proto))
        tag = frame.packet_tag_hex
        if tag == "00000000":
            tag = "push"
        time = frame.capture_time[11:23] if len(frame.capture_time) >= 23 else frame.capture_time
        lines.append(
            f"| {frame.index} | {frame.sort_id} | {time} | {frame.direction} | "
            f"{frame.message_id_hex} | `{tag}` | {frame.length} | "
            f"{len(frame.body)} | {'<br>'.join(notes)} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `REV` is Fatbeans' receive direction label.")
    lines.append("- `tag=push` means the server-side request tag is zero, so the frame is likely an unsolicited server push.")
    lines.append("- Message ids and protobuf fields are heuristic until matched against game semantics.")
    timeline = [row for frame in frames if (row := candidate_event_row(frame))]
    if timeline:
        lines.append("")
        lines.append("## Candidate Game Event Timeline")
        lines.append("")
        lines.append(
            "These rows are heuristic. They mark messages whose shape matches "
            "bids/actions or server-side round/settlement pushes."
        )
        lines.append("")
        lines.append("| frame | sort | time | dir | msg | candidate | session | value | details |")
        lines.append("|---:|---:|---|---|---:|---|---|---|---|")
        for row in timeline:
            session = str(row["session"]).replace("|", "\\|")
            value = str(row["value"]).replace("|", "\\|")
            details = str(row["details"]).replace("|", "\\|")
            lines.append(
                f"| {row['frame']} | {row['sort']} | {row['time']} | "
                f"{row['dir']} | {row['msg']} | {row['meaning']} | "
                f"{session} | {value} | {details} |"
            )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path, help="Fatbeans JSON export path")
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for a markdown report",
    )
    parser.add_argument(
        "--large-threshold",
        type=int,
        default=700,
        help="Minimum frame length to include as interesting",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=80,
        help="Maximum interesting frames to print",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packets = load_packets(args.capture)
    frames = [
        *reconstruct_frames(packets, "SEND"),
        *reconstruct_frames(packets, "REV"),
    ]
    frames.sort(key=lambda frame: (frame.capture_time, frame.direction, frame.index))
    report = render_report(
        args.capture,
        packets,
        frames,
        large_threshold=args.large_threshold,
        max_frames=args.max_frames,
    )
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
