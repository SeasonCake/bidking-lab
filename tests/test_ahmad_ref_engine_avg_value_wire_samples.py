from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
FATBEANS_SAMPLE_DIR = ROOT / "data" / "samples" / "fatbeans"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))

from ahmad_ref_engine import (  # noqa: E402
    _ref_normalize_avg_value_wire,
    extract_evidence,
    run_reference_engine,
)
from test_ahmad_ref_engine_public_info import (  # noqa: E402
    _ahmed_fatbeans_snapshot,
    _aisha_fatbeans_snapshot,
    _snapshot,
)

PUBLIC_AVG_INFO_IDS = {200036: "q4", 200037: "q5"}
HERO_FROM_SAMPLE_PREFIX = {
    "aisha": "aisha",
    "ahmed": "ahmed",
    "ethan": "ethan",
    "isabella": "isabella",
    "gabriela": "gabriela",
    "maria": "maria",
    "victor": "victor",
    "mixed": "aisha",
}

# Known acceptable non-ok statuses on fractional wire samples (other locks / missing total).
ACCEPTABLE_FRACTIONAL_FAILURES = {
    (
        "fatbeans_valid_aisha_2601_4rounds_2601_1295018741324567_0222.json",
        "q5",
        40343.30859375,
    ): "no_reachable_combo",
    (
        "fatbeans_valid_ethan_2410_3rounds_2410_1295018605936393_0287.json",
        "q4",
        10348.8330078125,
    ): "missing_total_count",
}


@dataclass(frozen=True)
class FractionalPublicAvgCase:
    sample_name: str
    tier: str
    raw_value: float
    sort_id: int

    @property
    def id(self) -> str:
        return f"{self.sample_name[:36]}:{self.tier}:{self.raw_value:g}"


def _hero_from_sample_name(name: str) -> str:
    for prefix, hero in HERO_FROM_SAMPLE_PREFIX.items():
        if f"_{prefix}_" in name:
            return hero
    return "ahmed"


