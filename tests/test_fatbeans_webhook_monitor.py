from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any


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

    def fake_write(artifact, *, log_dir, append_logs=True):
        calls["artifact"] = dict(artifact)
        calls["log_dir"] = Path(log_dir)
        calls["append_logs"] = append_logs

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
            full_shadow_trials=20,
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
    assert artifact["capture_rows"] == 1
    assert artifact["webhook_packets"] == 1
    assert calls["append_logs"] is True


def test_capture_row_monitor_uses_configured_source_name(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    log_dir = tmp_path / "logs"
    raw_dir = tmp_path / "raw"
    calls: dict[str, object] = {}

    def fake_build(payload, *, file, **_kwargs):
        calls["payload"] = json.loads(payload)
        return {"created_at": 1000.0, "file": file}

    def fake_write(artifact, *, log_dir, append_logs=True):
        calls["artifact"] = dict(artifact)
        calls["log_dir"] = Path(log_dir)
        calls["append_logs"] = append_logs

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
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
            file_name="windivert_live.json",
            source_name="windivert",
            packet_count_key="windivert_frames",
        ),
        tables=object(),
    )

    row = module._webhook_payload_to_row(_payload(), sort_id=1)
    assert row is not None
    monitor.accept_row(row)
    monitor._process_snapshot(force=True)

    artifact = calls["artifact"]
    assert artifact["source"] == "windivert"
    assert artifact["capture_rows"] == 1
    assert artifact["windivert_frames"] == 1
    assert "webhook_packets" not in artifact
    assert calls["append_logs"] is True


def test_monitor_passes_cached_local_player_id_hint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    log_dir = tmp_path / "logs"
    raw_dir = tmp_path / "raw"
    module._write_cached_local_player_id(
        module._local_player_cache_path(log_dir),
        600264629315280,
    )
    hints: list[int | None] = []

    def fake_build(payload, *, file, local_player_id_hint=None, **_kwargs):
        hints.append(local_player_id_hint)
        return {"created_at": 1000.0, "file": file}

    monkeypatch.setattr(module, "_semantic_signature_from_payload", lambda _payload: None)
    monkeypatch.setattr(module, "build_monitor_artifact_from_payload", fake_build)
    monkeypatch.setattr(
        module,
        "parse_fatbeans_capture_payload",
        lambda _payload, **_kwargs: SimpleNamespace(
            states=(SimpleNamespace(player_id=600264629315280),),
        ),
    )
    monkeypatch.setattr(module, "write_monitor_logs", lambda *args, **kwargs: None)

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=log_dir,
            raw_dir=raw_dir,
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=20,
            roi_trials=0,
            shadow_trials=20,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
        ),
        tables=object(),
    )

    monitor.accept_row({"SortID": 1, "Direct": "REV"}, schedule_process=True)
    monitor._process_snapshot(force=True)

    assert hints == [600264629315280]


def test_monitor_caches_inferred_local_player_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    log_dir = tmp_path / "logs"
    raw_dir = tmp_path / "raw"

    monkeypatch.setattr(module, "_semantic_signature_from_payload", lambda _payload: None)
    monkeypatch.setattr(
        module,
        "build_monitor_artifact_from_payload",
        lambda _payload, *, file, local_player_id_hint=None, **_kwargs: {
            "created_at": 1000.0,
            "file": file,
            "local_player_id_hint": local_player_id_hint,
        },
    )
    monkeypatch.setattr(
        module,
        "parse_fatbeans_capture_payload",
        lambda _payload, **_kwargs: SimpleNamespace(
            states=(SimpleNamespace(player_id=600264629315280),),
        ),
    )
    monkeypatch.setattr(module, "write_monitor_logs", lambda *args, **kwargs: None)

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=log_dir,
            raw_dir=raw_dir,
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=20,
            roi_trials=0,
            shadow_trials=20,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
        ),
        tables=object(),
    )

    monitor.accept_row({"SortID": 1, "Direct": "REV"}, schedule_process=True)
    monitor._process_snapshot(force=True)

    payload = json.loads(
        module._local_player_cache_path(log_dir).read_text(encoding="utf-8-sig")
    )
    assert payload["local_player_id"] == 600264629315280


def test_monitor_archives_raw_rows_before_reset(tmp_path: Path) -> None:
    module = _module()
    raw_dir = tmp_path / "raw"
    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=raw_dir,
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=20,
            roi_trials=0,
            shadow_trials=20,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
            file_name="windivert_live.json",
            source_name="windivert",
        ),
        tables=object(),
    )
    row = module._webhook_payload_to_row(_payload(), sort_id=1)
    assert row is not None
    row["SessionID"] = "2407:1295018931873899"
    row["MessageID"] = "0x0077"

    monitor.accept_row(row, schedule_process=False)
    monitor.reset_rows()

    archives = list(raw_dir.glob("archive/reset/windivert_live_*_reset.json"))
    assert len(archives) == 1
    archived_rows = json.loads(archives[0].read_text(encoding="utf-8"))
    assert isinstance(archived_rows, list)
    assert archived_rows[0]["SessionID"] == "2407:1295018931873899"


