# Hero Ref 支线索引

日期：2026-06-09

## 定位

Hero Ref 是 `external_references/ahmad_live_reference_lab/` 下的可版本化支线，用于把外援 Ahmad/Victor 计算器思路做成实战小窗：

- 读取主线 live monitor 生成的 `data/logs/live/latest_snapshot.json`；
- 消费 `structured_ref_inputs`、`ui_contract`、小地图和结算回放；
- 输出 compact Tk overlay、三档参考价、红品/格数范围、手填 fallback；
- 不写主线 formal decision，不替换 v3 sampler，不放宽 v3 promotion gate。

完整收口记录见：

`external_references/ahmad_live_reference_lab/CLOSEOUT_2026-06-09.zh-CN.md`

## 主线接点

当前支线可以读取和依赖这些主线稳定输出：

| 接点 | 作用 |
| --- | --- |
| `scripts/start_live_windivert_overlay.ps1 -NoOverlay` | 启动后台 monitor，不打开主线 overlay |
| `data/logs/live/latest_snapshot.json` | Hero Ref 唯一实时输入快照 |
| `structured_ref_inputs` | Ahmad/Victor/Aisha/普通道具的结构化数字证据 |
| `ui_contract.minimap` | 只读小地图、公开 marker、结算 footprint |
| `scripts/post_game_live.ps1` | 局后归档样本，供支线和主线审计复用 |

## 已收口能力

- Ahmad `100204x`、Victor `100209`、Aisha 白/绿 split、普通道具 `100104-100120` 已有 source -> transform -> output 回归。
- 手填 fallback 与 live snapshot 可叠加；跨局、结算、旧快照会清空手填覆盖。
- public marker / hard footprint 在小地图中区分显示。
- 快递/仓库、集装箱、别墅、沉船/活动沉船、hidden 地图族已有基础支持。
- portable 包模板位于 `apps/hero_ref/`，当前本地构建输出位于 `external_references/ahmad_live_reference_lab/dist/BidKingHeroRefPortable`。

## 主线边界

- Hero Ref 的 `ref_v0` 结果是应用层参考，不是主线 v3 readiness/promotion evidence。
- 支线截图、视频、UI 体验和实战反馈可以作为主线设计参考，但不能直接替代 archive/session/holdout 指标。
- hidden 缺专属 nest price 时会 fallback 默认价格；主线不得把这个当作 hidden 专属校准表。
- 当前 portable 包仍依赖本机 Python/pydivert/psutil；完全自包含 zip 是后续应用打包任务。
