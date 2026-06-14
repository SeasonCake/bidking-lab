# Hero Ref 诊断样本归档

统一存放 Hero Ref 支线排查用的 **导出 zip** 与匹配的 **reset json**，避免只在 `data/logs/live/exports` 里散落、也不再把路径写死在多处文档里。

## 目录

```text
data/samples/hero_ref/
  README.zh-CN.md          ← 本说明
  manifest.json            ← 机器可读 catalog（由脚本生成）
  archive/
    exports/YYYY-MM-DD/    ← HeroRefDiag-*.zip 副本
    reset/YYYY-MM-DD/      ← 同 session 的 windivert reset（若有）
```

**原始 live 目录仍保留**（monitor 正在写）：

- `data/logs/live/exports/` — 最新导出
- `data/logs/live/raw/archive/reset/` — reset 归档

`manifest.json` 里的路径以 **`data/samples/hero_ref/archive/...`** 为准；需要最新一局时仍以 live 目录为准。

## 刷新 catalog

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
python scripts/organize_hero_ref_samples.py          # 预览
python scripts/organize_hero_ref_samples.py --apply  # 复制 + 写 manifest
```

## 复放单包（ref + 公开信息）

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
$zip = "data/samples/hero_ref/archive/exports/2026-06-12/HeroRefDiag-20260612-211125-2102_1425860536614653.zip"
python -c "
import json, zipfile, sys
from pathlib import Path
sys.path.insert(0,'src'); sys.path.insert(0,'external_references/ahmad_live_reference_lab/src')
from bidking_lab.live.fatbeans import load_fatbeans_packets_from_rows, parse_fatbeans_packets
from bidking_lab.live.monitor import load_monitor_tables, build_monitor_artifact_from_events
from ahmad_ref_engine import run_reference_engine
zpath = Path(r'$zip'.Replace('\','/'))
rows = [json.loads(l) for l in zipfile.ZipFile(zpath).read('raw/windivert_live.jsonl').decode().splitlines() if l.strip()]
art = build_monitor_artifact_from_events(parse_fatbeans_packets(load_fatbeans_packets_from_rows(rows)), tables=load_monitor_tables(), run_debug_shadows=False)
snap = {'ui_contract': art['ui_contract'], 'structured_ref_inputs': art.get('structured_ref_inputs') or {}, 'public_info_rows': art.get('public_info_rows') or []}
res = run_reference_engine(snap, max_combos=60000).as_dict()
print('public_info_rows', [(r['info_id'], r['value']) for r in art.get('public_info_rows') or []])
print('q5 range', res.get('quality_count_ranges',{}).get('q5'))
print('notes', [n for n in res.get('notes',[]) if 'q5' in n or '200019' in n or '200037' in n])
"
```

## 主题 tag（manifest `themes`）

| tag | 用途 |
| --- | --- |
| `gold_zero_public` | 公开信息金均价/金件数/金均格为零（`200037` / `200019` / `200015` 等） |
| `maria_skill` | Maria `100108` / `10010801` skill + 公开信息 |
| `public_info_minimap` | 公开摇号/轮廓/命名物品 → 小地图 marker |
| `public_avg_cells` | 公开均格 `200013–200016` |
| `settlement_q5_zero` | 结算 truth 金件为 0 |
| `aisha_settled_estimate_leak` | 结算页「估价」泄露 `ui_contract.constraints` 结算证据（fix `b94c474`）；用于结算复核估价回归 |

## 文档索引

- 人读 catalog + 机制说明：[`docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md`](../../docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md) §9–§10
- 总索引：[`docs/HERO_REF_FILE_AND_DOC_INDEX.zh-CN.md`](../../docs/HERO_REF_FILE_AND_DOC_INDEX.zh-CN.md)
