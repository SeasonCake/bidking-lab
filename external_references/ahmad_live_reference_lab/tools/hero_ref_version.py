"""Display/build version for Hero Ref UI. Bump when cutting a release package."""

from __future__ import annotations

import re
from pathlib import Path

# Source of truth for dev/engineering runs; build_hero_ref_portable.ps1 -Version should match.
HERO_REF_VERSION = "0.1.9"

_MANIFEST_PATTERN = re.compile(r"^PackageVersion:\s*v?(.+)\s*$", re.MULTILINE)


def resolve_hero_ref_version() -> str:
    """Prefer packaged BUILD_MANIFEST when present; else module constant."""
    here = Path(__file__).resolve()
    for parent in here.parents[:6]:
        manifest = parent / "BUILD_MANIFEST.txt"
        if not manifest.is_file():
            continue
        try:
            text = manifest.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = _MANIFEST_PATTERN.search(text)
        if match:
            return match.group(1).strip()
    return HERO_REF_VERSION
