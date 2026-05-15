"""Posterior filter + per-bucket statistics for the bid-hint MC pipeline.

This module centralises the "given a list of sampled
:class:`SessionTruth` and the player's :class:`SessionObs`, return the
subset that matches every observation the player provided" operation.

It replaces the previous single-line filter in ``app/streamlit_app.py``
that only conditioned on ``warehouse_total_cells``. Every per-bucket
field the player typed (``total_cells``, ``count``, ``value_sum``,
``value_range``, ``huge_band``) becomes a filter constraint.

Two flavours are exported:

* :func:`filter_truths_by_obs` — single-pass filter at a fixed
  tolerance level. Pure function, easy to test.
* :func:`adaptive_filter` — tries the strict tolerance first, widens
  in two more steps if the strict pass yields too few samples, and
  flags ``low_confidence`` once it had to widen. Returns a structured
  :class:`FilterResult` for the UI to render rationale.

A separate helper :func:`bucket_posterior_stats` computes per-bucket
P10/P50/P90 (cells, count, value_sum, huge_count) on the filtered set,
plus the empirical probability that the bucket is empty. This is what
feeds the new "红品后验估计" card in the Streamlit hint tab — even when
the player never typed any red field, the model can still say
*"based on what you did observe, red has P50 ≈ 6 cells, P(red=0) ≈ 18%"*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from bidking_lab.inference.ground_truth import SessionTruth
from bidking_lab.inference.observation import SessionObs

QUALITIES: tuple[int, ...] = (1, 2, 3, 4, 5, 6)


@dataclass
class FilterResult:
    """Outcome of :func:`adaptive_filter`."""

    truths: list[SessionTruth]
    tol_level: int
    """0 = strict, 1 = relaxed, 2 = very relaxed. The UI shows ⚠️ for level ≥ 1."""
    low_confidence: bool
    n_total: int
    n_final: int
    cells_tol: int
    count_tol: int
    value_rel_tol: float
    warehouse_tol: int
    constraints_applied: list[str] = field(default_factory=list)
    """Human-readable strings like ``"q=4 (cells, count, value)"`` for the rationale."""


def _bucket_truth_fields(truth: SessionTruth, quality: int) -> tuple[int, int, int, int]:
    """Return ``(total_cells, count, value_sum, huge_count)`` for a quality.

    Returns all zeros when the bucket is absent from the sampled truth
    (i.e., the session contained nothing of that quality). That is the
    correct semantics for filtering: if the player observed
    ``red.total_cells = 0``, we want truths with no red items to match.
    """
    b = truth.buckets.get(quality)
    if b is None:
        return 0, 0, 0, 0
    return b.total_cells, b.count, b.value_sum, b.huge_count


def filter_truths_by_obs(
    truths: Sequence[SessionTruth],
    obs: SessionObs,
    *,
    cells_tol: int = 2,
    count_tol: int = 1,
    value_rel_tol: float = 0.10,
    warehouse_tol: int = 8,
) -> list[SessionTruth]:
    """Return truths compatible with every observation at the given tolerances.

    A truth is kept iff:

    * ``|truth.warehouse_total_cells - obs.warehouse_capacity()| <= warehouse_tol``
    * For every quality ``q`` the player filled into ``obs.buckets``:

      - If ``total_cells`` is given: ``|truth_cells - obs_cells| <= cells_tol``
      - If ``count`` is given: ``|truth_count - obs_count| <= count_tol``
      - If ``value_sum`` is given and > 0:
        ``|truth_value - obs_value| / obs_value <= value_rel_tol``
      - If ``value_range = (lo, hi)`` is given: ``lo <= truth_value <= hi``
      - If ``huge_band != "none"``: ``truth_huge_count`` falls inside the band

    A bucket the player did not fill (``q`` absent from ``obs.buckets``)
    imposes no constraint on that quality. A bucket whose `total_cells`
    is set to ``0`` is treated as the player asserting *no items of this
    quality* — truths with non-zero ``q`` cells get filtered out.
    """
    wh_target = obs.warehouse_capacity()
    out: list[SessionTruth] = []
    for t in truths:
        if abs(t.warehouse_total_cells - wh_target) > warehouse_tol:
            continue
        ok = True
        for q, b_obs in obs.buckets.items():
            t_cells, t_count, t_value, t_huge = _bucket_truth_fields(t, q)

            if b_obs.total_cells is not None:
                # ``total_cells == 0`` is a player ASSERTION ("confirmed no
                # items of this quality"), not a fuzzy reading — never widen
                # tolerance on it, even at the loosest adaptive level.
                effective_cells_tol = 0 if b_obs.total_cells == 0 else cells_tol
                if abs(t_cells - b_obs.total_cells) > effective_cells_tol:
                    ok = False
                    break
            if b_obs.count is not None:
                effective_count_tol = 0 if b_obs.count == 0 else count_tol
                if abs(t_count - b_obs.count) > effective_count_tol:
                    ok = False
                    break
            if b_obs.value_sum is not None and b_obs.value_sum > 0:
                rel = abs(t_value - b_obs.value_sum) / b_obs.value_sum
                if rel > value_rel_tol:
                    ok = False
                    break
            if b_obs.value_range is not None:
                lo, hi = b_obs.value_range
                if not (lo <= t_value <= hi):
                    ok = False
                    break
            if b_obs.huge_band != "none":
                lo, hi = b_obs.huge_count_range()
                if not (lo <= t_huge <= hi):
                    ok = False
                    break
        if ok:
            out.append(t)
    return out


def _describe_constraints(obs: SessionObs) -> list[str]:
    """Build a human-readable list of "what filters are active" for rationale."""
    parts: list[str] = [f"warehouse={obs.warehouse_capacity()}"]
    for q in sorted(obs.buckets.keys()):
        b = obs.buckets[q]
        items: list[str] = []
        if b.total_cells is not None:
            items.append(f"cells={b.total_cells}")
        if b.count is not None:
            items.append(f"count={b.count}")
        if b.value_sum is not None and b.value_sum > 0:
            items.append(f"value≈{b.value_sum:,}")
        if b.value_range is not None:
            items.append(f"value∈[{b.value_range[0]:,},{b.value_range[1]:,}]")
        if b.huge_band != "none":
            items.append(f"huge={b.huge_band}")
        if items:
            parts.append(f"q={q}({', '.join(items)})")
    return parts


def adaptive_filter(
    truths: Sequence[SessionTruth],
    obs: SessionObs,
    *,
    min_samples: int = 30,
    cells_tol_levels: Sequence[int] = (2, 4, 8),
    count_tol_levels: Sequence[int] = (1, 2, 3),
    value_rel_tol_levels: Sequence[float] = (0.10, 0.20, 0.40),
    warehouse_tol_levels: Sequence[int] = (8, 8, 12),
) -> FilterResult:
    """Try strict→loose tolerances until at least ``min_samples`` truths match.

    Returns the result at the strictest level that reaches ``min_samples``.
    If even the loosest level doesn't reach it, returns the loosest-level
    result anyway (which may have ``len(truths) < min_samples``) with
    ``low_confidence=True`` so the UI can warn instead of silently failing.

    The four ``*_levels`` tuples must have the same length; level i uses
    each tuple's i-th entry.
    """
    n_levels = len(cells_tol_levels)
    assert (
        len(count_tol_levels) == n_levels
        and len(value_rel_tol_levels) == n_levels
        and len(warehouse_tol_levels) == n_levels
    ), "tolerance level tuples must have equal length"

    constraints = _describe_constraints(obs)
    last_result: list[SessionTruth] = []
    last_level = n_levels - 1
    for level in range(n_levels):
        filtered = filter_truths_by_obs(
            truths,
            obs,
            cells_tol=cells_tol_levels[level],
            count_tol=count_tol_levels[level],
            value_rel_tol=value_rel_tol_levels[level],
            warehouse_tol=warehouse_tol_levels[level],
        )
        last_result = filtered
        last_level = level
        if len(filtered) >= min_samples:
            return FilterResult(
                truths=filtered,
                tol_level=level,
                low_confidence=(level > 0),
                n_total=len(truths),
                n_final=len(filtered),
                cells_tol=cells_tol_levels[level],
                count_tol=count_tol_levels[level],
                value_rel_tol=value_rel_tol_levels[level],
                warehouse_tol=warehouse_tol_levels[level],
                constraints_applied=constraints,
            )

    return FilterResult(
        truths=last_result,
        tol_level=last_level,
        low_confidence=True,
        n_total=len(truths),
        n_final=len(last_result),
        cells_tol=cells_tol_levels[last_level],
        count_tol=count_tol_levels[last_level],
        value_rel_tol=value_rel_tol_levels[last_level],
        warehouse_tol=warehouse_tol_levels[last_level],
        constraints_applied=constraints,
    )


@dataclass
class BucketPosterior:
    """Per-bucket posterior summary from the filtered truth set."""

    quality: int
    n: int
    cells_p10: int
    cells_p50: int
    cells_p90: int
    count_p10: int
    count_p50: int
    count_p90: int
    value_p10: int
    value_p50: int
    value_p90: int
    huge_p50: int
    huge_p90: int
    p_empty: float
    """Empirical probability that this quality bucket is empty in the filtered set."""


def bucket_posterior_stats(
    filtered: Sequence[SessionTruth],
    quality: int,
) -> BucketPosterior:
    """Compute P10/P50/P90 for cells / count / value of one quality bucket.

    Defined on the FILTERED set, not the raw map prior — so the numbers
    reflect "what is left possible after the observations".
    """
    n = len(filtered)
    if n == 0:
        return BucketPosterior(
            quality=quality, n=0,
            cells_p10=0, cells_p50=0, cells_p90=0,
            count_p10=0, count_p50=0, count_p90=0,
            value_p10=0, value_p50=0, value_p90=0,
            huge_p50=0, huge_p90=0,
            p_empty=0.0,
        )
    cells = np.empty(n, dtype=np.int64)
    counts = np.empty(n, dtype=np.int64)
    values = np.empty(n, dtype=np.int64)
    huges = np.empty(n, dtype=np.int64)
    for i, t in enumerate(filtered):
        c, k, v, h = _bucket_truth_fields(t, quality)
        cells[i] = c
        counts[i] = k
        values[i] = v
        huges[i] = h
    cells_p = np.percentile(cells, [10, 50, 90]).astype(int)
    count_p = np.percentile(counts, [10, 50, 90]).astype(int)
    value_p = np.percentile(values, [10, 50, 90]).astype(int)
    huge_p = np.percentile(huges, [50, 90]).astype(int)
    return BucketPosterior(
        quality=quality, n=n,
        cells_p10=int(cells_p[0]), cells_p50=int(cells_p[1]), cells_p90=int(cells_p[2]),
        count_p10=int(count_p[0]), count_p50=int(count_p[1]), count_p90=int(count_p[2]),
        value_p10=int(value_p[0]), value_p50=int(value_p[1]), value_p90=int(value_p[2]),
        huge_p50=int(huge_p[0]), huge_p90=int(huge_p[1]),
        p_empty=float(np.mean(cells == 0)),
    )
