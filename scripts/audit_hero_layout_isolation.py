"""Verify Aisha layout modes do not change Ahmed (and other non-Aisha) ref output."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture  # noqa: E402

from ahmad_ref_engine import run_reference_engine  # noqa: E402
from audit_aisha_gap import _build_snapshot, _hero_from_events, _map_id_from_events  # noqa: E402


def _ahmed_snapshot(path: Path) -> dict:
    events = parse_fatbeans_capture(path)
    hero = _hero_from_events(events)
    pre_batches = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
    audit_round = min(max(3, len(pre_batches) - 1), len(pre_batches))
    prefix = pre_batches[:audit_round]
    return _build_snapshot(
        hero=hero,
        events=events,
        prefix_batches=prefix,
        map_id=_map_id_from_events(events),
    )


def main() -> None:
    sample_dir = ROOT / "data/samples/fatbeans"
    paths = sorted(sample_dir.glob("fatbeans*ahmed*.json"))[:12]
    mismatches: list[str] = []
    for path in paths:
        snap = _ahmed_snapshot(path)
        off = run_reference_engine({**snap, "audit_aisha_layout_mode": "off"}, max_combos=50_000).as_dict()
        band = run_reference_engine({**snap, "audit_aisha_layout_mode": "band"}, max_combos=50_000).as_dict()
        keys = ("status", "balanced", "conservative", "aggressive", "total_grid_range", "combo_count")
        for key in keys:
            if off.get(key) != band.get(key):
                mismatches.append(f"{path.name}: {key} off={off.get(key)!r} band={band.get(key)!r}")
                break

    print(f"Ahmed layout isolation (n={len(paths)} samples, off vs band)")
    if mismatches:
        print(f"MISMATCH {len(mismatches)}")
        for line in mismatches:
            print(f"  - {line}")
        raise SystemExit(1)
    print("OK — no output delta on Ahmed samples")


if __name__ == "__main__":
    main()
