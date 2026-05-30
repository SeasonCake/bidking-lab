"""Print normalized game events from a FatbeansCreater JSON export."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.live.fatbeans import latest_player_bids, parse_fatbeans_capture


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/inspect_fatbeans_events.py <fatbeans.json>")
        return 2

    events = parse_fatbeans_capture(Path(sys.argv[1]))
    print(f"packets: {len(events.packets)}")
    print(f"frames: {len(events.frames)}")
    print(f"sends: {len(events.sends)}")
    print(f"states: {len(events.states)}")
    print(f"status events: {len(events.statuses)}")
    print()

    print("send timeline:")
    for send in events.sends:
        print(
            f"- sort={send.sort_id} msg=0x{send.message_id:04x} "
            f"{send.kind} session={send.session_id} value={send.value}"
        )
    print()

    print("state timeline:")
    for state in events.states:
        print(
            f"- sort={state.sort_id} msg=0x{state.message_id:04x} "
            f"map={state.map_id} round={state.round_index} "
            f"session={state.session_id}"
        )
        for info in state.public_infos:
            print(
                f"  public info={info.info_id} map={info.map_id} "
                f"field={info.value_field} value={info.value:g}"
            )
            for item in info.observed_items:
                print(
                    f"    public item local={item.local_index} "
                    f"runtime={item.runtime_id} quality={item.quality} "
                    f"shape={item.shape_code}"
                )
        for reveal in state.skill_reveals:
            print(
                f"  skill={reveal.skill_id} hero={reveal.hero_id} "
                f"round={reveal.round_index} items={len(reveal.observed_items)}"
            )
            for item in reveal.observed_items:
                print(
                    f"    skill item local={item.local_index} "
                    f"runtime={item.runtime_id} quality={item.quality} "
                    f"shape={item.shape_code}"
                )
        for result in state.action_results:
            print(
                f"  action={result.action_id} "
                f"field={result.result_field} result={result.result}"
            )
            for item in result.observed_items:
                print(
                    f"    item local={item.local_index} runtime={item.runtime_id} "
                    f"item_id={item.item_id} quality={item.quality} "
                    f"value={item.value} shape={item.shape_code} cells={item.cells}"
                )
        for bid in state.bids:
            print(
                f"  bid player={bid.name} hero={bid.hero_id} "
                f"values={','.join(str(v) for v in bid.values)}"
            )
        if state.inventory_items:
            total_cells = sum(item.cells for item in state.inventory_items)
            print(
                f"  inventory_items={len(state.inventory_items)} "
                f"inventory_cells={total_cells}"
            )
        if state.settlement_loss_units is not None:
            print(f"  settlement_loss_units={state.settlement_loss_units}")
    print()

    print("latest player bids:")
    for name, value in latest_player_bids(events.states).items():
        print(f"- {name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
