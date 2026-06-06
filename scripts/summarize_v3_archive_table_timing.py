"""Summarize raw table metadata against Fatbeans archive capture timing."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_ROOT = ROOT / "data" / "samples" / "fatbeans"
DEFAULT_RAW_ROOT = ROOT / "data" / "raw"
_VERSION_KEY_TOKENS = ("version", "hash", "fileversion", "tableversion")


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8-sig").strip()


def _mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=timezone.utc,
    ).astimezone().isoformat()


def _file_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "length": path.stat().st_size if path.exists() else None,
        "mtime": _mtime_iso(path),
    }


def _filelist_entry(filelist_text: str | None, table_path: str) -> str | None:
    if not filelist_text:
        return None
    prefix = f"{table_path}|"
    for line in filelist_text.splitlines():
        if line.startswith(prefix):
            return line
    return None


def _resolve_paths(paths: Iterable[Path]) -> list[Path]:
    seq = list(paths)
    if not seq:
        seq = [DEFAULT_SAMPLE_ROOT]
    out: list[Path] = []
    for path in seq:
        if path.is_dir():
            out.extend(sorted(path.glob("*.json")))
        elif path.exists():
            out.append(path)
    return out


def _capture_summary(paths: Iterable[Path]) -> dict[str, Any]:
    timestamp_rows: list[tuple[int, str, str]] = []
    version_like_keys: set[str] = set()
    file_mtimes: list[str] = []
    loaded_files = 0
    parse_errors: list[str] = []
    for path in _resolve_paths(paths):
        if path.exists():
            file_mtimes.append(_mtime_iso(path) or "")
        try:
            rows = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # pragma: no cover - retained for CLI diagnostics.
            parse_errors.append(f"{path}:{exc}")
            continue
        if not isinstance(rows, list):
            parse_errors.append(f"{path}:not a JSON list")
            continue
        loaded_files += 1
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in row:
                lowered = str(key).lower()
                if any(token in lowered for token in _VERSION_KEY_TOKENS):
                    version_like_keys.add(str(key))
            timestamp = row.get("CaptureTimestamp")
            if isinstance(timestamp, bool):
                continue
            try:
                parsed_ts = int(timestamp)
            except (TypeError, ValueError):
                continue
            timestamp_rows.append(
                (
                    parsed_ts,
                    str(row.get("CaptureTime") or ""),
                    path.name,
                )
            )
    timestamp_rows.sort(key=lambda item: item[0])
    file_mtimes = sorted(value for value in file_mtimes if value)
    return {
        "sample_file_count": loaded_files,
        "sample_parse_errors": parse_errors[:8],
        "capture_timestamp_rows": len(timestamp_rows),
        "capture_time_min": timestamp_rows[0][1] if timestamp_rows else None,
        "capture_time_min_file": timestamp_rows[0][2] if timestamp_rows else None,
        "capture_time_max": timestamp_rows[-1][1] if timestamp_rows else None,
        "capture_time_max_file": timestamp_rows[-1][2] if timestamp_rows else None,
        "capture_file_mtime_min": file_mtimes[0] if file_mtimes else None,
        "capture_file_mtime_max": file_mtimes[-1] if file_mtimes else None,
        "capture_version_like_keys": sorted(version_like_keys),
    }


def summarize_archive_table_timing(
    paths: Iterable[Path] = (),
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
) -> dict[str, Any]:
    tables_root = raw_root / "tables"
    filelist_text = _read_text(raw_root / "filelist.txt")
    table_files = {
        "bidmap": tables_root / "BidMap.txt",
        "drop": tables_root / "Drop.txt",
    }
    return {
        "raw_file_version": _read_text(raw_root / "fileVersion"),
        "raw_tables_file_version": _read_text(tables_root / "fileVersion"),
        "raw_filelist_header": (
            filelist_text.splitlines()[0] if filelist_text else None
        ),
        "raw_filelist_bidmap_entry": _filelist_entry(filelist_text, "Tables/BidMap.txt"),
        "raw_filelist_drop_entry": _filelist_entry(filelist_text, "Tables/Drop.txt"),
        "raw_files": {
            "file_version": _file_info(raw_root / "fileVersion"),
            "tables_file_version": _file_info(tables_root / "fileVersion"),
            "filelist": _file_info(raw_root / "filelist.txt"),
            "bidmap": _file_info(table_files["bidmap"]),
            "drop": _file_info(table_files["drop"]),
        },
        **_capture_summary(paths),
    }


def _print_summary(result: dict[str, Any]) -> None:
    print(
        " ".join(
            (
                f"raw_file_version={result['raw_file_version']}",
                f"raw_tables_file_version={result['raw_tables_file_version']}",
                f"filelist_header={json.dumps(result['raw_filelist_header'], ensure_ascii=False)}",
                f"bidmap_entry={json.dumps(result['raw_filelist_bidmap_entry'], ensure_ascii=False)}",
                f"drop_entry={json.dumps(result['raw_filelist_drop_entry'], ensure_ascii=False)}",
            )
        )
    )
    for key, value in result["raw_files"].items():
        print(
            " ".join(
                (
                    f"raw_file={key}",
                    f"exists={value['exists']}",
                    f"length={value['length']}",
                    f"mtime={json.dumps(value['mtime'], ensure_ascii=False)}",
                )
            )
        )
    print(
        " ".join(
            (
                f"sample_files={result['sample_file_count']}",
                f"capture_rows={result['capture_timestamp_rows']}",
                f"capture_min={json.dumps(result['capture_time_min'], ensure_ascii=False)}",
                f"capture_min_file={json.dumps(result['capture_time_min_file'], ensure_ascii=False)}",
                f"capture_max={json.dumps(result['capture_time_max'], ensure_ascii=False)}",
                f"capture_max_file={json.dumps(result['capture_time_max_file'], ensure_ascii=False)}",
                f"capture_file_mtime_min={json.dumps(result['capture_file_mtime_min'], ensure_ascii=False)}",
                f"capture_file_mtime_max={json.dumps(result['capture_file_mtime_max'], ensure_ascii=False)}",
                f"capture_version_like_keys={','.join(result['capture_version_like_keys']) or '-'}",
                f"parse_errors={len(result['sample_parse_errors'])}",
            )
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize raw table metadata against Fatbeans archive timing.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)

    result = summarize_archive_table_timing(args.paths, raw_root=args.raw_root)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_summary(result)
    return 1 if result["sample_parse_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
