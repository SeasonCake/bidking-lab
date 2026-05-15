"""Hero marginal value via contrast Monte Carlo.

For each trial:
1. Draw K items from the map's flattened pool (same as basic_mc).
2. **Baseline** (no hero): player bids equally on all items, winning
   a random subset limited by rounds. Expected take = mean of sample.
3. **With hero**: hero reveals info → player can rank items by
   estimated value and bid on the best ones first.

The hero's marginal value = E[take_with_hero] - E[take_baseline].

A hero who reveals quality on all items lets the player perfectly
prioritize high-quality items. A hero with only outline info helps
less. The difference shows up as higher selective take.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
from pydantic import BaseModel

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.simulation.basic_mc import FlattenedPool, flatten_pool
from bidking_lab.simulation.hero_skills import compute_info_score


class HeroValueResult(BaseModel):
    """Contrast MC result for one hero on one map."""

    hero_id: int
    hero_name: str
    map_id: int
    map_name: str
    n_trials: int

    baseline_mean: float
    hero_mean: float
    marginal_value: float
    marginal_pct: float

    baseline_q50: int
    hero_q50: int


def _sample_session_items(
    fp: FlattenedPool,
    k: int,
    items_db: Mapping[int, Item],
    rng: np.random.Generator,
) -> list[Item]:
    """Draw k items from flattened pool, returning Item objects."""
    if not fp.item_ids:
        return []
    probs = np.array(fp.probabilities)
    idx = rng.choice(len(fp.item_ids), size=k, replace=True, p=probs)
    return [items_db[fp.item_ids[i]] for i in idx]


def simulate_hero_value(
    hero_id: int,
    map_id: int,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    rounds_to_bid: int | None = None,
    n_trials: int = 10_000,
    rng: np.random.Generator | None = None,
) -> HeroValueResult:
    """Compare a hero vs no-hero on a given map.

    ``rounds_to_bid``: how many items the player can actually win per
    session (limited by rounds / budget). Defaults to map's rounds_total.
    If rounds_total > K (items in session), the player can bid on
    everything, so hero info has less marginal value.
    """
    rng = rng or np.random.default_rng()
    bid_map = maps[map_id]
    k_lo = bid_map.items_per_session_min
    k_hi = bid_map.items_per_session_max
    max_bids = rounds_to_bid or bid_map.rounds_total

    # Build pool. For anthology maps, pick a random sub-pool per trial.
    if not bid_map.sub_pool_weights:
        fps = [flatten_pool(bid_map.drop_pool_id, drops, items)]
        fp_p = np.array([1.0])
    else:
        fps_list = []
        w_list = []
        for sub_id, w in bid_map.sub_pool_weights:
            sub = maps.get(sub_id)
            if sub is None:
                continue
            fp = flatten_pool(sub.drop_pool_id, drops, items)
            if fp.item_ids:
                fps_list.append(fp)
                w_list.append(w)
        fps = fps_list or [FlattenedPool(item_ids=[], probabilities=[], n_min=[], n_max=[], values=[])]
        fp_p = np.array(w_list or [1.0], dtype=np.float64)
        fp_p /= fp_p.sum()

    from bidking_lab.simulation.hero_skills import HERO_SKILLS
    hero_name = HERO_SKILLS[hero_id].name if hero_id in HERO_SKILLS else f"hero_{hero_id}"

    baseline_totals = np.zeros(n_trials)
    hero_totals = np.zeros(n_trials)

    for t in range(n_trials):
        fp_idx = int(rng.choice(len(fps), p=fp_p)) if len(fps) > 1 else 0
        fp = fps[fp_idx]
        k = int(rng.integers(k_lo, k_hi + 1))
        session_items = _sample_session_items(fp, k, items, rng)
        if not session_items:
            continue

        values = np.array([it.value for it in session_items], dtype=np.float64)
        n_biddable = min(max_bids, len(session_items))

        # Baseline: random bid order → expected take is mean of random n_biddable subset
        random_idx = rng.choice(len(session_items), size=n_biddable, replace=False)
        baseline_totals[t] = values[random_idx].sum()

        # With hero: rank items by (info_score * value + noise), bid on top n_biddable
        info_scores = compute_info_score(hero_id, session_items)
        # Player's estimated value: known items use true value, unknown use session mean
        mean_val = float(values.mean()) if len(values) > 0 else 0.0
        estimated = np.array([
            values[i] if info_scores[i] >= 0.7 else  # quality or better → knows value tier
            values[i] * 0.6 + mean_val * 0.4 if info_scores[i] >= 0.3 else  # outline → partial
            mean_val
            for i in range(len(session_items))
        ])
        # Add small noise to break ties
        estimated += rng.normal(0, 1, size=len(estimated))
        top_idx = np.argsort(estimated)[-n_biddable:]
        hero_totals[t] = values[top_idx].sum()

    return HeroValueResult(
        hero_id=hero_id,
        hero_name=hero_name,
        map_id=map_id,
        map_name=bid_map.name,
        n_trials=n_trials,
        baseline_mean=float(baseline_totals.mean()),
        hero_mean=float(hero_totals.mean()),
        marginal_value=float(hero_totals.mean() - baseline_totals.mean()),
        marginal_pct=float(
            (hero_totals.mean() - baseline_totals.mean()) / baseline_totals.mean() * 100
            if baseline_totals.mean() > 0 else 0.0
        ),
        baseline_q50=int(np.median(baseline_totals)),
        hero_q50=int(np.median(hero_totals)),
    )


__all__ = ("HeroValueResult", "simulate_hero_value")
