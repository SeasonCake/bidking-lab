"""Settlement truth extraction for v3 archive diagnostics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

from bidking_lab.extract.item_table import Item


@dataclass(frozen=True)
class QualityTruthReport:
    quality: int
    count: int
    cells: int
    raw_value: int


@dataclass(frozen=True)
class SettlementTruthReport:
    session_id: str | None
    map_id: int | None
    sort_id: int | None
    item_count: int
    total_cells: int
    raw_total_value: int
    quality_truths: tuple[QualityTruthReport, ...]

    def quality(self, quality: int) -> QualityTruthReport | None:
        for truth in self.quality_truths:
            if truth.quality == quality:
                return truth
        return None

    def to_flat_dict(self, *, prefix: str = "v3_truth_") -> dict[str, Any]:
        q6 = self.quality(6)
        return {
            f"{prefix}available": True,
            f"{prefix}session_id": self.session_id,
            f"{prefix}map_id": self.map_id,
            f"{prefix}sort_id": self.sort_id,
            f"{prefix}item_count": self.item_count,
            f"{prefix}total_cells": self.total_cells,
            f"{prefix}raw_total_value": self.raw_total_value,
            f"{prefix}q6_count": q6.count if q6 is not None else 0,
            f"{prefix}q6_cells": q6.cells if q6 is not None else 0,
            f"{prefix}q6_raw_value": q6.raw_value if q6 is not None else 0,
        }


def settlement_truth_from_fatbeans(
    events: Any,
    *,
    items: Mapping[int, Item],
) -> SettlementTruthReport | None:
    """Return raw settlement inventory truth from the latest inventory state."""

    for state in reversed(tuple(getattr(events, "states", ()) or ())):
        inventory_items = tuple(getattr(state, "inventory_items", ()) or ())
        if not inventory_items:
            continue
        counts: defaultdict[int, int] = defaultdict(int)
        cells: defaultdict[int, int] = defaultdict(int)
        values: defaultdict[int, int] = defaultdict(int)
        total_cells = 0
        raw_total_value = 0
        for inv_item in inventory_items:
            item_id = getattr(inv_item, "item_id", None)
            item = items.get(int(item_id)) if item_id is not None else None
            quality = getattr(inv_item, "quality", None)
            if quality is None and item is not None:
                quality = item.quality
            item_cells = getattr(inv_item, "cells", None)
            if item_cells is None and item is not None:
                item_cells = item.shape_w * item.shape_h
            item_value = item.value if item is not None else 0
            total_cells += int(item_cells or 0)
            raw_total_value += int(item_value)
            if quality is None:
                continue
            q = int(quality)
            counts[q] += 1
            cells[q] += int(item_cells or 0)
            values[q] += int(item_value)
        return SettlementTruthReport(
            session_id=getattr(state, "session_id", None),
            map_id=getattr(state, "map_id", None),
            sort_id=getattr(state, "sort_id", None),
            item_count=len(inventory_items),
            total_cells=total_cells,
            raw_total_value=raw_total_value,
            quality_truths=tuple(
                QualityTruthReport(
                    quality=quality,
                    count=counts[quality],
                    cells=cells[quality],
                    raw_value=values[quality],
                )
                for quality in sorted(counts)
            ),
        )
    return None


def empty_truth_flat_dict(*, prefix: str = "v3_truth_") -> dict[str, Any]:
    return {
        f"{prefix}available": False,
        f"{prefix}session_id": None,
        f"{prefix}map_id": None,
        f"{prefix}sort_id": None,
        f"{prefix}item_count": None,
        f"{prefix}total_cells": None,
        f"{prefix}raw_total_value": None,
        f"{prefix}q6_count": None,
        f"{prefix}q6_cells": None,
        f"{prefix}q6_raw_value": None,
    }


__all__ = (
    "QualityTruthReport",
    "SettlementTruthReport",
    "empty_truth_flat_dict",
    "settlement_truth_from_fatbeans",
)
