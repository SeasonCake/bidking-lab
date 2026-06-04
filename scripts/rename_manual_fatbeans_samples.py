"""Rename manually exported Fatbeans samples with parsed metadata.

Default mode is dry-run. The script only renames files directly under the input
directory, not nested files, and it never overwrites an existing destination.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.live.fatbeans import (  # noqa: E402
    FatbeansCaptureEvents,
    live_batches_from_fatbeans_events,
    parse_fatbeans_capture,
)
from bidking_lab.live.state import (  # noqa: E402
    LiveSessionState,
    apply_observation_batch,
    live_state_to_session_obs,
)

DEFAULT_INBOX = ROOT / "data" / "samples" / "fatbeans_manual_inbox"


@dataclass(frozen=True)
class RenamePlan:
    source: Path
    destination: Path | None
    status: str
    reason: str
    index: int | None = None
    hero: str | None = None
    map_id: int | None = None
    rounds: int | None = None
    session_token: str | None = None


def _safe_token(value: Any, *, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return "".join(ch if ch.isalnum() else "_" for ch in text.lower()).strip("_") or fallback


def _hero_from_events(events: FatbeansCaptureEvents) -> str | None:
    state = LiveSessionState()
    for batch in live_batches_from_fatbeans_events(events):
        state = apply_observation_batch(state, batch)
    session = live_state_to_session_obs(state)
    return session.hero if session is not None else None


def _latest_map_id(events: FatbeansCaptureEvents) -> int | None:
    for state in reversed(events.states):
        if state.map_id is not None:
            return int(state.map_id)
    for send in reversed(events.sends):
        if send.session_id:
            prefix = str(send.session_id).split(":", 1)[0]
            try:
                return int(prefix)
            except ValueError:
                return None
    return None


def _session_token(events: FatbeansCaptureEvents) -> str | None:
    for send in reversed(events.sends):
        if send.session_id:
            return _safe_token(send.session_id)
    for state in reversed(events.states):
        if state.session_id:
            return _safe_token(state.session_id)
    for status in reversed(events.statuses):
        if status.session_id:
            return _safe_token(status.session_id)
    return None


def _rounds(events: FatbeansCaptureEvents) -> int:
    bid_windows = sum(1 for send in events.sends if getattr(send, "kind", "") == "bid")
    observed_rounds = [
        int(state.round_index)
        for state in events.states
        if state.round_index is not None
    ]
    return max([bid_windows, *observed_rounds], default=0)


def _looks_manually_renamed(path: Path, *, prefix: str) -> bool:
    return path.stem.startswith(prefix) and "rounds" in path.stem


def _next_available_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        candidate = directory / f"{stem}_dup{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def build_rename_plan(
    directory: Path,
    *,
    prefix: str = "manual_2026-06-04",
    start_index: int = 1,
    force_existing_named: bool = False,
) -> list[RenamePlan]:
    files = sorted(
        (path for path in directory.glob("*.json") if path.is_file()),
        key=lambda path: (path.stat().st_mtime, path.name.lower()),
    )
    plans: list[RenamePlan] = []
    next_index = int(start_index)
    for path in files:
        if _looks_manually_renamed(path, prefix=prefix) and not force_existing_named:
            plans.append(
                RenamePlan(
                    source=path,
                    destination=None,
                    status="skip",
                    reason="already_named",
                )
            )
            continue
        try:
            events = parse_fatbeans_capture(path)
        except Exception as exc:  # noqa: BLE001 - operational CLI reports bad exports
            plans.append(
                RenamePlan(
                    source=path,
                    destination=None,
                    status="error",
                    reason=type(exc).__name__,
                )
            )
            continue

        hero = _hero_from_events(events)
        map_id = _latest_map_id(events)
        rounds = _rounds(events)
        session_token = _session_token(events)
        parts = [
            prefix,
            f"{next_index:03d}",
            _safe_token(hero),
            _safe_token(map_id),
            f"{rounds or 0}rounds",
        ]
        if session_token:
            parts.append(session_token)
        destination = _next_available_path(path.parent, "_".join(parts), path.suffix.lower())
        plans.append(
            RenamePlan(
                source=path,
                destination=destination,
                status="rename",
                reason="ok",
                index=next_index,
                hero=hero,
                map_id=map_id,
                rounds=rounds,
                session_token=session_token,
            )
        )
        next_index += 1
    return plans


def _print_plan(plans: list[RenamePlan], *, dry_run: bool) -> None:
    renamed = sum(1 for plan in plans if plan.status == "rename")
    skipped = sum(1 for plan in plans if plan.status == "skip")
    errors = sum(1 for plan in plans if plan.status == "error")
    mode = "dry_run" if dry_run else "apply"
    print(f"rename_manual_fatbeans_samples: mode={mode} rename={renamed} skip={skipped} error={errors}")
    for plan in plans:
        if plan.status == "rename" and plan.destination is not None:
            arrow = "->" if dry_run else "renamed ->"
            print(f"{plan.source.name} {arrow} {plan.destination.name}")
        elif plan.status == "skip":
            print(f"{plan.source.name} skipped reason={plan.reason}")
        else:
            print(f"{plan.source.name} error={plan.reason}")


def apply_plan(plans: list[RenamePlan]) -> None:
    for plan in plans:
        if plan.status != "rename" or plan.destination is None:
            continue
        if plan.destination.exists():
            raise FileExistsError(plan.destination)
        plan.source.rename(plan.destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=DEFAULT_INBOX,
        help="Directory containing manually exported Fatbeans JSON files.",
    )
    parser.add_argument("--prefix", default="manual_2026-06-04")
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument(
        "--force-existing-named",
        action="store_true",
        help="Also rename files that already look like manual_YYYY_MM_DD_* samples.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rename files. Without this flag, only prints a dry-run plan.",
    )
    args = parser.parse_args(argv)

    directory = args.directory.resolve()
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
    plans = build_rename_plan(
        directory,
        prefix=args.prefix,
        start_index=max(1, int(args.start_index)),
        force_existing_named=bool(args.force_existing_named),
    )
    _print_plan(plans, dry_run=not args.apply)
    if args.apply:
        apply_plan(plans)
    return 1 if any(plan.status == "error" for plan in plans) else 0


if __name__ == "__main__":
    raise SystemExit(main())
