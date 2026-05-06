# bidking-lab

Unofficial hobby/research project: parse locally installed **BidKing** (`steamapps/common/BidKing`) data where possible, then build simulations (Monte Carlo / constraints — later).

This repo is **not** affiliated with the game or Steam. Game assets belong to their owners; do not redistribute ripped binaries.

**License**: this repository’s **source code** is under the [MIT License](LICENSE). It does **not** grant any rights to BidKing game assets, trademarks, or data files copied locally under `data/raw/` (those stay on your machine and out of git).

## Inspiration / attribution

- Data-shape ideas and prior art: [Jrinky908/bidking](https://github.com/Jrinky908/bidking) (Monte Carlo summaries, OCR notebook). If you reuse concepts, cite that repo in derivative work.

## Layout

| Path | Purpose |
|------|---------|
| `src/bidking_lab/` | Library code: config, schemas, extract stubs, simulation stubs |
| `data/raw/` | Local extracts / dumps (**gitignored** — put files here yourself) |
| `data/processed/` | Normalized CSV/JSON we generate |
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

1. **Extract**: locate tables / manifests under `BidKing_Data/StreamingAssets` → normalized probabilities & item metadata.
2. **Model**: warehouses, collectors’ skills (scoped constraints), items as grids (kernels), joint distributions — **TBD**.
3. **Simulate**: Monte Carlo and/or DP where tractable; convolution / bitmask grids for placement checks — **TBD**.
4. **UI**: thin wrapper (CLI first, then GUI/web).
