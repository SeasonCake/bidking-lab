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
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_snapshot(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fmt_int(value: Any) -> str:
    if value is None or value == "":
        return "?"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _flag(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def _first(rows: Any) -> dict[str, Any]:
    if isinstance(rows, list | tuple) and rows:
        row = rows[0]
        if isinstance(row, dict):
            return row
    return {}


def _short(value: Any, limit: int = 92) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _severity_for_bid(text: str) -> str:
    if "停止" in text or "过热" in text or "不追" in text:
        return "bad"
    if "防守" in text or "可守" in text or "谨慎" in text or "风险" in text:
        return "warn"
    return "good"


def _demo_snapshot() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at": time.time(),
        "file": "demo_overlay_snapshot.json",
        "hero": "ethan",
        "map_id": 2506,
        "round": 3,
        "known_value_sum": 1_292_866,
        "panel": {
            "summary_rows": [
                {
                    "topic": "当前最高价是否可追",
                    "conclusion": "可守不抢",
                    "detail": "对手 642,000 / 防守价 598,000 / 停止价 712,000",
                },
                {
                    "topic": "当前价值区间",
                    "conclusion": "402,000 / 741,000 / 1,180,000",
                    "detail": "v2 decision_value；raw 402,000 / 812,000 / 1,620,000",
                },
                {
                    "topic": "当前仓储区间",
                    "conclusion": "142 / 168 / 204",
                    "detail": "中；布局已知格较多，但仍有底部空间不确定性",
                },
                {
                    "topic": "下一次优先使用道具",
                    "conclusion": "随机抽检（2），ROI 318.4",
                    "detail": "优先确认 q6 是否为 3x4/4x4 大件",
                },
            ],
            "layout_stages": [
                {
                    "stage": "R3 / sort 66",
                    "known_cells": "128",
                    "coverage": "76%",
                    "deepest_row": "19",
                    "estimate": "142/168/204",
                    "confidence": "中",
                    "risk": "中：底部空间仍可能容纳红货",
                },
            ],
        },
        "v2_posterior_rows": [
            {
                "范围": "2506 探险家座舰资料库",
                "匹配": "244/500",
                "价值口径": "decision_value",
                "决策价值 P10/P50/P90": "402,000 / 741,000 / 1,180,000",
                "原始价值 P10/P50/P90": "402,000 / 812,000 / 1,620,000",
                "q6价值 P10/P50/P90": "120,000 / 452,800 / 932,715",
                "q6样本率": "68.0%",
                "诊断": "footprint_overlap_cells:1",
            },
        ],
        "bid_rows": [
            {
                "证据": "v2 decision_value",
                "轮次": "R3/5",
                "信息强度": "中",
                "仓储": "后验 142/168/204 (中)",
                "当前最高": "对手A 642,000",
                "风险带": "防守区",
                "探价(P10)": "401,999",
                "防守价": "598,000",
                "抢仓上限": "666,900",
                "停止价": "712,000",
                "建议": "可守不抢",
            },
        ],
        "model_eval": {
            "q6_p90_misses_truth": True,
            "layout_conflict": True,
            "decision_value_p50_error": -188_000,
            "warehouse_p50_error": 9,
            "stop_minus_final_value": -122_000,
        },
    }


def _summary_entries(snapshot: dict) -> list[tuple[str, str]]:
    panel = snapshot.get("panel") or {}
    rows = panel.get("summary_rows") or []
    entries: list[tuple[str, str]] = []
    if not snapshot:
        return [("等待 latest_snapshot.json ...", "dim")]
    age = ""
    stale = False
    created_at = snapshot.get("created_at")
    if isinstance(created_at, int | float):
        seconds_old = max(0, int(time.time() - created_at))
        stale = seconds_old > 120
        age = f"  {seconds_old}s前"
    hero = str(snapshot.get("hero") or "?")
    header = (
        f"{hero.upper()}  |  map {snapshot.get('map_id') or '?'}  "
        f"|  R{snapshot.get('round') or '?'}  "
        f"|  结算 {_fmt_int(snapshot.get('known_value_sum'))}{age}"
    )
    entries.append((header, "header"))
    if stale:
        entries.append(("状态: snapshot 超过 120 秒未更新，检查 Fatbeans 导出或 monitor 进程", "warn"))

    summary_by_topic = {
        str(row.get("topic") or ""): row
        for row in rows
        if isinstance(row, dict)
    }
    bid = _first(snapshot.get("bid_rows"))
    if bid:
        action = str(bid.get("建议") or "?")
        current = str(bid.get("当前最高") or "?")
        risk = str(bid.get("风险带") or "?")
        stop = str(bid.get("停止价") or "?")
        entries.append(
            (
                f"决策: {action}  |  最高 {current}  |  停止 {stop}  |  {risk}",
                _severity_for_bid(f"{action} {risk}"),
            )
        )
    elif decision_row := summary_by_topic.get("当前最高价是否可追"):
        line = (
            f"决策: {decision_row.get('conclusion', '')}  |  "
            f"{_short(decision_row.get('detail'), 90)}"
        )
        entries.append((line, _severity_for_bid(line)))

    value_row = summary_by_topic.get("当前价值区间")
    if value_row:
        entries.append(
            (
                "价值: "
                f"{value_row.get('conclusion', '')}  |  "
                f"{_short(value_row.get('detail'), 74)}",
                "normal",
            )
        )
    warehouse_row = summary_by_topic.get("当前仓储区间")
    if warehouse_row:
        entries.append(
            (
                "仓储: "
                f"{warehouse_row.get('conclusion', '')}  |  "
                f"{_short(warehouse_row.get('detail'), 70)}",
                "normal",
            )
        )

    v2_rows = snapshot.get("v2_posterior_rows") or []
    if v2_rows:
        row = v2_rows[0]
        q6_rate = row.get("q6样本率") or ""
        q6_value = row.get("q6价值 P10/P50/P90") or ""
        if q6_rate or q6_value:
            tag = "warn"
            try:
                tag = "bad" if float(str(q6_rate).strip("%")) < 10 else "normal"
            except ValueError:
                tag = "normal"
            entries.append((f"红货: q6样本率 {q6_rate or '?'}  |  {q6_value}", tag))
        diagnostics = str(row.get("诊断") or "")
        if diagnostics:
            tag = "warn"
            if "q6_unconstrained_low_sample_rate" in diagnostics:
                tag = "bad"
            entries.append((f"后验: {_short(diagnostics, 108)}", tag))
    layout = panel.get("layout_stages") or []
    if layout:
        stage = layout[0]
        risk = stage.get("risk", "")
        tag = "warn" if risk and risk not in ("低", "低风险") else "normal"
        entries.append(
            (
                f"布局: {stage.get('stage', '')}  |  "
                f"已知 {stage.get('known_cells', '')}格  "
                f"估计 {stage.get('estimate', '')}  "
                f"{stage.get('confidence', '')}  |  {_short(risk, 52)}",
                tag,
            )
        )
    tool_row = summary_by_topic.get("下一次优先使用道具")
    if tool_row:
        entries.append(
            (
                "道具: "
                f"{tool_row.get('conclusion', '')}"
                + (
                    f"  |  {_short(tool_row.get('detail'), 62)}"
                    if tool_row.get("detail")
                    else ""
                ),
                "good",
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
    def __init__(
        self,
        root: tk.Tk,
        snapshot_path: Path,
        interval_ms: int,
        *,
        demo: bool = False,
    ) -> None:
        self.root = root
        self.snapshot_path = snapshot_path
        self.interval_ms = interval_ms
        self.demo = demo
        root.title("BidKing Live")
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.94)
        root.geometry("680x280+40+80")
        root.minsize(560, 220)
        root.configure(bg="#0f172a")
        style = ttk.Style(root)
        style.configure("Overlay.TFrame", background="#0f172a")
        self.frame = ttk.Frame(root, padding=10, style="Overlay.TFrame")
        self.frame.pack(fill="both", expand=True)
        self.text = tk.Text(
            self.frame,
            height=10,
            wrap="word",
            bg="#0f172a",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            padx=4,
            pady=2,
            spacing1=2,
            spacing3=5,
            font=("Microsoft YaHei UI", 10),
        )
        self.text.tag_configure("header", foreground="#f9fafb", font=("Microsoft YaHei UI", 11, "bold"))
        self.text.tag_configure("normal", foreground="#e5e7eb")
        self.text.tag_configure("good", foreground="#86efac")
        self.text.tag_configure("warn", foreground="#fbbf24")
        self.text.tag_configure("bad", foreground="#f87171")
        self.text.tag_configure("dim", foreground="#9ca3af")
        self.text.pack(fill="both", expand=True)
        self.text.configure(state="disabled")
        self.refresh()

    def refresh(self) -> None:
        snapshot = _demo_snapshot() if self.demo else _load_snapshot(self.snapshot_path)
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
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Show a built-in demo snapshot instead of reading latest_snapshot.json.",
    )
    args = parser.parse_args()

    root = tk.Tk()
    Overlay(root, Path(args.snapshot), max(250, args.interval_ms), demo=args.demo)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
