# ABOUTME: Entry point for python -m fzflauncher.
# ABOUTME: Provides CLI argument handling and launches the application.

import argparse

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


if __name__ == "__main__":
    main()
