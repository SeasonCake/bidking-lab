"""Inspect one offline packet/protohub JSON fixture through the live adapter.

Usage:
    python scripts/inspect_packet_fixture.py data/samples/packet_fixture.example.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.live import (
    LiveSessionState,
    apply_observation_batch,
    live_batch_from_packet_fixture,
    live_state_to_session_obs,
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/inspect_packet_fixture.py <fixture.json>")
        return 2
    path = Path(sys.argv[1])
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("fixture root must be a JSON object")

    batch = live_batch_from_packet_fixture(payload)
    state = apply_observation_batch(LiveSessionState(), batch)
    session = live_state_to_session_obs(state)

    print(f"source={batch.source} event={batch.event_kind} phase={batch.phase}")
    print(
        f"updates={len(batch.field_updates)} grid_items={len(batch.grid_items)} "
        f"dirty={state.dirty}"
    )
    for update in batch.field_updates:
        print(f"  {'.'.join(update.path)} = {update.value!r}")
    for index, item in enumerate(batch.grid_items, start=1):
        print(
            f"  grid[{index}] cells={item.cells} quality={item.quality} "
            f"shape={item.shape_key!r} item_id={item.item_id} value={item.value}"
        )
    if session is None:
        print("SessionObs unavailable: map_id and hero are required.")
        return 0
    print(
        "session: map=%s hero=%s warehouse=%s approx=%s tolerance=%s items=%s"
        % (
            session.map_id,
            session.hero,
            session.warehouse_total_cells,
            session.warehouse_total_cells_approx,
            session.warehouse_total_cells_tolerance,
            session.total_item_count,
        )
    )
    print(f"pruning_upper_bound={session.warehouse_capacity_upper_bound()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
