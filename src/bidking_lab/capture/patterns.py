"""Regex and keyword rules for the center-left game info panel."""

from __future__ import annotations

import re

# Lines we deliberately do not map to form fields (still logged as ignored).
IGNORE_SUBSTRINGS: tuple[str, ...] = (
    "显示", "品质", "轮廓",
    "品质最高", "占位最高", "站位最高", "占格最高",
    "随机显示", "件藏品的品质",
    "当前预估最低价格",
)

IGNORE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE) for p in (
        r"^第\s*\d+\s*轮",
        r"显示.{0,12}品质.{0,8}藏品",
        r"显示.{0,12}品质.{0,8}轮廓",
        r"随机显示\s*\d+\s*件",
        r"随机显示\s*\d+\s*件藏品的品质",
        r"(品质|占位|站位).{0,4}最高",
        r"总藏品.{0,8}平均占位",  # 用户认为无用
    )
)

# Panel session hints (not per-quality scans).
SESSION_PANEL_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"所有藏品总占用.{0,16}?(\d+)\s*格"),
        "warehouse_cells",
        "面板 → 仓库总占格",
    ),
    (
        re.compile(r"所有.{0,4}品总占用.{0,24}?(\d+)\s*格"),
        "warehouse_cells",
        "面板 → 仓库总占格（OCR 容错）",
    ),
    (
        re.compile(r"(?:本仓|本场|本局).{0,12}?(\d+)\s*件"),
        "total_item_count",
        "地图 → 总藏品件数",
    ),
    (
        re.compile(r"(\d+)\s*件藏品(?!的)"),
        "total_item_count",
        "X 件藏品",
    ),
    (
        re.compile(r"总仓储空间.{0,12}?(\d+)\s*格"),
        "warehouse_cells",
        "道具 → 仓库总占格",
    ),
)

# Tool scans (道具) — white/green/blue never come from map hints in practice.
# Descriptions without the tool name prefix (map / merged scan lines).
# ``所有{色}…总占…`` lines are most reliable; require 所有 + color to avoid
# matching a stray 「蓝品」 inside a garbled purple OCR line.
_QUALITY_ALL_CELLS = r"所有.{{0,4}}(?:{color}).{{0,24}}总占.{{0,16}}?(\d+)\s*格"

QUALITY_CELLS_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(_QUALITY_ALL_CELLS.format(color="紫|紧")),
        "purple_cells",
        "紫品总格（所有紫…）",
    ),
    (
        re.compile(_QUALITY_ALL_CELLS.format(color="金")),
        "gold_cells",
        "金品总格（所有金…）",
    ),
    (
        re.compile(_QUALITY_ALL_CELLS.format(color="蓝")),
        "blue_cells",
        "蓝品总格（所有蓝…）",
    ),
    (
        re.compile(
            r"(?:白色|白).{0,24}(?:绿色|绿).{0,24}总占.{0,16}?(\d+)\s*格",
        ),
        "wg_cells",
        "白+绿总格",
    ),
    (
        re.compile(
            r"^(?!.*(?:蓝|紫|金)).*(?:白|绿).{0,24}总占.{0,16}?(\d+)\s*格",
        ),
        "wg_cells",
        "白+绿总格（OCR 断行）",
    ),
    (
        re.compile(r"^品总占.{0,16}?(\d+)\s*格"),
        "blue_cells",
        "蓝品总格（OCR 断行）",
    ),
    (
        re.compile(r"紫(?:色)?(?:品|色品质)?.{0,24}总占.{0,16}?(\d+)\s*格"),
        "purple_cells",
        "紫品总格",
    ),
    (
        re.compile(r"金(?:色)?(?:品|色品质)?.{0,24}总占.{0,16}?(\d+)\s*格"),
        "gold_cells",
        "金品总格",
    ),
)

