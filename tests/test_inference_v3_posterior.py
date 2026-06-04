from bidking_lab.inference.ground_truth import BucketTruth, SessionTruth
from bidking_lab.inference.v3 import (
    BucketFeasibleSummary,
    FeasibleSummaryReport,
    estimate_q6_posterior_from_truths,
    truth_matches_feasible_summary,
)


def _truth(
    *,
    q6_count: int = 0,
    q6_cells: int = 0,
    q6_value: int = 0,
    q1_count: int = 1,
    q1_cells: int = 1,
    q1_value: int = 100,
) -> SessionTruth:
    buckets = {
        1: BucketTruth(
            quality=1,
            count=q1_count,
            total_cells=q1_cells,
            value_sum=q1_value,
        )
    }
    if q6_count:
        buckets[6] = BucketTruth(
            quality=6,
            count=q6_count,
            total_cells=q6_cells,
            value_sum=q6_value,
        )
    return SessionTruth(
        map_id=2401,
        map_name="test_map",
        warehouse_total_cells=q1_cells + q6_cells,
        buckets=buckets,
    )


def test_v3_posterior_filters_truths_by_feasible_summary() -> None:
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
                cells_exact=16,
            ),
        ),
    )
    no_q6 = _truth()
    one_q6 = _truth(q6_count=1, q6_cells=16, q6_value=200_000)
    two_q6 = _truth(q6_count=2, q6_cells=32, q6_value=400_000)

    assert truth_matches_feasible_summary(no_q6, summary) is False
    assert truth_matches_feasible_summary(one_q6, summary) is True
    assert truth_matches_feasible_summary(two_q6, summary) is False

    report = estimate_q6_posterior_from_truths(
        map_id=2401,
        map_name="test_map",
        summary=summary,
        truths=(no_q6, one_q6, two_q6),
    )

    assert report.ready is True
    assert report.strict_ready is True
    assert report.match_scope == "strict"
    assert report.n_total == 3
    assert report.n_matched == 1
    assert report.n_strict_matched == 1
    assert report.q6_present_rate == 1.0
    assert report.q6_count.p50 == 1
    assert report.q6_cells.p50 == 16
    assert report.q6_value.p50 == 200_000


def test_v3_posterior_uses_summary_likelihood_when_exact_q6_is_unseen() -> None:
    summary = FeasibleSummaryReport(
        session_total_count_exact=None,
        session_total_cells_exact=None,
        known_count_floor=0,
        known_cells_floor=0,
        known_value_floor=0,
        buckets=(BucketFeasibleSummary(quality=6, count_exact=3),),
    )

    report = estimate_q6_posterior_from_truths(
        map_id=2401,
        map_name="test_map",
        summary=summary,
        truths=(_truth(), _truth(q6_count=1, q6_cells=16, q6_value=200_000)),
    )

    assert report.ready is True
    assert report.strict_ready is False
    assert report.match_scope == "summary_likelihood"
    assert report.n_strict_matched == 0
    assert report.q6_count.p50 == 1
    assert report.diagnostics[0:2] == (
        "no_strict_summary_matched_samples",
        "summary_likelihood_fallback",
    )


def test_v3_posterior_uses_summary_likelihood_when_strict_has_no_match() -> None:
    summary = FeasibleSummaryReport(
        session_total_count_exact=None,
        session_total_cells_exact=99,
        known_count_floor=0,
        known_cells_floor=0,
        known_value_floor=0,
        buckets=(BucketFeasibleSummary(quality=6, count_floor=1),),
    )

    report = estimate_q6_posterior_from_truths(
        map_id=2401,
        map_name="test_map",
        summary=summary,
        truths=(_truth(), _truth(q6_count=1, q6_cells=16, q6_value=200_000)),
    )

    assert report.ready is True
    assert report.strict_ready is False
    assert report.match_scope == "summary_likelihood"
    assert report.n_strict_matched == 0
    assert report.q6_count.p50 == 1
    assert report.diagnostics[0:2] == (
        "no_strict_summary_matched_samples",
        "summary_likelihood_fallback",
    )
