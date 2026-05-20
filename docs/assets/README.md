# docs/assets — README image assets

Static images referenced from the top-level `README.md` / `README.zh-CN.md` showcase.

## Files

| Filename | Content | Used in |
|---|---|---|
| `01-inputs.png` | Readings tab — OCR sidebar, field scope captions, purple/gold candidate preview | Snapshots table cell 1 |
| `02-bidding.png` | Bidding tab — MC histogram (P25/P50/P75/P90), bucket posterior table, analytical band | Snapshots table cell 2 |

Both rendered from a Streamlit session at default zoom; PNG.

## Refreshing screenshots

If the UI changes substantially, retake with:

1. `streamlit run app/streamlit_app.py`
2. Sidebar: pick a representative map (e.g. **别墅 → 2405 望族居所**, warehouse 72 cells)
3. Fill a reading set with OCR or manual input (see `notebooks/05_end_to_end_case.ipynb` scenario C)
4. Screenshot the **读数输入** tab (sidebar + one bucket section + candidate preview) → `01-inputs.png`
5. Switch to **出价推荐** and screenshot the histogram + bucket posterior table → `02-bidding.png`

Keep the filenames stable — the README hardcodes them.

## Demo video

The 30-second demo video is hosted via GitHub user-attachments (drag-and-drop upload in any issue / PR comment, then copy the resulting `https://github.com/user-attachments/assets/<uuid>` URL into the README's Demo section). GitHub auto-renders it as an inline player, no `<video>` tag needed.

Current video URL (`9fb463dc-ca85-4fc0-b10e-56b81091a5a8`) is wired into both `README.md` and `README.zh-CN.md`. To swap it, search-replace the URL in both files.
