# Upstream Reference Notes

This project keeps third-party BidKing-related repositories as **local-only references** under `external_references/`.
They are intentionally ignored by git and are not vendored into this repository, except for the isolated Hero Ref lab described below.

## Why local-only references?

- Keep our MIT-licensed source separate from upstream code and game-derived datasets.
- Preserve clear attribution and license boundaries.
- Let us inspect useful ideas without accidentally redistributing game data or unreviewed automation code.

Current local reference clones:

| Local path | Upstream | License / status | Role |
|---|---|---|---|
| `external_references/bidking-booooot` | <https://github.com/nql1314/bidking-booooot> | Apache-2.0 | Automation/OCR/log parsing/grid viewer/pricing architecture |
| `external_references/jrinky-bidking` | <https://github.com/Jrinky908/bidking> | No explicit license found in repo snapshot; README requests attribution | Monte Carlo calculator prior art, OCR notebook, merged CSVs, map priors |

Current local reference bundles:

| Local path | Source / status | Role |
|---|---|---|
| `external_references/grid_view_v1.3.7` | Local binary/data bundle, not vendored | Grid/value prior comparison data such as `map_quality_p50_out.csv` |
| `external_references/AuctionAnalyzer4.13.3` | Local binary/decompiled reference, not vendored | OCR/parser/calculator reference and reverse-engineering notes |
| `external_references/AuctionAnalyzer4.13.3.zip` | Local archive copy, not vendored | Original archive for the AuctionAnalyzer reference bundle |

Do not commit raw upstream bundles under `external_references/**`. Use them for inspection, comparison, and manually documented design notes.

Exception: `external_references/ahmad_live_reference_lab/` is local BidKing Lab code that wraps the Ahmad/Victor reference route. Its source, scripts, and docs are versioned; generated `build/`, `dist/`, `__pycache__`, and packaged binaries remain ignored.

---

## `nql1314/bidking-booooot`

### High-level positioning

This repository appears to be an integration of two earlier projects:

- `bidking-bot`: automation + OCR + bidding loop.
- `bidking-master`: log parsing + board viewer + valuation.

Its README describes a layered architecture:

```text
interaction/  # window, OCR, input, observe, round flow
parsing/      # logs -> events/state/processors
analysis/     # snapshot/grid overlay/quality stats/scan inference/unknown value
pricing/      # role-specific bidding strategies
ui/           # tkinter UI and grid board
logsys/       # app/perf/OCR/mouse/debug logs
config/       # runtime/pricing/per-map overrides
bridge/       # snapshot store / glue
runner/       # bot/viewer entry points
```

### What is useful for `bidking-lab`

Useful mainly as **design reference**, not as direct code import:

- **Data model ideas**:
  - `CsvItem`: `item_id`, `name`, `category_tags`, `shape`, `quality`, `base_value`.
  - `ItemKnowledge`: cumulative constraints about an unknown item: quality, categories, exact item id, price, excluded categories/qualities.
  - `GameState`: maintains items, players, round, and scan history.
- **Constraint modeling**:
  - `scan_inference.py` converts scan history into possible remaining qualities.
  - `state.py` records negative constraints: if a full scan misses an item, that item cannot belong to that quality/category.
- **Valuation ideas**:
  - `unknown_value.py` estimates unknown-contour items by converting weighted expected value into equivalent cell count.
  - `grid_overlay.py` merges game-known items with manually drawn / inferred shapes.
- **Reference datasets**:
  - `data/item_prices.csv`: normalized item catalog (`item_id`, `name`, categories, shape, quality, base value, grid size).
  - `data/drop_table_weights.csv`: simplified drop graph (`drop_id`, `ref_id`, `weight`, `ref_type`).
  - `data/calculator_data_merged.csv`: merged item + drop records.
  - `data/map_quality_avg_out.csv`, `data/tier_combo_presolve_q456.json`, and `物品轮廓爆率推断器.html` are useful for later validation.

### What is not our current scope

For now, avoid importing these into `bidking-lab`:

- Mouse/keyboard automation (`pyautogui`, bot runners).
- OCR runtime and screenshot loops (`rapidocr`, `onnxruntime`, GUI control).
- Tkinter GUI and PyInstaller packaging.
- Live bidding strategies that control the game.

Those are valuable if we later build an assistant UI, but they are outside the current goal: **local table decoding + probability simulation**.

### License note

`bidking-booooot` is Apache-2.0. If we copy code directly later, we must preserve attribution/license notices and mark modifications.
For now, it remains a local-only reference clone.

---

## `Jrinky908/bidking`

### High-level positioning

This is closer to our current target: a calculator based on Monte Carlo summaries and OCR-assisted data extraction.

README summary:

- It provides a Monte Carlo-derived dict after extracting `map_static_dict.rar`.
- Shape:

```text
{
  map_id: {
    rarity: {
      (total_grid_cells, item_count): (mean, std, min, max)
    }
  }
}
```

- Code is mostly in a notebook.
- OCR is used and the author notes it can be inaccurate.
- README requests attribution for derivative work.

### What is useful for `bidking-lab`

- Monte Carlo output schema: summarize by map / rarity / `(cells, item_count)`.
- Reference files:
  - `Drop.txt`, `Item.txt` — older or different table snapshots for comparison with our local game files.
  - `calculator_data_merged.csv` — useful to compare whether our decoded tables match public derived data.
  - `bidking_map_priors.csv` — map prior reference.
  - `maincode.py` — basic screenshot/OCR crop coordinates (not a data parser).
- README is useful for attribution language and expected simulator outputs.

### What to be careful about

- No explicit license was found in the snapshot. Treat as **reference only** unless permission/license is clarified.
- Do not vendor the `.rar` or large generated data into our public repository.
- Re-derive our own normalized tables from the installed game data where possible, and cite the repo as inspiration/reference.

---

## Near-term action plan

1. Decode / probe our local `data/raw/tables/Drop.txt`, `Item.txt`, and `BidMap.txt`.
2. Compare decoded records against:
   - `external_references/bidking-booooot/data/drop_table_weights.csv`
   - `external_references/bidking-booooot/data/calculator_data_merged.csv`
   - `external_references/jrinky-bidking/calculator_data_merged.csv`
3. Add our own normalized outputs under `data/processed/` only if they are safe to publish.
4. Keep upstream-derived raw files and cloned repositories out of git.
