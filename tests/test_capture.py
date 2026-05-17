"""Tests for capture text parser (no OCR)."""

from bidking_lab.capture.apply import apply_capture_result
from bidking_lab.capture.parser import parse_panel_text

MAP_NAMES = {
    2405: "望族居所",
    2510: "现代货轮娱乐库",
}


def test_ethan_screenshot_panel():
    text = (
        "\u7b2c3\u8f6e\n"
        "\u826f\u54c1\u626b\u63cf:\u826f\u54c1\u626b\u63cf\n"
        "\u6240\u6709\u84dd\u8272\u54c1\u8d28\u85cf\u54c1\u603b\u5360\u4f4d\u6570\u4e3a15\u683c\n"
        "\u4f0a\u68ee:\u7a7a\u95f4\u89c9\u77e5\n"
        "\u663e\u793a\u6240\u6709\u5df2\u77e5\u54c1\u8d28\u7684\u85cf\u54c1\u5404\u81ea\u7684\u8f6e\u5ed3\n"
        "\u666e\u54c1\u626b\u63cf:\u666e\u54c1\u626b\u63cf\n"
        "\u6240\u6709\u767d\u8272\u548c\u7eff\u8272\u54c1\u8d28\u85cf\u54c1\u603b\u5360\u4f4d\u6570\u4e3a 22 \u683c\n"
        "\u671b\u65cf\u5c45\u6240:\u7ade\u62cd\u4fe1\u606f\n"
        "\u968f\u673a\u663e\u793a9\u4ef6\u85cf\u54c1\u7684\u54c1\u8d28\n"
        "\u4f18\u54c1\u5747\u683c:\u4f18\u54c1\u5747\u683c\n"
        "\u6240\u6709\u7d2b\u8272\u54c1\u8d28\u85cf\u54c1\u5e73\u5747\u5360\u4f4d\u7ea63.27\u683c\n"
    )
    r = parse_panel_text(text, map_names=MAP_NAMES)
    m = r.suggestion_map()
    assert r.map_id == 2405
    assert m["blue_cells"] == 15
    assert m["wg_cells"] == 22
    assert m["purple_avg_raw"] == "3.27"
    assert "total_item_count" not in m  # 「随机显示9件藏品的品质」为无用 hint
    assert any("显示" in x for x in r.ignored)


def test_ignore_quality_fluff():
    text = "显示紫色品质藏品的轮廓"
    r = parse_panel_text(text, map_names=MAP_NAMES)
    assert r.suggestions == []
    assert len(r.ignored) >= 1


def test_map_purple_avg_value():
    text = "紫色品质藏品均价为 9,400 silver"
    r = parse_panel_text(text, map_names=MAP_NAMES)
    assert r.suggestion_map()["purple_avg_value"] == 9400


def test_map_name_ocr_typos_doomsday():
    names = {2409: "末日庇护所", 2510: "现代货轮娱乐库"}
    text = "末日底护所：完拍信息\n"
    r = parse_panel_text(text, map_names=names)
    assert r.map_id == 2409


def test_map_name_longest_match():
    names = {2405: "望族居所", 2403: "设计师居所", 2510: "现代货轮娱乐库"}
    text = "设计师居所:竞拍信息\n"
    r = parse_panel_text(text, map_names=names)
    assert r.map_id == 2403


def test_purple_value_total_phrase():
    text = "所有紫色品质藏品的总价值为86490"
    r = parse_panel_text(text, map_names=MAP_NAMES)
    assert r.suggestion_map()["purple_value"] == 86490


def test_apply_sets_streamlit_widget_keys():
    from bidking_lab.capture.apply import reading_widget_key

    text = (
        "\u6240\u6709\u84dd\u8272\u54c1\u8d28\u85cf\u54c1\u603b\u5360\u4f4d\u6570\u4e3a15\u683c\n"
        "\u6240\u6709\u767d\u8272\u548c\u7eff\u8272\u54c1\u8d28\u85cf\u54c1\u603b\u5360\u4f4d\u6570\u4e3a 22 \u683c\n"
        "\u6240\u6709\u7d2b\u8272\u54c1\u8d28\u85cf\u54c1\u5e73\u5747\u5360\u4f4d\u7ea63.27\u683c\n"
    )
    result = parse_panel_text(text, map_names=MAP_NAMES)
    obs: dict = {}
    ui: dict = {}
    apply_capture_result(result, obs, ui)
    assert obs["wg_cells"] == 22
    assert obs["blue_cells"] == 15
    assert ui[reading_widget_key("obs_reading_wg_cells", ui)] == 22
    assert ui[reading_widget_key("obs_reading_blue_cells", ui)] == 15
    assert ui[reading_widget_key("purple_avg_raw_widget", ui)] == "3.27"


