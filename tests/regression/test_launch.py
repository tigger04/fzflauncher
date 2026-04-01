# ABOUTME: Regression tests for application launch dispatch (issue #6).
# ABOUTME: Covers display name resolution, command construction, path validation, and error handling.

from __future__ import annotations

from unittest.mock import patch

import pytest

from fzflauncher.launch import LaunchError, launch_application
from fzflauncher.models import Target, TargetType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def targets(tmp_path):
    """Create a target list with real .app bundle directories."""
    app1 = tmp_path / "Safari.app"
    app1.mkdir()
    app2 = tmp_path / "My Cool App.app"
    app2.mkdir()
    return [
        Target(
            type=TargetType.APPLICATION,
            display_name="Safari",
            path=app1,
            metadata={},
        ),
        Target(
            type=TargetType.APPLICATION,
            display_name="My Cool App",
            path=app2,
            metadata={},
        ),
    ]


# ---------------------------------------------------------------------------
# AC6.1 — Display name resolved and launched via open -a
# ---------------------------------------------------------------------------


@patch("fzflauncher.launch.subprocess.run")
def test_launch_constructs_open_command_RT6_1(mock_run, targets):
    """RT-6.1: Constructed command is ["open", "-a", <path>]."""
    mock_run.return_value = None
    launch_application("Safari", targets)
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "open"
    assert cmd[1] == "-a"
    assert "Safari.app" in str(cmd[2])


@patch("fzflauncher.launch.subprocess.run")
def test_launch_resolves_display_name_to_path_RT6_2(mock_run, targets):
    """RT-6.2: Display name correctly maps to the .app path from the target list."""
    mock_run.return_value = None
    launch_application("Safari", targets)
    cmd = mock_run.call_args[0][0]
    assert cmd[2] == str(targets[0].path)


def test_launch_unknown_name_raises_RT6_3(targets):
    """RT-6.3: Display name not found in target list raises a specific error."""
    with pytest.raises(LaunchError, match="not found"):
        launch_application("NonExistent", targets)


# ---------------------------------------------------------------------------
# AC6.2 — Commands are lists, not shell strings
# ---------------------------------------------------------------------------


@patch("fzflauncher.launch.subprocess.run")
def test_command_is_list_RT6_4(mock_run, targets):
    """RT-6.4: Command passed to subprocess is a list type."""
    mock_run.return_value = None
    launch_application("Safari", targets)
    cmd = mock_run.call_args[0][0]
    assert isinstance(cmd, list)


@patch("fzflauncher.launch.subprocess.run")
def test_subprocess_not_called_with_shell_RT6_5(mock_run, targets):
    """RT-6.5: subprocess is not called with shell=True."""
    mock_run.return_value = None
    launch_application("Safari", targets)
    kwargs = mock_run.call_args[1] if mock_run.call_args[1] else {}
    assert kwargs.get("shell") is not True


@patch("fzflauncher.launch.subprocess.run")
def test_app_name_with_spaces_RT6_6(mock_run, targets):
    """RT-6.6: App name containing spaces is handled without shell quoting issues."""
    mock_run.return_value = None
    launch_application("My Cool App", targets)
    cmd = mock_run.call_args[0][0]
    assert isinstance(cmd, list)
    assert "My Cool App.app" in str(cmd[2])


# ---------------------------------------------------------------------------
# AC6.3 — Rejects targets whose .app path no longer exists
# ---------------------------------------------------------------------------


def test_nonexistent_app_path_raises_RT6_7(tmp_path):
    """RT-6.7: Non-existent .app path raises a specific error."""
    gone = tmp_path / "Gone.app"
    target_list = [
        Target(
            type=TargetType.APPLICATION,
            display_name="Gone",
            path=gone,
            metadata={},
        ),
    ]
    with pytest.raises(LaunchError, match="no longer exists"):
        launch_application("Gone", target_list)


def test_error_includes_missing_path_RT6_8(tmp_path):
    """RT-6.8: Error message includes the path that was not found."""
    gone = tmp_path / "Missing.app"
    target_list = [
        Target(
            type=TargetType.APPLICATION,
            display_name="Missing",
            path=gone,
            metadata={},
        ),
    ]
    with pytest.raises(LaunchError, match="Missing.app"):
        launch_application("Missing", target_list)
