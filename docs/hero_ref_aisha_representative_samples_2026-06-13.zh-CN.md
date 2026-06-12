# Hero Ref 艾莎代表样本表（2026-06-13）

从 curated gap audit 中按误差类型分层抽取，供 §61 批 B 回归与人工复核。
不全库使用；高 tail / ≤2 轮 / 证据不足样本已排除。

- 源脚本：`scripts/audit_aisha_gap.py`
- curated 池：见 `data/reports/audit_aisha_gap.txt`
- 本表条数：**20**

| # | 桶 | 文件 | map | r | 总格gap | 总件gap | q5 | q6值 | 金价only | balanced Δ |
|---|---|---|---:|---:|---:|---:|---|---|---|---:|
| 1 | grid_exact_total | `fatbeans_valid_aisha_2410_2rounds_2410_129501857` | 2410 | 3/4 | 18 | 0 | 7 | -173574 | - | 25527 |
| 2 | grid_exact_total | `fatbeans_mixed_aisha_2403_3rounds_2403_129501899` | 2403 | 3/4 | 13 | -2 | -2 | 46571 | - | -3290 |
| 3 | grid_exact_total | `fatbeans_valid_aisha_2510_3rounds_2510_129501857` | 2510 | 5/6 | 9 | 0 | 2 | -302080 | - | -152279 |
| 4 | grid_count_prior | `fatbeans_valid_aisha_2501_4rounds_2501_129501862` | 2501 | 6/7 | 97 | 25 | 6 | 494640 | - | 798245 |
| 5 | grid_count_prior | `fatbeans_valid_aisha_2503_2rounds_2503_129501865` | 2503 | 3/4 | 96 | 24 | 6 | 302580 | - | 539004 |
| 6 | grid_count_prior | `fatbeans_valid_aisha_2504_4rounds_2504_129501867` | 2504 | 6/7 | 30 | 27 | 4 | 788358 | - | 1007402 |
| 7 | total_items | `fatbeans_mixed_aisha_2504_4rounds_2504_127412812` | 2504 | 4/5 | 0 | 11 | 6 | 397392 | - | 466370 |
| 8 | total_items | `fatbeans_valid_aisha_2502_4rounds_2502_129501870` | 2502 | 7/8 | 0 | -6 | -4 | 69877 | - | 46935 |
| 9 | total_items | `fatbeans_valid_aisha_2408_5rounds_2408_129501857` | 2408 | 8/9 | 2 | 5 | 3 | 10756 | - | 69481 |
| 10 | red_value | `fatbeans_valid_aisha_2401_4rounds_2401_129501856` | 2401 | 6/7 | 5 | -1 | -2 | 887060 | - | 831758 |
| 11 | red_value | `fatbeans_valid_aisha_2501_5rounds_2501_129501866` | 2501 | 7/8 | 0 | 0 | 2 | -325341 | - | -230987 |
| 12 | red_value | `fatbeans_valid_aisha_2507_5rounds_2507_129501870` | 2507 | 8/9 | 4 | 3 | 2 | 296516 | - | 374247 |
| 13 | tier_counts | `fatbeans_valid_aisha_2508_4rounds_2508_127412812` | 2508 | 6/7 | 3 | 3 | 0 | -170240 | - | -151330 |
| 14 | tier_counts | `fatbeans_valid_aisha_2501_2rounds_2501_129501870` | 2501 | 3/4 | 0 | -2 | 4 | -73648 | - | 50348 |
| 15 | tier_counts | `fatbeans_mixed_aisha_2401_4rounds_2401_129501899` | 2401 | 4/5 | 7 | 1 | -3 | -87426 | - | -155716 |
| 16 | good_regression | `fatbeans_valid_aisha_2501_4rounds_2501_129501866` | 2501 | 6/7 | 3 | 3 | 2 | -170240 | - | -63702 |
| 17 | good_regression | `fatbeans_valid_aisha_2505_5rounds_2505_129501859` | 2505 | 7/8 | 3 | 1 | 1 | 25722 | - | 83626 |
| 18 | grid_count_prior | `fatbeans_valid_aisha_2410_2rounds_2410_129501866` | 2410 | 3/4 | 66 | 22 | 4 | 969764 | - | 1228115 |
| 19 | grid_count_prior | `fatbeans_valid_aisha_2408_2rounds_2408_136751777` | 2408 | 3/4 | 80 | 23 | 2 | 225104 | - | 383674 |
| 20 | grid_count_prior | `fatbeans_valid_aisha_2503_2rounds_2503_129501864` | 2503 | 3/4 | 92 | 17 | 3 | 299360 | - | 487613 |

## 批 B 回归门禁（15 条 `total_count_exact`）

优先用桶 `grid_exact_total` + `gold_price_only` 中带精确总件的样本；
每条改动需：`total_cells` band 覆盖或 mid-gap 缩小，且 `balanced` 不劣化 >15%。

1. `fatbeans_valid_aisha_2410_2rounds_2410_1295018574148404_0093.json` — map 2410, cells_gap=18, q5_gap=7, status=count_prior
2. `fatbeans_mixed_aisha_2403_3rounds_2403_1295018990047075_0002.json` — map 2403, cells_gap=13, q5_gap=-2, status=ok
3. `fatbeans_valid_aisha_2501_5rounds_2501_1295018669960456_0139.json` — map 2501, cells_gap=0, q5_gap=2, status=ok
4. `fatbeans_valid_aisha_2510_3rounds_2510_1295018576112447_0210.json` — map 2510, cells_gap=9, q5_gap=2, status=ok
5. `fatbeans_valid_aisha_2507_5rounds_2507_1295018647628127_0196.json` — map 2507, cells_gap=11, q5_gap=0, status=ok
6. `fatbeans_valid_aisha_2401_5rounds_2401_1295018668661353_0045.json` — map 2401, cells_gap=0, q5_gap=-1, status=ok
7. `fatbeans_valid_aisha_2401_3rounds_2401_1295019017806948_0032.json` — map 2401, cells_gap=0, q5_gap=0, status=ok
8. `fatbeans_valid_aisha_2401_5rounds_2401_1367517779389841_0050.json` — map 2401, cells_gap=2, q5_gap=1, status=ok
9. `fatbeans_valid_aisha_2403_3rounds_2403_1295019017648392_0051.json` — map 2403, cells_gap=0, q5_gap=-1, status=ok
10. `fatbeans_valid_aisha_2510_3rounds_2510_1274128128479934_0209.json` — map 2510, cells_gap=1, q5_gap=0, status=ok
11. `fatbeans_valid_aisha_2401_4rounds_2401_1295018573249457_0039.json` — map 2401, cells_gap=9, q5_gap=-1, status=ok
12. `fatbeans_valid_aisha_2404_3rounds_2404_1295018992793264_0056.json` — map 2404, cells_gap=12, q5_gap=-1, status=ok
13. `fatbeans_valid_aisha_2401_3rounds_2401_1295018668515929_0030.json` — map 2401, cells_gap=0, q5_gap=2, status=ok
14. `fatbeans_valid_aisha_2504_5rounds_2504_1295018708289152_0166.json` — map 2504, cells_gap=0, q5_gap=0, status=ok