def test_webhook_monitor_writes_fast_snapshot_without_appending_logs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    calls: list[dict[str, object]] = []

    def fake_build(
        payload,
        *,
        file,
        n_trials,
        roi_trials,
        shadow_trials,
        run_debug_shadows,
        **_kwargs,
    ):
        return {
            "created_at": 1000.0,
            "file": file,
            "payload_rows": len(json.loads(payload)),
            "n_trials": n_trials,
            "roi_trials": roi_trials,
            "shadow_trials": shadow_trials,
            "run_debug_shadows": run_debug_shadows,
        }

    def fake_write(artifact, *, log_dir, append_logs=True):
        calls.append(
            {
                "artifact": dict(artifact),
                "log_dir": Path(log_dir),
                "append_logs": append_logs,
            }
        )

    monkeypatch.setattr(module, "build_monitor_artifact_from_payload", fake_build)
    monkeypatch.setattr(module, "write_monitor_logs", fake_write)

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=tmp_path / "raw",
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=500,
            roi_trials=250,
            shadow_trials=None,
            full_shadow_trials=20,
            run_debug_shadows=True,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
            fast_n_trials=40,
        ),
        tables=object(),
    )

    monitor.accept_row({"SortID": 1}, schedule_process=True)
    monitor._process_snapshot(force=False)
    monitor._process_snapshot(force=True)

    fast = calls[0]["artifact"]
    full = calls[1]["artifact"]
    assert fast["snapshot_mode"] == "fast"
    assert fast["n_trials"] == 40
    assert fast["roi_trials"] == 0
    assert fast["shadow_trials"] == 20
    assert fast["run_debug_shadows"] is False
    assert fast["raw_capture"] == str(monitor.raw_jsonl_path.resolve())
    assert fast["raw_capture_jsonl"] == str(monitor.raw_jsonl_path.resolve())
    assert calls[0]["append_logs"] is False
    assert full["snapshot_mode"] == "full"
    assert full["n_trials"] == 500
    assert full["roi_trials"] == 250
    assert full["shadow_trials"] == 20
    assert full["inference_profile"]["n_trials"] == 500
    assert full["run_debug_shadows"] is True
    assert full["raw_capture"] == str(monitor.raw_path.resolve())
    assert full["raw_capture_jsonl"] == str(monitor.raw_jsonl_path.resolve())
    assert calls[1]["append_logs"] is True
    assert monitor.status()["last_full_processed_count"] == 1


def test_webhook_monitor_appends_jsonl_on_fast_without_rewriting_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    writes: list[Path] = []

    def fake_atomic(path: Path, value: Any) -> None:
        writes.append(path)

    monkeypatch.setattr(module, "_atomic_write_json", fake_atomic)
    monkeypatch.setattr(
        module,
        "build_monitor_artifact_from_payload",
        lambda *args, **kwargs: {"created_at": 1.0, "file": kwargs["file"]},
    )
    monkeypatch.setattr(
        module,
        "write_monitor_logs",
        lambda *args, **kwargs: None,
    )

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=tmp_path / "raw",
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=500,
            roi_trials=0,
            shadow_trials=None,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
            fast_n_trials=10,
            file_name="windivert_live.json",
        ),
        tables=object(),
    )

    monitor.accept_row({"SortID": 1, "Direct": "REV"}, schedule_process=True)
    monitor._process_snapshot(force=False)

    assert monitor.raw_jsonl_path.exists()
    assert not monitor.raw_path.exists()
    assert writes == []

    monitor.accept_row({"SortID": 2, "Direct": "REV"}, schedule_process=True)
    monitor._process_snapshot(force=True)
    assert writes == [monitor.raw_path]


def test_webhook_monitor_start_clears_stale_working_files(tmp_path: Path) -> None:
    module = _module()
    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=tmp_path / "raw",
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=500,
            roi_trials=0,
            shadow_trials=None,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
        ),
        tables=object(),
    )

    monitor.raw_path.parent.mkdir(parents=True, exist_ok=True)
    monitor.raw_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    monitor.raw_path.write_text("stale", encoding="utf-8")
    monitor.raw_jsonl_path.write_text("stale\n", encoding="utf-8")
    monitor.start()
    monitor.stop()

    assert not monitor.raw_path.exists()
    assert not monitor.raw_jsonl_path.exists()


