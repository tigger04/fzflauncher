# ABOUTME: Application launch dispatch — resolves display name to .app path and launches.
# ABOUTME: Validates path existence and constructs subprocess command as a list.

from __future__ import annotations

import logging
import subprocess

from fzflauncher.models import Target

logger = logging.getLogger(__name__)


class LaunchError(Exception):
    """Raised when an application cannot be launched."""


def launch_application(display_name: str, targets: list[Target]) -> None:
    """Resolve display_name to an .app path from targets and launch it.

    Args:
        display_name: The name the user selected in fzf.
        targets: The list of discovered Target instances.

    Raises:
        LaunchError: If the name is not found or the .app path is gone.
    """
    target = None
    for t in targets:
        if t.display_name == display_name:
            target = t
            break

    if target is None:
        raise LaunchError(f"Application not found in target list: {display_name!r}")

    path = target.path
    if not path.exists():
        raise LaunchError(f"Application no longer exists at {path}: {path.name}")

    cmd = ["open", "-a", str(path)]
    logger.info("Launching: %s", cmd)
    subprocess.run(cmd, check=False)
