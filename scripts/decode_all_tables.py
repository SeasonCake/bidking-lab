"""Decode every Tables/*.txt under data/raw/tables and print a uniform summary.

Read-only. UTF-8 output. Confirms each table is base64 + tab-separated and
records its row / column shape.

Usage:
  python scripts/decode_all_tables.py
  python scripts/decode_all_tables.py --rows 1 --col-width 60
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.tables import (
    assert_uniform_columns,
    decode_table_text,
    discover_tables,
)


def repo_data_tables_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent / "data" / "raw" / "tables"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1, help="rows to preview per table")
    parser.add_argument("--col-width", type=int, default=48)
    parser.add_argument(
        "--skip",
        nargs="*",
        default=["filelist", "fileVersion", "fileDiff"],
        help="logical names to skip (no .txt)",
    )
    args = parser.parse_args()

    root = repo_data_tables_dir()
    if not root.is_dir():
        print(f"missing tables dir: {root}", file=sys.stderr)
        return 2

    tables = discover_tables(root)
    skip_names = {s.lower() for s in args.skip}

    print(f"# Tables under {root}")
    print(f"# total files: {len(tables)}\n")

    for path in tables:
        if path.stem.lower() in skip_names:
            continue
        print("=" * 78)
        print(f"FILE: {path.name}   raw_bytes={path.stat().st_size}")
        try:
            decoded = decode_table_text(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  decode FAILED: {exc}")
            print()
            continue

        rows = [line.split("\t") for line in decoded.splitlines()]
        try:
            ncols = assert_uniform_columns(rows)
            shape_note = f"uniform cols={ncols}"
        except ValueError as exc:
            widths = sorted({len(r) for r in rows})
            shape_note = f"NON-uniform col widths={widths} ({exc})"

        print(f"  decoded_chars={len(decoded)}  rows={len(rows)}  {shape_note}")
        if not rows:
            print()
            continue

        for i, row in enumerate(rows[: args.rows]):
            print(f"  --- row[{i}] (cols={len(row)}) ---")
            for j, cell in enumerate(row):
                cw = args.col_width
                preview = cell if len(cell) <= cw else cell[: cw - 1] + "…"
                print(f"    [{j:>2}] {preview}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
