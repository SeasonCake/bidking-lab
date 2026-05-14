"""Profile each column of Item.txt to help reverse-engineer its schema.

Item.txt has 1132 rows and 38 columns with no header. This script
inspects each column independently and prints:

- distinct value count
- whether values look int / float / json-list / text
- numeric min/max if numeric
- 5 sample values

The output is used to *manually* assign meaning to each column index
in a follow-up `bidking_lab/extract/item_table.py`.

Usage:
  python scripts/profile_item_columns.py
  python scripts/profile_item_columns.py --col-width 60
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Iterable

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.tables import load_table_rows


def classify(value: str) -> str:
    if value == "":
        return "empty"
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return "json-list"
    try:
        int(stripped)
        return "int"
    except ValueError:
        pass
    try:
        float(stripped)
        return "float"
    except ValueError:
        pass
    return "text"


def short(value: str, width: int) -> str:
    return value if len(value) <= width else value[: width - 1] + "…"


def summarize_column(idx: int, values: list[str], col_width: int) -> None:
    n = len(values)
    distinct = len(set(values))
    type_counts: dict[str, int] = {}
    for v in values:
        type_counts[classify(v)] = type_counts.get(classify(v), 0) + 1
    dominant = max(type_counts, key=type_counts.get)

    numeric_summary = ""
    if dominant in ("int", "float") and "json-list" not in type_counts:
        nums: list[float] = []
        for v in values:
            try:
                nums.append(float(v))
            except ValueError:
                continue
        if nums:
            numeric_summary = (
                f"  min={min(nums):.4g} max={max(nums):.4g}"
                f" mean={sum(nums) / len(nums):.4g}"
            )

    pk_hint = "  (looks like PK)" if distinct == n and dominant == "int" else ""

    print(f"=== col[{idx:>2}]  rows={n}  distinct={distinct}  dominant={dominant}{pk_hint} ===")
    print(f"  type_counts: {dict(sorted(type_counts.items()))}")
    if numeric_summary:
        print(f"  numeric:{numeric_summary}")

    samples: list[str] = []
    seen: set[str] = set()
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        samples.append(v)
        if len(samples) >= 5:
            break
    print("  samples:")
    for s in samples:
        print(f"    {short(s, col_width)!r}")
    print()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--col-width", type=int, default=60)
    parser.add_argument(
        "--cols",
        nargs="*",
        type=int,
        default=None,
        help="only profile these column indices (default: all)",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    item_path = repo_root / "data" / "raw" / "tables" / "Item.txt"
    if not item_path.is_file():
        print(f"missing: {item_path}", file=sys.stderr)
        return 2

    rows = load_table_rows(item_path)
    if not rows:
        print("Item.txt has 0 rows", file=sys.stderr)
        return 3

    ncols = len(rows[0])
    if not all(len(r) == ncols for r in rows):
        print("WARN: jagged rows — profiler assumes rectangular", file=sys.stderr)

    print(f"# Item.txt rows={len(rows)} cols={ncols}\n")

    indices = args.cols if args.cols is not None else range(ncols)
    for idx in indices:
        if not (0 <= idx < ncols):
            print(f"SKIP col[{idx}]: out of range", file=sys.stderr)
            continue
        values = [r[idx] for r in rows]
        summarize_column(idx, values, args.col_width)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
