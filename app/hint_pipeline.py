"""MC hint computation (no Streamlit imports)."""

from __future__ import annotations

from typing import Any, Callable, Mapping

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.observation import SessionObs
from bidking_lab.inference.posterior import (
    adaptive_filter,
    compute_analytical_estimate,
)


def compute_hint_bundle(
    state: dict[str, Any],
    mc: dict[str, Any],
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    build_session: Callable[[dict[str, Any], Mapping[int, BidMap]], SessionObs],
    sample_truths: Callable[..., list],
    enable_snipe_pass: bool = False,
) -> dict[str, Any] | None:
    """Run MC + filter; return a plain dict for UI rendering."""
    from bidking_lab.inference.readings_validate import check_warehouse_cell_budget

    map_id = state.get("map_id")
    if map_id is None or not state.get("warehouse_cells"):
        return None
    if check_warehouse_cell_budget(state):
        return None

    n_trials = int(mc["n_trials"])
    seed = int(mc["seed"])
    warehouse_tol = int(mc["warehouse_tol"])
    purple_tol = int(mc.get("purple_tol", 4))

    session = build_session(state, maps)
    truths = sample_truths(int(map_id), n_trials=n_trials, seed=seed)
    all_values = [t.total_value() for t in truths]

    filter_result = adaptive_filter(
        truths, session, min_samples=30,
        warehouse_tol_levels=(
            warehouse_tol, warehouse_tol, max(warehouse_tol, 12),
        ),
    )
    conditional_truths = filter_result.truths
    conditional_values = [t.total_value() for t in conditional_truths]
    analytical = compute_analytical_estimate(session)

    snipe = None
    pass_rec = None
    if enable_snipe_pass:
        from bidking_lab.inference.snipe import (
            compute_pass_recommendation,
            compute_snipe_recommendation,
        )

        snipe = compute_snipe_recommendation(
            session, maps=maps, drops=drops, items=items,
            n_trials=n_trials, warehouse_tolerance=warehouse_tol,
            purple_tolerance=purple_tol, truths=truths,
        )
        pass_rec = compute_pass_recommendation(
            session, maps=maps, drops=drops, items=items,
            n_trials=n_trials, warehouse_tolerance=warehouse_tol,
            purple_tolerance=purple_tol, truths=truths,
        )

    return {
        "session": session,
        "filter_result": filter_result,
        "conditional_truths": conditional_truths,
        "conditional_values": conditional_values,
        "all_values": all_values,
        "analytical": analytical,
        "snipe": snipe,
        "pass_rec": pass_rec,
        "n_trials": n_trials,
        "seed": seed,
        "warehouse_tol": warehouse_tol,
        "purple_tol": purple_tol,
        "map_id": int(map_id),
        "warehouse_cells": int(state["warehouse_cells"]),
    }
