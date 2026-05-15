"""Phase 1A inference engine: turn tool readings + hero outlines into
posterior distributions over (quality, value) for each placeholder item.

See docstring of :mod:`bidking_lab.inference.display` for the decimal-
display model that underpins the small-decimal-leakage inference for the
``X品均格`` family.

Top-level surfaces:

* :func:`bidking_lab.inference.observation.top_k_for_session` — *greedy*
  per-bucket top-K, fast and good enough when the player gives at least
  one strong reading per quality.
* :func:`bidking_lab.inference.joint.joint_top_k_for_session` — *joint*
  posterior across buckets, uses the observed warehouse total as a
  soft global constraint. Use when greedy top-1 looks inconsistent
  across buckets, or when warehouse_total_cells is known exactly.
"""

from bidking_lab.inference.joint import (
    JointHypothesis,
    joint_top_k_for_session,
)
from bidking_lab.inference.observation import (
    AISHA_DEFAULT_LOADOUT,
    ETHAN_ALT_LOADOUT,
    ETHAN_DEFAULT_LOADOUT,
    STANDARD_LOADOUTS,
    BucketCandidate,
    QualityBucketObs,
    SessionObs,
    candidates_for_bucket,
    top_k_for_session,
)

__all__ = (
    # observation
    "BucketCandidate",
    "QualityBucketObs",
    "SessionObs",
    "candidates_for_bucket",
    "top_k_for_session",
    "AISHA_DEFAULT_LOADOUT",
    "ETHAN_DEFAULT_LOADOUT",
    "ETHAN_ALT_LOADOUT",
    "STANDARD_LOADOUTS",
    # joint
    "JointHypothesis",
    "joint_top_k_for_session",
)
