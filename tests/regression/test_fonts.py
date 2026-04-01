# ABOUTME: Regression tests for Fzfira Code font loading (issue #8).
# ABOUTME: Covers successful load from resources/fonts/, and system font fallback.

from __future__ import annotations

import os
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from fzflauncher.fonts import load_bundled_font

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def fonts_dir_with_ttf(tmp_path, qt_app):
    """A temp directory containing a real TTF file (borrowed from system fonts)."""
    # Use any system TTF to stand in for the Fzfira Code TTF.
    # We just need QFontDatabase.addApplicationFont to return a valid id.
    system_ttf = _find_any_system_ttf()
    if system_ttf is None:
        pytest.skip("No system TTF found for font load test")
    dest = tmp_path / "FzfiraCode-Regular.ttf"
    shutil.copy(system_ttf, dest)
    return tmp_path


@pytest.fixture
def empty_fonts_dir(tmp_path):
    """A temp directory with no TTF files."""
    return tmp_path


def _find_any_system_ttf() -> str | None:
    """Return the path of any .ttf in ~/Library/Fonts or /Library/Fonts."""
    for base in ("~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts"):
        base = os.path.expanduser(base)
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            if name.lower().endswith(".ttf"):
                return os.path.join(base, name)
    return None


# ---------------------------------------------------------------------------
# AC8.1 — Font loads when TTF present
# ---------------------------------------------------------------------------


def test_load_bundled_font_returns_fzfira_code_when_ttf_present_RT8_1(
    qt_app, fonts_dir_with_ttf
):
    """RT-8.1: load_bundled_font returns "Fzfira Code" when TTF is present in font_dir."""
    family = load_bundled_font(fonts_dir_with_ttf)
    assert family == "Fzfira Code"


# ---------------------------------------------------------------------------
# AC8.2 — Fallback when TTF absent
# ---------------------------------------------------------------------------


def test_load_bundled_font_returns_system_font_when_ttf_absent_RT8_2(
    qt_app, empty_fonts_dir
):
    """RT-8.2: load_bundled_font returns the system fixed font family when no TTF present."""
    fallback = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
    family = load_bundled_font(empty_fonts_dir)
    assert family == fallback
