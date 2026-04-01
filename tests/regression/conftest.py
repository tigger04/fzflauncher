# ABOUTME: Shared pytest fixtures for fzfLAUNCHER regression tests.
# ABOUTME: Provides common paths and configuration used across test modules.

from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def shim_path(project_root):
    """Return the path to the shell shim."""
    return project_root / "bin" / "fzflauncher"


@pytest.fixture
def makefile_path(project_root):
    """Return the path to the Makefile."""
    return project_root / "Makefile"
