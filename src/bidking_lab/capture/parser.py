"""Parse OCR / copy-pasted text from the game info panel."""

from __future__ import annotations

import re
from typing import Mapping

from bidking_lab.capture.log_util import LOG, configure_capture_logging
from bidking_lab.capture.ocr_normalize import normalize_ocr_text

configure_capture_logging()
from bidking_lab.capture.patterns import (
    AVG_CELLS_RULES,
    IGNORE_PATTERNS,
    MAP_METRIC_RULES,
    MAP_NAME_PATTERN,
    QUALITY_CELLS_RULES,
    SESSION_PANEL_RULES,
    TOOL_SCAN_RULES,
)
from bidking_lab.capture.types import (
    CaptureParseResult,
    CaptureSource,
    FieldSuggestion,
    ParsedLine,
)


def _normalize_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        s = raw.strip()
        if s:
            lines.append(s)
    return lines


def _parse_int(s: str) -> int:
    return int(s.replace(",", "").replace("，", ""))


def _should_ignore(line: str) -> bool:
    return any(pat.search(line) for pat in IGNORE_PATTERNS)


def _match_rules(
    line: str,
    rules: tuple[tuple[re.Pattern[str], str, str], ...],
    *,
    source: CaptureSource,
) -> FieldSuggestion | None:
    for pat, key, label in rules:
        m = pat.search(line)
        if not m:
            continue
        raw_val = m.group(1)
        if key.endswith("_avg_raw"):
            value: str | int = raw_val.strip()
        elif key in ("purple_avg_value", "gold_avg_value", "purple_value", "gold_value"):
            value = _parse_int(raw_val)
        else:
            value = _parse_int(raw_val)
        return FieldSuggestion(
            key=key,
            value=value,
            label=label,
            confidence=0.92,
            source_line=line,
        )
    return None


def _best_map_name_in_text(text: str, map_names: Mapping[int, str]) -> tuple[int | None, str | None]:
    """Pick the longest map name contained in *text* (avoids short false positives)."""
    best_len = 0
    best_mid: int | None = None
    best_name: str | None = None
    for mid, name in map_names.items():
        if not name or name not in text:
            continue
        if len(name) > best_len:
            best_len = len(name)
            best_mid = mid
            best_name = name
    return best_mid, best_name


def resolve_map_id(line: str, map_names: Mapping[int, str]) -> tuple[int | None, str | None]:
    m = MAP_NAME_PATTERN.search(line)
    if m:
        fragment = m.group(1).strip()
        exact: list[tuple[int, str]] = []
        for mid, name in map_names.items():
            if name == fragment:
                exact.append((mid, name))
        if len(exact) == 1:
            return exact[0]
        if exact:
            exact.sort(key=lambda x: len(x[1]), reverse=True)
            return exact[0]
        return _best_map_name_in_text(line, map_names)
    return _best_map_name_in_text(line, map_names)


def parse_panel_text(
    text: str,
    *,
    map_names: Mapping[int, str] | None = None,
) -> CaptureParseResult:
    """Parse panel text into UI field suggestions (no SessionObs)."""
    map_names = map_names or {}
    text = normalize_ocr_text(text)
    result = CaptureParseResult()
    seen_keys: set[str] = set()

    if map_names:
        blob = text.replace("\r\n", "\n")
        mid, name = _best_map_name_in_text(blob, map_names)
        if mid is not None:
            result.map_id = mid
            result.map_name = name

    for line in _normalize_lines(text):
        if _should_ignore(line):
            result.ignored.append(line)
            result.lines.append(ParsedLine(line, "ignored", "规则过滤"))
            continue

        mid, mname = resolve_map_id(line, map_names)
        if mid is not None:
            result.map_id = mid
            result.map_name = mname
            result.lines.append(ParsedLine(line, "map_hint", mname or ""))
            continue

        if "空间觉知" in line or "遗珍慧眼" in line:
            result.lines.append(ParsedLine(line, "hero_skill", "技能说明"))
            if "显示" in line and "轮廓" in line:
                result.ignored.append(line)
            continue

        sug: FieldSuggestion | None = None
        for rules, src in (
            (SESSION_PANEL_RULES, "map_hint"),
            (TOOL_SCAN_RULES, "tool_scan"),
            (QUALITY_CELLS_RULES, "map_metric"),
            (AVG_CELLS_RULES, "tool_scan"),
            (MAP_METRIC_RULES, "map_metric"),
        ):
            sug = _match_rules(line, rules, source=src)
            if sug:
                break

        if sug is None:
            result.unknown.append(line)
            result.lines.append(ParsedLine(line, "unknown"))
            continue

        # Later lines do not override earlier unless higher confidence map metric
        if sug.key in seen_keys and sug.key not in ("purple_avg_raw", "gold_avg_raw"):
            continue
        seen_keys.add(sug.key)
        result.suggestions.append(sug)
        result.lines.append(
            ParsedLine(line, "tool_scan" if "扫描" in line else "map_metric", sug.label),
        )

    keys = [s.key for s in result.suggestions]
    LOG.info(
        "parse: map_id=%s suggestions=%s ignored=%d unknown=%d",
        result.map_id,
        keys,
        len(result.ignored),
        len(result.unknown),
    )
    return result
