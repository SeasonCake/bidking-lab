"""User-facing observation dataclasses + brute-force candidate enumeration.

This module is the bridge between *what the player types into the UI* and
*what the inference engine consumes*. It deliberately keeps the data
model flat and dataclass-shaped so that a future Streamlit / form UI
can bind to fields directly.

Field tiers (from the 2026-05-15 design session):

* **Required** in all modes: ``warehouse_total_cells``, ``red``
  ``value_range`` (red variance is too high to skip).
* **Required for Ethan** but optional for Aisha: blue/white-green
  ``total_cells`` (Ethan scans quickly; Aisha makes you count outlines
  by hand). Ethan also sees huge items in every quality; Aisha can
  only see *purple* huge items (the rest she has to guess).
* **Always optional**: ``count``, ``avg_cells``, ``value_sum`` — these
  come from tool readings the player may or may not have used.

Huge-count input is a **band**, not a single integer: the player picks
``"1"``, ``"2-3"``, or ``"4+"`` from a dropdown. The engine enumerates
within the band. When the player does **not** pick a ``★`` concrete item,
``huge_cells_per_item()`` uses the per-quality **minimum** huge footprint
(see ``HUGE_CELLS_PER_QUALITY``: purple 10, gold/red 12). Picking
``★ 具体物品`` sets ``huge_cells_override`` to that item's exact cells
(e.g. gold yacht = 18). Value-side priors use ``PER_CELL_VALUE_HUGE``
(drop-weighted ~7000/cell gold, ~30000/cell red), separate from the
cell floor.

The brute-force candidate enumeration walks ``(total_cells, count)``
integer pairs and filters by every constraint the player provided.
Output is ranked top-K by a composite score combining the cells-side
display-rule match and the value-side prior fit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bidking_lab.inference.display import (
    Reading,
    enumerate_candidates,
    filter_by_warehouse_size,
    is_compatible,
    parse_reading,
)
from bidking_lab.inference.quality_priors import (
    PER_CELL_VALUE_DEFAULT,
    estimate_total_cells,
    per_cell_value,
    value_consistency_score,
)

HeroMode = Literal["aisha", "ethan"]
"""Which hero the player has equipped; controls which fields are required."""

HugeBand = Literal["none", "1", "2-3", "4+"]
"""Discrete buckets the UI offers for huge-item count input.

