from __future__ import annotations

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropEntry, DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.observation import QualityBucketObs, SessionObs
from bidking_lab.inference.v2 import (
    ConditionalSampler,
    EvidenceStoreBuilder,
    RuntimeEvidence,
    build_residual_problem,
    estimate_posterior_v2,
    evidence_store_from_fatbeans_events,
    known_item_anchors,
)
from bidking_lab.live.fatbeans import (
    FatbeansActionResult,
    FatbeansCaptureEvents,
    FatbeansObservedItem,
    FatbeansPublicInfo,
    FatbeansStateEvent,
)


def _item(
    item_id: int,
    *,
    quality: int,
    value: int,
    shape: tuple[int, int],
    tags: list[int] | None = None,
) -> Item:
    w, h = shape
    return Item(
        item_id=item_id,
        name=f"item_{item_id}",
        description="",
        name_key=f"item_{item_id}",
        desc_key=f"item_{item_id}_desc",
        quality=quality,
        quality_color="",
        value=value,
        shape_w=w,
        shape_h=h,
        tags=tags or [],
        allowed_shelves=[],
        icon_name="",
        model_name="",
        raw_row=[],
    )


def _map() -> BidMap:
    return BidMap(
        map_id=2401,
        name="test_map",
        description="",
        category=101,
        auction_mode="open",
        sub_pool_weights=[],
        rounds_total=5,
        entry_fee_silver=0,
        starting_budget_silver=100_000,
        drop_pool_id=9001,
        items_per_session_min=2,
        items_per_session_max=2,
        value_tier_ui="",
        mode_flag=4,
        bid_price_ladder=[],
        raw_row=[],
    )


def _tables() -> tuple[dict[int, BidMap], dict[int, DropPool], dict[int, Item]]:
    anchor = _item(1103006, quality=3, value=3_240, shape=(2, 1), tags=[110])
    filler = _item(1011001, quality=1, value=100, shape=(1, 1), tags=[101])
    red = _item(1086001, quality=6, value=444_000, shape=(4, 4), tags=[108])
    return (
        {2401: _map()},
        {
            9001: DropPool(
                pool_id=9001,
                name="pool",
                description="",
                pool_type=2,
                entries=[
                    DropEntry(
                        category=110,
                        item_id=anchor.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                    DropEntry(
                        category=101,
                        item_id=filler.item_id,
                        n_min=1,
                        n_max=1,
                        weight=999,
                    ),
                    DropEntry(
                        category=108,
                        item_id=red.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                ],
            ),
        },
        {anchor.item_id: anchor, filler.item_id: filler, red.item_id: red},
    )


def test_evidence_store_from_fatbeans_merges_item_and_category_runtime() -> None:
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(),
        statuses=(),
        states=(
            FatbeansStateEvent(
                sort_id=7,
                capture_time="",
                message_id=0x0025,
                session_id="s1",
                map_id=2401,
                round_index=1,
                public_infos=(
                    FatbeansPublicInfo(
                        info_id=200022,
                        map_id=2401,
                        value=4,
                        value_field=11,
                        observed_items=(
                            FatbeansObservedItem(
                                local_index=22,
                                runtime_id=123,
                                item_id=1103006,
                                quality=3,
                                value=3_240,
                                shape_code=21,
                                cells=2,
                            ),
                        ),
                    ),
                ),
                action_results=(
                    FatbeansActionResult(
                        action_id=100160,
                        result=None,
                        result_field=None,
                        observed_items=(
                            FatbeansObservedItem(
                                local_index=22,
                                runtime_id=123,
                                item_id=None,
                                quality=None,
                                value=None,
                                shape_code=21,
                                cells=None,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    _maps, _drops, items = _tables()

    store = evidence_store_from_fatbeans_events(events)
    anchors = known_item_anchors(store, items=items)

    assert len(store.by_runtime) == 1
    assert store.by_runtime[123].categories == (110,)
    assert len(anchors) == 1
    assert anchors[0].item_id == 1103006
    assert anchors[0].cells == 2
    assert anchors[0].categories == (110,)


def test_conditional_sampler_forces_known_item_anchor() -> None:
    maps, drops, items = _tables()
    builder = EvidenceStoreBuilder()
    builder.add_item(
        RuntimeEvidence(
            runtime_id=123,
            item_id=1103006,
            quality=3,
            shape_key="21",
            cells=2,
            categories=(110,),
            sources=("public:200022",),
        )
    )
    problem = build_residual_problem(
        2401,
        builder.build(),
        maps=maps,
        drops=drops,
        items=items,
    )
    sampler = ConditionalSampler(problem, maps=maps, drops=drops, items=items)

    for _ in range(20):
        truth = sampler.sample(rng=np.random.default_rng(1))
        q3 = truth.buckets[3]
        assert any(item.item_id == 1103006 for item in q3.items)
        assert truth.total_value() >= 3_240


def test_estimate_posterior_v2_uses_anchor_without_rejection_dead_end() -> None:
    maps, drops, items = _tables()
    builder = EvidenceStoreBuilder()
    builder.add_item(
        RuntimeEvidence(
            runtime_id=123,
            item_id=1103006,
            quality=3,
            shape_key="21",
            cells=2,
            categories=(110,),
            sources=("public:200022",),
        )
    )
    obs = SessionObs(
        map_id=2401,
        hero="aisha",
        buckets={3: QualityBucketObs(quality=3, total_cells_min=2, count_min=1)},
    )

    report = estimate_posterior_v2(
        2401,
        obs,
        builder.build(),
        maps=maps,
        drops=drops,
        items=items,
        n_trials=50,
        seed=1,
    )

    assert report.anchor_count == 1
    assert report.known_value == 3_240
    assert report.n_matched == 50
    assert report.total_value is not None
    assert report.total_value.p10 >= 3_240


def test_residual_problem_guides_per_quality_bucket_targets() -> None:
    maps, drops, items = _tables()
    builder = EvidenceStoreBuilder()
    builder.add_item(
        RuntimeEvidence(
            runtime_id=123,
            item_id=1103006,
            quality=3,
            shape_key="21",
            cells=2,
            sources=("public:200022",),
        )
    )
    obs = SessionObs(
        map_id=2401,
        hero="aisha",
        buckets={3: QualityBucketObs(quality=3, total_cells_min=6, count_min=3)},
    )
    problem = build_residual_problem(
        2401,
        builder.build(),
        maps=maps,
        drops=drops,
        items=items,
        obs=obs,
    )
    sampler = ConditionalSampler(problem, maps=maps, drops=drops, items=items)

    truth = sampler.sample(rng=np.random.default_rng(2))

    assert problem.bucket_targets[3].total_cells_floor == 6
    assert problem.bucket_targets[3].count_floor == 3
    assert truth.buckets[3].total_cells >= 6
    assert truth.buckets[3].count >= 3


def test_quality_only_runtime_evidence_guides_count_floor() -> None:
    maps, drops, items = _tables()
    builder = EvidenceStoreBuilder()
    builder.add_item(
        RuntimeEvidence(
            runtime_id=999,
            quality=6,
            sources=("public:200027",),
        )
    )
    problem = build_residual_problem(
        2401,
        builder.build(),
        maps=maps,
        drops=drops,
        items=items,
    )
    sampler = ConditionalSampler(problem, maps=maps, drops=drops, items=items)

    truth = sampler.sample(rng=np.random.default_rng(3))

    assert problem.bucket_targets[6].count_floor == 1
    assert problem.bucket_targets[6].total_cells_floor is None
    assert truth.buckets[6].count >= 1
