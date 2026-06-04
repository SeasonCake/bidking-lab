"""Summarize v3 hard constraint compiler output for Fatbeans captures."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.inference.v3 import (  # noqa: E402
    compile_hard_constraints,
    events_from_fatbeans,
)
from bidking_lab.live.fatbeans import parse_fatbeans_capture  # noqa: E402


def _default_paths() -> tuple[Path, ...]:
    root = ROOT / "data" / "samples" / "fatbeans"
    return (root,) if root.exists() else ()


def _iter_paths(paths: list[Path]) -> tuple[Path, ...]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(path.rglob("*.json"))
        elif path.exists():
            expanded.append(path)
    return tuple(sorted(set(expanded)))


def summarize_paths(paths: list[Path]) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    parse_errors: list[dict[str, str]] = []
    conflict_examples: list[dict[str, Any]] = []
    files_with_conflicts = 0

    expanded = _iter_paths(paths)
    for path in expanded:
        totals["files"] += 1
        try:
            events = parse_fatbeans_capture(path)
            constraints = compile_hard_constraints(events_from_fatbeans(events))
        except Exception as exc:
            parse_errors.append({"file": str(path), "error": type(exc).__name__})
            continue
        totals["parsed_files"] += 1
        totals["numeric"] += len(constraints.numeric)
        totals["item_anchors"] += len(constraints.item_anchors)
        totals["shape_anchors"] += len(constraints.shape_anchors)
        totals["quality_floor_anchors"] += len(constraints.quality_floor_anchors)
        totals["conflicts"] += len(constraints.conflicts)
        if constraints.conflicts:
            files_with_conflicts += 1
            for conflict in constraints.conflicts[:3]:
                if len(conflict_examples) >= 10:
                    break
                conflict_examples.append(
                    {
                        "file": str(path),
                        "target": conflict.target,
                        "first": {
                            "value": conflict.first.value,
                            "event_id": conflict.first.event_id,
                        },
                        "second": {
                            "value": conflict.second.value,
                            "event_id": conflict.second.event_id,
                        },
                    }
                )

    return {
        "files": totals["files"],
        "parsed_files": totals["parsed_files"],
        "parse_errors": parse_errors,
        "numeric": totals["numeric"],
        "item_anchors": totals["item_anchors"],
        "shape_anchors": totals["shape_anchors"],
        "quality_floor_anchors": totals["quality_floor_anchors"],
        "conflicts": totals["conflicts"],
        "files_with_conflicts": files_with_conflicts,
        "conflict_examples": conflict_examples,
        "constraint_ok": totals["conflicts"] == 0,
        "parse_ok": not parse_errors,
        "ok": totals["conflicts"] == 0 and not parse_errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize v3 hard constraint compiler output.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--fail-on-conflicts",
        action="store_true",
        help="Exit non-zero when hard constraint conflicts are present.",
    )
    parser.add_argument(
        "--fail-on-parse-errors",
        action="store_true",
        help="Exit non-zero when any capture cannot be parsed.",
    )
    args = parser.parse_args(argv)

    summary = summarize_paths(args.paths or list(_default_paths()))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            " ".join(
                (
                    f"files={summary['files']}",
                    f"parsed_files={summary['parsed_files']}",
                    f"parse_errors={len(summary['parse_errors'])}",
                    f"numeric={summary['numeric']}",
                    f"item_anchors={summary['item_anchors']}",
                    f"shape_anchors={summary['shape_anchors']}",
                    f"quality_floor_anchors={summary['quality_floor_anchors']}",
                    f"conflicts={summary['conflicts']}",
                    f"constraint_ok={summary['constraint_ok']}",
                    f"ok={summary['ok']}",
                )
            )
        )
        if summary["parse_errors"]:
            examples = ";".join(
                f"{item['file']}:{item['error']}"
                for item in summary["parse_errors"][:5]
            )
            print("parse_error_examples=" + examples)
        if summary["conflict_examples"]:
            print("conflict_examples=" + json.dumps(summary["conflict_examples"], ensure_ascii=False))
    if args.fail_on_conflicts and not summary["constraint_ok"]:
        return 1
    if args.fail_on_parse_errors and not summary["parse_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
