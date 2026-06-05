"""Fatbeans JSON capture adapter.

This module is deliberately read-only. It parses FatbeansCreater JSON exports
into normalized game events, then exposes a narrow conversion for fields that
already have stable ``LiveObservationBatch`` semantics.
"""

from __future__ import annotations

import base64
import json
import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from bidking_lab.live.types import (
    FieldUpdate,
    GridItemObservation,
    LiveObservationBatch,
)

_CATEGORY_OUTLINE_ACTIONS: dict[int, int] = {
    100151: 101,  # 家具物品
    100152: 102,  # 医疗药品
    100153: 103,  # 时尚潮流
    100154: 104,  # 兵装军火
    100155: 105,  # 珠宝矿藏
    100156: 106,  # 文物古董
    100157: 107,  # 数码娱乐
    100158: 108,  # 能源交通
    100159: 109,  # 食饮珍馐
    100160: 110,  # 书画古籍
}
_HERO_MODE_BY_ID: dict[int, str] = {
    101: "fatima",
    102: "chenmei",
    103: "aisha",
    104: "gabriela",
    105: "tatiana",
    106: "naomi",
    107: "sophie",
    108: "maria",
    109: "helena",
    110: "isabella",
    201: "george",
    202: "carlos",
    203: "leonard",
    204: "ahmed",
    205: "ivan",
    206: "takeda",
    207: "wuqilin",
    208: "ethan",
    209: "victor",
    301: "raven",
}
_SKILL_REVEAL_CATEGORIES: dict[int, int] = {
    100101: 106,  # 法蒂玛: 文物古董轮廓/品质
    1001011: 106,
    1001012: 106,
    1001013: 106,
    1001014: 106,
    100105: 103,  # 塔蒂安娜: 时尚潮流轮廓/品质
    100109: 102,  # 海琳娜: 医疗药品品质/轮廓
    1001091: 102,
    1001092: 102,
    1001093: 102,
    1001094: 102,
    1001101: 105,  # 伊莎贝拉: 珠宝矿藏轮廓
    100201: 104,  # 乔治: 兵装军火轮廓/品质
    100206: 110,  # 武田宏志: 书画古籍轮廓/品质
    1002062: 110,
    1002063: 110,
    1002064: 110,
    1002065: 110,
    10002071: 106,  # 吴起灵: 文物古董轮廓
    10002072: 106,  # 吴起灵: 文物古董品质
    10002073: 106,  # 吴起灵: 文物古董完整信息
}
_ACTION_SESSION_FIELDS: dict[int, tuple[str, ...]] = {
    100103: ("session", "warehouse_total_cells"),  # 总仓储空间
    100115: ("session", "total_item_count"),  # 库存清点
}
_ACTION_TOTAL_CELLS: dict[int, int] = {
    100104: 1,  # 普品扫描: green/white merged bucket
    100105: 3,  # 良品扫描
    100106: 4,  # 优品扫描
    100107: 5,  # 极品扫描
    100108: 6,  # 珍品扫描
}
_ACTION_AVG_CELLS: dict[int, int] = {
    100110: 1,  # 普品均格: green/white merged bucket
    100111: 3,  # 良品均格
    100112: 4,  # 优品均格
    100113: 5,  # 极品均格
    100114: 6,  # 珍品均格
}
_ACTION_VALUE_SUM: dict[int, int] = {
    100122: 1,  # 普品估价: green/white merged bucket
    100123: 3,  # 良品估价
    100124: 4,  # 优品估价
    100125: 5,  # 极品估价
    100126: 6,  # 珍品估价
}
_ACTION_COUNT: dict[int, int] = {
    100116: 1,  # 普品存量: green/white merged bucket
    100117: 3,  # 良品存量
    100118: 4,  # 优品存量
    100119: 5,  # 极品存量
    100120: 6,  # 珍品存量
}
_ACTION_SIZE_AVG_VALUE: dict[int, int] = {
    100169: 1,  # 单格均价
    100170: 2,  # 两格均价
    100171: 3,  # 三格均价
    100172: 4,  # 四格均价
    100173: 6,  # 六格均价
}
_PUBLIC_INFO_INT_VALUE_FIELDS: dict[int, int] = {
    200009: 14,  # 所有藏品总占用格数
    200010: 14,  # 紫色品质藏品总占用格数
    200011: 14,  # 金色品质藏品总占用格数
    200012: 14,  # 红色品质藏品总占用格数
    200017: 7,  # 所有藏品件数
    200018: 7,  # 紫色品质藏品件数
    200019: 7,  # 金色品质藏品件数
    200020: 7,  # 红色品质藏品件数
}
_PUBLIC_INFO_EXACT_UPDATE_PATHS: dict[int, tuple[str, ...]] = {
    200009: ("session", "warehouse_total_cells"),
    200010: ("bucket", "4", "total_cells"),
    200011: ("bucket", "5", "total_cells"),
    200012: ("bucket", "6", "total_cells"),
    200017: ("session", "total_item_count"),
    200018: ("bucket", "4", "count"),
    200019: ("bucket", "5", "count"),
    200020: ("bucket", "6", "count"),
}
_PUBLIC_OUTLINE_QUALITY_BY_INFO_ID: dict[int, int] = {
    200001: 4,
    200002: 5,
    200003: 6,
}
_MAX_FRAME_BYTES = 4 * 1024 * 1024


Direction = Literal["SEND", "REV"]


@dataclass(frozen=True)
class FatbeansPacket:
    sort_id: int
    direction: Direction
    src: str
    dst: str
    capture_time: str
    data: bytes