def test_webhook_monitor_skips_duplicate_fast_inference_for_same_sort(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    build_calls = 0

    def fake_build(*args, **kwargs):
        nonlocal build_calls
        build_calls += 1
        return {"created_at": 1.0, "file": kwargs["file"]}

    monkeypatch.setattr(module, "build_monitor_artifact_from_payload", fake_build)
    monkeypatch.setattr(module, "write_monitor_logs", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "_atomic_write_json", lambda *args, **kwargs: None)

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=tmp_path / "raw",
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=500,
            roi_trials=0,
            shadow_trials=None,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
            fast_n_trials=10,
        ),
        tables=object(),
    )

    monitor.accept_row({"SortID": 5, "Direct": "REV"}, schedule_process=True)
    monitor._process_snapshot(force=False)
    monitor._queue.put_nowait(object())
    monitor._process_if_due()
    assert build_calls == 1


def test_webhook_monitor_skips_fast_write_when_semantics_do_not_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    build_calls = 0
    write_calls = 0

    def fake_build(*args, **kwargs):
        nonlocal build_calls
        build_calls += 1
        return {"created_at": 1.0, "file": kwargs["file"]}

    def fake_write(*args, **kwargs):
        nonlocal write_calls
        write_calls += 1

    monkeypatch.setattr(
        module,
        "_semantic_signature_from_payload",
        lambda _payload: ("same-session", "same-facts"),
    )
    monkeypatch.setattr(module, "build_monitor_artifact_from_payload", fake_build)
    monkeypatch.setattr(module, "write_monitor_logs", fake_write)
    monkeypatch.setattr(module, "_atomic_write_json", lambda *args, **kwargs: None)

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=tmp_path / "raw",
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=500,
            roi_trials=0,
            shadow_trials=None,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
            fast_n_trials=10,
        ),
        tables=object(),
    )

    monitor.accept_row({"SortID": 1, "Direct": "REV"}, schedule_process=True)
    monitor._process_snapshot(force=False)
    monitor.accept_row({"SortID": 2, "Direct": "REV"}, schedule_process=True)
    monitor._process_snapshot(force=False)

    assert build_calls == 1
    assert write_calls == 1
    assert monitor.status()["last_processed_count"] == 2


def test_capture_row_can_wait_for_state_before_scheduling_inference(
    tmp_path: Path,
) -> None:
    module = _module()
    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=tmp_path / "raw",
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=20,
            roi_trials=0,
            shadow_trials=20,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
        ),
        tables=object(),
    )
    calls: list[bool] = []
    monitor._process_snapshot = lambda *, force: calls.append(force)

    monitor.accept_row({"SortID": 1}, schedule_process=False)
    monitor._process_if_due()
    assert calls == []
    assert monitor.status()["last_requested_count"] == 0

    monitor.accept_row({"SortID": 2}, schedule_process=True)
    monitor._process_if_due()
    assert calls == [False]
    assert monitor.status()["last_requested_count"] == 2


def test_should_skip_fast_bootstrap_settled_snapshot() -> None:
    module = _module()
    artifact = {"phase": "settled", "ui_contract": {"context": {"phase": "settled"}}}
    assert module._should_skip_fast_bootstrap_snapshot(
        artifact,
        row_count=1,
        snapshot_mode="fast",
    )
    assert not module._should_skip_fast_bootstrap_snapshot(
        artifact,
        row_count=3,
        snapshot_mode="fast",
    )
    assert not module._should_skip_fast_bootstrap_snapshot(
        artifact,
        row_count=1,
        snapshot_mode="full",
    )


def test_webhook_monitor_skips_fast_bootstrap_settled_write(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        module,
        "build_monitor_artifact_from_payload",
        lambda *args, **kwargs: {
            "created_at": 1000.0,
            "phase": "settled",
            "ui_contract": {"context": {"phase": "settled"}},
        },
    )
    monkeypatch.setattr(
        module,
        "write_monitor_logs",
        lambda artifact, **kwargs: calls.append(dict(artifact)),
    )

    monitor = module.FatbeansWebhookMonitor(
        config=module.WebhookMonitorConfig(
            log_dir=tmp_path / "logs",
            raw_dir=tmp_path / "raw",
            process_name="BidKing.exe",
            server_ports=(10000,),
            n_trials=500,
            roi_trials=0,
            shadow_trials=None,
            full_shadow_trials=20,
            run_debug_shadows=False,
            seed=1,
            debounce_seconds=0.0,
            min_inference_interval_seconds=0.0,
            fast_n_trials=10,
            source_name="windivert",
        ),
        tables=object(),
    )

    monitor.accept_row({"SortID": 1, "Direct": "REV"})
    monitor._process_snapshot(force=False)
    assert calls == []
