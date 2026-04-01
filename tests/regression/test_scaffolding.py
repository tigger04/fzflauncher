# ABOUTME: Regression tests for project scaffolding (issue #1).
# ABOUTME: Verifies shell shim quality and Makefile target correctness.

import subprocess


class TestShimConformance:
    """RT-1.1 through RT-1.3: Shell shim conforms to coding standards."""

    def test_shim_contains_safety_header_RT1_1(self, shim_path):
        """RT-1.1: Shell shim contains set -euo pipefail."""
        content = shim_path.read_text()
        assert "set -euo pipefail" in content

    def test_shim_passes_shellcheck_RT1_2(self, shim_path):
        """RT-1.2: Shell shim passes ShellCheck with no warnings."""
        result = subprocess.run(
            ["shellcheck", str(shim_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"ShellCheck failed:\n{result.stdout}\n{result.stderr}"

    def test_shim_has_bash_shebang_RT1_3(self, shim_path):
        """RT-1.3: Shell shim uses #!/usr/bin/env bash shebang."""
        first_line = shim_path.read_text().splitlines()[0]
        assert first_line == "#!/usr/bin/env bash"


class TestMakefileTargets:
    """RT-1.4 through RT-1.5: Makefile test target correctness."""

    def _read_test_target_block(self, makefile_path):
        """Extract the test: target block from Makefile (up to next target)."""
        lines = makefile_path.read_text().splitlines()
        in_test_target = False
        block = []
        for line in lines:
            if line.startswith("test:") or line.startswith("test :"):
                in_test_target = True
                block.append(line)
                continue
            if in_test_target:
                if line.startswith("\t") or line.strip() == "":
                    block.append(line)
                else:
                    break
        return "\n".join(block)

    def test_makefile_test_target_references_regression_RT1_4(self, makefile_path):
        """RT-1.4: Makefile test target references tests/regression/."""
        block = self._read_test_target_block(makefile_path)
        assert "tests/regression/" in block, (
            f"test: target does not reference tests/regression/\n{block}"
        )

    def test_makefile_test_target_excludes_one_off_RT1_5(self, makefile_path):
        """RT-1.5: Makefile test target does not reference tests/one_off/."""
        block = self._read_test_target_block(makefile_path)
        assert "tests/one_off/" not in block, (
            f"test: target must not reference tests/one_off/\n{block}"
        )
