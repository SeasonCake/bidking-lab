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
