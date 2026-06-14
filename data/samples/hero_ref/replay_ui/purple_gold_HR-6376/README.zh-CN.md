# 真实样本回放：紫金件数+格子（HR-20260614-6376）

来源：`data/samples/hero_ref/archive/exports/2026-06-14/HeroRefDiag-20260614-015004-2404_1425860640906376.zip`  
Session：`2404:1425860640906376`（艾莎 · 2404）

| 文件 | 场景 | 「紫金件」预期 |
|---|---|---|
| `r02_bidding.json` | R2 竞价中 | `紫件 4/7/10 · 金3`（live 未锁 top3，显示区间） |
| `r02_settled.json` | R2 结算 | `紫4/11 · 金3/11`（结算 truth + final_quality_cells） |

刷新时间戳并打开 UI：

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
python -c "import json,time,zipfile; from pathlib import Path; z=Path('data/samples/hero_ref/archive/exports/2026-06-14/HeroRefDiag-20260614-015004-2404_1425860640906376.zip'); o=Path('data/samples/hero_ref/replay_ui/purple_gold_HR-6376');
with zipfile.ZipFile(z) as zf:
  [ (lambda n,d:(d.update({'created_at':time.time()}), o.joinpath(Path(n).name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')))[1] for n in ('round_snapshots/r02_bidding.json','round_snapshots/r02_settled.json') for d in [json.loads(zf.read(n))] ]"

python external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py --snapshot data\samples\hero_ref\replay_ui\purple_gold_HR-6376\r02_bidding.json --load-existing
python external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py --snapshot data\samples\hero_ref\replay_ui\purple_gold_HR-6376\r02_settled.json --load-existing
```

看 **「红品与价值 → 紫金件」** 行。