The wide ``"4+"`` bucket is bounded at 7 in the enumerator (no real
map has more than ~10 large items across all qualities combined).
"""

HUGE_BAND_RANGE: dict[str, tuple[int, int]] = {
    "none": (0, 0),
    "1":    (1, 1),
    "2-3":  (2, 3),
    "4+":   (4, 7),
}

HUGE_CELLS_PER_QUALITY: dict[int, int] = {
    4: 10,   # 紫品大件: 5×2 加特林重机枪 (31688) / 3×4 可折叠高韧性防护盾 (20082)
    5: 12,   # 金品巨物最小: 3×4 重型全生态作战防弹衣 (74745) / 波斯毯 / 分析仪 / 无人作战车
    6: 12,   # 红品巨物最小: 3×4 单兵外骨骼 (305920) / 重型巡航摩托车 / 相控阵雷达
}
# Purple uses a relaxed ≥10-cell threshold because the game data has
# only 1 item ≥ 12 cells but a few 5×2=10 / 2×5=10 items the player
# can plausibly identify as "large" (notably 加特林重机枪).


def aisha_can_observe_huge(quality: int) -> bool:
    """Aisha sees outlines only for the purple bucket; for gold/red she guesses.

    This is the central asymmetry between the two heroes' observation
    forms: the UI should grey-out non-purple huge inputs in Aisha mode.
    """
    return quality == 4


# --- Standard tool loadouts (refined 2026-05-15 per user playtesting) ---
#
# Tool-name → target-quality mapping (per BattleItem.txt, verified 2026-05-15):
#   普品 → white+green (q=1+2)   良品 → blue (q=3)
#   优品 → purple (q=4)          极品 → gold (q=5)   珍品 → red (q=6)

# 伊森 default kit (5 slots, 4 cheap + 1 gold):
#   普品扫描   (cheap)   → white-green total cells
#   良品扫描   (cheap)   → blue total cells
#   优品估价   (cheap)   → purple value sum
#   优品均格   (cheap)   → purple avg cells (decimal-truncation leak)
#   极品估价   (gold)    → gold value sum   (swap 极品扫描 if cells-bias preferred)
ETHAN_DEFAULT_LOADOUT: tuple[str, ...] = (
    "普品扫描",
    "良品扫描",
    "优品估价",
    "优品均格",
    "极品估价",
)

# 伊森 alt kit: trade purple-value for category info via 随机抽检.
# Useful when the player wants category breakdown (lets us pre-filter
# the value brute force by category before per-cell computation).
ETHAN_ALT_LOADOUT: tuple[str, ...] = (
    "普品扫描",
    "良品扫描",
    "随机抽检(1)",     # reveals 1 full item (incl. category)
    "优品均格",
    "极品估价",
)

# 艾莎 default kit (5 slots; her hero skill already pins outline+quality
# for q=1..4, so she leans on per-item reveals + warehouse-size + gold
# value/cells to pick off the remaining unknowns):
#   随机抽检(2) (low)    → 2 full items revealed
#   随机抽检(1) (low)    → 1 full item revealed
#   宝光四鉴   (mid)     → quality of 4 random items
#   极品估价 OR 极品扫描 (gold) → gold value sum or total cells
#   总仓储空间 (gold)    → warehouse total cells
AISHA_DEFAULT_LOADOUT: tuple[str, ...] = (
    "随机抽检(2)",
    "随机抽检(1)",
    "宝光四鉴",
    "极品估价",
    "总仓储空间",
)

# Catalogue keyed by hero mode for UI defaults / Phase 2 contrast MC.
STANDARD_LOADOUTS: dict[HeroMode, tuple[str, ...]] = {
    "ethan": ETHAN_DEFAULT_LOADOUT,
    "aisha": AISHA_DEFAULT_LOADOUT,
}

# --- Battle-item silver prices, used by Phase 2 tool-ROI math ---
#
# User-reported live-game medians (2026-05-15). The actual price fluctuates
# session-to-session ("有的时候是更贵有的时候是更便宜"); ROI tables should
# report sensitivity to a ±30% band on top of these point estimates.
TOOL_PRICE_BY_RARITY: dict[str, int] = {
    "white":  1_200,    # 普品扫描 类
    "green":  2_500,    # 良品扫描 类
    "blue":   20_000,   # 优品扫描 / 估价 / 均格 类 (q=4 purple reads)
    "purple": 35_000,   # 极品估价 类 (q=5 gold reads)
    "gold":   50_000,   # 珍品扫描 / 估价 / 均格 类 (q=6 red reads); placeholder
}

# Tool-name-specific overrides (use when the tool's price diverges from
# its quality-rarity tier). Phase 2 ROI code should call ``tool_price()``
# below rather than indexing TOOL_PRICE_BY_RARITY directly.
TOOL_PRICE_OVERRIDES: dict[str, int] = {
    "总仓储空间": 55_000,        # user-confirmed 2026-05-15
}


def tool_price(tool_name: str, rarity: str = "gold") -> int:
    """Resolve the silver price for ``tool_name``.

    Falls back to ``TOOL_PRICE_BY_RARITY[rarity]`` if no override is set
    for this specific tool.
    """
    if tool_name in TOOL_PRICE_OVERRIDES:
        return TOOL_PRICE_OVERRIDES[tool_name]
    return TOOL_PRICE_BY_RARITY[rarity]


@dataclass
class QualityBucketObs:
    """Everything the player knows about one quality bucket.

    All fields are optional at the dataclass level; the inference engine
    will raise if a required field (per the hero mode) is missing.

    Huge-item input is a **band** (``"none"`` / ``"1"`` / ``"2-3"`` /
    ``"4+"``). Without ``huge_cells_override``, enumeration uses the
    quality's **minimum** huge footprint (10 purple / 12 gold / 12 red).
    ``★`` UI selections set ``huge_cells_override`` to the item's exact
    cell count. MC filtering uses **huge count band only**, not per-item
    cells (by design).
    """

    quality: int   # 1=白 … 6=红
    avg_cells: Reading | None = None
    total_cells: int | None = None        # exact, from scan tool or map
    total_cells_approx: int | None = None # player estimate, soft prior only
    count: int | None = None              # X品存量
    value_sum: int | None = None          # X品估价 silver
    avg_value: float | None = None        # X品均价（每件均价 silver；某些地图 R3 hint）
    value_range: tuple[int, int] | None = None
    huge_band: HugeBand = "none"
    huge_cells_override: int = 0          # if set, beats the per-quality default

    def huge_count_range(self) -> tuple[int, int]:
        """Min and max huge-item count from the band."""
        return HUGE_BAND_RANGE[self.huge_band]

    def huge_cells_per_item(self) -> int:
        """Cells consumed by one huge item in this quality (UI-side spec)."""
        if self.huge_cells_override:
            return self.huge_cells_override
        return HUGE_CELLS_PER_QUALITY.get(self.quality, 12)

    def min_huge_cells(self) -> int:
        return self.huge_count_range()[0] * self.huge_cells_per_item()

    def max_huge_cells(self) -> int:
        return self.huge_count_range()[1] * self.huge_cells_per_item()


@dataclass
class SessionObs:
    """All inputs for one auction session."""

    map_id: int
    hero: HeroMode
    warehouse_total_cells: int | None = None
    warehouse_total_cells_approx: int | None = None
    total_item_count: int | None = None
    """Total number of items in the warehouse, when revealed by a map hint
    (some 别墅 maps surface ``X 件藏品`` as a R1/R3 hint) or by a tool such
    as Aisha's R4 ``全量轮廓`` / ``总藏品数量`` reveal. Used by the joint
    inference engine as a cross-bucket constraint: ``sum(count_q) == total``.
    None means the player did not provide this hint."""
    buckets: dict[int, QualityBucketObs] = field(default_factory=dict)

    def warehouse_capacity(self) -> int:
        """Best estimate of total cabinet cells."""
        if self.warehouse_total_cells is not None:
            return self.warehouse_total_cells
        if self.warehouse_total_cells_approx is not None:
            return self.warehouse_total_cells_approx
        return 159   # fallback: big shipwreck size


@dataclass(frozen=True)
class BucketCandidate:
    """One ``(total_cells, count)`` candidate for a quality bucket, with its rank score."""

    quality: int
    total_cells: int
    count: int
    avg_match: bool        # True iff candidate matches the avg_cells reading exactly
    value_score: float     # value_consistency_score (lower = better)
    cells_score: float     # |total_cells - estimate_from_value| / total_cells
    composite: float       # weighted sum used for ranking (lower = better)
    is_db_matched: bool = False
    """True iff this candidate's (count==1, total_cells) matches a unique
    Item.txt price hit (exact ±0.5% then ±2%). Used by UI for green ✅."""


def _check_required_fields(session: SessionObs) -> list[str]:
    """Return a list of human-readable missing-field warnings.

    Not raised — the engine still tries to return candidates, but the
    caller (a Streamlit UI) can surface these to ask the user to fill in.
    """
    issues: list[str] = []
    if session.warehouse_total_cells is None and session.warehouse_total_cells_approx is None:
        issues.append("warehouse_total_cells: required (exact or approximate)")
    red = session.buckets.get(6)
    if red and red.value_range is None and red.value_sum is None:
        issues.append("red.value_range: required (red variance too high)")
    if session.hero == "ethan":
        for q in (1, 2, 3):
            b = session.buckets.get(q)
            if b is not None and b.total_cells is None:
                issues.append(f"quality {q} total_cells: required in Ethan mode")
    # Aisha cannot observe huge items in gold/red — if the player set a
    # non-"none" band for those qualities in Aisha mode they likely
    # confused herself with Ethan; warn rather than error.
    if session.hero == "aisha":
        for q in (5, 6):
            b = session.buckets.get(q)
            if b is not None and b.huge_band != "none":
                issues.append(
                    f"quality {q} huge_band: Aisha cannot observe huge "
                    f"items for non-purple quality; treat as guess"
                )
    return issues


# --- Item-DB single-item lookup (lazy, cached) ---
# Used to boost candidates when count=1 + value_sum given: e.g. value=24435
# at q=5 maps to 手稿驾驶证页 (1×2 = 2 cells) — the prior-only ranking would
# guess 3 cells (≈ 24435 / pcv_default[5]=9400), which is wrong for this
# specific item. By looking up Item.txt we can pin the right cell count.
#
# Also exposes the per-quality maximum cells/item so the enumerator can
# reject physically-impossible singletons like "(35, 1) purple": no
# purple item has 35 cells (max purple = 12 cells = 折叠防护盾).
_ITEM_DB_BY_QUALITY: dict[int, list[tuple[int, int]]] | None = None
_MAX_CELLS_PER_ITEM_BY_QUALITY: dict[int, int] | None = None
_MAX_VALUE_PER_ITEM_BY_QUALITY: dict[int, int] | None = None
# Conservative fallback (used when Item.txt cannot be located): allow up
# to 24 cells/item across the board, slightly above the highest known
# huge item (red/gold huge = 18 cells, blue 墙面涂鸦墙 = 20 cells).
_MAX_CELLS_PER_ITEM_FALLBACK = 24
_MAX_VALUE_PER_ITEM_FALLBACK = 10**9
# Item-DB value match tiers (enumeration boost only — MC filter unchanged).
EXACT_VALUE_TOL_PCT = 0.005
FALLBACK_VALUE_TOL_PCT = 0.02


@dataclass(frozen=True, slots=True)
class SingleItemValueLookup:
    """Result of Item.txt price lookup for one quality bucket."""

    boost_cells: frozenset[int]
    ambiguous: bool
    over_max: bool
    tier: Literal["none", "exact", "tolerance"]


def _load_item_db_by_quality() -> dict[int, list[tuple[int, int]]]:
    """Lazy-load Item.txt and group `(value, cells)` per quality.

    Returns ``{}`` (and never raises) if Item.txt cannot be located — the
    caller must treat the empty result as "no DB boost available".
    Also populates ``_MAX_CELLS_PER_ITEM_BY_QUALITY`` as a side-effect.
    """
    global _ITEM_DB_BY_QUALITY, _MAX_CELLS_PER_ITEM_BY_QUALITY
    global _MAX_VALUE_PER_ITEM_BY_QUALITY
    if _ITEM_DB_BY_QUALITY is not None:
        return _ITEM_DB_BY_QUALITY
    try:
        from pathlib import Path

        from bidking_lab.extract.item_table import load_item_table

        here = Path(__file__).resolve()
        candidates = [
            Path("data/raw/tables/Item.txt"),
            here.parent.parent.parent.parent / "data" / "raw" / "tables" / "Item.txt",
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            _ITEM_DB_BY_QUALITY = {}
            _MAX_CELLS_PER_ITEM_BY_QUALITY = {}
            _MAX_VALUE_PER_ITEM_BY_QUALITY = {}
            return _ITEM_DB_BY_QUALITY
        items = load_item_table(path)
        db: dict[int, list[tuple[int, int]]] = {}
        max_cells: dict[int, int] = {}
        max_value: dict[int, int] = {}
        for it in items.values():
            cells = it.shape_w * it.shape_h
            if cells <= 0:
                continue
            if it.value > 0:
                db.setdefault(it.quality, []).append((it.value, cells))
                if it.value > max_value.get(it.quality, 0):
                    max_value[it.quality] = it.value
            if cells > max_cells.get(it.quality, 0):
                max_cells[it.quality] = cells
        _ITEM_DB_BY_QUALITY = db
        _MAX_CELLS_PER_ITEM_BY_QUALITY = max_cells
        _MAX_VALUE_PER_ITEM_BY_QUALITY = max_value
    except Exception:                                          # noqa: BLE001
        _ITEM_DB_BY_QUALITY = {}
        _MAX_CELLS_PER_ITEM_BY_QUALITY = {}
        _MAX_VALUE_PER_ITEM_BY_QUALITY = {}
    return _ITEM_DB_BY_QUALITY


def _max_value_per_single_item(quality: int) -> int:
    """Largest ``Item.value`` at ``quality`` (single-item price ceiling)."""
    _load_item_db_by_quality()
    if _MAX_VALUE_PER_ITEM_BY_QUALITY is None:
        return _MAX_VALUE_PER_ITEM_FALLBACK
    return _MAX_VALUE_PER_ITEM_BY_QUALITY.get(
        quality, _MAX_VALUE_PER_ITEM_FALLBACK,
    )


def _value_in_band(target: int, item_value: int, tol_pct: float) -> bool:
    lo = target * (1.0 - tol_pct)
    hi = target * (1.0 + tol_pct)
    return lo <= item_value <= hi


def _cells_with_exact_item_value(quality: int, value: int) -> set[int]:
    """Footprints whose ``Item.value`` equals ``value`` exactly (no tolerance)."""
    db = _load_item_db_by_quality()
    return {cells for item_value, cells in db.get(quality, []) if item_value == value}


def _distinct_cells_for_value(
    quality: int,
    value: int,
    *,
    tol_pct: float,
) -> set[int]:
    db = _load_item_db_by_quality()
    items = db.get(quality, [])
    if not items or value <= 0:
        return set()
    return {
        cells
        for item_value, cells in items
        if _value_in_band(value, item_value, tol_pct)
    }


def lookup_single_item_value(quality: int, value: int) -> SingleItemValueLookup:
    """Match ``value_sum`` to Item.txt for enumeration boost (not MC).

    * ``value`` above the per-quality max item price → no boost (combo hint).
    * Exact tier (±0.5%) then fallback (±2%).
    * Boost only when exactly one distinct ``cells`` matches; multiple
      cell footprints at the same tier → ``ambiguous`` (no boost).
    """
    if value <= 0:
        return SingleItemValueLookup(
            frozenset(), ambiguous=False, over_max=False, tier="none",
        )
    if value > _max_value_per_single_item(quality):
        return SingleItemValueLookup(
            frozenset(), ambiguous=False, over_max=True, tier="none",
        )
    exact_cells = _cells_with_exact_item_value(quality, value)
    if len(exact_cells) == 1:
        return SingleItemValueLookup(
            frozenset(exact_cells),
            ambiguous=False,
            over_max=False,
            tier="exact",
        )
    if len(exact_cells) > 1:
        return SingleItemValueLookup(
            frozenset(),
            ambiguous=True,
            over_max=False,
            tier="exact",
        )
    for tier, tol in (
        ("exact", EXACT_VALUE_TOL_PCT),
        ("tolerance", FALLBACK_VALUE_TOL_PCT),
    ):
        cells_set = _distinct_cells_for_value(quality, value, tol_pct=tol)
        if len(cells_set) == 1:
            return SingleItemValueLookup(
                frozenset(cells_set),
                ambiguous=False,
                over_max=False,
                tier=tier,  # type: ignore[arg-type]
            )
        if len(cells_set) > 1:
            return SingleItemValueLookup(
                frozenset(),
                ambiguous=True,
                over_max=False,
                tier=tier,  # type: ignore[arg-type]
            )
    return SingleItemValueLookup(
        frozenset(), ambiguous=False, over_max=False, tier="none",
    )


def _single_item_match_cells(
    quality: int, value: int, *, tol_pct: float = 0.02
) -> set[int]:
    """Cell counts eligible for DB boost (see :func:`lookup_single_item_value`)."""
    if tol_pct != FALLBACK_VALUE_TOL_PCT:
        lo = value * (1.0 - tol_pct)
        hi = value * (1.0 + tol_pct)
        db = _load_item_db_by_quality()
        items = db.get(quality, [])
        if not items or value <= 0:
            return set()
        return {cells for v, cells in items if lo <= v <= hi}
    return set(lookup_single_item_value(quality, value).boost_cells)


def _single_item_match_names(
    quality: int,
    value: int,
    *,
    cells: int | None = None,
    tol_pct: float = 0.02,
) -> list[tuple[str, int, int]]:
    """Return ``[(name, cells, value), ...]`` for items at ``quality``
    whose value is within ±tol_pct of ``value``. If ``cells`` is given,
    additionally filter by that cell count.

    Returns ``[]`` when no match (or DB unavailable). Used by the UI to
    surface item names in green ✅ confirmations like
    "已锁定 2 格 / 1 件 — 可能为 手稿驾驶证页".
    """
    try:
        from pathlib import Path

        from bidking_lab.extract.item_table import load_item_table

        here = Path(__file__).resolve()
        candidates = [
            Path("data/raw/tables/Item.txt"),
            here.parent.parent.parent.parent / "data" / "raw" / "tables" / "Item.txt",
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path is None or value <= 0:
            return []
        items = load_item_table(path)
    except Exception:                                          # noqa: BLE001
        return []
    out: list[tuple[str, int, int]] = []
    for it in items.values():
        if it.quality != quality or it.value <= 0:
            continue
        c = it.shape_w * it.shape_h
        if c <= 0:
            continue
        if not _value_in_band(value, it.value, tol_pct):
            continue
        if cells is not None and c != cells:
            continue
        out.append((it.name, c, it.value))
    return out


# When the player fills this many reading fields on one bucket, ``avg_value``
# tolerance widens in ``candidates_for_bucket`` only (MC path unchanged).
JOINT_CONSTRAINT_RELAX_THRESHOLD = 4


def active_reading_constraint_count(bucket: QualityBucketObs) -> int:
    """Count filled fields that prune enumeration (not used by MC filter)."""
    n = 0
    if bucket.total_cells is not None:
        n += 1
    if bucket.count is not None:
        n += 1
    if bucket.avg_cells is not None:
        n += 1
    if bucket.value_sum is not None and bucket.value_sum > 0:
        n += 1
    if bucket.avg_value is not None and bucket.avg_value > 0:
        n += 1
    if bucket.huge_band != "none":
        n += 1
    if bucket.value_range is not None:
        lo, hi = bucket.value_range
        if lo > 0 or hi > 0:
            n += 1
    return n


def _max_cells_per_single_item(quality: int) -> int:
    """Largest possible cells/item at ``quality`` from Item.txt.

    Used to reject physically-impossible candidates such as ``(35, 1)``
    purple — no purple item has 35 cells. Returns
    ``_MAX_CELLS_PER_ITEM_FALLBACK`` if the DB is unavailable.
    """
    _load_item_db_by_quality()       # populate cache as side-effect
    if _MAX_CELLS_PER_ITEM_BY_QUALITY is None:
        return _MAX_CELLS_PER_ITEM_FALLBACK
    return _MAX_CELLS_PER_ITEM_BY_QUALITY.get(
        quality, _MAX_CELLS_PER_ITEM_FALLBACK
    )


def relax_bucket_for_enumeration_preview(
    bucket: QualityBucketObs,
    *,
    warehouse_capacity: int,
    other_known_cells: int = 0,
) -> tuple[QualityBucketObs, list[str]]:
    """Drop optional fields that make enumeration empty (OCR residue).

    Only affects the candidate preview path — MC / filter_truths unchanged.
    """
    from dataclasses import replace

    try:
        if candidates_for_bucket(
            bucket,
            warehouse_capacity=warehouse_capacity,
            other_known_cells=other_known_cells,
        ):
            return bucket, []
    except Exception:
        return bucket, []

    dropped: list[str] = []
    relaxed = bucket
    for field in ("avg_cells", "avg_value", "count", "value_sum"):
        val = getattr(relaxed, field)
        if val is None:
            continue
        if field == "avg_value" and (not val or float(val) <= 0):
            continue
        if field == "count" and int(val) <= 0:
            continue
        if field == "value_sum" and int(val) <= 0:
            continue
        trial = replace(relaxed, **{field: None})
        try:
            ok = candidates_for_bucket(
                trial,
                warehouse_capacity=warehouse_capacity,
                other_known_cells=other_known_cells,
            )
        except Exception:
            ok = []
        if ok:
            dropped.append(field)
            relaxed = trial

    if relaxed.total_cells == 0:
        relaxed = replace(relaxed, total_cells=None)
        dropped.append("total_cells_zero")

    return relaxed, dropped


def candidates_for_bucket(
    bucket: QualityBucketObs,
    *,
    warehouse_capacity: int,
    other_known_cells: int = 0,
    max_count: int = 50,
) -> list[BucketCandidate]:
    """Brute-force enumeration for one quality bucket.

    The enumeration is pruned at three levels:

    1. **Hard ceiling on total cells**: ``warehouse_capacity -
       other_known_cells`` (the budget remaining for this bucket).
    2. **Huge-cells floor**: ``total_cells >= huge_cells``,
       ``count >= huge_count``.
    3. **avg_cells reading**: if provided, only candidates matching the
       game-display rule survive.

    The output list is sorted ascending by composite score. The top-3
    are what the UI shows to the user.
    """
    capacity = max(0, warehouse_capacity - other_known_cells)
    huge_min, huge_max = bucket.huge_count_range()
    huge_per_item = bucket.huge_cells_per_item()

    # Item-DB single-item boost: when value_sum is given, look up which
    # (cells) values correspond to a real item at this quality with value
    # ≈ value_sum. The boost is applied only to candidates with ``count==1``,
    # so explicit count!=1 inputs are unaffected. When ``count`` is not
    # specified, the matched single-item solution is lifted ahead of the
    # multi-item priors so the player sees "value=24435 → 2格/1件
    # (手稿驾驶证页)" without having to also type count=1.
    db_boost_cells: set[int] = set()
    if bucket.value_sum is not None and bucket.value_sum > 0:
        db_boost_cells = set(
            lookup_single_item_value(bucket.quality, bucket.value_sum).boost_cells,
        )

    # Physical max cells/item per quality (from Item.txt). Used to reject
    # impossibly-large singletons like "(35, 1) purple" — the largest
    # purple item is 12 cells.
    max_cpi = _max_cells_per_single_item(bucket.quality)

    base: list[tuple[int, int]]
    if bucket.avg_cells is not None:
        # Display rule already filters tightly; pull candidates from there.
        base = enumerate_candidates(
            bucket.avg_cells,
            max_count=max_count,
            max_total_cells=min(capacity, 252),
        )
    else:
        # No avg reading → enumerate everything within budget. Floor the
        # count at max(1, huge_min); floor the cells at huge_min cells.
        min_cells_floor = huge_min * huge_per_item
        # Cap count: can't have more items than cells (each item ≥ 1 cell).
        effective_max_cells = bucket.total_cells if bucket.total_cells is not None else capacity
        effective_max_count = min(max_count, max(1, effective_max_cells))
        base = [
            (tc, c)
            for c in range(max(1, huge_min), effective_max_count + 1)
            for tc in range(min_cells_floor, capacity + 1)
        ]

    out: list[BucketCandidate] = []
    for total_cells, count in base:
        if bucket.total_cells is not None and total_cells != bucket.total_cells:
            continue
        if bucket.count is not None and count != bucket.count:
            continue
        if total_cells > capacity:
            continue
        # Physical filter: cells/item cannot exceed the largest item of
        # this quality. Integer-safe form of (total_cells / count > max_cpi).
        if count > 0 and total_cells > max_cpi * count:
            continue
        # avg_value (per-item average price) hard filter — the game's
        # R3 hint surfaces this directly. We test it against either the
        # user-given value_sum (tight) or the per-cell prior estimate
        # (loose). Tolerance widens correspondingly.
        if bucket.avg_value is not None and bucket.avg_value > 0:
            if bucket.value_sum is not None and bucket.value_sum > 0:
                implied_avg = bucket.value_sum / max(1, count)
                tol = 0.10
            else:
                pcv = PER_CELL_VALUE_DEFAULT.get(bucket.quality, 0)
                if pcv <= 0:
                    implied_avg = 0
                else:
                    implied_avg = (pcv * total_cells) / max(1, count)
                tol = 0.25
            # Joint-field softening: many simultaneous readings AND away
            # can zero-out enumeration; widen avg_value tol only (MC untouched).
            if active_reading_constraint_count(bucket) >= JOINT_CONSTRAINT_RELAX_THRESHOLD:
                tol = (
                    0.18
                    if bucket.value_sum is not None and bucket.value_sum > 0
                    else 0.35
                )
            if implied_avg <= 0:
                continue
            if abs(implied_avg - bucket.avg_value) / bucket.avg_value > tol:
                continue

        # Huge-band constraint: there must exist an integer ``h`` in
        # [huge_min, huge_max] such that ``h <= count`` and
        # ``h * huge_per_item <= total_cells``. Otherwise the candidate
        # is incompatible with the player-reported huge band.
        h_lo = huge_min
        h_hi = min(huge_max, count, total_cells // max(1, huge_per_item))
        if h_hi < h_lo:
            continue
        # Pick the value of h that minimizes value-side error (the
        # engine doesn't need to commit to a specific h here; the band
        # is just a hard filter and a soft prior on huge cells).
        huge_cells = h_lo * huge_per_item

        avg_match = (
            bucket.avg_cells is None
            or is_compatible(bucket.avg_cells, total_cells, count)
        )
        value_score = value_consistency_score(
            bucket.quality,
            total_cells,
            value_sum=bucket.value_sum,
            value_range=bucket.value_range,
            huge_cells=huge_cells,
        )

        if bucket.value_sum is not None:
            implied_cells = estimate_total_cells(
                bucket.quality,
                bucket.value_sum,
                huge_cells=huge_cells,
            )
            cells_score = abs(total_cells - implied_cells) / max(1, total_cells)
        else:
            cells_score = 0.0

        # Prior on average cells/item: drop-weighted averages from game data.
        _EXPECTED_AVG_CELLS: dict[int, float] = {
            1: 2.0, 2: 2.5, 3: 3.5, 4: 3.5, 5: 4.5, 6: 5.0,
        }
        expected_avg = _EXPECTED_AVG_CELLS.get(bucket.quality, 3.0)
        candidate_avg = total_cells / max(1, count)
        avg_prior_penalty = abs(candidate_avg - expected_avg) / expected_avg

        # Composite: 70% value-side fit + 30% cells-side fit, then a
        # prior-based penalty on avg cells/item and a small Occam penalty.
        composite = (0.7 * value_score + 0.3 * cells_score
                     + 0.15 * avg_prior_penalty + 0.001 * count)

        # Apply item-DB boost: count=1 candidates whose total_cells matches
        # a unique Item.txt price hit get composite ×0.001 so they beat
        # tight multi-item fits (e.g. 9/2 vs 8/1 at value_sum=88473).
        is_db_match = count == 1 and total_cells in db_boost_cells
        if is_db_match:
            composite *= 0.001

        out.append(
            BucketCandidate(
                quality=bucket.quality,
                total_cells=total_cells,
                count=count,
                avg_match=avg_match,
                value_score=value_score,
                cells_score=cells_score,
                composite=composite,
                is_db_matched=is_db_match,
            )
        )

    out.sort(key=lambda c: c.composite)
    return out


def top_k_for_session(
    session: SessionObs,
    *,
    k: int = 3,
) -> dict[int, list[BucketCandidate]]:
    """Top-K candidates per quality bucket, processed in priority order.

    "Priority order" handles the huge-item-first cut: gold and red
    buckets are solved first (where the player likely flagged huge
    items), the chosen total-cells contributions are subtracted from
    the warehouse budget, then purple, then white-green/blue.

    This is intentional brute-force — typical session sizes (<= 252
    cells, <= 50 count per bucket) leave well under 10^4 candidate
    pairs per bucket, total wall time is sub-second on a laptop.
    """
    capacity = session.warehouse_capacity()
    other_known_cells = 0
    out: dict[int, list[BucketCandidate]] = {}

    for q in (6, 5, 4, 3, 2, 1):
        bucket = session.buckets.get(q)
        if bucket is None:
            continue
        cands = candidates_for_bucket(
            bucket,
            warehouse_capacity=capacity,
            other_known_cells=other_known_cells,
        )
        if not cands:
            out[q] = []
            continue
        out[q] = cands[:k]
        # Subtract the top-1 cells from the remaining budget for the
        # next, less-valuable quality (a coarse but effective greedy
        # approach).
        other_known_cells += cands[0].total_cells

    return out


__all__ = (
    "HeroMode",
    "HugeBand",
    "HUGE_BAND_RANGE",
    "HUGE_CELLS_PER_QUALITY",
    "ETHAN_DEFAULT_LOADOUT",
    "ETHAN_ALT_LOADOUT",
    "AISHA_DEFAULT_LOADOUT",
    "STANDARD_LOADOUTS",
    "TOOL_PRICE_BY_RARITY",
    "TOOL_PRICE_OVERRIDES",
    "tool_price",
    "aisha_can_observe_huge",
    "QualityBucketObs",
    "SessionObs",
    "BucketCandidate",
    "SingleItemValueLookup",
    "EXACT_VALUE_TOL_PCT",
    "FALLBACK_VALUE_TOL_PCT",
    "lookup_single_item_value",
    "candidates_for_bucket",
    "top_k_for_session",
)
