"""Run the Fatbeans live monitor and append model-evaluation logs.

This script is source-agnostic at the inference boundary. Today it can watch
a directory of Fatbeans JSON files, process one file, or read one JSON payload
from stdin. A future true realtime source should feed the same monitor module
and keep the log schema unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.live.monitor import (  # noqa: E402
    build_monitor_artifact_from_file,
    build_monitor_artifact_from_payload,
    load_monitor_tables,
    write_monitor_logs,
)


def _json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.glob("*.json"))


def _process_file(
    path: Path,
    *,
    tables,
    log_dir: Path,
    n_trials: int,
    roi_trials: int,
    seed: int,
) -> None:
    artifact = build_monitor_artifact_from_file(
        path,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        seed=seed,
    )
    write_monitor_logs(artifact, log_dir=log_dir)
    print(
        f"[ok] {path.name}: map={artifact.get('map_id')} "
        f"round={artifact.get('round')} value={artifact.get('known_value_sum')}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process or watch Fatbeans JSON captures for live monitor logs.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="Process one Fatbeans JSON file")
    source.add_argument("--watch-dir", help="Poll a directory for new JSON files")
    source.add_argument(
        "--stdin",
        action="store_true",
        help="Read one Fatbeans JSON payload from stdin",
    )
    parser.add_argument(
        "--log-dir",
        default=str(ROOT / "data" / "logs" / "live"),
        help="Directory for latest_snapshot.json and JSONL logs",
    )
    parser.add_argument(
        "--tables-dir",
        default=None,
        help="Override raw game table directory; defaults to data/raw/tables",
    )
    parser.add_argument("--poll", type=float, default=1.0, help="Watch poll seconds")
    parser.add_argument("--once", action="store_true", help="Watch existing files once")
    parser.add_argument("--n-trials", type=int, default=500, help="MC trials per map")
    parser.add_argument("--roi-trials", type=int, default=250, help="ROI MC trials")
    parser.add_argument("--seed", type=int, default=20260530)
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    tables = load_monitor_tables(tables_dir=args.tables_dir)

    if args.stdin:
        payload = sys.stdin.buffer.read()
        artifact = build_monitor_artifact_from_payload(
            payload,
            tables=tables,
            n_trials=args.n_trials,
            roi_trials=args.roi_trials,
            seed=args.seed,
        )
        write_monitor_logs(artifact, log_dir=log_dir)
        print("[ok] stdin payload processed")
        return 0

    if args.file:
        _process_file(
            Path(args.file),
            tables=tables,
            log_dir=log_dir,
            n_trials=args.n_trials,
            roi_trials=args.roi_trials,
            seed=args.seed,
        )
        return 0

    root = Path(args.watch_dir)
    seen: set[Path] = set()
    print(f"[watch] {root} -> {log_dir}")
    while True:
        for path in _json_files(root):
            resolved = path.resolve()
            if resolved in seen:
                continue
            try:
                _process_file(
                    path,
                    tables=tables,
                    log_dir=log_dir,
                    n_trials=args.n_trials,
                    roi_trials=args.roi_trials,
                    seed=args.seed,
                )
                seen.add(resolved)
            except Exception as exc:  # noqa: BLE001 - long-running monitor boundary
                print(f"[error] {path}: {exc}", file=sys.stderr)
        if args.once:
            return 0
        time.sleep(max(0.2, args.poll))


if __name__ == "__main__":
    raise SystemExit(main())
