"""Summarize v3 evidence registry coverage for Fatbeans captures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.inference.v3.coverage import audit_fatbeans_paths  # noqa: E402


def _default_paths() -> tuple[Path, ...]:
    root = ROOT / "data" / "samples" / "fatbeans"
    return (root,) if root.exists() else ()


def _format_counter(counter: dict[str, int]) -> str:
    if not counter:
        return "none"
    return ";".join(f"{key}:{value}" for key, value in sorted(counter.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize v3 evidence registry coverage.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--fail-on-gaps",
        action="store_true",
        help="Exit non-zero when unknown/pending evidence ids are present.",
    )
    parser.add_argument(
        "--fail-on-parse-errors",
        action="store_true",
        help="Exit non-zero when any capture cannot be parsed.",
    )
    args = parser.parse_args(argv)

    report = audit_fatbeans_paths(args.paths or _default_paths())
    payload = report.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            " ".join(
                (
                    f"files={payload['files']}",
                    f"parsed_files={payload['parsed_files']}",
                    f"parse_errors={len(payload['parse_errors'])}",
                    f"events={payload['events']}",
                    f"coverage_ok={payload['coverage_ok']}",
                    f"ok={payload['ok']}",
                )
            )
        )
        print("by_kind=" + _format_counter(payload["by_kind"]))
        print("by_strength=" + _format_counter(payload["by_strength"]))
        print("unknown=" + _format_counter(payload["unknown"]))
        print("pending=" + _format_counter(payload["pending"]))
        if payload["parse_errors"]:
            examples = ";".join(
                f"{item['file']}:{item['error']}"
                for item in payload["parse_errors"][:5]
            )
            print("parse_error_examples=" + examples)
    if args.fail_on_gaps and not report.coverage_ok:
        return 1
    if args.fail_on_parse_errors and not report.parse_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
