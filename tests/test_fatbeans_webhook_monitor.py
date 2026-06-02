from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "scripts" / "run_fatbeans_webhook_monitor.py"
    spec = importlib.util.spec_from_file_location("run_fatbeans_webhook_monitor", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload(**overrides):
    payload = {
        "Protocol": "Tcp",
        "SrcIP": "127.0.0.1",
        "SrcPort": 50123,
        "DstIP": "8.133.195.27",
        "DstPort": 10000,
        "Url": None,
        "PID": 1234,
        "ProcessName": "BidKing.exe",
        "Data": base64.b64encode(b"\x00\x00\x00\x04").decode("ascii"),
        "Request": None,
        "Response": None,
    }
    payload.update(overrides)
    return payload


def test_webhook_payload_to_row_infers_send_and_data_length() -> None:
    module = _module()

    row = module._webhook_payload_to_row(_payload(), sort_id=7)

    assert row["SortID"] == 7
    assert row["Direct"] == "SEND"
    assert row["Protocol"] == "Tcp"
    assert row["DstPort"] == 10000
    assert row["DataLength"] == 4
    assert row["ProcessName"] == "BidKing.exe"


def test_webhook_payload_to_row_infers_receive_from_server_port() -> None:
    module = _module()

    row = module._webhook_payload_to_row(
        _payload(
            SrcIP="8.133.195.27",
            SrcPort=10000,
            DstIP="127.0.0.1",
            DstPort=50123,
        ),
        sort_id=8,
    )

    assert row["Direct"] == "REV"
    assert row["SrcPort"] == 10000


def test_webhook_payload_to_row_filters_non_target_process() -> None:
    module = _module()

    assert (
        module._webhook_payload_to_row(
            _payload(ProcessName="chrome.exe"),
            sort_id=1,
            process_name="BidKing.exe",
        )
        is None
    )


def test_webhook_monitor_processes_accumulated_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    log_dir = tmp_path / "logs"
    raw_dir = tmp_path / "raw"
    calls: dict[str, object] = {}

    def fake_build(payload, *, file, **_kwargs):
        calls["payload"] = json.loads(payload)
        calls["file"] = file
        return {
            "created_at": 1000.0,
            "file": file,
            "ui_contract": {
                "baseline": {
                    "decision": {"action": "可守不抢"},
                    "posterior": {"status": "ok"},
                }
            },
        }

    def fake_write(artifact, *, log_dir):
        calls["artifact"] = dict(artifact)
        calls["log_dir"] = Path(log_dir)

    monkeypatch.setattr(module, "build_monitor_artifact_from_payload", fake_build)
    monkeypatch.setattr(module, "write_monitor_logs", fake_write)

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=log_dir,
            raw_dir=raw_dir,
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=20,
            roi_trials=0,
            shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
        ),
        tables=object(),
    )

    result = monitor.accept_payload(_payload())
    monitor._process_snapshot(force=True)

    assert result["accepted"] is True
    assert raw_dir.joinpath("fatbeans_webhook_live.json").exists()
    assert calls["file"] == "fatbeans_webhook_live.json"
    assert calls["log_dir"] == log_dir
    rows = calls["payload"]
    assert rows[0]["Direct"] == "SEND"
    artifact = calls["artifact"]
    assert artifact["source"] == "fatbeans_webhook"
    assert artifact["webhook_packets"] == 1
