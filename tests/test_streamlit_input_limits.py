from pathlib import Path

from bidking_lab.capture.parser import parse_panel_text


APP_SOURCE = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def test_total_item_count_parser_accepts_values_above_legacy_ui_cap() -> None:
    result = parse_panel_text("本仓共有90件藏品", map_names={})

    assert result.suggestion_map()["total_item_count"] == 90


def test_observation_inputs_do_not_keep_legacy_small_caps() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "max_value=60" not in source
    assert "max_value=80" not in source
