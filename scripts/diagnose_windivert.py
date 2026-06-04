"""Quick WinDivert / admin diagnostics for live capture setup."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO / "data" / "logs" / "live" / "monitor.lock"

MONITOR_MARKERS = (
    "run_windivert_live_monitor.py",
    "run_fatbeans_webhook_monitor.py",
    "run_fatbeans_live_monitor.py",
)

PORT_FILTER = (
    "tcp and tcp.PayloadLength > 0 and (tcp.DstPort == 10000 or tcp.SrcPort == 10000)"
)
# pydivert bundles WinDivert 2.2; this hash is on Microsoft's vulnerable driver blocklist.
WINDIVERT22_BLOCKED_SHA256 = "8da085332782708d8767bcace5327a6ec7283c17cfb85e40b03cd2323a90ddc2"
BLOCKLIST_REG = (
    r"HKLM\SYSTEM\CurrentControlSet\Control\CI\Config",
    "VulnerableDriverBlocklistEnable",
)


def _query_windivert_service() -> dict[str, str | int] | None:
    import re
    import subprocess

    try:
        proc = subprocess.run(
            ["sc.exe", "query", "WinDivert"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:  # noqa: BLE001
        return None
    if proc.returncode != 0:
        return {"registered": 0}
    text = proc.stdout or ""
    state_match = re.search(r"STATE\s+:\s+\d+\s+(\w+)", text)
    exit_match = re.search(r"WIN32_EXIT_CODE\s+:\s+(\d+)", text)
    return {
        "registered": 1,
        "state": state_match.group(1) if state_match else "unknown",
        "win32_exit_code": int(exit_match.group(1)) if exit_match else -1,
    }


def _vulnerable_driver_blocklist_enabled() -> bool | None:
    import subprocess

    key, value = BLOCKLIST_REG
    try:
        proc = subprocess.run(
            ["reg.exe", "query", key, "/v", value],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:  # noqa: BLE001
        return None
    if proc.returncode != 0:
        return None
    for line in (proc.stdout or "").splitlines():
        if value.lower() in line.lower() and "0x1" in line.replace(" ", ""):
            return True
        if value.lower() in line.lower() and "0x0" in line.replace(" ", ""):
            return False
        parts = line.split()
        if len(parts) >= 3 and parts[0].endswith(value):
            return parts[-1] in {"0x1", "1"}
    return None


def _bundled_windivert_sha256() -> str | None:
    try:
        import pydivert
    except ImportError:
        return None
    sys_path = Path(pydivert.__file__).resolve().parent / "windivert_dll" / "WinDivert64.sys"
    if not sys_path.is_file():
        return None
    import hashlib

    digest = hashlib.sha256(sys_path.read_bytes()).hexdigest()
    return digest.lower()


def _print_blocklist_guidance(*, blocklist: bool | None, service: dict[str, str | int] | None) -> None:
    driver_hash = _bundled_windivert_sha256()
    if driver_hash:
        print(f"windivert_driver_sha256={driver_hash}")
        if driver_hash == WINDIVERT22_BLOCKED_SHA256:
            print("windivert_driver=WinDivert_2.2_blocklisted_by_microsoft")

    if blocklist is not None:
        print(f"vulnerable_driver_blocklist={'on' if blocklist else 'off'}")
    if service is not None:
        if service.get("registered") == 0:
            print("windivert_service=not_registered")
        else:
            print(
                "windivert_service="
                f"state={service.get('state')} "
                f"win32_exit_code={service.get('win32_exit_code')}"
            )

    blocked = blocklist is True and driver_hash == WINDIVERT22_BLOCKED_SHA256
    stale_service = (
        service is not None
        and service.get("registered") == 1
        and service.get("win32_exit_code") == 5
    )
    if blocked or stale_service:
        print("root_cause=microsoft_vulnerable_driver_blocklist_blocks_windivert_2.2")
        print(
            "fix=Windows Security -> Device security -> Core isolation details -> "
            "turn OFF 'Microsoft vulnerable driver blocklist' -> reboot"
        )
        print(
            "fix_registry_admin=reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\CI\\Config "
            "/v VulnerableDriverBlocklistEnable /t REG_DWORD /d 0 /f  (then reboot)"
        )
        print("alt_capture=.\\scripts\\start_live_webhook_overlay.ps1  (Fatbeans WebHook, no WinDivert)")
    print(
        "huorong_trust=add windivert_driver_path to 火绒 trust list "
        "(bidking-lab uses Python313, not Anaconda, when started via project scripts)"
    )


def _process_is_elevated() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _find_live_monitors() -> list[tuple[int, str]]:
    try:
        import psutil
    except ImportError:
        return []

    hits: list[tuple[int, str]] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if not name.startswith("python"):
                continue
            cmdline = proc.info.get("cmdline") or []
            cmd = " ".join(str(part) for part in cmdline)
            if any(marker in cmd for marker in MONITOR_MARKERS):
                hits.append((int(proc.info["pid"]), cmd[:160]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return hits


def _read_lock_pid() -> int | None:
    if not LOCK_PATH.is_file():
        return None
    try:
        import json

        payload = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        pid = payload.get("pid")
        return int(pid) if pid else None
    except Exception:  # noqa: BLE001
        return None


def _try_open(label: str, filter_text: str, flags: int) -> bool:
    import pydivert

    try:
        with pydivert.WinDivert(filter_text, flags=flags):
            print(f"{label}=ok")
            return True
    except PermissionError as exc:
        winerror = getattr(exc, "winerror", None)
        print(f"{label}=permission_denied winerror={winerror}")
        return False
    except OSError as exc:
        winerror = getattr(exc, "winerror", None)
        print(f"{label}=os_error winerror={winerror} msg={exc}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"{label}=failed:{type(exc).__name__}:{exc}")
        return False


def main() -> int:
    print(f"python={sys.executable}")
    elevated = _process_is_elevated()
    print(f"process_elevated={elevated}")

    monitors = _find_live_monitors()
    if monitors:
        print(f"live_monitor_processes={len(monitors)}")
        for pid, cmd in monitors:
            print(f"  pid={pid} cmd={cmd}")
        print("hint=stop monitors first: .\\scripts\\stop_live_monitor.ps1")
    else:
        print("live_monitor_processes=0")

    lock_pid = _read_lock_pid()
    if lock_pid:
        print(f"monitor_lock_pid={lock_pid}")

    try:
        import pydivert
    except ImportError:
        print("pydivert=missing")
        print(f"install_for_this_python: {sys.executable} -m pip install pydivert psutil")
        print('or_from_repo: python -m pip install -e ".[packet]"')
        print(
            "note=use the same interpreter as start_live_windivert_overlay.ps1 "
            "(default C:\\Python313\\python.exe)"
        )
        return 2

    print(f"pydivert={getattr(pydivert, '__version__', 'unknown')}")
    driver_path = Path(pydivert.__file__).resolve().parent / "windivert_dll" / "WinDivert64.sys"
    print(f"windivert_driver_path={driver_path}")
    if "anaconda3" in str(driver_path).lower():
        print("hint=driver from Anaconda; use C:\\Python313\\python.exe for bidking-lab live")
    sniff_flag = getattr(getattr(pydivert, "Flag", object), "SNIFF", None)
    if sniff_flag is None:
        print("pydivert_flag_sniff=missing")
        return 2

    if monitors:
        print("windivert_open=skipped_live_monitor_running")
        print("result=STOP_MONITORS_THEN_RETRY")
        return 2

    service = _query_windivert_service()
    blocklist = _vulnerable_driver_blocklist_enabled()

    ok_port = _try_open("windivert_port_filter", PORT_FILTER, sniff_flag)
    if ok_port:
        print("result=OK")
        return 0

    ok_true = _try_open("windivert_true_filter", "true", sniff_flag)
    if ok_true:
        print("hint=minimal filter works but port filter denied; check filter syntax/driver")
        print("result=PARTIAL")
        return 2

    _print_blocklist_guidance(blocklist=blocklist, service=service)
    if not elevated:
        print("hint=run this script from Administrator PowerShell")
    print("result=FAIL")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
