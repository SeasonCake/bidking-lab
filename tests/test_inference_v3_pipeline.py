from bidking_lab.inference.ground_truth import BucketTruth, SessionTruth
from bidking_lab.inference.v3 import (
    BucketFeasibleSummary,
    FeasibleSummaryReport,
    estimate_shadow_pipeline,
)


def _truth(
    *,
    q6_count: int,
    q6_cells: int,
    q6_value: int,
) -> SessionTruth:
    return SessionTruth(
        map_id=2401,
        map_name="test_map",
        warehouse_total_cells=10 + q6_cells,
        buckets={
            1: BucketTruth(
                quality=1,
                count=1,
                total_cells=10,
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
    assert flat["v3_resid_available"] is True
    assert flat["v3_resid_affects_bid"] is False
    assert flat["v3_resid_gate_available"] is True
    assert flat["v3_resid_gate_affects_bid"] is False
    assert flat["v3_cal_available"] is True
    assert flat["v3_cal_status"] == "missing_entry"
    assert flat["v3_under_available"] is True
    assert flat["v3_under_status"] == "missing_entry"
    assert flat["v3_under_affects_bid"] is False
    assert flat["v3_tail_review_available"] is True
    assert flat["v3_tail_review_status"] == "missing_entry"
    assert flat["v3_tail_review_affects_bid"] is False
