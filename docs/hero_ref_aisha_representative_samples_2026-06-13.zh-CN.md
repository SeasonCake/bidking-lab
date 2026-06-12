# Hero Ref 艾莎代表样本表（2026-06-13）

从 curated gap audit 中按误差类型分层抽取，供 §61 批 B 回归与人工复核。
不全库使用；高 tail / ≤2 轮 / 证据不足样本已排除。

- 源脚本：`scripts/audit_aisha_gap.py`
- curated 池：见 `data/reports/audit_aisha_gap.txt`
- 本表条数：**20**

| # | 桶 | 文件 | map | r | 总格gap | 总件gap | q5 | q6值 | 金价only | balanced Δ |
|---|---|---|---:|---:|---:|---:|---|---|---|---:|
| 1 | grid_exact_total | `fatbeans_valid_aisha_2501_5rounds_2501_129501866` | 2501 | 3/8 | 12 | 0 | 1 | -386697 | - | -248610 |
| 2 | grid_exact_total | `fatbeans_valid_aisha_2410_2rounds_2410_129501857` | 2410 | 3/4 | 18 | 0 | 7 | -173574 | - | 25527 |
| 3 | grid_exact_total | `fatbeans_valid_aisha_2401_3rounds_2401_129501901` | 2401 | 3/6 | 15 | 0 | 1 | -122200 | - | -92342 |
| 4 | grid_count_prior | `fatbeans_valid_aisha_2503_4rounds_2503_129501870` | 2503 | 3/8 | 95 | 30 | 6 | 438000 | - | 640084 |
| 5 | grid_count_prior | `fatbeans_valid_aisha_2504_4rounds_2504_129501867` | 2504 | 3/7 | 65 | 35 | 3 | 755814 | - | 958898 |
| 6 | grid_count_prior | `fatbeans_valid_aisha_2508_5rounds_2508_129501859` | 2508 | 3/9 | 93 | 29 | 6 | 605209 | - | 876342 |
| 7 | total_items | `fatbeans_mixed_aisha_2504_4rounds_2504_127412812` | 2504 | 3/5 | 0 | 11 | 6 | 397392 | - | 466370 |
| 8 | red_value | `fatbeans_valid_aisha_2502_4rounds_2502_129501870` | 2502 | 3/8 | 0 | -10 | -1 | 419151 | - | 411136 |
| 9 | red_value | `fatbeans_valid_aisha_2401_3rounds_2401_129501856` | 2401 | 3/6 | 5 | 0 | 0 | 296853 | - | 269589 |
| 10 | tier_counts | `fatbeans_valid_aisha_2401_3rounds_2401_129501866` | 2401 | 3/6 | -3 | -4 | -1 | -228288 | - | -294094 |
| 11 | tier_counts | `fatbeans_valid_aisha_2408_4rounds_2408_140277068` | 2408 | 3/7 | -1 | -1 | 0 | -170240 | - | -140095 |
| 12 | tier_counts | `fatbeans_valid_aisha_2404_4rounds_2404_129501857` | 2404 | 3/7 | 1 | -2 | 4 | 123760 | - | 131215 |
| 13 | good_regression | `fatbeans_valid_aisha_2507_4rounds_2507_129501870` | 2507 | 3/7 | 0 | 4 | 2 | -126580 | - | -57344 |
| 14 | good_regression | `fatbeans_valid_aisha_2403_4rounds_2403_129501898` | 2403 | 3/7 | 0 | 5 | 2 | -1488 | - | 28571 |
| 15 | grid_count_prior | `fatbeans_valid_aisha_2510_5rounds_2510_129501867` | 2510 | 3/10 | 87 | 29 | 11 | 754400 | - | 1423841 |
| 16 | grid_count_prior | `fatbeans_valid_aisha_2408_5rounds_2408_127412812` | 2408 | 3/9 | 87 | 26 | 6 | 842360 | - | 1083792 |
| 17 | grid_count_prior | `fatbeans_valid_aisha_2501_4rounds_2501_129501862` | 2501 | 3/7 | 99 | 26 | 5 | 350000 | - | 681837 |
| 18 | grid_count_prior | `fatbeans_valid_aisha_2508_5rounds_2508_127412812` | 2508 | 3/9 | 81 | 25 | 7 | 407925 | - | 633828 |
| 19 | grid_count_prior | `fatbeans_valid_aisha_2501_4rounds_2501_129501870` | 2501 | 3/8 | 93 | 21 | 5 | 728100 | - | 938572 |
| 20 | grid_count_prior | `fatbeans_valid_aisha_2503_2rounds_2503_129501865` | 2503 | 3/4 | 96 | 24 | 6 | 302580 | - | 539004 |

## 批 B 回归门禁（15 条 `total_count_exact`）

优先用桶 `grid_exact_total` + `gold_price_only` 中带精确总件的样本；
每条改动需：`total_cells` band 覆盖或 mid-gap 缩小，且 `balanced` 不劣化 >15%。

1. `fatbeans_valid_aisha_2501_5rounds_2501_1295018669960456_0139.json` — map 2501, cells_gap=12, q5_gap=1, status=count_prior
2. `fatbeans_valid_aisha_2410_2rounds_2410_1295018574148404_0093.json` — map 2410, cells_gap=18, q5_gap=7, status=count_prior
3. `fatbeans_valid_aisha_2401_3rounds_2401_1295019017806948_0032.json` — map 2401, cells_gap=15, q5_gap=1, status=count_prior
4. `fatbeans_valid_aisha_2507_5rounds_2507_1295018647628127_0196.json` — map 2507, cells_gap=32, q5_gap=1, status=count_prior
5. `fatbeans_mixed_aisha_2403_3rounds_2403_1295018990047075_0002.json` — map 2403, cells_gap=13, q5_gap=-2, status=ok
6. `fatbeans_valid_aisha_2510_3rounds_2510_1295018576112447_0210.json` — map 2510, cells_gap=9, q5_gap=3, status=count_prior
7. `fatbeans_valid_aisha_2401_5rounds_2401_1367517779389841_0050.json` — map 2401, cells_gap=-12, q5_gap=-2, status=count_prior
8. `fatbeans_valid_aisha_2510_3rounds_2510_1274128128479934_0209.json` — map 2510, cells_gap=14, q5_gap=1, status=count_prior
9. `fatbeans_valid_aisha_2403_3rounds_2403_1295019017648392_0051.json` — map 2403, cells_gap=21, q5_gap=-1, status=count_prior
10. `fatbeans_mixed_aisha_2410_4rounds_2410_1295018987511073_0006.json` — map 2410, cells_gap=-7, q5_gap=0, status=ok
