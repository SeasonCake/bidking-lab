"""Profile each column of BidMap.txt to map out the 21-column schema.

Same idea as scripts/profile_item_columns.py.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.tables import load_table_rows


def classify(value: str) -> str:
    if value == "":
        return "empty"
    s = value.strip()
    if s.startswith("[") and s.endswith("]"):
        return "json-list"
    try:
        int(s)
        return "int"
    except ValueError:
        pass
    return "text"


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    rows = load_table_rows(repo_root / "data" / "raw" / "tables" / "BidMap.txt")
    if not rows:
        return 2
    ncols = len(rows[0])
    print(f"# BidMap rows={len(rows)} cols={ncols}\n")

    for c in range(ncols):
        col_vals = [r[c] for r in rows]
        type_counts: dict[str, int] = {}
        for v in col_vals:
            type_counts[classify(v)] = type_counts.get(classify(v), 0) + 1
        distinct = len(set(col_vals))
        print(f"=== col[{c:>2}]  distinct={distinct}  types={dict(sorted(type_counts.items()))} ===")
        seen: set[str] = set()
        for v in col_vals:
            if v in seen:
                continue
            seen.add(v)
            preview = v if len(v) <= 90 else v[:89] + "…"
            print(f"  {preview!r}")
            if len(seen) >= 6:
                break
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
