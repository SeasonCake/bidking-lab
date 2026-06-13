"""Smoke-check band layout mode vs off on fixed gate samples (local audit only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ahmad_ref_engine import run_reference_engine  # noqa: E402
from tests.test_ahmad_ref_engine_public_info import (  # noqa: E402
    AISHA_0052_SAMPLE,
    AISHA_BATCH_B_BAND_SAMPLES,
    _aisha_fatbeans_snapshot,
)


def _hit(cells: int, grid_range: tuple) -> bool:
    low, _mid, high = grid_range
    if low is None or high is None:
        return False
    return int(low) <= int(cells) <= int(high)


def main() -> None:
    gate_paths: list[tuple[Path, int | None]] = [
        (path, cells) for path, cells in AISHA_BATCH_B_BAND_SAMPLES
    ]
    gate173 = (
        ROOT / "data/samples/fatbeans/fatbeans_valid_aisha_2505_5rounds_2505_1295018595274342_0173.json"
    )
    if gate173.is_file():
        gate_paths.append((gate173, None))

    worsened: list[str] = []
    improved: list[str] = []
    for path, truth in gate_paths:
        snap = _aisha_fatbeans_snapshot(path)
        off = run_reference_engine({**snap, "audit_aisha_layout_mode": "off"}, max_combos=50_000).as_dict()
        band = run_reference_engine({**snap, "audit_aisha_layout_mode": "band"}, max_combos=50_000).as_dict()
        off_range = off["total_grid_range"]
        band_range = band["total_grid_range"]
        if truth is None:
            continue
        o_hit = _hit(int(truth), off_range)
        b_hit = _hit(int(truth), band_range)
        label = path.name
        if o_hit and not b_hit:
            worsened.append(f"{label} truth={truth} off={off_range} band={band_range}")
        elif not o_hit and b_hit:
            improved.append(f"{label} truth={truth} off={off_range} band={band_range}")

    print("Aisha band gate smoke (7-band + 173 with known truth)")
    print(f"worsened vs off: {len(worsened)}")
    for line in worsened:
        print(f"  - {line}")
    print(f"improved vs off: {len(improved)}")
    for line in improved:
        print(f"  + {line}")

    snap = _aisha_fatbeans_snapshot(AISHA_0052_SAMPLE, round_count=3)
    for mode in ("off", "band"):
        result = run_reference_engine({**snap, "audit_aisha_layout_mode": mode}, max_combos=50_000).as_dict()
        print(
            f"0052 bridge {mode}: status={result['status']} "
            f"range={result['total_grid_range']} combos={result['combo_count']}"
        )


if __name__ == "__main__":
    main()
