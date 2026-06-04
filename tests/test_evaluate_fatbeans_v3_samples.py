import importlib.util
from pathlib import Path
from types import SimpleNamespace

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