def _build_fatbeans_snapshot(sample_path: Path, *, sort_id: int, hero: str) -> dict:
    from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture
    from bidking_lab.live.monitor import (
        _ahmad_ref_inputs_from_batches,
        _public_info_rows,
        _skill_reveal_rows,
    )

    events = parse_fatbeans_capture(sample_path)
    prefix_events = type(events)(
        packets=tuple(row for row in events.packets if int(row.sort_id) <= sort_id),
        frames=tuple(row for row in events.frames if int(row.sort_id) <= sort_id),
        sends=tuple(row for row in events.sends if int(row.sort_id) <= sort_id),
        states=tuple(row for row in events.states if int(row.sort_id) <= sort_id),
        statuses=tuple(row for row in events.statuses if int(row.sort_id) <= sort_id),
    )
    batches = [
        batch
        for batch in live_batches_from_fatbeans_events(events)
        if batch.phase != "settled" and batch.sequence is not None and int(batch.sequence) <= sort_id
    ]
    return {
        "ui_contract": {
            "context": {"hero": hero, "phase": "bidding"},
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": _ahmad_ref_inputs_from_batches(batches, hero=hero) or {},
        "public_info_rows": _public_info_rows(prefix_events, {}),
        "skill_reveals": _skill_reveal_rows(prefix_events, {}),
        "skill_reveal_rows": _skill_reveal_rows(prefix_events, {}),
        "action_result_rows": [],
    }


def _is_wire_float_public_avg(raw: float) -> bool:
    normalized = _ref_normalize_avg_value_wire(raw)
    if normalized is None:
        return False
    return abs(float(normalized) - float(raw)) > 1e-9


def _snapshot_with_public_avg(
    snapshot: dict,
    *,
    tier: str,
    raw_value: float,
) -> dict:
    working = dict(snapshot)
    ui_contract = dict(working.get("ui_contract") or {})
    context = dict(ui_contract.get("context") or {})
    constraints = dict(ui_contract.get("constraints") or {})
    quality = {"q4": 4, "q5": 5}[tier]
    constraints["public_info"] = {
        "public_avg_values": [
            {
                "semantic": f"{tier}_avg_value",
                "kind": "avg_value",
                "quality": quality,
                "value": raw_value,
            }
        ]
    }
    ui_contract["context"] = context
    ui_contract["constraints"] = constraints
    working["ui_contract"] = ui_contract
    return working


@lru_cache(maxsize=1)
def _collect_fractional_public_avg_cases() -> tuple[FractionalPublicAvgCase, ...]:
    from bidking_lab.live.fatbeans import parse_fatbeans_capture
    from bidking_lab.live.monitor import _public_info_rows

    cases: list[FractionalPublicAvgCase] = []
    seen: set[tuple[str, str, float]] = set()
    for path in sorted(FATBEANS_SAMPLE_DIR.glob("*.json")):
        try:
            events = parse_fatbeans_capture(path)
            rows = _public_info_rows(events, {})
        except Exception:
            continue
        for row in rows:
            info_id = row.get("info_id")
            if info_id not in PUBLIC_AVG_INFO_IDS:
                continue
            value = row.get("value")
            if value is None:
                continue
            raw = float(value)
            if abs(raw - round(raw)) <= 1e-9:
                continue
            tier = PUBLIC_AVG_INFO_IDS[int(info_id)]
            key = (path.name, tier, raw)
            if key in seen:
                continue
            seen.add(key)
            cases.append(
                FractionalPublicAvgCase(
                    sample_name=path.name,
                    tier=tier,
                    raw_value=raw,
                    sort_id=int(row.get("sort") or 0),
                )
            )
    return tuple(cases)


FRACTIONAL_PUBLIC_AVG_CASES = _collect_fractional_public_avg_cases()

P0_WIRE_CURATED = [
    c
    for c in FRACTIONAL_PUBLIC_AVG_CASES
    if c.sample_name
    in {
        "fatbeans_valid_aisha_2402_3rounds_2402_1367586310602652_0052.json",
        "fatbeans_valid_ahmed_2402_4rounds_2402_1425860532062933_0088.json",
        "fatbeans_valid_ahmed_4405_4rounds_4405_1425860535995398_0161.json",
        "fatbeans_valid_aisha_2501_5rounds_2501_1295018576737646_0133.json",
    }
]


def test_fractional_public_avg_catalog_non_empty() -> None:
    assert len(FRACTIONAL_PUBLIC_AVG_CASES) >= 50


@pytest.mark.parametrize("case", P0_WIRE_CURATED, ids=lambda case: case.id)
def test_ref_engine_curated_wire_public_avg_reachable(case: FractionalPublicAvgCase) -> None:
    path = FATBEANS_SAMPLE_DIR / case.sample_name
    hero = _hero_from_sample_name(case.sample_name)
    snapshot = _build_fatbeans_snapshot(path, sort_id=case.sort_id, hero=hero)
    snapshot = _snapshot_with_public_avg(snapshot, tier=case.tier, raw_value=case.raw_value)

    evidence = extract_evidence(snapshot)
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()

    assert f"public_{case.tier}_avg_value_wire_normalized" in evidence.source_notes
    assert "public_quality_avg_value_conflict_fallback" not in result["notes"]
    assert result["status"] in {"ok", "count_prior"}
    assert result["combo_count"] > 0
    stored = result["evidence"]["avg_values"].get(case.tier)
    assert stored is not None
    assert stored == _ref_normalize_avg_value_wire(case.raw_value)


def test_ref_engine_all_fractional_public_avg_wire_batch_audit() -> None:
    failures: list[str] = []
    unexpected_fallbacks: list[str] = []

    for case in FRACTIONAL_PUBLIC_AVG_CASES:
        path = FATBEANS_SAMPLE_DIR / case.sample_name
        hero = _hero_from_sample_name(case.sample_name)
        snapshot = _build_fatbeans_snapshot(path, sort_id=case.sort_id, hero=hero)
        snapshot = _snapshot_with_public_avg(snapshot, tier=case.tier, raw_value=case.raw_value)

        evidence = extract_evidence(snapshot)
        result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
        notes = result.get("notes", [])
        status = result["status"]
        combos = result["combo_count"]
        wire_note = f"public_{case.tier}_avg_value_wire_normalized" in evidence.source_notes
        fallback = "public_quality_avg_value_conflict_fallback" in notes

        if fallback and wire_note:
            no_fb = run_reference_engine(
                snapshot, max_combos=50_000, _allow_public_avg_fallback=False
            ).as_dict()
            if (
                no_fb["status"] == "no_reachable_combo"
                and status in {"ok", "count_prior"}
                and combos > 0
            ):
                continue
            unexpected_fallbacks.append(case.id)

        acceptable = ACCEPTABLE_FRACTIONAL_FAILURES.get(
            (case.sample_name, case.tier, case.raw_value)
        )
        if acceptable is not None:
            if status != acceptable:
                failures.append(f"{case.id}: expected {acceptable}, got {status}")
            continue

        if status not in {"ok", "count_prior"} or combos <= 0:
            failures.append(f"{case.id}: status={status} combos={combos}")
            continue

        if _is_wire_float_public_avg(case.raw_value) and not wire_note:
            failures.append(f"{case.id}: missing wire_normalized note for raw={case.raw_value}")

        if not _is_wire_float_public_avg(case.raw_value):
            continue

        stored = result["evidence"]["avg_values"].get(case.tier)
        expected = _ref_normalize_avg_value_wire(case.raw_value)
        if stored != expected:
            failures.append(f"{case.id}: stored avg {stored!r} != normalized {expected!r}")

    assert not unexpected_fallbacks, "wire-normalized avg should not fallback: " + "; ".join(
        unexpected_fallbacks[:5]
    )
    assert not failures, "fractional public avg audit failures:\n" + "\n".join(failures[:12])


@pytest.mark.parametrize(
    ("avg_value", "tier", "hero", "map_id", "structured_ref_inputs", "expected_count"),
    [
        (
            5615.625,
            "q4",
            "ahmed",
            4402,
            {
                "total_count": 10,
                "fixed_counts": {"q1": 0, "q3": 2, "q5": 0, "q6": 0},
            },
            8,
        ),
        (
            34288.75,
            "q5",
            "ahmed",
            4406,
            {
                "total_count": 10,
                "fixed_counts": {"q1": 0, "q3": 3, "q4": 0},
                "count_sums": {"q4q5q6": 7},
            },
            4,
        ),
        (
            1560.125,
            "q5",
            "aisha",
            2404,
            {"total_count": 15},
            8,
        ),
    ],
)
def test_ref_engine_clean_decimal_public_avg_locks_count_precisely(
    avg_value: float,
    tier: str,
    hero: str,
    map_id: int,
    structured_ref_inputs: dict,
    expected_count: int,
) -> None:
    quality = {"q4": 4, "q5": 5}[tier]
    result = run_reference_engine(
        _snapshot(
            hero=hero,
            map_id=map_id,
            structured_ref_inputs=structured_ref_inputs,
            public_info={
                "public_avg_values": [
                    {
                        "semantic": f"{tier}_avg_value",
                        "kind": "avg_value",
                        "quality": quality,
                        "value": avg_value,
                    }
                ]
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] in {"ok", "count_prior"}
    low, mid, high = result["quality_count_ranges"][tier]
    assert low == mid == high == expected_count
    fixed = result["evidence"]["fixed_counts"].get(tier)
    if fixed is not None:
        assert fixed == expected_count
    assert f"public_{tier}_avg_value" in result["notes"]
    assert f"public_{tier}_avg_value_wire_normalized" not in result["notes"]


def test_ref_engine_aisha_0052_wire_q4_avg_preserves_split_bridge() -> None:
    sample = FATBEANS_SAMPLE_DIR / (
        "fatbeans_valid_aisha_2402_3rounds_2402_1367586310602652_0052.json"
    )
    snapshot = _aisha_fatbeans_snapshot(sample, round_count=3)
    snapshot = _snapshot_with_public_avg(
        snapshot,
        tier="q4",
        raw_value=6659.21435546875,
    )
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()

    assert result["status"] == "count_prior"
    assert result["combo_count"] > 0
    assert result["evidence"]["avg_values"] == {"q4": 6659.214}
    assert result["quality_count_ranges"]["q4"] == [3, 6, 9]
    assert result["quality_count_ranges"]["q4"] != [14, 14, 14]
    assert "public_q4_avg_value_wire_normalized" in result["notes"]
    assert "public_quality_avg_value_conflict_fallback" not in result["notes"]


def test_ref_engine_ahmed_2404_fatbeans_q5_avg_locks_from_public_rows() -> None:
    sample = FATBEANS_SAMPLE_DIR / (
        "fatbeans_valid_ahmed_2404_3rounds_2404_1388889386153348_0040.json"
    )
    result = run_reference_engine(_ahmed_fatbeans_snapshot(sample, round_count=3), max_combos=50_000).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["fixed_counts"]["q5"] == 4
    assert result["quality_count_ranges"]["q5"] == [4, 4, 4]
