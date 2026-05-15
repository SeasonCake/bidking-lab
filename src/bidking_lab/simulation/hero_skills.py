"""Hero skill information model for MC.

Each hero reveals partial information about session items. We model
the **information coverage** as a per-item score in [0, 1]:

  1.0 = player knows the item's exact value (or full info)
  0.7 = player knows the item's quality tier
  0.3 = player knows the item's outline/shape
  0.1 = player has a statistical aggregate (count, avg cells)
  0.0 = player knows nothing about this item

A "rational player" bids on items in descending order of
*expected value given revealed info*. Items with quality revealed
can be ranked by quality tier (higher quality ≈ higher value);
items with no info are valued at the session's mean.

For the MC contrast, we compare:
  - **baseline**: no hero, all items equally unknown → bid randomly
  - **with hero**: hero reveals info → player bids on best-known items first

The difference in expected net value is the hero's **marginal value**.

Implementation note: rather than hard-coding 20 hero-specific functions,
we define a small DSL of "skill effects" and compose them. Each hero
maps to a list of effects. Effects are evaluated per-item to produce
the info score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from bidking_lab.extract.item_table import Item


class InfoType(Enum):
    NONE = 0.0
    COUNT_HINT = 0.1
    OUTLINE = 0.3
    QUALITY = 0.7
    VALUE = 1.0
    FULL = 1.0


@dataclass(frozen=True)
class SkillEffect:
    """One component of a hero's skill.

    ``filter_categories``: only items whose category (from Item.txt
    col[5] or our mapped tags) matches. Empty = all items.

    ``filter_qualities``: only items whose quality matches. Empty = all.

    ``info_type``: what's revealed for matching items.

    ``max_items``: if >0, only applies to this many items (randomly
    chosen from the matching set). 0 = unlimited.

    ``per_round``: if >0, this effect fires this many items per round
    rather than all at once. Combined with ``rounds`` to get total.

    ``rounds``: how many rounds this effect fires over.
    """

    info_type: InfoType
    filter_categories: frozenset[int] = field(default_factory=frozenset)
    filter_qualities: frozenset[int] = field(default_factory=frozenset)
    max_items: int = 0
    per_round: int = 0
    rounds: int = 1


# Category IDs from Item.txt col[5] (tags field). These are approximate
# groupings reverse-engineered from item names + hero skill text.
# Not all are needed; we define those referenced by hero skills.
CAT_ANTIQUE = 101       # 文玩古董
CAT_JEWELRY = 102       # 珠宝矿藏
CAT_FASHION = 103       # 时尚潮流
CAT_DIGITAL = 104       # 数码电子
CAT_MEDICAL = 105       # 医疗药品
CAT_WEAPON = 106        # 武器装备
CAT_HOUSEHOLD = 107     # 家居日用
CAT_FOOD = 108          # 食品烹饪
CAT_BOOK = 109          # 书籍绘画
CAT_ENERGY = 110        # 能源交通


@dataclass(frozen=True)
class HeroSkillProfile:
    hero_id: int
    name: str
    tier: int
    effects: tuple[SkillEffect, ...]
    description: str = ""


def _e(info: InfoType, cats: frozenset[int] = frozenset(),
       quals: frozenset[int] = frozenset(), max_items: int = 0,
       per_round: int = 0, rounds: int = 1) -> SkillEffect:
    return SkillEffect(info, cats, quals, max_items, per_round, rounds)


# All 20 heroes. Skill breakdown from docs/hero_skill_schema.md.
HERO_SKILLS: dict[int, HeroSkillProfile] = {
    101: HeroSkillProfile(101, "法蒂玛", 1, (
        _e(InfoType.QUALITY, frozenset({CAT_ANTIQUE}), max_items=1),  # top-value antique
        _e(InfoType.OUTLINE, frozenset({CAT_ANTIQUE}), max_items=12, per_round=3, rounds=4),
        _e(InfoType.QUALITY, frozenset({CAT_ANTIQUE}), max_items=6, per_round=3, rounds=2),
    )),
    102: HeroSkillProfile(102, "陈美", 1, (
        _e(InfoType.OUTLINE, frozenset({CAT_JEWELRY, CAT_FASHION})),
    )),
    103: HeroSkillProfile(103, "艾莎", 1, (
        _e(InfoType.OUTLINE, quals=frozenset({3})),   # blue outline
        _e(InfoType.OUTLINE, quals=frozenset({2})),   # green outline
        _e(InfoType.OUTLINE, quals=frozenset({1})),   # white outline
    )),
    104: HeroSkillProfile(104, "加布里埃拉", 1, (
        _e(InfoType.QUALITY, max_items=2, per_round=2, rounds=10),
    )),
    105: HeroSkillProfile(105, "塔蒂安娜", 1, (
        _e(InfoType.QUALITY, frozenset({CAT_FASHION})),
        _e(InfoType.OUTLINE, frozenset({CAT_FASHION})),
    )),
    106: HeroSkillProfile(106, "娜奥米", 1, (
        _e(InfoType.OUTLINE, frozenset({CAT_FASHION, CAT_DIGITAL})),
        _e(InfoType.COUNT_HINT, quals=frozenset({5, 6})),  # gold+red count
    )),
    107: HeroSkillProfile(107, "索菲", 1, (
        _e(InfoType.QUALITY, max_items=5),
        _e(InfoType.QUALITY, max_items=2, per_round=2, rounds=9),
    )),
    108: HeroSkillProfile(108, "玛丽亚", 1, (
        _e(InfoType.VALUE, quals=frozenset({1})),   # white total value
        _e(InfoType.VALUE, quals=frozenset({2})),   # green total value
        _e(InfoType.VALUE, quals=frozenset({3})),   # blue total value
        _e(InfoType.QUALITY, quals=frozenset({1, 2, 3})),  # quality shown
    )),
    109: HeroSkillProfile(109, "海琳娜", 1, (
        _e(InfoType.QUALITY, frozenset({CAT_MEDICAL})),
        _e(InfoType.OUTLINE, frozenset({CAT_MEDICAL}), max_items=2, per_round=2, rounds=10),
    )),
    110: HeroSkillProfile(110, "伊莎贝拉", 1, (
        _e(InfoType.OUTLINE, max_items=1),  # top-1 quality item
        _e(InfoType.OUTLINE, frozenset({CAT_JEWELRY}), max_items=4),
    )),
    201: HeroSkillProfile(201, "乔治", 2, (
        _e(InfoType.QUALITY, frozenset({CAT_WEAPON})),
        _e(InfoType.OUTLINE, frozenset({CAT_WEAPON})),
    )),
    202: HeroSkillProfile(202, "卡洛斯", 2, (
        _e(InfoType.OUTLINE, frozenset({CAT_HOUSEHOLD, CAT_DIGITAL})),
        _e(InfoType.QUALITY, frozenset({CAT_HOUSEHOLD, CAT_DIGITAL}), max_items=2, per_round=2, rounds=10),
    )),
    203: HeroSkillProfile(203, "莱昂纳德", 2, (
        _e(InfoType.QUALITY, frozenset({CAT_FOOD})),
        _e(InfoType.QUALITY, frozenset({CAT_ANTIQUE}), max_items=2),
    )),
    204: HeroSkillProfile(204, "艾哈迈德", 2, (
        _e(InfoType.COUNT_HINT),  # total count
        _e(InfoType.COUNT_HINT, quals=frozenset({5})),  # gold avg cells
        _e(InfoType.COUNT_HINT, quals=frozenset({4})),  # purple avg cells
        _e(InfoType.COUNT_HINT, quals=frozenset({3})),  # blue avg cells
        _e(InfoType.COUNT_HINT, quals=frozenset({1, 2})),  # green+white total count
    )),
    205: HeroSkillProfile(205, "伊万", 2, (
        _e(InfoType.OUTLINE, frozenset({CAT_WEAPON, CAT_ENERGY})),
    )),
    206: HeroSkillProfile(206, "武田宏志", 2, (
        _e(InfoType.OUTLINE, frozenset({CAT_BOOK})),
        _e(InfoType.QUALITY, frozenset({CAT_BOOK}), max_items=2, per_round=2, rounds=10),
    )),
    207: HeroSkillProfile(207, "吴起灵", 2, (
        _e(InfoType.COUNT_HINT, frozenset({CAT_ANTIQUE})),
        _e(InfoType.OUTLINE, frozenset({CAT_ANTIQUE})),
        _e(InfoType.QUALITY, frozenset({CAT_ANTIQUE})),
        _e(InfoType.FULL, frozenset({CAT_ANTIQUE}), max_items=0),  # ~1/3 get full info
    )),
    208: HeroSkillProfile(208, "伊森", 2, (
        _e(InfoType.OUTLINE, max_items=5),  # 5 random type outlines
        _e(InfoType.OUTLINE, max_items=2, per_round=2, rounds=4),  # known-quality → outline
        _e(InfoType.OUTLINE),  # R5: ALL outlines
    )),
    209: HeroSkillProfile(209, "维克托", 2, (
        _e(InfoType.COUNT_HINT, quals=frozenset({4, 5})),  # purple+gold count
    )),
    301: HeroSkillProfile(301, "拉文", 0, (
        _e(InfoType.QUALITY),  # R5: all quality (very late)
    )),
}


def compute_info_score(
    hero_id: int,
    session_items: Sequence[Item],
) -> list[float]:
    """Compute per-item info score [0, 1] for a hero + session.

    Returns a list parallel to ``session_items``. The score represents
    how well the player can estimate each item's value given the hero's
    skill revelations.

    Simplified: we take the max info score across all skill effects that
    match each item. In reality some effects are progressive (per-round),
    but for v1 we assume the player eventually gets all the info the
    hero can provide.
    """
    profile = HERO_SKILLS.get(hero_id)
    if profile is None:
        return [0.0] * len(session_items)

    scores = [0.0] * len(session_items)
    for effect in profile.effects:
        matching_indices = []
        for i, item in enumerate(session_items):
            if effect.filter_categories and _item_category(item) not in effect.filter_categories:
                continue
            if effect.filter_qualities and item.quality not in effect.filter_qualities:
                continue
            matching_indices.append(i)

        if effect.max_items > 0 and len(matching_indices) > effect.max_items:
            effective_count = min(
                effect.max_items * max(1, effect.rounds),
                len(matching_indices),
            )
            matching_indices = matching_indices[:effective_count]

        for i in matching_indices:
            scores[i] = max(scores[i], effect.info_type.value)

    return scores


def _item_category(item: Item) -> int:
    """Extract category from Item. Uses the first tag or falls back to raw_row col[5]."""
    if item.tags:
        return item.tags[0]
    try:
        return int(item.raw_row[5])
    except (IndexError, ValueError):
        return 0


__all__ = (
    "CAT_ANTIQUE", "CAT_BOOK", "CAT_DIGITAL", "CAT_ENERGY",
    "CAT_FASHION", "CAT_FOOD", "CAT_HOUSEHOLD", "CAT_JEWELRY",
    "CAT_MEDICAL", "CAT_WEAPON",
    "HERO_SKILLS",
    "HeroSkillProfile",
    "InfoType",
    "SkillEffect",
    "compute_info_score",
)
