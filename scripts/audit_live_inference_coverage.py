"""Audit Fatbeans live facts against current inference coverage.

This script is deliberately diagnostic. It scans Fatbeans sample/live raw JSON
captures and classifies observed action/public/skill facts as hard-modeled,
item-evidence modeled, soft/diagnostic, or pending.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bidking_lab.inference import v2
from bidking_lab.live.fatbeans import (
    _ACTION_AVG_CELLS,
    _ACTION_SESSION_FIELDS,
    _ACTION_SIZE_AVG_VALUE,
    _ACTION_TOTAL_CELLS,
    _ACTION_VALUE_SUM,
    _CATEGORY_OUTLINE_ACTIONS,
    _SKILL_REVEAL_CATEGORIES,
    _aisha_skill_quality,
    parse_fatbeans_capture,
)
from bidking_lab.live.monitor import load_monitor_tables


ROOT = Path(__file__).resolve().parents[1]
QUALITY_SAMPLE_ACTIONS = {100135, 100136, 100137, 100138, 100139, 100140}
PENDING_NUMERIC_ACTIONS: dict[int, str] = {}
PUBLIC_GLOBAL_ITEM_CONSTRAINTS = {200048, 200050}


@dataclass
class CoverageCounts:
    count: Counter[int] = field(default_factory=Counter)
    numeric: Counter[int] = field(default_factory=Counter)
    items: Counter[int] = field(default_factory=Counter)
    files: dict[int, set[str]] = field(default_factory=lambda: defaultdict(set))

    def add(
        self,
        key: int,
        *,
        file_name: str,
        numeric: bool = False,
        item_count: int = 0,
    ) -> None:
        self.count[key] += 1
        if numeric:
            self.numeric[key] += 1
        self.items[key] += item_count
        self.files[key].add(file_name)


def _default_paths() -> tuple[Path, ...]:
    roots = (
        ROOT / "data" / "samples" / "fatbeans",
        ROOT / "data" / "logs" / "live" / "raw",
    )
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(root.rglob("*.json"))
    return tuple(sorted(set(paths)))


def _iter_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(path.rglob("*.json"))
        elif path.exists():
            expanded.append(path)
    return tuple(sorted(set(expanded)))


def _action_status(action_id: int, counts: CoverageCounts) -> str:
    if action_id in _ACTION_SESSION_FIELDS:
        return f"hard_session_field:{'.'.join(_ACTION_SESSION_FIELDS[action_id])}"
    if action_id in _ACTION_TOTAL_CELLS:
        return f"hard_bucket_total_cells:q{_ACTION_TOTAL_CELLS[action_id]}"
    if action_id in _ACTION_VALUE_SUM:
        return f"hard_bucket_value_sum:q{_ACTION_VALUE_SUM[action_id]}"
    if action_id in _ACTION_AVG_CELLS:
        return f"hard_bucket_avg_cells:q{_ACTION_AVG_CELLS[action_id]}"
    if action_id in _ACTION_SIZE_AVG_VALUE:
        return f"soft_size_avg_value:{_ACTION_SIZE_AVG_VALUE[action_id]}cell"
    if action_id == 100100:
        return "hard_full_outline_session_total"
    if action_id in _CATEGORY_OUTLINE_ACTIONS:
        return f"item_evidence_category:{_CATEGORY_OUTLINE_ACTIONS[action_id]}"
    if action_id in PENDING_NUMERIC_ACTIONS:
        return PENDING_NUMERIC_ACTIONS[action_id]
    if counts.items[action_id]:
        if action_id in QUALITY_SAMPLE_ACTIONS:
            return "item_evidence_quality_only_not_quality_sample_constraint"
        if action_id == 100134:
            return "item_evidence_mirror_quality_join"
        return "item_evidence_generic"
    if counts.numeric[action_id]:
        return "UNMODELED_NUMERIC"
    return "observed_no_payload"


def _public_status(info_id: int, counts: CoverageCounts) -> str:
    if info_id == 200001:
        return "hard_q4_outline_bucket_total_count"
    if info_id in PUBLIC_GLOBAL_ITEM_CONSTRAINTS:
        return "hard_global_constraint_from_item_evidence"
    if info_id in v2._PUBLIC_AVG_VALUE_QUALITY:
        return f"soft_public_avg_value:q{v2._PUBLIC_AVG_VALUE_QUALITY[info_id]}"
    if info_id in v2._PUBLIC_AVG_CELLS_QUALITY:
        return f"soft_public_avg_cells:q{v2._PUBLIC_AVG_CELLS_QUALITY[info_id]}"
    if info_id in v2._PUBLIC_TOTAL_AVG_CELLS_IDS:
        return "soft_public_total_avg_cells"
    if info_id in v2._PUBLIC_RANDOM_SAMPLE_AVG_VALUE_COUNT:
        return (
            "diagnostic_random_sample_avg_value:"
            f"n{v2._PUBLIC_RANDOM_SAMPLE_AVG_VALUE_COUNT[info_id]}"
        )
    if counts.items[info_id]:
        return "item_evidence_generic"
    return "PENDING_OR_UNKNOWN_FACT"


def _skill_status(skill_id: int, counts: CoverageCounts) -> str:
    quality = _aisha_skill_quality(skill_id)
    if quality is not None:
        return f"hard_aisha_outline:q{quality}"
    if skill_id in _SKILL_REVEAL_CATEGORIES:
        return f"item_evidence_category:{_SKILL_REVEAL_CATEGORIES[skill_id]}"
    if skill_id in {1002082, 1002083, 1002084, 1002085}:
        return "ethan_outline_full_or_mirror_join"
    if counts.items[skill_id]:
        return "item_evidence_generic"
    return "observed_no_payload"


def _item_names() -> dict[int, str]:
    try:
        return {
            item_id: item.name
            for item_id, item in load_monitor_tables().items.items()
        }
    except Exception:
        return {}


def _format_rows(
    title: str,
    counts: CoverageCounts,
    status_fn: Any,
    *,
    item_names: dict[int, str] | None = None,
) -> list[str]:
    rows = [title, "id,name,count,numeric,items,files,status"]
    names = item_names or {}
    for key in sorted(counts.count):
        rows.append(
            ",".join(
                (
                    str(key),
                    names.get(key, ""),
                    str(counts.count[key]),
                    str(counts.numeric[key]),
                    str(counts.items[key]),
                    str(len(counts.files[key])),
                    status_fn(key, counts),
                )
            )
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit current Fatbeans live fact coverage in inference.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans and data/logs/live/raw.",
    )
    args = parser.parse_args()

    paths = _iter_paths(args.paths) if args.paths else _default_paths()
    actions = CoverageCounts()
    publics = CoverageCounts()
    skills = CoverageCounts()
    parse_errors: list[tuple[str, str]] = []
    parsed_files = 0

    for path in paths:
        try:
            events = parse_fatbeans_capture(path)
        except Exception as exc:
            parse_errors.append((str(path), type(exc).__name__))
            continue
        if not events.states:
            continue
        parsed_files += 1
        for state in events.states:
            for result in state.action_results:
                actions.add(
                    int(result.action_id),
                    file_name=path.name,
                    numeric=result.result is not None,
                    item_count=len(result.observed_items or ()),
                )
            for info in state.public_infos:
                publics.add(
                    int(info.info_id),
                    file_name=path.name,
                    numeric=info.value is not None,
                    item_count=len(info.observed_items or ()),
                )
            for reveal in state.skill_reveals:
                skills.add(
                    int(reveal.skill_id),
                    file_name=path.name,
                    item_count=len(reveal.observed_items or ()),
                )

    names = _item_names()
    print(
        f"scanned_files={len(paths)} parsed_files={parsed_files} "
        f"parse_errors={len(parse_errors)}"
    )
    if parse_errors:
        print("parse_error_examples=" + ";".join(f"{p}:{e}" for p, e in parse_errors[:5]))
    print()
    print("\n".join(_format_rows("ACTIONS", actions, _action_status, item_names=names)))
    print()
    print("\n".join(_format_rows("PUBLIC_INFOS", publics, _public_status)))
    print()
    print("\n".join(_format_rows("SKILLS", skills, _skill_status, item_names=names)))

    unmodeled_numeric = [
        action_id
        for action_id in sorted(actions.count)
        if _action_status(action_id, actions) == "UNMODELED_NUMERIC"
    ]
    pending_numeric = [
        action_id
        for action_id in sorted(actions.count)
        if _action_status(action_id, actions).startswith("pending_")
    ]
    pending_public = [
        info_id
        for info_id in sorted(publics.count)
        if _public_status(info_id, publics) == "PENDING_OR_UNKNOWN_FACT"
    ]
    quality_sample = [
        action_id
        for action_id in sorted(actions.count)
        if "not_quality_sample_constraint" in _action_status(action_id, actions)
    ]
    print()
    print(f"UNMODELED_NUMERIC_ACTIONS={unmodeled_numeric}")
    print(f"PENDING_NUMERIC_ACTIONS={pending_numeric}")
    print(f"PENDING_PUBLIC_FACTS={pending_public}")
    print(f"QUALITY_SAMPLE_ACTIONS_NOT_HARD_CONSTRAINT={quality_sample}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