@dataclass(frozen=True)
class FatbeansFrame:
    index: int
    direction: Direction
    sort_id: int
    capture_time: str
    raw: bytes

    @property
    def header_len(self) -> int:
        return 12 if self.direction == "SEND" else 16

    @property
    def body(self) -> bytes:
        return self.raw[self.header_len :]

    @property
    def packet_tag(self) -> int:
        if self.direction == "SEND":
            return int.from_bytes(self.raw[4:8], "big")
        return int.from_bytes(self.raw[8:12], "big")

    @property
    def message_id(self) -> int:
        if self.direction == "SEND":
            return int.from_bytes(self.raw[8:12], "big")
        return int.from_bytes(self.raw[12:16], "big")


@dataclass(frozen=True)
class FatbeansSendEvent:
    sort_id: int
    capture_time: str
    message_id: int
    session_id: str | None
    value: int | None

    @property
    def kind(self) -> str:
        if self.message_id == 0x0022:
            return "bid"
        if self.message_id == 0x0026:
            return "action"
        return "send"


@dataclass(frozen=True)
class FatbeansPlayerBid:
    player_id: int
    name: str
    hero_id: int | None
    values: tuple[int, ...]

    @property
    def current_value(self) -> int | None:
        return self.values[-1] if self.values else None


@dataclass(frozen=True)
class FatbeansObservedItem:
    local_index: int | None
    runtime_id: int | None
    item_id: int | None
    quality: int | None
    value: int | None
    shape_code: int | None
    cells: int | None


@dataclass(frozen=True)
class FatbeansActionResult:
    action_id: int
    result: int | float | None
    result_field: int | None
    observed_items: tuple[FatbeansObservedItem, ...] = ()


@dataclass(frozen=True)
class FatbeansSkillReveal:
    skill_id: int
    hero_id: int | None
    round_index: int | None
    observed_items: tuple[FatbeansObservedItem, ...] = ()


@dataclass(frozen=True)
class FatbeansInventoryItem:
    runtime_id: int
    item_id: int
    quality: int | None
    cells: int
    local_index: int | None = None


@dataclass(frozen=True)
class FatbeansPublicInfo:
    info_id: int
    map_id: int | None
    value: float | int
    value_field: int
    observed_items: tuple[FatbeansObservedItem, ...] = ()


@dataclass(frozen=True)
class FatbeansStatusEvent:
    sort_id: int
    capture_time: str
    player_id: int | None
    session_id: str | None


@dataclass(frozen=True)
class FatbeansStateEvent:
    sort_id: int
    capture_time: str
    message_id: int
    session_id: str | None
    map_id: int | None
    round_index: int | None
    player_id: int | None = None
    bids: tuple[FatbeansPlayerBid, ...] = ()
    action_results: tuple[FatbeansActionResult, ...] = ()
    skill_reveals: tuple[FatbeansSkillReveal, ...] = ()
    public_infos: tuple[FatbeansPublicInfo, ...] = ()
    inventory_items: tuple[FatbeansInventoryItem, ...] = ()
    settlement_loss_units: int | None = None

    @property
    def round_no(self) -> int | None:
        """One-based in-game round number from the state payload."""
        return self.round_index


@dataclass(frozen=True)
class FatbeansCaptureEvents:
    packets: tuple[FatbeansPacket, ...]
    frames: tuple[FatbeansFrame, ...]
    sends: tuple[FatbeansSendEvent, ...]
    states: tuple[FatbeansStateEvent, ...]
    statuses: tuple[FatbeansStatusEvent, ...]


ProtoField = tuple[int, int, Any]


def _direction(raw: Any) -> Direction:
    text = str(raw or "").upper()
    if text == "RECV":
        text = "REV"
    if text not in ("SEND", "REV"):
        raise ValueError(f"unsupported Fatbeans direction: {raw!r}")
    return text  # type: ignore[return-value]


def load_fatbeans_packets(path: str | Path) -> list[FatbeansPacket]:
    rows = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return load_fatbeans_packets_from_rows(rows)


