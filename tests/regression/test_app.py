# ABOUTME: Regression tests for PySide6 window and lifecycle (issue #4).
# ABOUTME: Uses QT_QPA_PLATFORM=offscreen for headless execution.

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from fzflauncher.app import LauncherWindow
from fzflauncher.config import (
    Config,
    DisplayConfig,
    FzfConfig,
    HotkeyConfig,
    PathsConfig,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qt_app():
    """Session-scoped QApplication for offscreen Qt tests."""
    app = QApplication.instance() or QApplication([])
    return app


def make_config(
    width: int = 800,
    height: int = 400,
    opacity: float = 0.9,
    position: str = "center",
) -> Config:
    """Construct a minimal test Config with given display parameters."""
    return Config(
        paths=PathsConfig(applications=(), use_bundle_name=True),
        display=DisplayConfig(
            width=width,
            height=height,
            opacity=opacity,
            position=position,
            x_offset=0,
            y_offset=0,
        ),
        fzf=FzfConfig(options="--reverse"),
        hotkey=HotkeyConfig(global_hotkey="alt+space"),
    )


@pytest.fixture
def window(qt_app):
    """Create a LauncherWindow for each test; close and delete after."""
    cfg = make_config()
    win = LauncherWindow(cfg)
    yield win
    win.close()
    win.deleteLater()


# ---------------------------------------------------------------------------
# AC4.1 — Window is borderless and always-on-top
# ---------------------------------------------------------------------------


def test_window_has_frameless_hint_RT4_1(window):
    """RT-4.1: Window has Qt.FramelessWindowHint set."""
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint


def test_window_has_stays_on_top_hint_RT4_2(window):
    """RT-4.2: Window has Qt.WindowStaysOnTopHint set."""
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


# ---------------------------------------------------------------------------
# AC4.2 — Window dimensions and opacity match config
# ---------------------------------------------------------------------------


def test_window_size_matches_config_RT4_3(qt_app):
    """RT-4.3: Window size matches display.width and display.height from config."""
    from PySide6.QtGui import QFont, QFontMetrics

    cols, rows = 80, 20
    cfg = make_config(width=cols, height=rows)
    win = LauncherWindow(cfg)
    fm = QFontMetrics(QFont("Menlo", 14))
    assert win.width() == cols * fm.averageCharWidth()
    assert win.height() == rows * fm.height()
    win.close()
    win.deleteLater()


def test_window_opacity_matches_config_RT4_4(qt_app):
    """RT-4.4: Window opacity matches display.opacity from config."""
    cfg = make_config(opacity=0.75)
    win = LauncherWindow(cfg)
    # Qt quantizes opacity to 8-bit precision; allow for rounding
    assert win.windowOpacity() == pytest.approx(0.75, abs=0.005)
    win.close()
    win.deleteLater()


# ---------------------------------------------------------------------------
# AC4.3 — Window is centred on primary screen
# ---------------------------------------------------------------------------


def test_window_centred_on_screen_RT4_5(qt_app):
    """RT-4.5: Window geometry is centred relative to primary screen dimensions."""
    from PySide6.QtGui import QFont, QFontMetrics

    cols, rows = 40, 10
    cfg = make_config(width=cols, height=rows, position="center")
    win = LauncherWindow(cfg)
    win.show()

    fm = QFontMetrics(QFont("Menlo", 14))
    pixel_w = cols * fm.averageCharWidth()
    pixel_h = rows * fm.height()

    screen = QApplication.primaryScreen()
    screen_geo = screen.geometry()
    expected_x = (screen_geo.width() - pixel_w) // 2 + screen_geo.x()
    expected_y = (screen_geo.height() - pixel_h) // 2 + screen_geo.y()

    assert win.x() == expected_x
    assert win.y() == expected_y
    win.close()
    win.deleteLater()


# ---------------------------------------------------------------------------
# AC4.4 — Escape key dismisses the window
# ---------------------------------------------------------------------------


def test_escape_key_hides_window_RT4_6(qt_app, window):
    """RT-4.6: Simulated Escape keypress hides the window."""
    window.show()
    assert window.isVisible()
    QTest.keyClick(window, Qt.Key.Key_Escape)
    assert not window.isVisible()


# ---------------------------------------------------------------------------
# AC4.5 — Window hides on focus loss
# ---------------------------------------------------------------------------


def test_window_deactivate_hides_window_RT4_7(qt_app, window):
    """RT-4.7: Simulated WindowDeactivate event hides the window."""
    window.show()
    assert window.isVisible()
    event = QEvent(QEvent.Type.WindowDeactivate)
    QApplication.sendEvent(window, event)
    assert not window.isVisible()
