"""Tiny always-on-top live overlay for ``data/logs/live/latest_snapshot.json``.

The overlay has no game integration by itself. It displays the latest monitor
snapshot, so it works with the directory/stdin monitor today and can keep
working when the monitor source becomes a true realtime feed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk


ROOT = Path(__file__).resolve().parents[1]


def _load_snapshot(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _summary_lines(snapshot: dict) -> list[str]:
    panel = snapshot.get("panel") or {}
    rows = panel.get("summary_rows") or []
    lines: list[str] = []
    if not snapshot:
        return ["等待 latest_snapshot.json ..."]
    header = (
        f"map {snapshot.get('map_id') or '?'}  "
        f"R{snapshot.get('round') or '?'}  "
        f"value {snapshot.get('known_value_sum') or '?'}"
    )
    lines.append(header)
    for row in rows[:4]:
        topic = row.get("topic", "")
        conclusion = row.get("conclusion", "")
        detail = row.get("detail", "")
        line = f"{topic}: {conclusion}"
        if detail:
            line = f"{line} | {detail}"
        lines.append(line)
    layout = panel.get("layout_stages") or []
    if layout:
        stage = layout[0]
        lines.append(
            "布局: "
            f"{stage.get('stage', '')} "
            f"已知{stage.get('known_cells', '')}格 "
            f"估计{stage.get('estimate', '')} "
            f"{stage.get('confidence', '')}"
        )
    eval_row = snapshot.get("model_eval") or {}
    if eval_row:
        parts = []
        if eval_row.get("value_p50_error") is not None:
            parts.append(f"价值P50误差 {eval_row['value_p50_error']:,}")
        if eval_row.get("warehouse_p50_error") is not None:
            parts.append(f"仓储P50误差 {eval_row['warehouse_p50_error']}")
        if parts:
            lines.append("评估: " + " / ".join(parts))
    return lines


class Overlay:
    def __init__(self, root: tk.Tk, snapshot_path: Path, interval_ms: int) -> None:
        self.root = root
        self.snapshot_path = snapshot_path
        self.interval_ms = interval_ms
        root.title("BidKing Live")
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.92)
        root.geometry("620x210+40+80")
        root.configure(bg="#111827")
        self.frame = ttk.Frame(root, padding=10)
        self.frame.pack(fill="both", expand=True)
        self.text = tk.Text(
            self.frame,
            height=9,
            wrap="word",
            bg="#111827",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            font=("Microsoft YaHei UI", 10),
        )
        self.text.pack(fill="both", expand=True)
        self.text.configure(state="disabled")
        self.refresh()

    def refresh(self) -> None:
        snapshot = _load_snapshot(self.snapshot_path)
        lines = _summary_lines(snapshot)
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(lines))
        self.text.configure(state="disabled")
        self.root.after(self.interval_ms, self.refresh)


def main() -> int:
    parser = argparse.ArgumentParser(description="Show BidKing live overlay.")
    parser.add_argument(
        "--snapshot",
        default=str(ROOT / "data" / "logs" / "live" / "latest_snapshot.json"),
        help="Path to latest_snapshot.json",
    )
    parser.add_argument("--interval-ms", type=int, default=1000)
    args = parser.parse_args()

    root = tk.Tk()
    Overlay(root, Path(args.snapshot), max(250, args.interval_ms))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