def load_fatbeans_packets_from_payload(raw: str | bytes) -> list[FatbeansPacket]:
    """Load packets from a Fatbeans JSON export already held in memory."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    rows = json.loads(raw)
    return load_fatbeans_packets_from_rows(rows)


def load_fatbeans_packets_from_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[FatbeansPacket]:
    """Load packets from decoded Fatbeans export rows."""
    if not isinstance(rows, list):
        raise ValueError("Fatbeans export must be a JSON array")

    packets: list[FatbeansPacket] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        protocol = str(row.get("Protocol") or "").lower()
        if protocol and protocol != "tcp":
            continue
        payload = base64.b64decode(row.get("Data") or "")
        expected_len = int(row.get("DataLength") or 0)
        if len(payload) != expected_len:
            raise ValueError(
                f"DataLength mismatch at SortID={row.get('SortID')}: "
                f"decoded={len(payload)} expected={expected_len}"
            )
        packets.append(
            FatbeansPacket(
                sort_id=int(row["SortID"]),
                direction=_direction(row.get("Direct")),
                src=f"{row.get('SrcIP')}:{row.get('SrcPort')}",
                dst=f"{row.get('DstIP')}:{row.get('DstPort')}",
                capture_time=str(row.get("CaptureTime") or ""),
                data=payload,
            )
        )
    return sorted(packets, key=lambda packet: packet.sort_id)


def reconstruct_fatbeans_frames(
    packets: Sequence[FatbeansPacket],
    direction: Direction,
) -> list[FatbeansFrame]:
    frames: list[FatbeansFrame] = []
    packets_by_stream: dict[tuple[str, str], list[FatbeansPacket]] = {}
    for packet in packets:
        if packet.direction != direction:
            continue
        packets_by_stream.setdefault((packet.src, packet.dst), []).append(packet)

    min_frame_len = 12 if direction == "SEND" else 16
    stream_groups = sorted(
        packets_by_stream.values(),
        key=lambda group: min(packet.sort_id for packet in group),
    )
    for selected in stream_groups:
        selected.sort(key=lambda packet: packet.sort_id)
        stream = bytearray()
        segments: list[tuple[int, int, FatbeansPacket]] = []
        for packet in selected:
            start = len(stream)
            stream.extend(packet.data)
            segments.append((start, len(stream), packet))

        offset = 0
        segment_index = 0
        while offset < len(stream):
            if offset + 4 > len(stream):
                break
            frame_len = int.from_bytes(stream[offset : offset + 4], "big")
            if (
                frame_len < min_frame_len
                or frame_len > _MAX_FRAME_BYTES
                or offset + frame_len > len(stream)
            ):
                offset += 1
                continue
            while (
                segment_index + 1 < len(segments)
                and segments[segment_index][1] <= offset
            ):
                segment_index += 1
            packet = segments[segment_index][2]
            frames.append(
                FatbeansFrame(
                    index=len(frames),
                    direction=direction,
                    sort_id=packet.sort_id,
                    capture_time=packet.capture_time,
                    raw=bytes(stream[offset : offset + frame_len]),
                )
            )
            offset += frame_len
    return frames


def _read_varint(data: bytes, offset: int) -> tuple[int, int] | None:
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


def _parse_fields(data: bytes, *, limit: int = 1024) -> list[ProtoField]:
    fields: list[ProtoField] = []
    offset = 0
    while offset < len(data) and len(fields) < limit:
        key = _read_varint(data, offset)
        if key is None:
            break
        key_value, offset = key
        field_no = key_value >> 3
        wire_type = key_value & 0x07
        if field_no <= 0:
            break

        if wire_type == 0:
            parsed = _read_varint(data, offset)
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
            parsed_len = _read_varint(data, offset)
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


def _first(fields: Sequence[ProtoField], field_no: int) -> Any:
    for fn, _wt, value in fields:
        if fn == field_no:
            return value
    return None


def _all(fields: Sequence[ProtoField], field_no: int) -> list[Any]:
    return [value for fn, _wt, value in fields if fn == field_no]


def _text(value: Any) -> str | None:
    if not isinstance(value, bytes):
        return None
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if text and all(ord(char) >= 32 for char in text):
        return text
    return None


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _fixed32_float(value: bytes) -> float:
    return struct.unpack("<f", value)[0]


def _parse_send_event(frame: FatbeansFrame) -> FatbeansSendEvent | None:
    if frame.direction != "SEND" or frame.message_id not in (0x0022, 0x0026):
        return None
    fields = _parse_fields(frame.body)
    return FatbeansSendEvent(
        sort_id=frame.sort_id,
        capture_time=frame.capture_time,
        message_id=frame.message_id,
        session_id=_text(_first(fields, 2)),
        value=_int(_first(fields, 3)),
    )


def _parse_status_event(frame: FatbeansFrame) -> FatbeansStatusEvent | None:
    if frame.direction != "REV" or frame.packet_tag != 0 or frame.message_id != 0x0077:
        return None
    fields = _parse_fields(frame.body)
    return FatbeansStatusEvent(
        sort_id=frame.sort_id,
        capture_time=frame.capture_time,
        player_id=_int(_first(fields, 1)),
        session_id=_text(_first(fields, 2)),
    )


def _parse_player_bid(block: bytes) -> FatbeansPlayerBid | None:
    fields = _parse_fields(block)
    player_id = _int(_first(fields, 1))
    name = _text(_first(fields, 2))
    if player_id is None or name is None:
        return None
    values: list[int] = []
    for raw_bid in _all(fields, 5):
        if not isinstance(raw_bid, bytes):
            continue
        bid_fields = _parse_fields(raw_bid)
        bid = _int(_first(bid_fields, 2))
        if bid is not None:
            values.append(bid)
    return FatbeansPlayerBid(
        player_id=player_id,
        name=name,
        hero_id=_int(_first(fields, 3)),
        values=tuple(values),
    )


def _parse_action_result(block: bytes) -> FatbeansActionResult | None:
    fields = _parse_fields(block)
    action_id = _int(_first(fields, 4))
    if action_id is None:
        return None
    observed_items = tuple(
        item
        for raw in _all(fields, 8)
        if isinstance(raw, bytes)
        for item in (_parse_observed_item(raw),)
        if item is not None
    )
    for result_field in (14, 12):
        result = _int(_first(fields, result_field))
        if result is not None:
            return FatbeansActionResult(
                action_id=action_id,
                result=result,
                result_field=result_field,
                observed_items=observed_items,
            )
    for result_field in (11, 9, 10):
        raw_result = _first(fields, result_field)
        if isinstance(raw_result, bytes) and len(raw_result) == 4:
            return FatbeansActionResult(
                action_id=action_id,
                result=_fixed32_float(raw_result),
                result_field=result_field,
                observed_items=observed_items,
            )
    if observed_items:
        return FatbeansActionResult(
            action_id=action_id,
            result=None,
            result_field=None,
            observed_items=observed_items,
        )
    return None


def _parse_direct_action_response(
    frame: FatbeansFrame,
) -> FatbeansActionResult | None:
    """Parse ``REV msg=0x0027`` direct tool/action responses.

    These frames carry only the action result payload. They do not repeat the
    session/map/round fields, so callers must attach the current auction
    context before converting them into state events.
    """
    if (
        frame.direction != "REV"
        or frame.packet_tag != 0
        or frame.message_id != 0x0027
    ):
        return None
    fields = _parse_fields(frame.body)
    payload = _first(fields, 2)
    if not isinstance(payload, bytes):
        return None
    return _parse_action_result(payload)


def _parse_observed_item(block: bytes) -> FatbeansObservedItem | None:
    fields = _parse_fields(block)
    local_index = _int(_first(fields, 1))
    runtime_id = _int(_first(fields, 2))
    quality = _int(_first(fields, 6))
    if runtime_id is None and quality is None:
        return None
    return FatbeansObservedItem(
        local_index=local_index,
        runtime_id=runtime_id,
        item_id=_int(_first(fields, 3)),
        quality=quality,
        value=_int(_first(fields, 7)),
        shape_code=_int(_first(fields, 4)),
        cells=_int(_first(fields, 8)),
    )


def _shape_cells(shape_code: int | None) -> int | None:
    if shape_code is None:
        return None
    width = shape_code // 10
    height = shape_code % 10
    if width <= 0 or height <= 0:
        return None
    return width * height


def _observed_item_cells(item: FatbeansObservedItem) -> int | None:
    return item.cells or _shape_cells(item.shape_code)


def _parse_skill_reveal(block: bytes) -> FatbeansSkillReveal | None:
    fields = _parse_fields(block)
    skill_id = _int(_first(fields, 1))
    if skill_id is None:
        return None
    observed_items = tuple(
        item
        for raw in _all(fields, 8)
        if isinstance(raw, bytes)
        for item in (_parse_observed_item(raw),)
        if item is not None
    )
    if not observed_items:
        return None
    return FatbeansSkillReveal(
        skill_id=skill_id,
        hero_id=_int(_first(fields, 2)),
        round_index=_int(_first(fields, 6)),
        observed_items=observed_items,
    )


def _parse_public_info(block: bytes) -> FatbeansPublicInfo | None:
    fields = _parse_fields(block)
    info_id = _int(_first(fields, 1))
    if info_id is None:
        return None
    observed_items = tuple(
        item
        for raw in _all(fields, 8)
        if isinstance(raw, bytes)
        for item in (_parse_observed_item(raw),)
        if item is not None
    )
    int_value_field = _PUBLIC_INFO_INT_VALUE_FIELDS.get(info_id)
    if int_value_field is not None:
        raw = _first(fields, int_value_field)
        if isinstance(raw, int):
            return FatbeansPublicInfo(
                info_id=info_id,
                map_id=_int(_first(fields, 3)),
                value=raw,
                value_field=int_value_field,
                observed_items=observed_items,
            )
    for value_field in (11, 9):
        raw = _first(fields, value_field)
        if isinstance(raw, bytes) and len(raw) == 4:
            return FatbeansPublicInfo(
                info_id=info_id,
                map_id=_int(_first(fields, 3)),
                value=_fixed32_float(raw),
                value_field=value_field,
                observed_items=observed_items,
            )
        if isinstance(raw, int):
            return FatbeansPublicInfo(
                info_id=info_id,
                map_id=_int(_first(fields, 3)),
                value=raw,
                value_field=value_field,
                observed_items=observed_items,
            )
    if observed_items:
        return FatbeansPublicInfo(
            info_id=info_id,
            map_id=_int(_first(fields, 3)),
            value=len(observed_items),
            value_field=8,
            observed_items=observed_items,
        )
    return None


def _parse_inventory_items(block: Any) -> tuple[FatbeansInventoryItem, ...]:
    if not isinstance(block, bytes):
        return ()
    items: list[FatbeansInventoryItem] = []
    seen: set[tuple[int, int]] = set()

    def is_inventory_item(ints: dict[int, list[int]]) -> bool:
        runtime_id = ints.get(1, [None])[0]
        item_id = ints.get(2, [None])[0]
        return (
            isinstance(runtime_id, int)
            and isinstance(item_id, int)
            and 1_000_000 <= item_id < 2_000_000
        )

    def direct_item_child_count(
        byte_fields: dict[int, list[bytes]],
    ) -> int:
        count = 0
        for values in byte_fields.values():
            for value in values:
                child_ints: dict[int, list[int]] = {}
                for field_no, _wire_type, child_value in _parse_fields(value):
                    if isinstance(child_value, int):
                        child_ints.setdefault(field_no, []).append(child_value)
                if is_inventory_item(child_ints):
                    count += 1
        return count

    def walk(
        data: bytes,
        depth: int,
        inherited_local_index: int | None,
    ) -> None:
        if depth > 8:
            return
        fields = _parse_fields(data)
        ints: dict[int, list[int]] = {}
        byte_fields: dict[int, list[bytes]] = {}
        for field_no, _wire_type, value in fields:
            if isinstance(value, int):
                ints.setdefault(field_no, []).append(value)
            elif isinstance(value, bytes):
                byte_fields.setdefault(field_no, []).append(value)

        runtime_id = ints.get(1, [None])[0]
        item_id = ints.get(2, [None])[0]
        if is_inventory_item(ints):
            key = (runtime_id, item_id)
            if key not in seen:
                seen.add(key)
                items.append(
                    FatbeansInventoryItem(
                        runtime_id=runtime_id,
                        item_id=item_id,
                        quality=ints.get(9, [None])[0],
                        cells=len(byte_fields.get(4, ())),
                        local_index=inherited_local_index,
                    )
                )
            return

        local_index_for_children = inherited_local_index
        if direct_item_child_count(byte_fields) == 1:
            raw_local_index = ints.get(1, [None])[0]
            local_index_for_children = (
                raw_local_index
                if isinstance(raw_local_index, int) and 0 <= raw_local_index < 1000
                else 0
            )

        for values in byte_fields.values():
            for value in values:
                walk(value, depth + 1, local_index_for_children)

    walk(block, 0, None)
    return tuple(items)


def _state_payload(frame: FatbeansFrame) -> tuple[bytes | None, int | None]:
    fields = _parse_fields(frame.body)
    if frame.direction != "REV" or frame.packet_tag != 0:
        return None, None
    if frame.message_id in (0x0021, 0x0025):
        payload = _first(fields, 1)
        return (payload if isinstance(payload, bytes) else None), None
    if frame.message_id == 0x002D:
        payload = _first(fields, 2)
        return (
            payload if isinstance(payload, bytes) else None,
            _int(_first(fields, 5)),
        )
    return None, None


def _parse_state_event(frame: FatbeansFrame) -> FatbeansStateEvent | None:
    payload, loss_units = _state_payload(frame)
    if payload is None:
        return None
    fields = _parse_fields(payload)
    bids = tuple(
        parsed
        for raw in _all(fields, 5)
        if isinstance(raw, bytes)
        for parsed in (_parse_player_bid(raw),)
        if parsed is not None
    )
    actions = tuple(
        parsed
        for raw in _all(fields, 8)
        if isinstance(raw, bytes)
        for parsed in (_parse_action_result(raw),)
        if parsed is not None
    )
    skill_reveals = tuple(
        parsed
        for raw in _all(fields, 6)
        if isinstance(raw, bytes)
        for parsed in (_parse_skill_reveal(raw),)
        if parsed is not None
    )
    public_infos = tuple(
        parsed
        for raw in _all(fields, 7)
        if isinstance(raw, bytes)
        for parsed in (_parse_public_info(raw),)
        if parsed is not None
    )
    inventory_items = _parse_inventory_items(_first(fields, 4))
    return FatbeansStateEvent(
        sort_id=frame.sort_id,
        capture_time=frame.capture_time,
        message_id=frame.message_id,
        session_id=_text(_first(fields, 1)),
        map_id=_int(_first(fields, 2)),
        round_index=_int(_first(fields, 3)),
        bids=bids,
        action_results=actions,
        skill_reveals=skill_reveals,
        public_infos=public_infos,
        inventory_items=inventory_items,
        settlement_loss_units=loss_units,
    )


def parse_fatbeans_capture(path: str | Path) -> FatbeansCaptureEvents:
    packets = load_fatbeans_packets(path)
    return parse_fatbeans_packets(packets)


def parse_fatbeans_capture_payload(raw: str | bytes) -> FatbeansCaptureEvents:
    """Parse a Fatbeans JSON export already held in memory."""
    packets = load_fatbeans_packets_from_payload(raw)
    return parse_fatbeans_packets(packets)


def parse_fatbeans_packets(
    packets: Sequence[FatbeansPacket],
) -> FatbeansCaptureEvents:
    """Parse loaded Fatbeans packets into normalized capture events."""
    frames = [
        *reconstruct_fatbeans_frames(packets, "SEND"),
        *reconstruct_fatbeans_frames(packets, "REV"),
    ]
    frames.sort(key=lambda frame: (frame.sort_id, frame.index))
    sends = tuple(
        event
        for frame in frames
        for event in (_parse_send_event(frame),)
        if event is not None
    )
    statuses = tuple(
        event
        for frame in frames
        for event in (_parse_status_event(frame),)
        if event is not None
    )
    states_list: list[FatbeansStateEvent] = []
    current_session_id: str | None = None
    current_map_id: int | None = None
    current_round_index: int | None = None
    local_player_by_session: dict[str, int] = {}
    pending_bid_values_by_session: dict[str, list[int]] = {}
    for frame in frames:
        status = _parse_status_event(frame)
        if status is not None:
            if status.session_id is not None:
                current_session_id = status.session_id
            continue
        send = _parse_send_event(frame)
        if send is not None and send.kind == "bid" and send.session_id and send.value:
            pending_bid_values_by_session.setdefault(send.session_id, []).append(
                int(send.value)
            )
        state = _parse_state_event(frame)
        if state is not None:
            if state.session_id is not None:
                local_player_id = local_player_by_session.get(state.session_id)
                if (
                    local_player_id is not None
                    and state.bids
                    and not any(bid.player_id == local_player_id for bid in state.bids)
                ):
                    local_player_by_session.pop(state.session_id, None)
                    local_player_id = None
                if local_player_id is None:
                    local_player_id = _infer_local_player_id_from_bid_values(
                        state.bids,
                        pending_bid_values_by_session.get(state.session_id, ()),
                    )
                    if local_player_id is not None:
                        local_player_by_session[state.session_id] = local_player_id
                if local_player_id is not None:
                    state = replace(state, player_id=local_player_id)
            states_list.append(state)
            if state.session_id is not None:
                current_session_id = state.session_id
            if state.map_id is not None:
                current_map_id = state.map_id
            if state.round_index is not None:
                current_round_index = state.round_index
            continue

        direct_action = _parse_direct_action_response(frame)
        if direct_action is None or current_session_id is None:
            continue
        states_list.append(
            FatbeansStateEvent(
                sort_id=frame.sort_id,
                capture_time=frame.capture_time,
                message_id=frame.message_id,
                session_id=current_session_id,
                player_id=local_player_by_session.get(current_session_id),
                map_id=current_map_id,
                round_index=current_round_index,
                action_results=(direct_action,),
            )
        )
    return FatbeansCaptureEvents(
        packets=tuple(packets),
        frames=tuple(frames),
        sends=sends,
        states=tuple(states_list),
        statuses=statuses,
    )


def _infer_local_player_id_from_bid_values(
    bids: Sequence[FatbeansPlayerBid],
    pending_bid_values: Sequence[int],
) -> int | None:
    if not bids or not pending_bid_values:
        return None
    matched: set[int] = set()
    for value in pending_bid_values:
        candidates = [
            bid.player_id
            for bid in bids
            if value in bid.values
        ]
        if len(candidates) == 1:
            matched.add(candidates[0])
    return next(iter(matched)) if len(matched) == 1 else None


def _event_kind_for_state(state: FatbeansStateEvent) -> str:
    if state.message_id == 0x0021:
        return "session_started"
    if state.message_id == 0x002D or state.inventory_items:
        return "session_settled"
    if state.action_results or state.skill_reveals:
        return "tool_revealed"
    if state.public_infos:
        return "public_info_changed"
    return "round_changed"


def _state_updates(state: FatbeansStateEvent) -> list[FieldUpdate]:
    updates: list[FieldUpdate] = []
    if state.map_id is not None:
        updates.append(
            FieldUpdate(
                path=("session", "map_id"),
                value=state.map_id,
                source="packet",
                confidence="exact",
                sequence=state.sort_id,
            )
        )
    if state.round_index is not None:
        updates.append(
            FieldUpdate(
                path=("session", "round"),
                value=state.round_index,
                source="packet",
                confidence="exact",
                sequence=state.sort_id,
            )
        )
    hero = _hero_mode_from_state(state)
    if hero is not None:
        updates.append(
            FieldUpdate(
                path=("session", "hero"),
                value=hero,
                source="packet",
                confidence="exact",
                sequence=state.sort_id,
            )
        )
    for result in state.action_results:
        if result.result is None:
            continue
        if result.action_id in _ACTION_SESSION_FIELDS:
            updates.append(
                FieldUpdate(
                    path=_ACTION_SESSION_FIELDS[result.action_id],
                    value=result.result,
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                )
            )
        elif result.action_id in _ACTION_TOTAL_CELLS:
            quality = _ACTION_TOTAL_CELLS[result.action_id]
            updates.append(
                FieldUpdate(
                    path=("bucket", str(quality), "total_cells"),
                    value=result.result,
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                )
            )
        elif result.action_id in _ACTION_VALUE_SUM:
            quality = _ACTION_VALUE_SUM[result.action_id]
            updates.append(
                FieldUpdate(
                    path=("bucket", str(quality), "value_sum"),
                    value=result.result,
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                )
            )
        elif result.action_id in _ACTION_COUNT:
            quality = _ACTION_COUNT[result.action_id]
            updates.append(
                FieldUpdate(
                    path=("bucket", str(quality), "count"),
                    value=result.result,
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                )
            )
        elif result.action_id in _ACTION_AVG_CELLS:
            quality = _ACTION_AVG_CELLS[result.action_id]
            updates.append(
                FieldUpdate(
                    path=("bucket", str(quality), "avg_cells"),
                    value=result.result,
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                )
            )
    return updates


def _hero_mode_from_state(state: FatbeansStateEvent) -> str | None:
    player_id = getattr(state, "player_id", None)
    bids = tuple(getattr(state, "bids", ()) or ())
    skill_reveals = tuple(getattr(state, "skill_reveals", ()) or ())
    if player_id is not None:
        for bid in bids:
            if bid.player_id != player_id or bid.hero_id is None:
                continue
            hero = _HERO_MODE_BY_ID.get(bid.hero_id)
            if hero is not None:
                return hero
        return None

    reveal_heroes = {
        hero
        for reveal in skill_reveals
        if reveal.hero_id is not None
        for hero in (_HERO_MODE_BY_ID.get(reveal.hero_id),)
        if hero is not None
    }
    bid_heroes = {
        hero
        for bid in bids
        if bid.hero_id is not None
        for hero in (_HERO_MODE_BY_ID.get(bid.hero_id),)
        if hero is not None
    }
    if len(reveal_heroes) == 1:
        return next(iter(reveal_heroes))
    if len(bid_heroes) == 1:
        return next(iter(bid_heroes))
    return None


def hero_mode_from_state(state: FatbeansStateEvent) -> str | None:
    return _hero_mode_from_state(state)


def _skill_reveal_category(skill_id: int | None) -> int | None:
    if skill_id is None:
        return None
    return _SKILL_REVEAL_CATEGORIES.get(int(skill_id))


def _inventory_updates(state: FatbeansStateEvent) -> list[FieldUpdate]:
    if not state.inventory_items:
        return []

    updates: list[FieldUpdate] = [
        FieldUpdate(
            path=("session", "warehouse_total_cells"),
            value=sum(item.cells for item in state.inventory_items),
            source="packet",
            confidence="exact",
            sequence=state.sort_id,
        ),
        FieldUpdate(
            path=("session", "total_item_count"),
            value=len(state.inventory_items),
            source="packet",
            confidence="exact",
            sequence=state.sort_id,
        ),
    ]
    for quality in (1, 2, 3, 4, 5, 6):
        quality_items = [
            item for item in state.inventory_items
            if item.quality == quality
        ]
        if not quality_items:
            continue
        updates.extend(
            (
                FieldUpdate(
                    path=("bucket", str(quality), "total_cells"),
                    value=sum(item.cells for item in quality_items),
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                ),
                FieldUpdate(
                    path=("bucket", str(quality), "count"),
                    value=len(quality_items),
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                ),
            )
        )
    return updates


def _aisha_skill_quality(skill_id: int) -> int | None:
    # Aisha exposes cumulative per-quality outlines for q=1..4.
    return {
        1001034: 1,
        1001033: 2,
        1001032: 3,
        1001031: 4,
    }.get(skill_id)


def _aisha_skill_updates(state: FatbeansStateEvent) -> list[FieldUpdate]:
    updates: list[FieldUpdate] = []
    for reveal in state.skill_reveals:
        if reveal.hero_id != 103:
            continue
        quality = _aisha_skill_quality(reveal.skill_id)
        if quality is None:
            continue
        cells_by_runtime: dict[int | None, int] = {}
        anonymous_index = 0
        for item in reveal.observed_items:
            cells = _observed_item_cells(item)
            if cells is None:
                continue
            key = item.runtime_id
            if key is None:
                key = -anonymous_index - 1
                anonymous_index += 1
            cells_by_runtime[key] = cells
        if not cells_by_runtime:
            continue
        updates.extend(
            (
                FieldUpdate(
                    path=("bucket", str(quality), "total_cells"),
                    value=sum(cells_by_runtime.values()),
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                ),
                FieldUpdate(
                    path=("bucket", str(quality), "count"),
                    value=len(cells_by_runtime),
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                ),
            )
        )
    return updates


def _public_outline_updates(state: FatbeansStateEvent) -> list[FieldUpdate]:
    updates: list[FieldUpdate] = []
    for info in state.public_infos:
        quality = _PUBLIC_OUTLINE_QUALITY_BY_INFO_ID.get(info.info_id)
        if quality is None or not info.observed_items:
            continue
        observed_qualities = {
            item.quality for item in info.observed_items
            if item.quality is not None
        }
        if observed_qualities and observed_qualities != {quality}:
            continue
        cells_by_runtime: dict[int | None, int] = {}
        anonymous_index = 0
        for item in info.observed_items:
            cells = _observed_item_cells(item)
            if cells is None:
                continue
            key = item.runtime_id
            if key is None:
                key = -anonymous_index - 1
                anonymous_index += 1
            cells_by_runtime[key] = cells
        if not cells_by_runtime:
            continue
        updates.extend(
            (
                FieldUpdate(
                    path=("bucket", str(quality), "total_cells"),
                    value=sum(cells_by_runtime.values()),
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                ),
                FieldUpdate(
                    path=("bucket", str(quality), "count"),
                    value=len(cells_by_runtime),
                    source="packet",
                    confidence="exact",
                    sequence=state.sort_id,
                ),
            )
        )
    return updates


def _public_numeric_updates(state: FatbeansStateEvent) -> list[FieldUpdate]:
    updates: list[FieldUpdate] = []
    for info in state.public_infos:
        path = _PUBLIC_INFO_EXACT_UPDATE_PATHS.get(info.info_id)
        if path is None or isinstance(info.value, bool):
            continue
        try:
            value = int(info.value)
        except (TypeError, ValueError, OverflowError):
            continue
        if value < 0 or float(info.value) != value:
            continue
        updates.append(
            FieldUpdate(
                path=path,
                value=value,
                source="packet",
                confidence="exact",
                sequence=state.sort_id,
            )
        )
    return updates


def _exact_outline_totals(
    items: Sequence[FatbeansObservedItem],
) -> tuple[int, int] | None:
    cells_by_key: dict[int, int] = {}
    anonymous_index = 0
    for item in items:
        cells = _observed_item_cells(item)
        if cells is None:
            return None
        key = item.runtime_id
        if key is None:
            key = -anonymous_index - 1
            anonymous_index += 1
        cells_by_key[key] = cells
    if not cells_by_key:
        return None
    return len(cells_by_key), sum(cells_by_key.values())


def _mirror_quality_runtime_ids(state: FatbeansStateEvent) -> set[int]:
    runtime_ids: set[int] = set()
    for result in state.action_results:
        if result.action_id != 100134:
            continue
        for item in result.observed_items:
            if item.runtime_id is not None and item.quality is not None:
                runtime_ids.add(item.runtime_id)
    return runtime_ids


def _full_mirror_join_outline_items(
    state: FatbeansStateEvent,
) -> Sequence[FatbeansObservedItem]:
    quality_runtime_ids = _mirror_quality_runtime_ids(state)
    if not quality_runtime_ids:
        return ()

    full_items: Sequence[FatbeansObservedItem] = ()
    for reveal in state.skill_reveals:
        if reveal.hero_id != 208 or reveal.skill_id not in (1002082, 1002083, 1002084):
            continue
        outline_runtime_ids = {
            item.runtime_id
            for item in reveal.observed_items
            if item.runtime_id is not None and _observed_item_cells(item) is not None
        }
        if outline_runtime_ids == quality_runtime_ids:
            full_items = reveal.observed_items
    return full_items


def _full_outline_updates(state: FatbeansStateEvent) -> list[FieldUpdate]:
    if state.inventory_items:
        return []

    full_items: Sequence[FatbeansObservedItem] = ()
    for reveal in state.skill_reveals:
        if reveal.hero_id == 208 and reveal.skill_id == 1002085:
            full_items = reveal.observed_items
    for result in state.action_results:
        if result.action_id == 100100:
            full_items = result.observed_items
    mirror_join_items = _full_mirror_join_outline_items(state)
    if mirror_join_items:
        full_items = mirror_join_items

    totals = _exact_outline_totals(full_items)
    if totals is None:
        return []
    count, cells = totals
    return [
        FieldUpdate(
            path=("session", "warehouse_total_cells"),
            value=cells,
            source="packet",
            confidence="exact",
            sequence=state.sort_id,
        ),
        FieldUpdate(
            path=("session", "total_item_count"),
            value=count,
            source="packet",
            confidence="exact",
            sequence=state.sort_id,
        ),
    ]


def _state_grid_items(state: FatbeansStateEvent) -> tuple[GridItemObservation, ...]:
    if state.inventory_items:
        return tuple(
            GridItemObservation(
                cells=item.cells,
                source="packet",
                confidence="exact",
                runtime_id=item.runtime_id,
                item_id=item.item_id,
                quality=item.quality,
                local_index=item.local_index,
            )
            for item in state.inventory_items
        )

    revealed_items: list[GridItemObservation] = []
    seen_runtime_ids: set[int] = set()
    index_by_runtime: dict[int, int] = {}
    metadata_by_runtime: dict[int, FatbeansObservedItem] = {}

    def remember_item_metadata(item: FatbeansObservedItem) -> None:
        if item.runtime_id is None:
            return
        if item.quality is None and item.item_id is None and item.value is None:
            return
        current = metadata_by_runtime.get(item.runtime_id)
        if current is None:
            metadata_by_runtime[item.runtime_id] = item
            return
        metadata_by_runtime[item.runtime_id] = FatbeansObservedItem(
            local_index=current.local_index or item.local_index,
            runtime_id=item.runtime_id,
            item_id=current.item_id or item.item_id,
            quality=current.quality or item.quality,
            value=current.value or item.value,
            shape_code=current.shape_code or item.shape_code,
            cells=current.cells or item.cells,
        )

    for info in state.public_infos:
        for item in info.observed_items:
            remember_item_metadata(item)
    for result in state.action_results:
        for item in result.observed_items:
            remember_item_metadata(item)

    def append_observed_item(
        item: FatbeansObservedItem,
        *,
        category: int | None = None,
    ) -> None:
        cells = _observed_item_cells(item)
        if cells is None:
            return
        if item.runtime_id is not None:
            if item.runtime_id in seen_runtime_ids:
                if category is not None:
                    index = index_by_runtime.get(item.runtime_id)
                    if index is not None and revealed_items[index].category is None:
                        revealed_items[index] = replace(
                            revealed_items[index],
                            category=category,
                        )
                return
            seen_runtime_ids.add(item.runtime_id)
        metadata = (
            metadata_by_runtime.get(item.runtime_id)
            if item.runtime_id is not None
            else None
        )
        revealed_items.append(
            GridItemObservation(
                cells=cells,
                source="packet",
                confidence="exact",
                runtime_id=item.runtime_id,
                item_id=item.item_id or (metadata.item_id if metadata else None),
                quality=item.quality or (metadata.quality if metadata else None),
                shape_key=str(item.shape_code) if item.shape_code else None,
                value=item.value or (metadata.value if metadata else None),
                local_index=item.local_index,
                category=category,
            )
        )
        if item.runtime_id is not None:
            index_by_runtime[item.runtime_id] = len(revealed_items) - 1

    for reveal in state.skill_reveals:
        category = _skill_reveal_category(reveal.skill_id)
        for item in reveal.observed_items:
            append_observed_item(item, category=category)
    for info in state.public_infos:
        for item in info.observed_items:
            append_observed_item(item)
    for result in state.action_results:
        category = _CATEGORY_OUTLINE_ACTIONS.get(result.action_id)
        for item in result.observed_items:
            append_observed_item(item, category=category)
    return tuple(revealed_items)


def live_batches_from_fatbeans_capture(path: str | Path) -> tuple[LiveObservationBatch, ...]:
    """Return live batches for Fatbeans facts with stable current semantics.

    Cross-quality facts, opponent bids, and raw public info remain in
    ``parse_fatbeans_capture`` until the inference schema has explicit fields
    for them.
    """

    events = parse_fatbeans_capture(path)
    return live_batches_from_fatbeans_events(events)


def live_batches_from_fatbeans_capture_payload(
    raw: str | bytes,
) -> tuple[LiveObservationBatch, ...]:
    """Return live batches from an in-memory Fatbeans JSON export."""
    events = parse_fatbeans_capture_payload(raw)
    return live_batches_from_fatbeans_events(events)


def live_batches_from_fatbeans_events(
    events: FatbeansCaptureEvents,
) -> tuple[LiveObservationBatch, ...]:
    """Return live batches from already parsed Fatbeans events."""
    batches: list[LiveObservationBatch] = []
    for state in events.states:
        updates = [
            *_state_updates(state),
            *_public_numeric_updates(state),
            *_public_outline_updates(state),
            *_aisha_skill_updates(state),
            *_full_outline_updates(state),
            *_inventory_updates(state),
        ]
        grid_items = _state_grid_items(state)
        if not updates and not grid_items:
            continue
        batches.append(
            LiveObservationBatch(
                source="packet",
                event_kind=_event_kind_for_state(state),  # type: ignore[arg-type]
                phase=(
                    "settled"
                    if state.message_id == 0x002D or state.inventory_items
                    else "reading" if state.message_id == 0x0021 else "bidding"
                ),
                field_updates=tuple(updates),
                grid_items=grid_items,
                sequence=state.sort_id,
            )
        )
    return tuple(batches)


def latest_player_bids(states: Iterable[FatbeansStateEvent]) -> dict[str, int]:
    out: dict[str, int] = {}
    for state in states:
        for bid in state.bids:
            if bid.current_value is not None:
                out[bid.name] = bid.current_value
    return out


__all__ = (
    "FatbeansActionResult",
    "FatbeansCaptureEvents",
    "FatbeansFrame",
    "FatbeansInventoryItem",
    "FatbeansObservedItem",
    "FatbeansPacket",
    "FatbeansPlayerBid",
    "FatbeansPublicInfo",
    "FatbeansSendEvent",
    "FatbeansSkillReveal",
    "FatbeansStateEvent",
    "FatbeansStatusEvent",
    "hero_mode_from_state",
    "latest_player_bids",
    "live_batches_from_fatbeans_capture",
    "live_batches_from_fatbeans_capture_payload",
    "live_batches_from_fatbeans_events",
    "load_fatbeans_packets",
    "load_fatbeans_packets_from_payload",
    "load_fatbeans_packets_from_rows",
    "parse_fatbeans_capture",
    "parse_fatbeans_capture_payload",
    "parse_fatbeans_packets",
    "reconstruct_fatbeans_frames",
)
