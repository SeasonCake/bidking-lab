"""Tiny always-on-top live overlay for ``data/logs/live/latest_snapshot.json``.

The overlay has no game integration by itself. It displays the latest monitor
snapshot, so it works with the directory/stdin monitor today and can keep
working when the monitor source becomes a true realtime feed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk


ROOT = Path(__file__).resolve().parents[1]


def _load_snapshot(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fmt_int(value) -> str:
    if value is None or value == "":
        return "?"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _flag(value) -> bool:
    return value is True or str(value).lower() == "true"


def _summary_entries(snapshot: dict) -> list[tuple[str, str]]:
    panel = snapshot.get("panel") or {}
    rows = panel.get("summary_rows") or []
    entries: list[tuple[str, str]] = []
    if not snapshot:
        return [("等待 latest_snapshot.json ...", "dim")]
    age = ""
    created_at = snapshot.get("created_at")
    if isinstance(created_at, int | float):
        age = f"  {max(0, int(time.time() - created_at))}s前"
    header = (
        f"{snapshot.get('hero') or '?'}  "
        f"map {snapshot.get('map_id') or '?'}  "
        f"R{snapshot.get('round') or '?'}  "
        f"结算{_fmt_int(snapshot.get('known_value_sum'))}"
        f"{age}"
    )
    entries.append((header, "header"))
    for row in rows[:4]:
        topic = row.get("topic", "")
        conclusion = row.get("conclusion", "")
        detail = row.get("detail", "")
        line = f"{topic}: {conclusion}"
        if detail:
            line = f"{line} | {detail}"
        tag = "normal"
        if "停止" in line or "不追" in line or "风险" in line:
            tag = "warn"
        entries.append((line, tag))
    v2_rows = snapshot.get("v2_posterior_rows") or []
    if v2_rows:
        row = v2_rows[0]
        q6_rate = row.get("q6样本率") or ""
        q6_value = row.get("q6价值 P10/P50/P90") or ""
        if q6_rate or q6_value:
            entries.append((f"q6: 样本率 {q6_rate or '?'} | {q6_value}", "normal"))
        diagnostics = str(row.get("诊断") or "")
        if diagnostics:
            tag = "warn"
            if "q6_unconstrained_low_sample_rate" in diagnostics:
                tag = "bad"
            entries.append((f"后验诊断: {diagnostics}", tag))
    layout = panel.get("layout_stages") or []
    if layout:
        stage = layout[0]
        risk = stage.get("risk", "")
        tag = "warn" if risk and risk not in ("低", "低风险") else "normal"
        entries.append(
            (
                "布局: "
                f"{stage.get('stage', '')} "
                f"已知{stage.get('known_cells', '')}格 "
                f"估计{stage.get('estimate', '')} "
                f"{stage.get('confidence', '')} "
                f"{risk}",
                tag,
            )
        )
    eval_row = snapshot.get("model_eval") or {}
    if eval_row:
        if _flag(eval_row.get("q6_false_low_risk")):
            entries.append(("回测警告: 真实有红货，但后验 q6 样本率过低", "bad"))
        elif _flag(eval_row.get("q6_p90_misses_truth")):
            entries.append(("回测警告: q6 P90 低于结算 q6 价值", "warn"))
        if _flag(eval_row.get("layout_conflict")):
            entries.append(("布局诊断: footprint 存在重叠或越界", "warn"))
        if _flag(eval_row.get("relaxed_exact_used")):
            entries.append(("约束诊断: exact 桶约束已放宽", "warn"))
        parts = []
        if eval_row.get("decision_value_p50_error") is not None:
            parts.append(f"决策P50误差 {_fmt_int(eval_row['decision_value_p50_error'])}")
        if eval_row.get("warehouse_p50_error") is not None:
            parts.append(f"仓储P50误差 {eval_row['warehouse_p50_error']}")
        if eval_row.get("stop_minus_final_value") is not None:
            parts.append(f"停止价-结算 {_fmt_int(eval_row['stop_minus_final_value'])}")
        if parts:
            entries.append(("评估: " + " / ".join(parts), "dim"))
    return entries


def _summary_lines(snapshot: dict) -> list[str]:
    return [line for line, _tag in _summary_entries(snapshot)]


class Overlay:
    def __init__(self, root: tk.Tk, snapshot_path: Path, interval_ms: int) -> None:
        self.root = root
        self.snapshot_path = snapshot_path
        self.interval_ms = interval_ms
        root.title("BidKing Live")
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.92)
        root.geometry("760x300+40+80")
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
        self.text.tag_configure("header", foreground="#f9fafb")
        self.text.tag_configure("normal", foreground="#e5e7eb")
        self.text.tag_configure("warn", foreground="#fbbf24")
        self.text.tag_configure("bad", foreground="#f87171")
        self.text.tag_configure("dim", foreground="#9ca3af")
        self.text.pack(fill="both", expand=True)
        self.text.configure(state="disabled")
        self.refresh()

    def refresh(self) -> None:
        snapshot = _load_snapshot(self.snapshot_path)
        entries = _summary_entries(snapshot)
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for line, tag in entries:
            self.text.insert("end", line + "\n", tag)
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
