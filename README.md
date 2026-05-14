# bidking-lab

Unofficial hobby/research project: parse locally installed **BidKing** (`steamapps/common/BidKing`) data where possible, then build simulations (Monte Carlo / constraints — later).

This repo is **not** affiliated with the game or Steam. Game assets belong to their owners; do not redistribute ripped binaries.

**License**: this repository’s **source code** is under the [MIT License](LICENSE). It does **not** grant any rights to BidKing game assets, trademarks, or data files copied locally under `data/raw/` (those stay on your machine and out of git).

## Inspiration / attribution

- Data-shape ideas and prior art: [Jrinky908/bidking](https://github.com/Jrinky908/bidking) (Monte Carlo summaries, OCR notebook). If you reuse concepts, cite that repo in derivative work.
- Architecture / log-parsing / grid-view reference: [nql1314/bidking-booooot](https://github.com/nql1314/bidking-booooot) (Apache-2.0). See [`docs/upstream_references.md`](docs/upstream_references.md) for notes.

## Layout

| Path | Purpose |
|------|---------|
| `src/bidking_lab/` | Library code: config, schemas, extract stubs, simulation stubs |
| `data/raw/` | Local extracts / dumps (**gitignored** — put files here yourself) |
| `data/processed/` | Normalized CSV/JSON we generate |
| `docs/upstream_references.md` | Notes on external projects we inspect but do not vendor |
| `external_references/` | Local-only clones of upstream projects (**gitignored**) |
| `scripts/copy_game_tables.ps1` | Copy key `StreamingAssets/Tables` files into `data/raw/tables` |
| `TROUBLESHOOTING.md` | Problems & fixes during setup / data extraction |
| `notebooks/` | Exploration (StreamingAssets, probabilities) |
| `tests/` | Smoke tests |

### Sync game tables into `data/raw` (local only)

After installing the game, run from repo root:

```powershell
.\scripts\copy_game_tables.ps1
```

See **TROUBLESHOOTING.md** for path pitfalls and why `Tables/*.txt` may look encoded.

## Quick start

```powershell
cd bidking-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
pytest -q
```

Set game root (optional; overrides auto-detect on Windows):

```powershell
$env:BIDKING_GAME_ROOT = "C:\path\to\steamapps\common\BidKing"
python -c "from bidking_lab.config import get_game_root; print(get_game_root())"
```

## Roadmap (high level)

See **[`docs/project_vision.md`](docs/project_vision.md)** for the full three-layer map, the explicit list of player-facing questions we want to answer (Q1–Q5), and the things we deliberately do **not** do (no automation, no OCR, no ML-fitted drop tables — the rates are known, we sample them).

Short version:

1. **Layer 1 — Data**: decode `BidKing_Data/StreamingAssets/Tables/*.txt` (base64 + TSV) into typed JSON. Decoder + tests are in. Per-table schemas in progress.
2. **Layer 2 — Compute**: Monte Carlo over known drop weights; 2D convolution for grid placement; conditional probability for "what's left?" queries.
3. **Layer 3 — Surface**: notebooks first; Streamlit later if useful.
