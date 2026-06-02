"""Receive Fatbeans WebHook packets and feed the live monitor.

Fatbeans sends one captured packet per HTTP POST. This receiver keeps the
request path read-only and returns "allow" immediately, then debounces the
accumulated TCP stream in a background worker and reuses the existing Fatbeans
JSON parser / live monitor artifact builder.
"""

from __future__ import annotations

import argparse
import atexit
import base64
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import traceback
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.live.monitor import (  # noqa: E402
    build_monitor_artifact_from_payload,
    load_monitor_tables,
    write_monitor_logs,
)


ALLOW_RESPONSE = {
    "ErrorCode": 0,
    "ErrorMsg": "ok",
    "OpCode": 0,
    "NewData": "",
    "Request": None,
    "Response": None,
}


def _allow_response() -> dict[str, Any]:
    return dict(ALLOW_RESPONSE)


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_local_ip(value: Any) -> bool:
    if value in (None, ""):
        return False
    try:
        ip = ipaddress.ip_address(str(value))
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local


def _infer_direction(
    *,
    src_ip: Any,
    src_port: Any,
    dst_ip: Any,
    dst_port: Any,
    server_ports: Sequence[int],
) -> str | None:
    src_port_int = _safe_int(src_port)
    dst_port_int = _safe_int(dst_port)
    server_port_set = {int(port) for port in server_ports}
    if dst_port_int in server_port_set:
        return "SEND"
    if src_port_int in server_port_set:
        return "REV"

    src_local = _is_local_ip(src_ip)
    dst_local = _is_local_ip(dst_ip)
    if src_local and not dst_local:
        return "SEND"
    if dst_local and not src_local:
        return "REV"
    return None


def _capture_time() -> str:
    now = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)) + (
        f".{int((now % 1) * 1000):03d}"
    )


def _process_name_matches(actual: Any, expected: str | None) -> bool:
    if expected in (None, "", "*"):
        return True
    return str(actual or "").casefold() == str(expected).casefold()


def _webhook_payload_to_row(
    payload: Mapping[str, Any],
    *,
    sort_id: int,
    process_name: str | None = "BidKing.exe",
    server_ports: Sequence[int] = (10000,),
) -> dict[str, Any] | None:
    """Convert one Fatbeans WebHook payload to a Fatbeans export row.

    Non-target processes, non-TCP packets, missing data, and ambiguous
    directions are filtered out. Invalid base64 is treated as malformed input.
    """
    if not isinstance(payload, Mapping):
        return None
    protocol = str(payload.get("Protocol") or "").lower()
    if protocol and protocol != "tcp":
        return None
    if not _process_name_matches(payload.get("ProcessName"), process_name):
        return None
    data = payload.get("Data") or ""
    if not isinstance(data, str) or not data:
        return None
    decoded = base64.b64decode(data, validate=True)
    direction = _infer_direction(
        src_ip=payload.get("SrcIP"),
        src_port=payload.get("SrcPort"),
        dst_ip=payload.get("DstIP"),
        dst_port=payload.get("DstPort"),
        server_ports=server_ports,
    )
    if direction is None:
        return None

    return {
        "SortID": int(sort_id),
        "Direct": direction,
        "Protocol": "Tcp",
        "SrcIP": payload.get("SrcIP"),
        "SrcPort": _safe_int(payload.get("SrcPort")) or 0,
        "DstIP": payload.get("DstIP"),
        "DstPort": _safe_int(payload.get("DstPort")) or 0,
        "CaptureTime": str(payload.get("CaptureTime") or _capture_time()),
        "Data": data,
        "DataLength": len(decoded),
        "PID": payload.get("PID"),
        "ProcessName": payload.get("ProcessName"),
        "Url": payload.get("Url"),
    }


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        tmp = Path(fh.name)
    try:
        for attempt in range(5):
            try:
                tmp.replace(path)
                return
            except PermissionError:
                if attempt >= 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if tmp.exists():
            tmp.unlink()


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
        fh.write("\n")


