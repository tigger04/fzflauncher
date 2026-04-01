# ABOUTME: One-off tests for project scaffolding verification (issue #1).
# ABOUTME: Verifies directory structure, file existence, and Makefile target functionality.

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestDirectoryStructure:
    """OT-1.1: All required directories exist."""

    @pytest.mark.one_off(issue="#1")
    @pytest.mark.parametrize(
        "directory",
        [
            "src/fzflauncher",
            "bin",
            "config",
            "tests/regression",
            "tests/one_off",
            "docs",
            "hooks",
        ],
    )
    def test_required_directories_exist_OT1_1(self, directory):
        """OT-1.1: All required directories exist."""
        path = PROJECT_ROOT / directory
        assert path.is_dir(), f"Required directory missing: {directory}"


class TestRequiredFiles:
    """OT-1.2: All required files exist."""

    @pytest.mark.one_off(issue="#1")
    @pytest.mark.parametrize(
        "filepath",
        [
            "Makefile",
            "requirements.txt",
            ".gitignore",
            ".python-version",
            "bin/fzflauncher",
            "src/fzflauncher/__init__.py",
            "hooks/pre-commit",
        ],
    )
    def test_required_files_exist_OT1_2(self, filepath):
        """OT-1.2: All required files exist."""
        path = PROJECT_ROOT / filepath
        assert path.is_file(), f"Required file missing: {filepath}"


class TestMakefileTargetFunctionality:
    """OT-1.3 through OT-1.7: Makefile targets work correctly."""

    @pytest.mark.one_off(issue="#1")
    def test_make_lint_runs_successfully_OT1_3(self):
        """OT-1.3: make lint runs successfully."""
        result = subprocess.run(
            ["make", "lint"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"make lint failed:\n{result.stderr}"

    @pytest.mark.one_off(issue="#1")
    def test_make_fmt_runs_successfully_OT1_4(self):
        """OT-1.4: make fmt runs successfully."""
        result = subprocess.run(
            ["make", "fmt"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"make fmt failed:\n{result.stderr}"

    @pytest.mark.one_off(issue="#1")
    def test_make_test_one_off_targets_one_off_dir_OT1_5(self):
        """OT-1.5: make test-one-off targets tests/one_off/."""
        makefile = (PROJECT_ROOT / "Makefile").read_text()
        # Find the test-one-off target block
        lines = makefile.splitlines()
        in_target = False
        block = []
        for line in lines:
            if line.startswith("test-one-off:") or line.startswith("test-one-off :"):
                in_target = True
                block.append(line)
                continue
            if in_target:
                if (
                    line.startswith("\t")
                    or line.strip() == ""
                    or line.startswith("ifdef")
                    or line.startswith("else")
                    or line.startswith("endif")
                ):
                    block.append(line)
                else:
                    break
        block_text = "\n".join(block)
        assert "tests/one_off/" in block_text, (
            f"test-one-off: target does not reference tests/one_off/\n{block_text}"
        )

    @pytest.mark.one_off(issue="#1")
    def test_make_install_creates_symlink_OT1_6(self):
        """OT-1.6: make install creates symlink; fzflauncher --help shows usage."""
        symlink = Path.home() / ".local" / "bin" / "fzflauncher"

        # Run make install
        result = subprocess.run(
            ["make", "install"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"make install failed:\n{result.stderr}"
        assert symlink.is_symlink(), f"Symlink not created at {symlink}"

        # Verify --help works
        help_result = subprocess.run(
            [str(symlink), "--help"],
            capture_output=True,
            text=True,
        )
        assert help_result.returncode == 0, (
            f"fzflauncher --help failed:\n{help_result.stderr}"
        )

    @pytest.mark.one_off(issue="#1")
    def test_make_uninstall_removes_symlink_OT1_7(self):
        """OT-1.7: make uninstall removes the symlink."""
        symlink = Path.home() / ".local" / "bin" / "fzflauncher"

        # Ensure installed first
        subprocess.run(
            ["make", "install"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )

        # Run make uninstall
        result = subprocess.run(
            ["make", "uninstall"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"make uninstall failed:\n{result.stderr}"
        assert not symlink.exists(), f"Symlink still exists at {symlink}"


class TestPreCommitHooks:
    """OT-1.8 through OT-1.9: Pre-commit hook enforces ruff."""

    @pytest.mark.one_off(issue="#1")
    def test_hook_rejects_lint_violation_OT1_8(self):
        """OT-1.8: Committing a file with a ruff lint violation is rejected by the hook."""
        bad_file = PROJECT_ROOT / "src" / "fzflauncher" / "_test_lint_violation.py"
        hook = PROJECT_ROOT / "hooks" / "pre-commit"
        try:
            # Create a file with an unused import (F401)
            bad_file.write_text("import os\n")
            # Stage it
            subprocess.run(
                ["git", "add", str(bad_file)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
            )
            # Run the hook directly
            result = subprocess.run(
                [str(hook)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
            )
            assert result.returncode != 0, "Hook should have rejected lint violation"
        finally:
            subprocess.run(
                ["git", "reset", "HEAD", str(bad_file)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
            )
            if bad_file.exists():
                bad_file.unlink()

    @pytest.mark.one_off(issue="#1")
    def test_hook_rejects_format_violation_OT1_9(self):
        """OT-1.9: Committing a file with a ruff formatting violation is rejected by the hook."""
        bad_file = PROJECT_ROOT / "src" / "fzflauncher" / "_test_fmt_violation.py"
        hook = PROJECT_ROOT / "hooks" / "pre-commit"
        try:
            # Create a file with bad formatting
            bad_file.write_text("x=1\ny  =   2\n")
            # Stage it
            subprocess.run(
                ["git", "add", str(bad_file)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
            )
            # Run the hook directly
            result = subprocess.run(
                [str(hook)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
            )
            assert result.returncode != 0, (
                "Hook should have rejected formatting violation"
            )
        finally:
            subprocess.run(
                ["git", "reset", "HEAD", str(bad_file)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
            )
            if bad_file.exists():
                bad_file.unlink()
