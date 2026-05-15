# docs/assets — README image assets

Static images referenced from the top-level `README.md` / `README.zh-CN.md` showcase.

## Files

| Filename | Content | Used in |
|---|---|---|
| `01-inputs.png` | Streamlit "observation input" panel — purple bucket fields filled, live top-K candidate enumeration showing | Snapshots table cell 1 |
| `02-bidding.png` | Streamlit "bidding hint" panel — value distribution histogram with P25/P50/P75/P90 reference lines | Snapshots table cell 2 |

Both rendered at ~1100 × 620 from a Streamlit session at default zoom; PNG, ~75 KB each.

## Refreshing screenshots

If the UI changes substantially, retake with:

1. `streamlit run app/streamlit_app.py`
2. Sidebar: select **别墅 → 2405 望族居所**, warehouse 72 cells
3. Fill a representative reading set (see `notebooks/05_end_to_end_case.ipynb` scenario C for one example)
4. Screenshot the "input" tab (covering the purple-bucket section) → `01-inputs.png`
5. Run `运行出价 hint` and screenshot the bidding panel (covering value distribution + bucket posterior cards) → `02-bidding.png`

Keep the filenames stable — the README hardcodes them.

## Demo video

The 30-second demo video is hosted via GitHub user-attachments (drag-and-drop upload in any issue / PR comment, then copy the resulting `https://github.com/user-attachments/assets/<uuid>` URL into the README's Demo section). GitHub auto-renders it as an inline player, no `<video>` tag needed.

Current video URL is wired into both `README.md` and `README.zh-CN.md`. To swap it, search-replace the URL in both files.
