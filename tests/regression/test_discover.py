# ABOUTME: Regression tests for application discovery (issue #3).
# ABOUTME: Covers .app scanning, display name extraction, deduplication, sorting, and error handling.

from __future__ import annotations

import logging
import plistlib
from pathlib import Path

from fzflauncher.discover import discover_applications
from fzflauncher.models import TargetType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_app_bundle(
    parent: Path, bundle_stem: str, bundle_name: str | None = None
) -> Path:
    """Create a minimal .app bundle; optionally include CFBundleName in Info.plist."""
    app_path = parent / f"{bundle_stem}.app"
    contents = app_path / "Contents"
    contents.mkdir(parents=True)
    if bundle_name is not None:
        with open(contents / "Info.plist", "wb") as f:
            plistlib.dump({"CFBundleName": bundle_name}, f)
    return app_path


# ---------------------------------------------------------------------------
# AC3.1 — Discovery finds .app bundles in configured paths
# ---------------------------------------------------------------------------


def test_single_dir_apps_found_RT3_1(tmp_path):
    """RT-3.1: Single directory with .app bundles; all found."""
    make_app_bundle(tmp_path, "Alpha", "Alpha")
    make_app_bundle(tmp_path, "Beta", "Beta")
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    names = {t.display_name for t in results}
    assert names == {"Alpha", "Beta"}


def test_two_dirs_apps_found_from_both_RT3_2(tmp_path):
    """RT-3.2: Two directories with .app bundles; all found from both."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    make_app_bundle(dir1, "AppOne", "AppOne")
    make_app_bundle(dir2, "AppTwo", "AppTwo")
    results = discover_applications((str(dir1), str(dir2)), use_bundle_name=True)
    names = {t.display_name for t in results}
    assert names == {"AppOne", "AppTwo"}


def test_non_app_items_excluded_RT3_3(tmp_path):
    """RT-3.3: Directory containing non-.app items; none included."""
    (tmp_path / "README.txt").write_text("hi")
    (tmp_path / "somedir").mkdir()
    make_app_bundle(tmp_path, "Real", "Real")
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert len(results) == 1
    assert results[0].display_name == "Real"


# ---------------------------------------------------------------------------
# AC3.2 — Display name extraction with plist fallback
# ---------------------------------------------------------------------------


def test_display_name_from_plist_RT3_4(tmp_path):
    """RT-3.4: .app with valid Info.plist CFBundleName; display name matches plist value."""
    make_app_bundle(tmp_path, "myapp", "My Fancy App")
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert results[0].display_name == "My Fancy App"


def test_display_name_fallback_no_plist_RT3_5(tmp_path):
    """RT-3.5: .app without Info.plist; display name is dirname minus .app."""
    make_app_bundle(tmp_path, "MyApp")  # no plist
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert results[0].display_name == "MyApp"


def test_display_name_fallback_no_bundle_name_key_RT3_6(tmp_path):
    """RT-3.6: .app with Info.plist but no CFBundleName key; display name is dirname minus .app."""
    app_path = tmp_path / "MyApp.app"
    contents = app_path / "Contents"
    contents.mkdir(parents=True)
    with open(contents / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleVersion": "1.0"}, f)  # no CFBundleName
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert results[0].display_name == "MyApp"


# ---------------------------------------------------------------------------
# AC3.3 — Deduplication by display name
# ---------------------------------------------------------------------------


def test_duplicate_display_name_appears_once_RT3_7(tmp_path):
    """RT-3.7: Same display name from two paths; appears once in result."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    make_app_bundle(dir1, "SameApp", "SameApp")
    make_app_bundle(dir2, "SameApp", "SameApp")
    results = discover_applications((str(dir1), str(dir2)), use_bundle_name=True)
    same = [t for t in results if t.display_name == "SameApp"]
    assert len(same) == 1


