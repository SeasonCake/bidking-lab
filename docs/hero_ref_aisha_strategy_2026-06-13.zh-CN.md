# Hero Ref · 艾莎 v0 策略与推进方案（2026-06-13）

**Git 基线**：`de2b438` · `origin/main`  
**角色**：后续工作按本文顺序推进；handoff 只保留当日 checkpoint。

---

## 1. 目标与边界

| 项 | v0 要 | v0 不要 |
|---|---|---|
| 报价 | 少 `no-combo`、有 conservative/balanced/aggressive | curated MAE≈0、14/14 band 全绿 |
| 样本 | 173 curated 方向监控；7 hit 不回归 | 在 14 exact-total 上扫参、合成凑 hit |
| 引擎 | 语义规则 + synthetic/单条代表 fatbeans | 复制 v3 地图似然整包权重 |
| 产品 | 实战可读、署名正确、低品件/格信息更全 | 接正式出价、写回 v3 promotion |

**样本现实**：244 艾莎 fatbeans → **173 curated** → exact-total **n=14**（7 hit / 7 miss 跟踪）。不做合成扩池时，结构性 miss 长期存在是预期，不是失败。

---

## 2. 格/件推断 — 分层策略（叠加，非互斥）

```
证据进入 extract_evidence
    │
    ├─ [已落地 B1] total_count 精确 + ≥2 档 q3–q5 整数 quality_cells
    │       → total_grid_target_from_known_high_tier_cells
    │
    ├─ [已落地 B2] 残差件 + unfixed tier avg_cells
    │       → 均值估残差格；无信号 → 4.0（note: total_grid_target_residual_avg_cells_estimate）
    │
    ├─ [已落地] avg_value_only 金件 pin（unique fraction 均价 + synthetic）
    │
    ├─ [按轮次 · 待 shadow] 地图/位置似然
    │       R1：禁用点估计（仅白，误差大）
    │       R2：仅宽 band / soft floor（白绿 skill，仓位误差仍大）
    │       R3–R4：地图似然 + 格子位置 → 件数/格范围（较可信）
    │       金/红：可能在已知最深格 **下方** → 总格 target 留 footroom
    │
    └─ ref_v0 枚举 + count_prior（主路径，不动 v3 promotion gate）
```

**与 v3**：v3 地图似然曾长期调参未 promotion → ref_v0 只接 **shadow/soft 约束**，权重不在 curated 上迭代。

---

## 3. 批次路线图（执行顺序）

| 阶段 | 内容 | 状态 | 门禁 |
|---|---|---|---|
| **A** | curated gap audit + 20 代表样本 + 14 门禁简表 | ✅ | 文档 |
| **B1** | high-tier cells → total_grid_target | ✅ `9982365` | 7 band 不回归 |
| **B2** | 残差 unfixed avg_cells | ✅ `ffbb038` | synthetic + 7 不回归 |
| **B3** | 0052 r3 + 白绿 bridge | ✅ `c2bac60` | fatbeans 单测 |
| **B4** | 0052 downgrade | ✅ synthetic 已有 | 不绑 n=1 fatbeans 调参 |
| **B5** | UI 低品件/格 + 署名 | ✅ `de2b438` | overlay pytest |
| **C1** | `good_regression` 2 条 balanced 报价锁定 + gap 不劣化 >15% | ✅ | pytest |
| **C2** | R3+ 地图似然 shadow hook（设计+最小 prototype） | ⏳ | synthetic + 1 fatbeans；**不扫 173 权重** |
| **C3** | 金/红 deepest-row footroom（与 C2 同 PR 或紧随） | ⏳ | 同上 |
| **D** | UX：R1 hero 识别、mini/next-info | 📋 P2 | overlay 测试 |
| **E** | 新抓包 / 地图扩池 | 📋 P2 | 扩大 n 优先于调参 |
| **—** | q1 split 口径 | 📋 单独 | 不进 B 门禁 |
| **§50** | Ahmed 性能 | ✅ defer | warm <500ms 已记录 |

---

## 4. 下一迭代（C1 → C2，按此顺序）

### C1 · good_regression balanced 门禁（✅ 2026-06-13）

- 代表表 **2 条**（非 3 条）：2501_0123、2505_0173
- 现状：settlement 不在 balanced ±15% 内（nest 估价偏差 ~25–28%）
- pytest：**锁定** `combo_count` + `balanced`；`|truth−balanced|` 不得比基线 gap 恶化 **>15%**

### C2 · R3+ shadow 总格 hint（中成本，防过拟合）

**Do**

1. 在 `extract_evidence` 末尾增加 **optional** `aisha_layout_grid_hint`（仅 `round>=3` 且非 R1-only-white）
2. 输入：minimap/skill 已有 deepest row + map_id；输出：**宽** `[low, high]` 或 soft `total_grid_target` 上界/下界
3. 与 B1/B2 **取 max/min 合并**，note 标明来源
4. synthetic：deepest row + 金在下 → target 含 footroom
5. 单条 fatbeans R3+ 代表：**路径可达**即可，不绑 truth band

**Don't**

- R1/R2 启用位置点估计
- 在 14 exact-total 或 173 curated 上扫权重
- 替换 count_prior 主枚举

### C3 · 扩池（并行、人工）

- 新 live/fatbeans 进 `data/samples` 后再跑 audit；miss% 仅作趋势

---

## 5. 验证节奏

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
# 每次引擎改动
python -m pytest tests/test_ahmad_ref_engine_public_info.py -k "aisha_batch_b or 0052 or total_grid_target_residual" -q
# UI 改动
python -m pytest tests/test_live_overlay.py -k "quality_uncertainty_summary" -q
# 方向监控（非 gate，月/里程碑）
python scripts/audit_aisha_gap.py
```

---

## 6. 参考文件

- 代表样本 / 门禁简表：`docs/hero_ref_aisha_representative_samples_2026-06-13.zh-CN.md`
- 执行细节 §61–§63：`external_references/ahmad_live_reference_lab/EXECUTION_NOTES_2026-06-10.zh-CN.md`
- 当日 checkpoint：`handoff_2026-06-13.zh-CN.md`
