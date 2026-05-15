"""Experimental Streamlit tabs that are not part of the core flow.

These are kept around because the code is wired up correctly and may
become useful when the engine grows new features (e.g. when
``SessionObs`` learns about ``unconfirmed_huge_shapes`` and the joint
table can actually pin down meaningful (cells × count) combinations
for unobserved buckets).

For the current core flow (价格区间 + 秒仓/放仓 + 道具 ROI), the joint
table tends to return three near-identical hypotheses because the user
has already fixed ``total_cells`` for every observed bucket, leaving
only ``count`` as a degree of freedom — not enough variation to give
useful information. So we hide it behind a sidebar toggle.

Re-enable via the "高级 → 显示实验性 tab" checkbox in the sidebar.
"""

from __future__ import annotations

import streamlit as st

from bidking_lab.inference.joint import joint_top_k_for_session
from bidking_lab.inference.quality_priors import PER_CELL_VALUE_DEFAULT

QUALITY_LABEL = {1: "白品", 2: "绿品", 3: "蓝品", 4: "紫品", 5: "金品", 6: "红品"}


def render_joint_inference_tab(*, session_builder, state, per_bucket_top: int):
    """Render the joint posterior tab.

    Parameters
    ----------
    session_builder
        Zero-arg callable that returns a fresh ``SessionObs`` from the
        current sidebar/tab inputs.
    state
        ``st.session_state.obs`` dict.
    per_bucket_top
        Search width forwarded to ``joint_top_k_for_session``.
    """
    st.subheader("联合后验 — top-3 仓库组成假设  ⚗️ 实验性")
    st.caption(
        "枚举所有品质 bucket 的可能【总格数×件数】组合，加上仓库容量软罚分，"
        "输出综合 score 最低的 3 个。composite 越小越紧。"
    )
    st.info(
        "💡 当前若所有 bucket 都给了 `total_cells`，top-3 只会在 `count` 上有微小差异，"
        "看着像 '三个结果一样'。这个表在你**只给了均格/估值、未给总格数**时才能看到真正的"
        "组合枚举效果。"
    )

    if st.button("运行联合推断", key="run_joint", type="primary"):
        session = session_builder()
        with st.spinner("联合枚举中..."):
            hyps = joint_top_k_for_session(
                session, k=3, per_bucket_top=per_bucket_top,
            )
        if not hyps:
            st.warning(
                "未产生假设 — 可能输入中 bucket cells 总和超出仓库容量太多，"
                "或某个 bucket 的 cells/value 组合不存在。"
            )
        else:
            for rank, hyp in enumerate(hyps, start=1):
                with st.container(border=True):
                    st.markdown(
                        f"**第 {rank} 名**  ·  综合评分 "
                        f"`{hyp.composite:.3f}`  ·  总格数 "
                        f"`{hyp.total_cells}`  ·  仓库超容罚分 "
                        f"`{hyp.warehouse_penalty:.2f}`"
                    )
                    rows = []
                    confirmed_cells = sum(
                        c.total_cells for c in hyp.per_bucket.values()
                    )
                    capacity = session.warehouse_capacity() or 0
                    leftover_cells = max(0, capacity - confirmed_cells)
                    for q in (1, 2, 3, 4, 5, 6):
                        c = hyp.per_bucket.get(q)
                        if c is None:
                            rows.append({
                                "品质": f"{QUALITY_LABEL[q]} (q={q})",
                                "总格数": "—",
                                "件数": "—",
                                "均格": "—",
                                "每格估值": "—",
                                "价值一致度": "—",
                            })
                            continue
                        avg = c.total_cells / c.count if c.count > 0 else 0
                        per_cell = PER_CELL_VALUE_DEFAULT.get(q, 0)
                        rows.append({
                            "品质": f"{QUALITY_LABEL[q]} (q={q})",
                            "总格数": c.total_cells,
                            "件数": c.count,
                            "均格": f"{avg:.2f}",
                            "每格估值": f"{per_cell:,}",
                            "价值一致度": f"{c.value_score:.3f}",
                        })
                    st.table(rows)
                    st.caption(
                        f"已确认 {confirmed_cells} 格 · 未记录 {leftover_cells} 格"
                        "（未提供读数的 bucket，价值靠先验估计）。"
                        "价值一致度越小越加紧，0 = 仅依赖格数、未提供估价。"
                    )
    else:
        st.info("设置好读数后点击上面按钮。")
