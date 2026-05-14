"""Base64-decode a single Tables/*.txt and print the first few TSV rows.

Confirms that decoded payload is UTF-8 TSV with consistent column counts.
Read-only. Does not write decoded output anywhere.

Usage:
  python scripts/decode_table_preview.py Drop
  python scripts/decode_table_preview.py Item --rows 5 --cols 20
"""

from __future__ import annotations

import argparse
import base64
import io
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def repo_data_tables_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent / "data" / "raw" / "tables"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="Table base name without .txt (e.g. Drop)")
    parser.add_argument("--rows", type=int, default=3)
    parser.add_argument("--cols", type=int, default=12)
    parser.add_argument("--col-width", type=int, default=40)
    args = parser.parse_args()

    path = repo_data_tables_dir() / f"{args.name}.txt"
    if not path.is_file():
        print(f"not found: {path}", file=sys.stderr)
        return 2

    raw_b64 = path.read_text(encoding="utf-8", errors="strict")
    raw_b64_clean = "".join(raw_b64.split())
    decoded = base64.b64decode(raw_b64_clean, validate=False)

    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"decoded payload is not UTF-8: {exc}", file=sys.stderr)
        return 3

    lines = text.splitlines()
    print(f"file        : {path.name}")
    print(f"raw bytes   : {len(path.read_bytes())}")
    print(f"decoded len : {len(decoded)}")
    print(f"row count   : {len(lines)}")

    col_counts: dict[int, int] = {}
    for line in lines:
        n = line.count("\t") + 1
        col_counts[n] = col_counts.get(n, 0) + 1
    print(f"col-count histogram (col_count -> rows): {dict(sorted(col_counts.items()))}")
    print()

    width = max(4, args.col_width)
    for i, line in enumerate(lines[: args.rows]):
        cells = line.split("\t")
        shown = cells[: args.cols]
        print(f"--- row[{i}] (cols={len(cells)}) ---")
        for j, cell in enumerate(shown):
            preview = cell if len(cell) <= width else cell[: width - 1] + "…"
            print(f"  [{j:>2}] {preview}")
        if len(cells) > args.cols:
            print(f"  ... + {len(cells) - args.cols} more cols")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
