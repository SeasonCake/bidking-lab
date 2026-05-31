from bidking_lab.inference.diagnostics import (
    has_layout_conflict,
    layout_conflict_root,
)


def test_layout_conflict_root_splits_overlap_overflow_and_trust() -> None:
    root = layout_conflict_root(
        (
            "footprint_overflow:1",
            "footprint_overlap_cells:4",
            "footprint_count_relaxed:2->0",
        ),
        footprint_count=2,
        trusted_footprint_count=0,
    )

    assert root == (
        "footprint_overlap;"
        "footprint_overflow;"
        "footprint_count_relaxed;"
        "all_footprints_untrusted"
    )
    assert has_layout_conflict(root)


def test_layout_conflict_root_empty_without_layout_markers() -> None:
    assert layout_conflict_root("q6_below_drop_prior:0.1<prior:0.5") == ""
    assert has_layout_conflict("") is False
