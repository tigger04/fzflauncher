# ABOUTME: Regression tests for terminal widget and fzf hosting (issue #5).
# ABOUTME: Covers pty spawning, display buffer, keyboard forwarding, exit handling.

from __future__ import annotations

import os
import stat
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from fzflauncher.terminal import TerminalWidget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ITEMS = ["Alpha", "Beta", "Gamma", "Delta"]


def wait_until(predicate, app, timeout=5.0, interval=0.05):
    """Poll predicate, processing Qt events, until True or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(interval)
    return False


def screen_text(widget):
    """Return the full pyte screen content as a single string."""
    return "\n".join(widget.screen.display)


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def widget(qt_app):
    """Create a TerminalWidget, start fzf, yield, then clean up."""
    w = TerminalWidget(items=ITEMS, fzf_options="--reverse")
    w.start()
    yield w
    w.cleanup()


# ---------------------------------------------------------------------------
# Mock fzf scripts for deterministic exit code testing
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_fzf_exit_0(tmp_path):
    """Mock fzf that selects the first item and exits 0."""
    script = tmp_path / "mock_fzf"
    script.write_text("#!/bin/bash\nhead -1\nexit 0\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


@pytest.fixture
def mock_fzf_exit_130(tmp_path):
    """Mock fzf that discards input and exits 130 (cancelled)."""
    script = tmp_path / "mock_fzf"
    script.write_text("#!/bin/bash\ncat > /dev/null\nexit 130\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


@pytest.fixture
def mock_fzf_exit_1(tmp_path):
    """Mock fzf that discards input and exits 1 (no match)."""
    script = tmp_path / "mock_fzf"
    script.write_text("#!/bin/bash\ncat > /dev/null\nexit 1\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


@pytest.fixture
def mock_fzf_exit_2(tmp_path):
    """Mock fzf that discards input and exits 2 (error)."""
    script = tmp_path / "mock_fzf"
    script.write_text("#!/bin/bash\ncat > /dev/null\nexit 2\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


# ---------------------------------------------------------------------------
# AC5.1 — Widget spawns fzf connected to a pty
# ---------------------------------------------------------------------------


def test_widget_spawns_fzf_process_RT5_1(widget):
    """RT-5.1: Widget creation spawns an fzf process."""
    assert widget.pid is not None
    assert widget.is_running()


def test_widget_holds_pty_master_fd_RT5_2(widget):
    """RT-5.2: fzf process is connected to a pty (widget holds master fd)."""
    assert widget.master_fd is not None
    # Master fd of a pty pair is a valid fd
    os.fstat(widget.master_fd)  # would raise if invalid


# ---------------------------------------------------------------------------
# AC5.2 — Items appear in the display buffer
# ---------------------------------------------------------------------------


def test_items_appear_in_display_buffer_RT5_3(qt_app, widget):
    """RT-5.3: Piped items appear in the widget's display buffer."""
    found = wait_until(lambda: "Alpha" in screen_text(widget), qt_app)
    assert found, f"Items not found in screen:\n{screen_text(widget)}"


def test_fzf_prompt_visible_RT5_4(qt_app, widget):
    """RT-5.4: fzf's input prompt (match count) is visible in display buffer."""
    # fzf shows a count like "4/4" or "> " prompt
    found = wait_until(
        lambda: ">" in screen_text(widget) or "/" in screen_text(widget),
        qt_app,
    )
    assert found, f"Prompt not found in screen:\n{screen_text(widget)}"


# ---------------------------------------------------------------------------
# AC5.3 — Keyboard input forwarded to fzf
# ---------------------------------------------------------------------------


def test_typing_updates_filter_RT5_5(qt_app, widget):
    """RT-5.5: Simulate typing; fzf's filter input updates."""
    # Wait for fzf to be ready
    wait_until(lambda: "Alpha" in screen_text(widget), qt_app)
    # Type "Al" to filter
    os.write(widget.master_fd, b"Al")
    # After filtering, only Alpha should remain (1/4 match count)
    found = wait_until(lambda: "1/" in screen_text(widget), qt_app)
    assert found, f"Filter not applied:\n{screen_text(widget)}"


def test_enter_selects_and_exits_RT5_6(qt_app):
    """RT-5.6: Simulate Enter; fzf exits with a selection."""
    w = TerminalWidget(items=ITEMS, fzf_options="--reverse")
    w.start()
    # Wait for fzf to be ready
    wait_until(lambda: "Alpha" in screen_text(w), qt_app)
    # Press Enter to select the highlighted item
    os.write(w.master_fd, b"\r")
    # Wait for exit
    exited = wait_until(lambda: w.exit_status is not None, qt_app)
    assert exited, "fzf did not exit after Enter"
    assert w.exit_status == 0
    w.cleanup()


# ---------------------------------------------------------------------------
# AC5.4 — Captures selection on normal exit
# ---------------------------------------------------------------------------


def test_selection_available_on_exit_0_RT5_7(qt_app, mock_fzf_exit_0):
    """RT-5.7: fzf exits 0; selected text is available from the widget."""
    w = TerminalWidget(items=ITEMS, fzf_path=mock_fzf_exit_0)
    w.start()
    exited = wait_until(lambda: w.exit_status is not None, qt_app)
    assert exited
    assert w.exit_status == 0
    assert w.selected_text == "Alpha"
    w.cleanup()


def test_no_selection_on_exit_130_RT5_8(qt_app, mock_fzf_exit_130):
    """RT-5.8: fzf exits 130 (cancel); widget reports no selection."""
    w = TerminalWidget(items=ITEMS, fzf_path=mock_fzf_exit_130)
    w.start()
    exited = wait_until(lambda: w.exit_status is not None, qt_app)
    assert exited
    assert w.exit_status == 130
    assert w.selected_text is None
    w.cleanup()


# ---------------------------------------------------------------------------
# AC5.5 — Error and edge-case exit states
# ---------------------------------------------------------------------------


def test_no_match_exit_1_RT5_9(qt_app, mock_fzf_exit_1):
    """RT-5.9: fzf exits 1 (no match); widget signals no selection."""
    w = TerminalWidget(items=ITEMS, fzf_path=mock_fzf_exit_1)
    w.start()
    exited = wait_until(lambda: w.exit_status is not None, qt_app)
    assert exited
    assert w.exit_status == 1
    assert w.selected_text is None
    w.cleanup()


def test_error_exit_2_RT5_10(qt_app, mock_fzf_exit_2):
    """RT-5.10: fzf exits 2 (error); widget signals error."""
    w = TerminalWidget(items=ITEMS, fzf_path=mock_fzf_exit_2)
    w.start()
    exited = wait_until(lambda: w.exit_status is not None, qt_app)
    assert exited
    assert w.exit_status == 2
    assert w.selected_text is None
    w.cleanup()


def test_fzf_not_in_path_raises_RT5_11(qt_app):
    """RT-5.11: fzf binary not in $PATH; clear error raised at widget creation."""
    w = TerminalWidget(items=ITEMS, fzf_path="/nonexistent/fzf")
    with pytest.raises(FileNotFoundError, match="fzf"):
        w.start()