def test_total_item_count_hint():
    text = "本场共有35件藏品"
    r = parse_panel_text(text, map_names=MAP_NAMES)
    assert r.suggestion_map()["total_item_count"] == 35


def test_warehouse_cells_from_panel_line():
    text = "所有藏品总占用的格子数量为159格"
    r = parse_panel_text(text, map_names=MAP_NAMES)
    assert r.suggestion_map()["warehouse_cells"] == 159


def test_warehouse_cells_ocr_typo_yipin():
    """RapidOCR often reads 藏品 as 意品 on the warehouse banner line."""
    text = "所有意品总占用的格子数量为159格"
    r = parse_panel_text(text, map_names=MAP_NAMES)
    assert r.suggestion_map()["warehouse_cells"] == 159


def test_realistic_ocr_fragment_lines():
    """Lines extracted from a full-screen OCR run (post-normalize)."""
    text = (
        "第3轮\n"
        "所有意品总占用的格子数量为159格\n"
        "品总占位款为35格\n"
        "色品质随品总占位致为28格\n"
        "品平均占位约3.43格\n"
    )
    m = parse_panel_text(text, map_names=MAP_NAMES).suggestion_map()
    assert m["warehouse_cells"] == 159
    assert m["blue_cells"] == 35
    assert m["purple_avg_raw"] == "3.43"
    # 「色品质随品…28格」断行碎片：旧版误写入 wg；现不强制映射


def test_clear_readings_for_map_change():
    from bidking_lab.capture.apply import clear_readings_for_map_change, reading_widget_key

    obs = {"wg_cells": 22, "blue_cells": 15, "map_id": 2405}
    ui = {
        reading_widget_key("obs_reading_wg_cells", {}): 22,
        reading_widget_key("obs_reading_blue_cells", {}): 15,
    }
    clear_readings_for_map_change(obs, ui)
    assert "wg_cells" not in obs
    assert ui["obs_readings_rev"] == 1
    assert reading_widget_key("obs_reading_wg_cells", ui) not in ui
    assert obs["map_id"] == 2405


def test_full_scan_panel_ocr_typos():
    """R4 full-screen OCR: 占位数/紧色/扫描误字 + 所有{色}…总占 lines."""
    text = (
        "第4轮\n"
        "所有蓝色品质藏品总点位数为35格\n"
        "普品扫描：普品扫描\n"
        "所有白色和绿色品质藏品总占位数为12格\n"
        "优品扫描：代优品扫描\n"
        "所有紧色品质蓝品总占位数为34格\n"
        "极品扫描：极品扫描\n"
        "所有金色品质藏品总占位数为28格\n"
    )
    m = parse_panel_text(text, map_names=MAP_NAMES).suggestion_map()
    assert m["wg_cells"] == 12
    assert m["blue_cells"] == 35
    assert m["purple_cells"] == 34
    assert m["gold_cells"] == 28


def test_apply_does_not_change_hero():
    text = "艾莎\n伊森：空间觉知\n所有蓝色品质藏品总占位数为35格"
    result = parse_panel_text(text, map_names=MAP_NAMES)
    obs = {"hero": "ethan"}
    ui = {"obs_hero": "ethan"}
    apply_capture_result(result, obs, ui)
    assert ui["obs_hero"] == "ethan"
    assert obs.get("hero") == "ethan"


def test_apply_switches_map_category():
    from bidking_lab.capture.types import CaptureParseResult

    result = CaptureParseResult(map_id=2510, map_name="现代货轮娱乐库")
    obs = {"map_id": 2403, "hero": "ethan"}
    ui: dict = {
        "obs_map_category": "mansion",
        "obs_map_select": 2403,
    }
    apply_capture_result(result, obs, ui, map_names={2510: "现代货轮娱乐库"})
    assert ui["obs_map_category"] == "shipwreck"
    rev = int(ui.get("obs_map_select_rev", 0))
    assert ui[f"obs_map_select__r{rev}"] == 2510
    assert obs["map_id"] == 2510
