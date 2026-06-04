import importlib.util
from pathlib import Path
from types import SimpleNamespace

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropEntry, DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.live.fatbeans import FatbeansCaptureEvents

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "evaluate_fatbeans_v3_samples.py"
    spec = importlib.util.spec_from_file_location("evaluate_fatbeans_v3_samples", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _item(
    item_id: int,
    *,
    quality: int,
    value: int,
    shape: tuple[int, int],
) -> Item:
    width, height = shape
    return Item(
        item_id=item_id,
        name=f"item_{item_id}",
        description="",
        name_key=f"item_{item_id}",
        desc_key=f"item_{item_id}_desc",
        quality=quality,
        quality_color="",
        value=value,
        shape_w=width,
        shape_h=height,
        tags=[],
        allowed_shelves=[],
        icon_name="",
        model_name="",
        raw_row=[],
    )


def _tables() -> SimpleNamespace:
    filler = _item(1011001, quality=1, value=1_000, shape=(1, 1))
    red = _item(1086001, quality=6, value=200_000, shape=(4, 4))
    return SimpleNamespace(
        maps={
            2401: BidMap(
                map_id=2401,
                name="test_map",
                description="",
                category=101,
                auction_mode="open",
                sub_pool_weights=[],
                rounds_total=5,
                entry_fee_silver=0,
                starting_budget_silver=100_000,
                drop_pool_id=9001,
                items_per_session_min=2,
                items_per_session_max=2,
                value_tier_ui="",
                mode_flag=4,
                bid_price_ladder=[],
                raw_row=[],
            ),
        },
        drops={
            9001: DropPool(
                pool_id=9001,
                name="pool",
                description="",
                pool_type=2,
                entries=[
                    DropEntry(
                        category=101,
                        item_id=filler.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                    DropEntry(
                        category=108,
                        item_id=red.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                ],
            ),
        },
        items={filler.item_id: filler, red.item_id: red},
    )


def test_v3_prebid_rows_compile_ready_constraints() -> None:
    module = _load_module()
    state = SimpleNamespace(
        sort_id=5,
        session_id="2401:abc",
        round_index=1,
        map_id=2401,
        public_infos=(
            SimpleNamespace(
                info_id=200009,
                value=98,
                value_field=14,
                observed_items=(),
            ),
        ),
        action_results=(),
        skill_reveals=(),
        inventory_items=(),
    )
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(SimpleNamespace(sort_id=10, kind="bid", session_id="2401:abc", value=1000),),
        states=(state,),
        statuses=(),
    )

    rows = module._round_rows_for_events(Path("sample.json"), events)

    assert len(rows) == 1
    assert rows[0]["status"] == "ready"
    assert rows[0]["numeric_constraints"] == 1
    assert rows[0]["constraint_ok"] is True


def test_v3_prebid_rows_include_prior_and_truth_shadow_fields() -> None:
    module = _load_module()
    prebid_state = SimpleNamespace(
        sort_id=5,
        session_id="2401:abc",
        round_index=1,
        map_id=2401,
        public_infos=(),
        action_results=(),
        skill_reveals=(),
        inventory_items=(),
    )
    settlement_state = SimpleNamespace(
        sort_id=20,
        session_id="2401:abc",
        round_index=5,
        map_id=2401,
        public_infos=(),
        action_results=(),
        skill_reveals=(),
        inventory_items=(
            SimpleNamespace(item_id=1011001, quality=1, cells=1),
            SimpleNamespace(item_id=1086001, quality=6, cells=16),
        ),
    )
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(SimpleNamespace(sort_id=10, kind="bid", session_id="2401:abc", value=1000),),
        states=(prebid_state, settlement_state),
        statuses=(),
    )

    rows = module._round_rows_for_events(Path("sample.json"), events, tables=_tables())

    assert len(rows) == 1
    assert rows[0]["v3_prior_available"] is True
    assert rows[0]["v3_prior_expected_value"] == 201_000
    assert rows[0]["v3_prior_q6_session_probability"] == 0.75
    assert rows[0]["v3_truth_available"] is True
    assert rows[0]["v3_truth_raw_total_value"] == 201_000
    assert rows[0]["v3_truth_q6_raw_value"] == 200_000
    assert rows[0]["v3_truth_decision_available"] is True
    assert rows[0]["v3_truth_formal_decision_value"] == 201_000
    assert rows[0]["v3_truth_tail_replacement_decision_value"] == 201_000


def test_v3_prebid_rows_separate_no_state_windows() -> None:
    module = _load_module()
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(SimpleNamespace(sort_id=10, kind="bid", session_id="2401:abc", value=1000),),
        states=(),
        statuses=(),
    )

    rows = module._round_rows_for_events(Path("sample.json"), events)

    assert len(rows) == 1
    assert rows[0]["status"] == "no_state"
    assert rows[0]["numeric_constraints"] == 0
    assert rows[0]["constraint_ok"] is False
