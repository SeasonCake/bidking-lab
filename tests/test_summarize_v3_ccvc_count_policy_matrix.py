import hashlib
import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_ccvc_count_policy_matrix.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_ccvc_count_policy_matrix",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _stable_fold(value: str, folds: int) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % int(folds)


def _session_for_fold(fold: int, *, prefix: str) -> str:
    for idx in range(1000):
        session_id = f"{prefix}_{idx}"
        if _stable_fold(session_id, 2) == fold:
            return session_id
    raise AssertionError(f"no session for fold {fold}")


def _row(*, session_id: str, profile: str = "shape") -> dict[str, object]:
    return {
        "file": f"{session_id}#r1",
        "status": "ready",
        "session_id": session_id,
        "map_id": "2502",
        "evidence_profile_key": profile,
        "v3_truth_available": True,
        "v3_post_ready": True,
        "v3_ccvc_ready": True,
        "v3_ccvc_match_scope": "ccv_component_likelihood",
        "v3_post_q6_count_p50": 2,
        "v3_ccvc_q6_count_p50": 3,
        "v3_truth_q6_count": 4,
    }


def test_ccvc_count_policy_matrix_compares_group_and_policy() -> None:
    module = _load_module()
    fold0 = [_session_for_fold(0, prefix=f"f0_{idx}") for idx in range(4)]
    fold1 = [_session_for_fold(1, prefix=f"f1_{idx}") for idx in range(4)]
    rows = [_row(session_id=session_id) for session_id in (*fold0, *fold1)]

    result = module.summarize_matrix(
        rows,
        group_fields=("map_id", "map_id,evidence_profile_key"),
        movement_policies=("all", "up_only"),
        folds=2,
        min_windows=2,
        min_sessions=2,
        min_changed=2,
    )

    assert len(result) == 4
    assert {row["movement_policy"] for row in result} == {"all", "up_only"}
    assert {row["group_field"] for row in result} == {
        "map_id",
        "map_id,evidence_profile_key",
    }
    assert all(row["overall_status"] == "watch" for row in result)
    assert all(row["candidate_delta_p50_mae"] == -1 for row in result)


def test_ccvc_count_policy_matrix_passes_candidate_exclude_pattern() -> None:
    module = _load_module()
    fold0 = [_session_for_fold(0, prefix=f"f0_{idx}") for idx in range(4)]
    fold1 = [_session_for_fold(1, prefix=f"f1_{idx}") for idx in range(4)]
    rows = [_row(session_id=session_id) for session_id in (*fold0, *fold1)]

    result = module.summarize_matrix(
        rows,
        group_fields=("map_id",),
        movement_policies=("all",),
        folds=2,
        min_windows=2,
        min_sessions=2,
        min_changed=2,
        candidate_exclude_pattern="^q6_count:2502$",
    )

    assert result[0]["candidate_exclude_pattern"] == "^q6_count:2502$"
    assert result[0]["candidate_rows"] == 0
    assert result[0]["overall_status"] == "sample_limited"
