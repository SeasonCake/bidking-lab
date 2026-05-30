"""Run the Fatbeans live monitor and append model-evaluation logs.

This script is source-agnostic at the inference boundary. Today it can watch
a directory of Fatbeans JSON files, process one file, or read one JSON payload
from stdin. A future true realtime source should feed the same monitor module
and keep the log schema unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any

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


def _fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, dict)
    }


def _save_manifest(path: Path, manifest: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _is_stable_file(path: Path, stable_seconds: float) -> bool:
    if stable_seconds <= 0:
        return path.exists()
    try:
        first = _fingerprint(path)
    except OSError:
        return False
    time.sleep(stable_seconds)
    try:
        second = _fingerprint(path)
    except OSError:
        return False
    return first == second


def _archive_raw_file(path: Path, archive_dir: Path) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = archive_dir / f"{stamp}_{path.name}"
    suffix = 1
    while target.exists():
        target = archive_dir / f"{stamp}_{suffix}_{path.name}"
        suffix += 1
    shutil.copy2(path, target)
    return target


def _process_file(
    path: Path,
    *,
    tables,
    log_dir: Path,
    n_trials: int,
    roi_trials: int,
    seed: int,
    archive_dir: Path | None = None,
) -> None:
    artifact = build_monitor_artifact_from_file(
        path,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        seed=seed,
    )
    if archive_dir is not None:
        archived = _archive_raw_file(path, archive_dir)
        artifact["raw_archive"] = str(archived)
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
    parser.add_argument(
        "--stable-seconds",
        type=float,
        default=1.0,
        help="Require file size/mtime to stay unchanged before processing",
    )
    parser.add_argument("--once", action="store_true", help="Watch existing files once")
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Ignore processed manifest and process matching files again",
    )
    parser.add_argument(
        "--ignore-existing",
        action="store_true",
        help="When watching, mark currently existing JSON files as processed at startup",
    )
    parser.add_argument(
        "--no-archive-raw",
        action="store_true",
        help="Do not copy processed raw JSON files into log-dir/raw",
    )
    parser.add_argument("--n-trials", type=int, default=500, help="MC trials per map")
    parser.add_argument("--roi-trials", type=int, default=250, help="ROI MC trials")
    parser.add_argument("--seed", type=int, default=20260530)
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    archive_dir = None if args.no_archive_raw else log_dir / "raw"
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
            archive_dir=archive_dir,
        )
        return 0

    root = Path(args.watch_dir)
    manifest_path = log_dir / "processed_files.json"
    manifest = _load_manifest(manifest_path)
    if args.ignore_existing and not args.reprocess:
        for path in _json_files(root):
            try:
                fingerprint = _fingerprint(path)
            except OSError:
                continue
            manifest[str(path.resolve())] = {
                **fingerprint,
                "processed_at": time.time(),
                "name": path.name,
                "ignored_at_startup": True,
            }
        _save_manifest(manifest_path, manifest)
    print(f"[watch] {root} -> {log_dir}")
    while True:
        for path in _json_files(root):
            resolved = path.resolve()
            try:
                fingerprint = _fingerprint(path)
            except OSError:
                continue
            manifest_key = str(resolved)
            if (
                not args.reprocess
                and manifest.get(manifest_key, {}).get("size") == fingerprint["size"]
                and manifest.get(manifest_key, {}).get("mtime_ns") == fingerprint["mtime_ns"]
            ):
                continue
            if not _is_stable_file(path, args.stable_seconds):
                continue
            try:
                _process_file(
                    path,
                    tables=tables,
                    log_dir=log_dir,
                    n_trials=args.n_trials,
                    roi_trials=args.roi_trials,
                    seed=args.seed,
                    archive_dir=archive_dir,
                )
                latest = _fingerprint(path)
                manifest[manifest_key] = {
                    **latest,
                    "processed_at": time.time(),
                    "name": path.name,
                }
                _save_manifest(manifest_path, manifest)
            except Exception as exc:  # noqa: BLE001 - long-running monitor boundary
                print(f"[error] {path}: {exc}", file=sys.stderr)
        if args.once:
            return 0
        time.sleep(max(0.2, args.poll))


if __name__ == "__main__":
    raise SystemExit(main())
