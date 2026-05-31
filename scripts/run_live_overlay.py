"""Tiny always-on-top live overlay for ``data/logs/live/latest_snapshot.json``.

The overlay has no game integration by itself. It displays the latest monitor
snapshot, so it works with the directory/stdin monitor today and can keep
working when the monitor source becomes a true realtime feed.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time
import tkinter as tk
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BG = "#09111f"
PANEL = "#111827"
PANEL_SOFT = "#162033"
BORDER = "#263244"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
GOOD = "#86efac"
WARN = "#fbbf24"
BAD = "#fb7185"
ACCENT = "#60a5fa"
PURPLE = "#c084fc"

TAG_COLORS = {
    "header": TEXT,
    "normal": TEXT,
    "good": GOOD,
    "warn": WARN,
    "bad": BAD,
    "dim": MUTED,
}


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


def _severity_color(severity: str) -> str:
    return TAG_COLORS.get(severity, TEXT)


def _age(snapshot: dict[str, Any]) -> tuple[str, bool]:
    created_at = snapshot.get("created_at")
    if not isinstance(created_at, int | float):
        return "", False
    seconds_old = max(0, int(time.time() - created_at))
    return f"{seconds_old}s前", seconds_old > 120


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
        "category_grid_items": [
            {
                "category": 108,
                "category_label": "能源",
                "quality": 6,
                "local_index": 14,
                "cells": 16,
                "shape_key": "44",
                "row": 2,
                "col": 4,
            },
            {
                "category": 107,
                "category_label": "数码",
                "quality": 4,
                "local_index": 26,
                "cells": 4,
                "shape_key": "22",
                "row": 3,
                "col": 6,
            },
        ],
    }


def _summary_entries(snapshot: dict) -> list[tuple[str, str]]:
    panel = snapshot.get("panel") or {}
    rows = panel.get("summary_rows") or []
    entries: list[tuple[str, str]] = []
    if not snapshot:
        return [("等待 latest_snapshot.json ...", "dim")]
    age, stale = _age(snapshot)
    hero = str(snapshot.get("hero") or "?")
    header = (
        f"{hero.upper()}  |  map {snapshot.get('map_id') or '?'}  "
        f"|  R{snapshot.get('round') or '?'}  "
        f"|  结算 {_fmt_int(snapshot.get('known_value_sum'))}"
        f"{f'  {age}' if age else ''}"
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
        q6_prior = row.get("q6掉落先验") or ""
        q6_value = row.get("q6价值 P10/P50/P90") or ""
        if q6_rate or q6_value:
            tag = "warn"
            try:
                tag = "bad" if float(str(q6_rate).strip("%")) < 10 else "normal"
            except ValueError:
                tag = "normal"
            prior_text = f" / 先验 {q6_prior}" if q6_prior else ""
            entries.append(
                (f"红货: q6样本率 {q6_rate or '?'}{prior_text}  |  {q6_value}", tag)
            )
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
            root = str(eval_row.get("layout_conflict_root") or "footprint 存在重叠或越界")
            entries.append((f"布局诊断: {root}", "warn"))
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


def _summary_by_topic(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    panel = snapshot.get("panel") or {}
    rows = panel.get("summary_rows") or []
    return {
        str(row.get("topic") or ""): row
        for row in rows
        if isinstance(row, dict)
    }


def _category_focus_text(items: list[dict[str, Any]]) -> tuple[str, str]:
    counts = Counter(str(item.get("category_label") or item.get("category") or "?") for item in items)
    summary = " / ".join(f"{label}×{count}" for label, count in counts.most_common(4))
    details: list[str] = []
    for item in items[:5]:
        label = item.get("category_label") or item.get("category") or "?"
        quality = item.get("quality")
        q_text = f"Q{quality}" if quality is not None else "Q?"
        loc = item.get("local_index")
        pos = f"#{loc}" if loc is not None else ""
        shape = item.get("shape_key") or ""
        details.append(" ".join(str(part) for part in (label, q_text, shape, pos) if part))
    return summary, "；".join(details)


def _overlay_model(snapshot: dict[str, Any]) -> dict[str, Any]:
    if not snapshot:
        return {
            "empty": True,
            "title": "BidKing Live",
            "subtitle": "等待 latest_snapshot.json",
            "status": ("等待", "dim"),
            "decision": ("等待数据", "", "dim"),
            "metrics": [],
            "sections": [],
            "alerts": [],
            "footer": "",
        }

    age, stale = _age(snapshot)
    summary = _summary_by_topic(snapshot)
    bid = _first(snapshot.get("bid_rows"))
    v2 = _first(snapshot.get("v2_posterior_rows"))
    model_eval = snapshot.get("model_eval") or {}
    panel = snapshot.get("panel") or {}
    category_items = snapshot.get("category_grid_items") or []
    layout = _first(panel.get("layout_stages"))
    hero = str(snapshot.get("hero") or "?").upper()
    map_id = snapshot.get("map_id") or "?"
    round_no = snapshot.get("round") or "?"
    title = f"{hero}  ·  map {map_id}  ·  R{round_no}"
    subtitle_parts = [
        f"文件 {snapshot.get('file') or '?'}",
        f"结算 {_fmt_int(snapshot.get('known_value_sum'))}",
    ]
    if age:
        subtitle_parts.append(age)
    status = ("过期", "bad") if stale else ("实时", "good")

    decision_text = "等待建议"
    decision_detail = ""
    decision_severity = "dim"
    if bid:
        action = str(bid.get("建议") or "?")
        current = str(bid.get("当前最高") or "?")
        risk = str(bid.get("风险带") or "?")
        stop = str(bid.get("停止价") or "?")
        decision_text = action
        decision_detail = f"最高 {current}  |  停止 {stop}  |  {risk}"
        decision_severity = _severity_for_bid(f"{action} {risk}")
    elif decision_row := summary.get("当前最高价是否可追"):
        decision_text = str(decision_row.get("conclusion") or "?")
        decision_detail = _short(decision_row.get("detail"), 96)
        decision_severity = _severity_for_bid(f"{decision_text} {decision_detail}")

    metrics: list[tuple[str, str, str, str]] = []
    if value_row := summary.get("当前价值区间"):
        metrics.append(
            (
                "决策价值",
                str(value_row.get("conclusion") or "?"),
                _short(value_row.get("detail"), 46),
                "normal",
            )
        )
    if warehouse_row := summary.get("当前仓储区间"):
        metrics.append(
            (
                "仓储",
                str(warehouse_row.get("conclusion") or "?"),
                _short(warehouse_row.get("detail"), 46),
                "normal",
            )
        )
    if v2:
        q6_rate = str(v2.get("q6样本率") or "?")
        q6_tag = "normal"
        try:
            q6_tag = "bad" if float(q6_rate.strip("%")) < 10 else "normal"
        except ValueError:
            pass
        metrics.append(
            (
                "红货 q6",
                q6_rate,
                str(v2.get("q6价值 P10/P50/P90") or ""),
                q6_tag,
            )
        )
    if layout:
        metrics.append(
            (
                "布局",
                str(layout.get("estimate") or "?"),
                f"已知 {layout.get('known_cells') or '?'}格 · {layout.get('confidence') or '?'}",
                "warn" if layout.get("risk") not in ("", "低", "低风险") else "normal",
            )
        )
    sections: list[tuple[str, str, str]] = []
    if tool_row := summary.get("下一次优先使用道具"):
        sections.append(
            (
                "下一步道具",
                str(tool_row.get("conclusion") or ""),
                _short(tool_row.get("detail"), 110),
            )
        )
    if category_items:
        category_summary, category_detail = _category_focus_text(category_items)
        sections.append(("鉴影命中", category_summary, _short(category_detail, 118)))
    diagnostics = str(v2.get("诊断") or "")
    if diagnostics:
        sections.append(("后验诊断", _short(diagnostics, 118), ""))
    if layout and layout.get("risk"):
        sections.append(("布局风险", _short(layout.get("risk"), 118), ""))

    alerts: list[tuple[str, str]] = []
    if stale:
        alerts.append(("snapshot 超过 120 秒未更新，检查 Fatbeans 导出或 monitor 进程", "bad"))
    if _flag(model_eval.get("q6_false_low_risk")):
        alerts.append(("真实有红货，但后验 q6 样本率过低", "bad"))
    elif _flag(model_eval.get("q6_p90_misses_truth")):
        alerts.append(("q6 P90 低于结算 q6 价值", "warn"))
    if _flag(model_eval.get("layout_conflict")):
        root = str(model_eval.get("layout_conflict_root") or "footprint 存在重叠或越界")
        alerts.append((root, "warn"))
    if _flag(model_eval.get("relaxed_exact_used")):
        alerts.append(("exact 桶约束已放宽", "warn"))

    eval_parts = []
    if model_eval.get("decision_value_p50_error") is not None:
        eval_parts.append(f"决策P50误差 {_fmt_int(model_eval['decision_value_p50_error'])}")
    if model_eval.get("warehouse_p50_error") is not None:
        eval_parts.append(f"仓储P50误差 {model_eval['warehouse_p50_error']}")
    if model_eval.get("stop_minus_final_value") is not None:
        eval_parts.append(f"停止价-结算 {_fmt_int(model_eval['stop_minus_final_value'])}")

    return {
        "empty": False,
        "title": title,
        "subtitle": "  ·  ".join(subtitle_parts),
        "status": status,
        "decision": (decision_text, decision_detail, decision_severity),
        "metrics": metrics,
        "sections": sections,
        "alerts": alerts,
        "footer": " / ".join(eval_parts),
    }


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
        root.attributes("-alpha", 0.96)
        root.geometry("760x430+40+80")
        root.minsize(620, 340)
        root.configure(bg=BG)
        self.frame = tk.Frame(root, bg=BG, padx=12, pady=12)
        self.frame.pack(fill="both", expand=True)
        self.refresh()

    def _clear(self) -> None:
        for child in self.frame.winfo_children():
            child.destroy()

    def _label(
        self,
        parent: tk.Widget,
        text: str,
        *,
        fg: str = TEXT,
        bg: str = PANEL,
        font: tuple[str, int, str] | tuple[str, int] = ("Microsoft YaHei UI", 10),
        anchor: str = "w",
        wraplength: int = 0,
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            fg=fg,
            bg=bg,
            font=font,
            anchor=anchor,
            justify="left",
            wraplength=wraplength,
        )

    def _card(self, parent: tk.Widget, *, bg: str = PANEL) -> tk.Frame:
        frame = tk.Frame(parent, bg=bg, bd=1, relief="solid", highlightthickness=1)
        frame.configure(highlightbackground=BORDER, highlightcolor=BORDER)
        return frame

    def _render(self, model: dict[str, Any]) -> None:
        self._clear()
        header = tk.Frame(self.frame, bg=BG)
        header.pack(fill="x")
        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left", fill="x", expand=True)
        self._label(
            title_box,
            model["title"],
            bg=BG,
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(anchor="w")
        self._label(
            title_box,
            model["subtitle"],
            fg=MUTED,
            bg=BG,
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(2, 0))
        status_text, status_tag = model["status"]
        status = tk.Label(
            header,
            text=status_text,
            fg=BG,
            bg=_severity_color(status_tag),
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=12,
            pady=5,
        )
        status.pack(side="right", padx=(10, 0))

        decision_text, decision_detail, decision_tag = model["decision"]
        decision = self._card(self.frame, bg=PANEL_SOFT)
        decision.pack(fill="x", pady=(12, 10), ipady=8)
        tk.Frame(decision, width=5, bg=_severity_color(decision_tag)).pack(
            side="left",
            fill="y",
        )
        decision_body = tk.Frame(decision, bg=PANEL_SOFT, padx=12, pady=8)
        decision_body.pack(fill="x", expand=True)
        self._label(
            decision_body,
            decision_text,
            fg=_severity_color(decision_tag),
            bg=PANEL_SOFT,
            font=("Microsoft YaHei UI", 18, "bold"),
        ).pack(anchor="w")
        if decision_detail:
            self._label(
                decision_body,
                decision_detail,
                fg=TEXT,
                bg=PANEL_SOFT,
                wraplength=690,
            ).pack(anchor="w", pady=(4, 0))

        metrics = tk.Frame(self.frame, bg=BG)
        metrics.pack(fill="x")
        for index, (title, value, detail, tag) in enumerate(model["metrics"][:4]):
            card = self._card(metrics)
            card.grid(row=0, column=index, padx=(0 if index == 0 else 8, 0), sticky="nsew")
            metrics.grid_columnconfigure(index, weight=1, uniform="metric")
            body = tk.Frame(card, bg=PANEL, padx=10, pady=8)
            body.pack(fill="both", expand=True)
            self._label(body, title, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor="w")
            self._label(
                body,
                value,
                fg=_severity_color(tag),
                font=("Microsoft YaHei UI", 12, "bold"),
                wraplength=145,
            ).pack(anchor="w", pady=(3, 0))
            if detail:
                self._label(
                    body,
                    _short(detail, 54),
                    fg=MUTED,
                    font=("Microsoft YaHei UI", 8),
                    wraplength=145,
                ).pack(anchor="w", pady=(3, 0))

        lower = tk.Frame(self.frame, bg=BG)
        lower.pack(fill="both", expand=True, pady=(10, 0))
        left = tk.Frame(lower, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(lower, bg=BG, width=230)
        right.pack(side="right", fill="y", padx=(10, 0))

        for title, value, detail in model["sections"][:4]:
            row = self._card(left)
            row.pack(fill="x", pady=(0, 8))
            body = tk.Frame(row, bg=PANEL, padx=10, pady=7)
            body.pack(fill="x")
            self._label(body, title, fg=ACCENT, font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w")
            self._label(body, value, wraplength=430).pack(anchor="w", pady=(3, 0))
            if detail:
                self._label(body, detail, fg=MUTED, wraplength=430, font=("Microsoft YaHei UI", 8)).pack(anchor="w")

        alert_card = self._card(right)
        alert_card.pack(fill="both", expand=True)
        alert_body = tk.Frame(alert_card, bg=PANEL, padx=10, pady=8)
        alert_body.pack(fill="both", expand=True)
        self._label(
            alert_body,
            "风险与回测",
            fg=PURPLE,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w")
        if model["alerts"]:
            for text, tag in model["alerts"][:5]:
                self._label(
                    alert_body,
                    "• " + text,
                    fg=_severity_color(tag),
                    wraplength=190,
                    font=("Microsoft YaHei UI", 9),
                ).pack(anchor="w", pady=(6, 0))
        else:
            self._label(
                alert_body,
                "暂无高亮风险",
                fg=GOOD,
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor="w", pady=(6, 0))
        if model["footer"]:
            self._label(
                alert_body,
                model["footer"],
                fg=MUTED,
                wraplength=190,
                font=("Microsoft YaHei UI", 8),
            ).pack(anchor="w", side="bottom", pady=(10, 0))

    def refresh(self) -> None:
        snapshot = _demo_snapshot() if self.demo else _load_snapshot(self.snapshot_path)
        self._render(_overlay_model(snapshot))
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
