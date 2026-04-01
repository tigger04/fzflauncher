# ABOUTME: Application discovery — scans configured directories for .app bundles.
# ABOUTME: Extracts display names from Info.plist, deduplicates, and returns sorted Targets.

from __future__ import annotations

import logging
import plistlib
from pathlib import Path

from fzflauncher.models import Target, TargetType

logger = logging.getLogger(__name__)


def _get_display_name(app_path: Path, use_bundle_name: bool) -> str:
    """Return the display name for a .app bundle.

    If use_bundle_name is True, reads CFBundleName from Contents/Info.plist.
    Falls back to the bundle directory stem (name without .app) if the plist
    is absent or the key is missing.
    """
    stem = app_path.stem

    if not use_bundle_name:
        return stem

    plist_path = app_path / "Contents" / "Info.plist"
    if not plist_path.exists():
        return stem

    try:
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)
        return plist.get("CFBundleName", stem)
    except Exception:
        logger.warning("Could not read %s; falling back to directory name", plist_path)
        return stem


def discover_applications(
    paths: tuple[str, ...], use_bundle_name: bool
) -> list[Target]:
    """Scan configured paths for .app bundles and return a sorted Target list.

    Args:
        paths: Absolute paths to search (already tilde-expanded).
        use_bundle_name: If True, prefer CFBundleName from Info.plist over dirname.

    Returns:
        Alphabetically sorted (case-insensitive) list of Target instances.
        Duplicates (same display name) are removed, first occurrence per path order kept.
        Returns an empty list when no applications are found — not an error.
    """
    seen: set[str] = set()
    results: list[Target] = []

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            logger.warning("Application path does not exist: %s", path)
            continue

        try:
            entries = list(path.iterdir())
        except PermissionError:
            logger.warning("Cannot access application path: %s", path)
            continue

        for entry in sorted(entries):
            if not entry.name.endswith(".app") or not entry.is_dir():
                continue

            display_name = _get_display_name(entry, use_bundle_name)

            if display_name in seen:
                continue
            seen.add(display_name)

            results.append(
                Target(
                    type=TargetType.APPLICATION,
                    display_name=display_name,
                    path=entry,
                    metadata={},
                )
            )

    return sorted(results, key=lambda t: t.display_name.lower())
