import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_settlement_payload_audit.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_settlement_payload_audit",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def _item(runtime_id: int, item_id: int, *, quality: int = 4, cells: int = 2) -> bytes:
    return b"".join(
        (
            _field_varint(1, runtime_id),
            _field_varint(2, item_id),
            *(_field_bytes(4, b"\x08\x01") for _ in range(cells)),
            _field_varint(9, quality),
        )
    )


def test_inventory_block_metrics_counts_slots_candidates_and_duplicates() -> None:
    module = _load_module()
    item = _item(101, 1001001, cells=2)
    occupied_slot = b"".join(
        (
            _field_varint(1, 7),
            _field_bytes(2, b"\x08\x01"),
            _field_bytes(3, item),
        )
    )
    duplicate_slot = _field_bytes(3, item)
    empty_slot = _field_bytes(2, b"\x10\x01")
    block = b"".join(
        (
            _field_varint(1, 1),
            _field_bytes(3, occupied_slot),
            _field_bytes(3, duplicate_slot),
            _field_bytes(3, empty_slot),
        )
    )

    result = module._inventory_block_metrics(block)

    assert result["inventory_slot_count"] == 3
    assert result["occupied_slot_count"] == 2
    assert result["raw_item_candidate_count"] == 2
    assert result["raw_duplicate_runtime_item_pair_count"] == 1
    assert result["item_field_signatures"]