def _append_webhook_error_log(
    log_dir: Path,
    *,
    raw_path: Path,
    packet_count: int,
    exc: Exception,
) -> None:
    _append_jsonl(
        log_dir / "monitor_errors.jsonl",
        {
            "ts": time.time(),
            "path": str(raw_path.resolve()),
            "name": raw_path.name,
            "packet_count": packet_count,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": "".join(
                traceback.format_exception(
                    type(exc),
                    exc,
                    exc.__traceback__,
                    limit=6,
                )
            ),
        },
    )


def _looks_like_partial_stream_error(exc: Exception) -> bool:
    text = str(exc)
    return "invalid frame length" in text or "incomplete length" in text


def _acquire_lock(log_dir: Path) -> Path:
    lock_path = log_dir / "monitor.lock"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(
            f"monitor already appears to be running; remove {lock_path} if stale"
        ) from exc
    payload = json.dumps(
        {
            "pid": os.getpid(),
            "started_at": time.time(),
            "kind": "fatbeans_webhook",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    with os.fdopen(fd, "wb") as fh:
        fh.write(payload)
        fh.write(b"\n")

    def _cleanup() -> None:
        try:
            lock_path.unlink()
        except OSError:
            pass

    atexit.register(_cleanup)
    return lock_path


@dataclass(frozen=True)
class WebhookMonitorConfig:
    log_dir: Path
    raw_dir: Path
    process_name: str | None
    server_ports: tuple[int, ...]
    n_trials: int
    roi_trials: int
    shadow_trials: int | None
    run_debug_shadows: bool
    seed: int
    debounce_seconds: float
    min_inference_interval_seconds: float
    file_name: str = "fatbeans_webhook_live.json"
    source_name: str = "fatbeans_webhook"
    packet_count_key: str = "webhook_packets"


class FatbeansWebhookMonitor:
    def __init__(self, *, config: WebhookMonitorConfig, tables: Any) -> None:
        self.config = config
        self.tables = tables
        self._rows: list[dict[str, Any]] = []
        self._next_sort_id = 1
        self._last_packet_at = 0.0
        self._last_inference_at = 0.0
        self._last_processed_count = 0
        self._last_partial_error = ""
        self._received = 0
        self._accepted = 0
        self._filtered = 0
        self._lock = threading.Lock()
        self._queue: queue.Queue[object] = queue.Queue()
        self._stop = threading.Event()
        self._worker = threading.Thread(
            target=self._run_worker,
            name="fatbeans-webhook-monitor",
            daemon=True,
        )

    @property
    def raw_path(self) -> Path:
        return self.config.raw_dir / self.config.file_name

    def start(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        self._queue.put_nowait(object())
        self._worker.join(timeout=5.0)

    def accept_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._received += 1
            try:
                row = _webhook_payload_to_row(
                    payload,
                    sort_id=self._next_sort_id,
                    process_name=self.config.process_name,
                    server_ports=self.config.server_ports,
                )
            except Exception as exc:  # noqa: BLE001 - external webhook boundary
                self._filtered += 1
                return {
                    "accepted": False,
                    "reason": f"malformed:{type(exc).__name__}:{exc}",
                    "received": self._received,
                    "accepted_count": self._accepted,
                    "filtered_count": self._filtered,
                }
            if row is None:
                self._filtered += 1
                return {
                    "accepted": False,
                    "reason": "filtered",
                    "received": self._received,
                    "accepted_count": self._accepted,
                    "filtered_count": self._filtered,
                }
            self._rows.append(row)
            self._next_sort_id += 1
            self._accepted += 1
            self._last_packet_at = time.monotonic()
            accepted_count = self._accepted
            received = self._received
            filtered = self._filtered
        self._queue.put_nowait(object())
        return {
            "accepted": True,
            "reason": "accepted",
            "received": received,
            "accepted_count": accepted_count,
            "filtered_count": filtered,
        }

    def accept_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Accept an already-normalized Fatbeans export row.

        This is used by source adapters that do their own packet capture but
        still want to reuse the same debounce, artifact, and log writer path.
        """
        with self._lock:
            self._received += 1
            normalized = dict(row)
            normalized["SortID"] = int(normalized.get("SortID") or self._next_sort_id)
            self._rows.append(normalized)
            self._next_sort_id = max(self._next_sort_id, normalized["SortID"] + 1)
            self._accepted += 1
            self._last_packet_at = time.monotonic()
            accepted_count = self._accepted
            received = self._received
            filtered = self._filtered
        self._queue.put_nowait(object())
        return {
            "accepted": True,
            "reason": "accepted",
            "received": received,
            "accepted_count": accepted_count,
            "filtered_count": filtered,
        }

    def reset_rows(self) -> None:
        """Clear accumulated raw rows before a new live session starts."""
        with self._lock:
            self._rows = []
            self._next_sort_id = 1
            self._last_packet_at = 0.0
            self._last_processed_count = 0
            self._last_partial_error = ""

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "received": self._received,
                "accepted": self._accepted,
                "filtered": self._filtered,
                "rows": len(self._rows),
                "last_processed_count": self._last_processed_count,
                "raw_path": str(self.raw_path.resolve()),
            }

    def _run_worker(self) -> None:
        while not self._stop.is_set():
            try:
                self._queue.get(timeout=0.2)
            except queue.Empty:
                pass
            if self._stop.is_set():
                break
            self._process_if_due()
        self._process_snapshot(force=True)

    def _process_if_due(self) -> None:
        with self._lock:
            row_count = len(self._rows)
            last_packet_at = self._last_packet_at
            last_inference_at = self._last_inference_at
        if row_count <= self._last_processed_count:
            return
        now = time.monotonic()
        if now - last_packet_at < self.config.debounce_seconds:
            return
        if now - last_inference_at < self.config.min_inference_interval_seconds:
            return
        self._process_snapshot(force=False)

    def _process_snapshot(self, *, force: bool) -> None:
        with self._lock:
            rows = list(self._rows)
        if not rows:
            return
        if not force and len(rows) <= self._last_processed_count:
            return

        raw_path = self.raw_path
        _atomic_write_json(raw_path, rows)
        try:
            artifact = build_monitor_artifact_from_payload(
                json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
                file=raw_path.name,
                tables=self.tables,
                n_trials=self.config.n_trials,
                roi_trials=self.config.roi_trials,
                shadow_trials=self.config.shadow_trials,
                run_debug_shadows=self.config.run_debug_shadows,
                seed=self.config.seed,
            )
            artifact["source"] = self.config.source_name
            artifact["raw_capture"] = str(raw_path.resolve())
            artifact["capture_rows"] = len(rows)
            artifact[self.config.packet_count_key] = len(rows)
            write_monitor_logs(artifact, log_dir=self.config.log_dir)
        except Exception as exc:  # noqa: BLE001 - long-running monitor boundary
            if _looks_like_partial_stream_error(exc):
                message = str(exc)
                if message != self._last_partial_error:
                    print(
                        f"[wait] partial Fatbeans stream: {message}",
                        file=sys.stderr,
                        flush=True,
                    )
                    self._last_partial_error = message
                return
            _append_webhook_error_log(
                self.config.log_dir,
                raw_path=raw_path,
                packet_count=len(rows),
                exc=exc,
            )
            print(
                f"[error] webhook inference failed: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return

        with self._lock:
            self._last_processed_count = len(rows)
            self._last_inference_at = time.monotonic()
            self._last_partial_error = ""
        count_label = self.config.packet_count_key.replace("_", " ")
        print(
            f"[ok] {self.config.source_name} {count_label}={len(rows)} -> "
            f"{self.config.log_dir / 'latest_snapshot.json'}",
            flush=True,
        )


def _write_json_response(
    handler: BaseHTTPRequestHandler,
    status_code: int,
    payload: Mapping[str, Any],
) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _make_handler(
    monitor: FatbeansWebhookMonitor,
    *,
    webhook_path: str,
    verbose: bool,
) -> type[BaseHTTPRequestHandler]:
    class FatbeansWebhookHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path.rstrip("/") == "/health":
                _write_json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        **monitor.status(),
                    },
                )
                return
            _write_json_response(self, 404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path.split("?", 1)[0] != webhook_path:
                _write_json_response(self, 404, _allow_response())
                return
            try:
                content_length = int(self.headers.get("Content-Length") or "0")
                raw = self.rfile.read(content_length)
                payload = json.loads(raw.decode("utf-8-sig") or "{}")
                if not isinstance(payload, Mapping):
                    raise ValueError("webhook payload must be a JSON object")
                result = monitor.accept_payload(payload)
                if verbose:
                    print(f"[webhook] {result}", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep packet path non-blocking
                if verbose:
                    print(f"[webhook-error] {exc}", file=sys.stderr, flush=True)
            _write_json_response(self, 200, _allow_response())

        def log_message(self, fmt: str, *args: Any) -> None:
            if verbose:
                super().log_message(fmt, *args)

    return FatbeansWebhookHandler


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Receive Fatbeans WebHook packet callbacks for live monitor.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", default="/fatbeans")
    parser.add_argument(
        "--log-dir",
        default=str(ROOT / "data" / "logs" / "live"),
        help="Directory for latest_snapshot.json and JSONL logs.",
    )
    parser.add_argument(
        "--raw-dir",
        default=None,
        help="Directory for rolling raw webhook capture JSON.",
    )
    parser.add_argument(
        "--tables-dir",
        default=None,
        help="Override raw game table directory; defaults to data/raw/tables.",
    )
    parser.add_argument(
        "--process-name",
        default="BidKing.exe",
        help="Only accept this process name; use '*' to disable process filtering.",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        action="append",
        default=None,
        help="BidKing server port used to infer SEND/REV. May be repeated.",
    )
    parser.add_argument("--debounce-seconds", type=float, default=0.7)
    parser.add_argument("--min-inference-interval-seconds", type=float, default=1.0)
    parser.add_argument("--n-trials", type=int, default=500)
    parser.add_argument("--roi-trials", type=int, default=250)
    parser.add_argument("--shadow-trials", type=int, default=None)
    parser.add_argument("--skip-debug-shadows", action="store_true")
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--no-lock", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    raw_dir = Path(args.raw_dir) if args.raw_dir else log_dir / "raw"
    if not args.no_lock:
        try:
            _acquire_lock(log_dir)
        except RuntimeError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 2
    tables = load_monitor_tables(tables_dir=args.tables_dir)
    server_ports = tuple(args.server_port or [10000])
    webhook_path = args.path if args.path.startswith("/") else f"/{args.path}"

    monitor = FatbeansWebhookMonitor(
        config=WebhookMonitorConfig(
            log_dir=log_dir,
            raw_dir=raw_dir,
            process_name=None if args.process_name == "*" else args.process_name,
            server_ports=server_ports,
            n_trials=args.n_trials,
            roi_trials=args.roi_trials,
            shadow_trials=args.shadow_trials,
            run_debug_shadows=not args.skip_debug_shadows,
            seed=args.seed,
            debounce_seconds=args.debounce_seconds,
            min_inference_interval_seconds=args.min_inference_interval_seconds,
        ),
        tables=tables,
    )
    monitor.start()

    server = ThreadingHTTPServer(
        (args.host, args.port),
        _make_handler(monitor, webhook_path=webhook_path, verbose=args.verbose),
    )
    print(
        f"[listen] Fatbeans WebHook URL: "
        f"http://{args.host}:{args.port}{webhook_path}",
        flush=True,
    )
    print(
        f"[listen] process={args.process_name} server_ports={list(server_ports)} "
        f"log_dir={log_dir}",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("[stop] interrupted", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        monitor.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