def test_first_occurrence_retained_RT3_8(tmp_path):
    """RT-3.8: First occurrence (per config path order) is the one retained."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    path1 = make_app_bundle(dir1, "Dupe", "Dupe")
    make_app_bundle(dir2, "Dupe", "Dupe")
    results = discover_applications((str(dir1), str(dir2)), use_bundle_name=True)
    match = next(t for t in results if t.display_name == "Dupe")
    assert match.path == path1


# ---------------------------------------------------------------------------
# AC3.4 — Alphabetical sort, case-insensitive
# ---------------------------------------------------------------------------


def test_results_sorted_alphabetically_RT3_9(tmp_path):
    """RT-3.9: Unsorted apps; output is alphabetical."""
    for name in ("Zebra", "Alpha", "Mango"):
        make_app_bundle(tmp_path, name, name)
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    names = [t.display_name for t in results]
    assert names == sorted(names)


def test_sort_is_case_insensitive_RT3_10(tmp_path):
    """RT-3.10: Mix of upper/lowercase names; sort is case-insensitive."""
    for name in ("zebra", "Alpha", "mango"):
        make_app_bundle(tmp_path, name, name)
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    names = [t.display_name for t in results]
    assert names == sorted(names, key=str.lower)


# ---------------------------------------------------------------------------
# AC3.5 — Graceful handling of missing/inaccessible paths
# ---------------------------------------------------------------------------


def test_missing_path_logs_warning_RT3_11(tmp_path, caplog):
    """RT-3.11: Configured path does not exist; warning logged, no crash."""
    missing = str(tmp_path / "nonexistent")
    with caplog.at_level(logging.WARNING, logger="fzflauncher.discover"):
        results = discover_applications((missing,), use_bundle_name=True)
    assert results == []
    assert any("nonexistent" in r.message for r in caplog.records)


def test_missing_path_does_not_block_other_paths_RT3_12(tmp_path, caplog):
    """RT-3.12: One path missing; apps from other valid paths still discovered."""
    missing = str(tmp_path / "nonexistent")
    make_app_bundle(tmp_path, "GoodApp", "GoodApp")
    with caplog.at_level(logging.WARNING, logger="fzflauncher.discover"):
        results = discover_applications((missing, str(tmp_path)), use_bundle_name=True)
    assert any(t.display_name == "GoodApp" for t in results)


# ---------------------------------------------------------------------------
# AC3.6 — Empty list is not an error
# ---------------------------------------------------------------------------


def test_no_paths_returns_empty_list_RT3_13():
    """RT-3.13: No paths configured; empty list returned."""
    results = discover_applications((), use_bundle_name=True)
    assert results == []


def test_paths_with_no_apps_returns_empty_list_RT3_14(tmp_path):
    """RT-3.14: Paths exist but contain no .app bundles; empty list returned."""
    (tmp_path / "README.txt").write_text("nothing here")
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert results == []


# ---------------------------------------------------------------------------
# AC3.7 — Configurable display name source
# ---------------------------------------------------------------------------


def test_use_bundle_name_true_uses_plist_RT3_15(tmp_path):
    """RT-3.15: use_bundle_name=True with CFBundleName present; plist value used."""
    make_app_bundle(tmp_path, "dirname", "Plist Name")
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert results[0].display_name == "Plist Name"


def test_use_bundle_name_false_uses_dirname_RT3_16(tmp_path):
    """RT-3.16: use_bundle_name=False; directory name used instead of CFBundleName."""
    make_app_bundle(tmp_path, "dirname", "Plist Name")
    results = discover_applications((str(tmp_path),), use_bundle_name=False)
    assert results[0].display_name == "dirname"


# ---------------------------------------------------------------------------
# Target dataclass integrity
# ---------------------------------------------------------------------------


def test_discovered_targets_have_correct_type(tmp_path):
    """Discovered targets carry TargetType.APPLICATION."""
    make_app_bundle(tmp_path, "MyApp", "MyApp")
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert all(t.type == TargetType.APPLICATION for t in results)


def test_discovered_targets_carry_absolute_path(tmp_path):
    """Discovered target paths are absolute Path objects pointing to the .app bundle."""
    make_app_bundle(tmp_path, "MyApp", "MyApp")
    results = discover_applications((str(tmp_path),), use_bundle_name=True)
    assert results[0].path.is_absolute()
    assert results[0].path.name == "MyApp.app"
