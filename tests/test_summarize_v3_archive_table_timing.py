import base64
import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_archive_table_timing.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_archive_table_timing",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_archive_table_timing_summarizes_versions_and_capture_range(tmp_path: Path) -> None:
    module = _load_module()
    raw_root = tmp_path / "raw"
    tables_root = raw_root / "tables"
    tables_root.mkdir(parents=True)
    (raw_root / "fileVersion").write_text("300", encoding="utf-8")
    (tables_root / "fileVersion").write_text("300", encoding="utf-8")
    (raw_root / "filelist.txt").write_text(
        "\n".join(
            (
                "Ver:300|FileCount:2",
                "Tables/BidMap.txt|abc=$10",
                "Tables/Drop.txt|def=$20",
            )
        ),
        encoding="utf-8",
    )
    (tables_root / "BidMap.txt").write_text("bidmap", encoding="utf-8")
    (tables_root / "Drop.txt").write_text("drop", encoding="utf-8")

    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            [
                {
                    "CaptureTime": "2026-06-01T10:00:00+08:00",
                    "CaptureTimestamp": 1780231200000,
                    "ClientVersion": "1.2.3",
                },
                {
                    "CaptureTime": "2026-06-01T10:01:00+08:00",
                    "CaptureTimestamp": 1780231260000,
                },
            ]
        ),
        encoding="utf-8",
    )

    result = module.summarize_archive_table_timing([sample], raw_root=raw_root)

    assert result["raw_file_version"] == "300"
    assert result["raw_tables_file_version"] == "300"
    assert result["raw_filelist_header"] == "Ver:300|FileCount:2"
    assert result["raw_filelist_bidmap_entry"] == "Tables/BidMap.txt|abc=$10"
    assert result["raw_filelist_drop_entry"] == "Tables/Drop.txt|def=$20"
    assert result["sample_file_count"] == 1
    assert result["capture_timestamp_rows"] == 2
    assert result["capture_time_min"] == "2026-06-01T10:00:00+08:00"
    assert result["capture_time_max"] == "2026-06-01T10:01:00+08:00"
    assert result["capture_version_like_keys"] == ["ClientVersion"]


def _encoded_table(rows: list[list[str]]) -> str:
    text = "\n".join("\t".join(row) for row in rows)
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def test_archive_table_timing_summarizes_bidmap_and_drop_semantics(
    tmp_path: Path,
) -> None:
    module = _load_module()
    raw_root = tmp_path / "raw"
    tables_root = raw_root / "tables"
    tables_root.mkdir(parents=True)
    (raw_root / "fileVersion").write_text("300", encoding="utf-8")
    (tables_root / "fileVersion").write_text("300", encoding="utf-8")
    (raw_root / "filelist.txt").write_text(
        "\n".join(
            (
                "Ver:300|FileCount:2",
                "Tables/BidMap.txt|abc=$10",
                "Tables/Drop.txt|def=$20",
            )
        ),
        encoding="utf-8",
    )
    bidmap_row = ["0"] * 23
    bidmap_row[0] = "2501"
    bidmap_row[1] = "未知残骸"
    bidmap_row[2] = "desc"
    bidmap_row[7] = "104"
    bidmap_row[8] = "1"
    bidmap_row[9] = "[[]]"
    bidmap_row[10] = "ui_value_higher"
    bidmap_row[11] = "25"
    bidmap_row[12] = "[1,1,2000]"
    bidmap_row[13] = "[[]]"
    bidmap_row[14] = "[50,50,50,50,50]"
    bidmap_row[15] = "[[1,1,10000]]"
    bidmap_row[16] = "[[]]"
    bidmap_row[17] = "[9999,2501,22,44]"
    bidmap_row[18] = "4"
    bidmap_row[19] = "[2000,1600,1300,1100,0]"
    bidmap_row[20] = "[104,0,0,0,0]"
    bidmap_row[21] = "iconmap_2501"
    bidmap_row[22] = "0"
    (tables_root / "BidMap.txt").write_text(
        _encoded_table([bidmap_row]),
        encoding="utf-8",
    )
    drop_rows = [
        [
            "2501",
            "top",
            "desc",
            "1",
            json.dumps([[9999, 2001, 1, 1, 100]]),
        ],
        [
            "2001",
            "leaf",
            "desc",
            "1",
            json.dumps(
                [
                    [101, 1001001, 1, 1, 100],
                    [102, 1002001, 1, 2, 50],
                ]
            ),
        ],
    ]
    (tables_root / "Drop.txt").write_text(
        _encoded_table(drop_rows),
        encoding="utf-8",
    )

    result = module.summarize_archive_table_timing([], raw_root=raw_root)

    bidmap = result["bidmap_semantics"]
    assert bidmap["row_count"] == 1
    assert bidmap["column_count_counts"] == {"23": 1}
    assert bidmap["current_23_column_rows"] == 1
    assert bidmap["col16_value_counts"] == {"[[]]": 1}
    assert bidmap["col16_drop_ref_like_rows"] == 0
    assert bidmap["col17_drop_ref_like_rows"] == 1
    assert bidmap["drop_ref_pair_counts"] == {"22-44": 1}
    target = {row["map_id"]: row for row in bidmap["target_maps"]}[2501]
    assert target["v300_flag_a"] == "1"
    assert target["col16_placeholder"] == "[[]]"
    assert target["drop_ref_col17"] == "[9999,2501,22,44]"

    drop = result["drop_semantics"]
    assert drop["pool_count"] == 2
    assert drop["ref_n_range_counts"] == {"1-1": 1}
    assert drop["leaf_n_range_counts"] == {"1-1": 1, "1-2": 1}
    drop_target = {row["map_id"]: row for row in drop["target_maps"]}[2501]
    assert drop_target["status"] == "ok"
    assert drop_target["visited_pool_count"] == 2
    assert drop_target["leaf_n_range_counts"] == {"1-1": 1, "1-2": 1}
    assert drop_target["leaf_n_max_max"] == 2
