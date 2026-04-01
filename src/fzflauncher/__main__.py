# ABOUTME: Entry point for python -m fzflauncher.
# ABOUTME: Wires config loading, window creation, and the MVP launch flow.

import argparse
import sys

from fzflauncher import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="fzflauncher",
        description="A keyboard-driven macOS application launcher using fzf.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"fzflauncher {__version__}",
    )
    parser.parse_args()

    from PySide6.QtWidgets import QApplication

    from fzflauncher.app import LauncherWindow
    from fzflauncher.config import ConfigError, load_config

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    app = QApplication(sys.argv)
    window = LauncherWindow(config)
    window.show()
    window.launch()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
