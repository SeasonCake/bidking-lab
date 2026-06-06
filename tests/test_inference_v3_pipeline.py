from bidking_lab.inference.ground_truth import BucketTruth, SessionTruth
from bidking_lab.inference.v3 import (
    BucketFeasibleSummary,
    FeasibleSummaryReport,
    V3CcvOptions,
    estimate_shadow_pipeline,
)


def _truth(
    *,
    q6_count: int,
    q6_cells: int,
    q6_value: int,
    q1_cells: int = 10,
) -> SessionTruth:
    return SessionTruth(
        map_id=2401,
        map_name="test_map",
        warehouse_total_cells=q1_cells + q6_cells,
        buckets={
            1: BucketTruth(
                quality=1,
                count=1,
                total_cells=q1_cells,
                value_sum=100,
            ),
            6: BucketTruth(
                quality=6,
                count=q6_count,
                total_cells=q6_cells,
                value_sum=q6_value,
            ),
        },
    )


def test_v3_shadow_pipeline_emits_all_shadow_namespaces() -> None:
    summary = FeasibleSummaryReport(
        session_total_count_exact=None,
        session_total_cells_exact=None,
        known_count_floor=0,
        known_cells_floor=0,
        known_value_floor=0,
        buckets=(
            BucketFeasibleSummary(
                quality=6,
                count_exact=1,
                cells_exact=4,
                value_exact=100_000,
            ),
        ),
    )

    report = estimate_shadow_pipeline(
        map_id=2401,
        map_name="test_map",
        summary=summary,
        truths=(
            _truth(q6_count=1, q6_cells=4, q6_value=100_000),
            _truth(q6_count=2, q6_cells=8, q6_value=200_000),
        ),
        hero="ethan",
    )
    flat = report.to_flat_dict()

    assert report.posterior.ready is True
    assert flat["v3_post_available"] is True
    assert flat["v3_post_affects_bid"] is False
    assert flat["v3_ccv_available"] is True
    assert flat["v3_ccv_affects_bid"] is False
    assert report.ccv_component_posterior is None
    assert flat["v3_ccvc_available"] is False
    assert flat["v3_ccvc_affects_bid"] is False
    assert flat["v3_resid_available"] is True
    assert flat["v3_resid_affects_bid"] is False
    assert flat["v3_resid_gate_available"] is True
    assert flat["v3_resid_gate_affects_bid"] is False
    assert flat["v3_rtc_available"] is True
    assert flat["v3_rtc_affects_bid"] is False
    assert flat["v3_rtc_active"] is False
    assert flat["v3_cal_available"] is True
    assert flat["v3_cal_status"] == "missing_entry"
    assert flat["v3_under_available"] is True
    assert flat["v3_under_status"] == "missing_entry"
    assert flat["v3_under_affects_bid"] is False
    assert flat["v3_tail_review_available"] is True
    assert flat["v3_tail_review_status"] == "missing_entry"
    assert flat["v3_tail_review_affects_bid"] is False
    assert flat["v3_fv_available"] is True
    assert flat["v3_fv_affects_bid"] is False
    assert flat["v3_fv_active"] is False
    assert flat["v3_fv_status"] == "prior_unavailable"


def test_v3_shadow_pipeline_can_emit_component_ccv_shadow() -> None:
    summary = FeasibleSummaryReport(
        session_total_count_exact=None,
        session_total_cells_exact=26,
        known_count_floor=1,
        known_cells_floor=4,
        known_value_floor=100_000,
        buckets=(
            BucketFeasibleSummary(
                quality=6,
                count_floor=1,
                cells_floor=4,
                value_floor=100_000,
            ),
        ),
    )

    report = estimate_shadow_pipeline(
        map_id=2401,
        map_name="test_map",
        summary=summary,
        truths=(
            _truth(q6_count=1, q6_cells=4, q6_value=100_000, q1_cells=10),
            _truth(q6_count=1, q6_cells=16, q6_value=200_000, q1_cells=4),
        ),
        hero="ethan",
        ccv_options=V3CcvOptions(component_likelihood=True),
    )
    flat = report.to_flat_dict()

    assert report.ccv_component_posterior is not None
    assert flat["v3_ccvc_available"] is True
    assert flat["v3_ccvc_affects_bid"] is False
    assert flat["v3_ccvc_match_scope"] == "ccv_component_likelihood"


def test_v3_shadow_pipeline_can_emit_formal_value_candidate() -> None:
    summary = FeasibleSummaryReport(
        session_total_count_exact=None,
        session_total_cells_exact=None,
        known_count_floor=0,
        known_cells_floor=0,
        known_value_floor=500_000,
        buckets=(
            BucketFeasibleSummary(
                quality=6,
                value_floor=400_000,
            ),
        ),
    )

    report = estimate_shadow_pipeline(
        map_id=2401,
        map_name="test_map",
        summary=summary,
        truths=(
            _truth(q6_count=1, q6_cells=4, q6_value=500_000),
            _truth(q6_count=1, q6_cells=4, q6_value=600_000),
        ),
        hero="ethan",
        prior_fields={
            "v3_prior_available": True,
            "v3_prior_expected_value": 100_000,
            "v3_prior_q6_expected_value": 80_000,
        },
    )
    flat = report.to_flat_dict()

    assert flat["v3_fv_available"] is True
    assert flat["v3_fv_candidate"] is True
    assert flat["v3_fv_active"] is False
    assert flat["v3_fv_affects_bid"] is False
    assert flat["v3_fv_status"] == "watch_only_value_floor_candidate"
    assert flat["v3_fv_total_value_target"] == 500_000
    assert flat["v3_fv_q6_value_target"] == 400_000


def test_v3_shadow_pipeline_can_freeze_component_cells() -> None:
    summary = FeasibleSummaryReport(
        session_total_count_exact=None,
        session_total_cells_exact=26,
        known_count_floor=1,
        known_cells_floor=4,
        known_value_floor=100_000,
        buckets=(
            BucketFeasibleSummary(
                quality=6,
                count_floor=1,
                cells_floor=4,
                value_floor=100_000,
            ),
        ),
    )

    report = estimate_shadow_pipeline(
        map_id=2401,
        map_name="test_map",
        summary=summary,
        truths=(
            _truth(q6_count=1, q6_cells=4, q6_value=100_000, q1_cells=10),
            _truth(q6_count=1, q6_cells=16, q6_value=200_000, q1_cells=4),
        ),
        hero="ethan",
        ccv_options=V3CcvOptions(
            component_likelihood=True,
            component_move_cells=False,
        ),
    )
    flat = report.to_flat_dict()

    assert report.ccv_component_posterior is not None
    assert flat["v3_ccvc_q6_cells_p50"] == flat["v3_post_q6_cells_p50"]
    assert "ccvc_cells_passthrough" in flat["v3_ccvc_diagnostics"]
