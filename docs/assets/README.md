# docs/assets — 顶层 README 用图片资源

这里放 `README.md` 引用的截图 / hero 图 / 视频缩略图等静态资源。

## 命名约定

| 文件名 | 内容 | 推荐尺寸 |
|---|---|---|
| `hero.png` | 顶部 hero 横图（Streamlit 主界面 + 一个出价分布图二合一截图） | 1280 × 640 |
| `01_inputs.png` | 「读数输入与候选预览」tab，紫品几个字段已填、下方有实时 top-3 预览 | 1100 × 620 |
| `02_bidding.png` | 「出价推荐」tab，分布直方图 + P25/P50/P75 + 秒仓上限 metric | 1100 × 620 |
| `03_roi.png` | 「道具 ROI」tab，柱状图英文 label + 详细表 + 仓库噪声 σ 滑块 | 1100 × 620 |
| `04_joint.png` | 「联合推断」tab（实验性，需要侧边栏勾选开启），top-3 候选表 | 1100 × 620 |

## 截图建议

1. 启动 `streamlit run app/streamlit_app.py`
2. 侧边栏选 **别墅 → 2407 私人金库**（或沉船 2510），仓库 128 格
3. 填一组真实读数（参考 `notebooks/05_end_to_end_case.ipynb` 场景 C）：
   - q=1 cells=24, count=12
   - q=2 cells=18, count=7
   - q=3 cells=22, count=5
   - q=4 cells=48, count=8, value_sum=89400, huge_band="2-3"
   - total_item_count=35
4. 切换到 4 个 tab 分别截图
5. 命名后丢到本目录，去 `README.md` 把对应的 `<!-- ![...]( ... ) -->` 取消注释

## 视频建议

GitHub 在 Issue 评论框里可以直接拖 `.mp4`（≤ 100 MB），上传完后会给一个 `https://github.com/<user>/<repo>/assets/...` 的永久 URL。把那个 URL 粘到 `README.md` 顶部的 `📹 完整演示视频` 位置就行，无需放仓库里。

15-30 秒的内容建议：
1. 5 秒：选地图 → 填一组读数
2. 10 秒：切到出价 tab，展示分布图 + 秒仓推荐
3. 10 秒：切到 ROI tab，拉一下 σ 滑块演示总仓储 ROI 灵敏度
4. 5 秒：底部 footer / GitHub 链接

不必加旁白，可以加 1-2 个 caption 字幕。