TOOL_SCAN_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"普.{0,4}品?.{0,4}扫描.{0,60}?(\d+)\s*格"),
        "wg_cells",
        "普品扫描 → 白+绿总格",
    ),
    (
        re.compile(r"良.{0,4}品?.{0,4}扫描.{0,60}?(\d+)\s*格"),
        "blue_cells",
        "良品扫描 → 蓝品总格",
    ),
    (
        re.compile(r"优.{0,4}品?.{0,4}扫描.{0,60}?(\d+)\s*格"),
        "purple_cells",
        "优品扫描 → 紫品总格",
    ),
    (
        re.compile(r"极.{0,4}品?.{0,4}扫描.{0,60}?(\d+)\s*格"),
        "gold_cells",
        "极品扫描 → 金品总格",
    ),
    (
        re.compile(r"珍品扫描.{0,40}?(\d+)\s*格"),
        "red_cells_total",
        "珍品扫描 → 红品总格",
    ),
)

AVG_CELLS_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"优品均格.{0,30}?约?\s*([\d.]+)\s*格"),
        "purple_avg_raw",
        "优品均格",
    ),
    (
        re.compile(r"极品均格.{0,30}?约?\s*([\d.]+)\s*格"),
        "gold_avg_raw",
        "极品均格",
    ),
    (
        re.compile(r"珍品均格.{0,30}?约?\s*([\d.]+)\s*格"),
        "red_avg_raw",
        "珍品均格（仅记录，红品少用均格）",
    ),
)

# Map session hints (dynamic, not in BidMap static columns).
MAP_METRIC_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"紫(?:色|品).{0,12}?均格.{0,20}?约?\s*([\d.]+)\s*格"),
        "purple_avg_raw",
        "地图 → 紫品均格",
    ),
    (
        re.compile(r"紫.{0,24}平均占位.{0,10}?约?\s*([\d.]+)\s*格"),
        "purple_avg_raw",
        "紫品平均占位（均格）",
    ),
    (
        re.compile(r"品.{0,4}平均占位约?\s*([\d.]+)\s*格"),
        "purple_avg_raw",
        "紫品均格（OCR 断行）",
    ),
    (
        re.compile(r"金(?:色|品).{0,12}?均格.{0,20}?约?\s*([\d.]+)\s*格"),
        "gold_avg_raw",
        "地图 → 金品均格",
    ),
    (
        re.compile(r"紫(?:色|品).{0,12}?均价.{0,20}?([\d,，]+)"),
        "purple_avg_value",
        "地图 → 紫品均价",
    ),
    (
        re.compile(r"金(?:色|品).{0,12}?均价.{0,20}?([\d,，]+)"),
        "gold_avg_value",
        "地图 → 金品均价",
    ),
    (
        re.compile(r"紫(?:色|品).{0,12}?总(?:价|估值).{0,20}?([\d,，]+)"),
        "purple_value",
        "地图 → 紫品总价",
    ),
    (
        re.compile(r"紫.{0,28}?总(?:价值|估价).{0,12}?(\d[\d,，]*)"),
        "purple_value",
        "优品估价 → 紫品总价",
    ),
    (
        re.compile(r"所有紫色品质藏品的总价值为\s*(\d[\d,，]*)"),
        "purple_value",
        "紫品总价值",
    ),
    (
        re.compile(r"金(?:色|品).{0,12}?总(?:价|估值).{0,20}?([\d,，]+)"),
        "gold_value",
        "地图 → 金品总价",
    ),
    (
        re.compile(r"紫(?:色|品).{0,12}?总格.{0,20}?(\d+)\s*格"),
        "purple_cells",
        "地图 → 紫品总格",
    ),
    (
        re.compile(r"金(?:色|品).{0,12}?总格.{0,20}?(\d+)\s*格"),
        "gold_cells",
        "地图 → 金品总格",
    ),
    (
        re.compile(r"紫(?:色|品).{0,12}?(\d+)\s*件"),
        "purple_count",
        "地图 → 紫品件数",
    ),
    (
        re.compile(r"金(?:色|品).{0,12}?(\d+)\s*件"),
        "gold_count",
        "地图 → 金品件数",
    ),
    (
        re.compile(r"(\d+)\s*件藏品"),
        "total_item_count",
        "地图 → 总藏品件数",
    ),
    (
        re.compile(r"总藏品.{0,12}?(\d+)\s*件"),
        "total_item_count",
        "地图 → 总藏品件数",
    ),
)

MAP_NAME_PATTERN = re.compile(
    r"^([^:：]{2,20})[:：]\s*(?:竞拍信息|完拍信息|地图信息|信息)",
)
