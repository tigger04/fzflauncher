<!-- Version: 0.2 | Last updated: 2026-04-01 -->

# fzfLAUNCHER — Testing Strategy

## Overview

Testing follows TDD per our standard process. The architecture deliberately
separates pure logic (discovery, config, launch dispatch) from GUI and
subprocess concerns (PySide6, fzf, pty), making the majority of the codebase
testable with fast, deterministic unit tests.

## Test Framework

- **Runner:** pytest
- **Assertions:** plain `assert` (pytest introspection handles the rest)
- **Fixtures:** pytest fixtures and `tmp_path` for filesystem tests
- **Mocking:** `unittest.mock` — restricted to external boundaries only (see
  below)

## Directory Structure

```
tests/
├── regression/
│   ├── conftest.py           # shared fixtures
│   ├── test_config.py        # config loading and validation
│   ├── test_discover.py      # target discovery
│   ├── test_launch.py        # launch dispatch
│   ├── test_preview.py       # preview generation
│   └── test_integration.py   # multi-component integration tests
├── one_off/
│   └── .gitkeep
└── NEXT_IDS.txt
```

## Test Boundaries

| Layer | Type | What's tested | External deps |
|-------|------|---------------|---------------|
| `config.py` | Unit | Parsing, validation, defaults, merging, error messages | None (reads from string/dict in tests) |
| `discover.py` | Unit + Integration | App scanning (v0.1), script/dir scanning (future), deduplication, formatting | Filesystem (via `tmp_path`) |
| `launch.py` | Unit | Dispatch logic, command construction | `subprocess` mocked at boundary |
| `preview.py` | Unit | Preview text generation for each target type (future) | Filesystem (via `tmp_path`) |
| `terminal.py` | Integration | fzf subprocess communication, pty management | fzf binary |
| `app.py` | Integration + UT | Window lifecycle, hotkey, focus handling | PySide6, display |

## What Gets Mocked (and What Doesn't)

### Acceptable mocks

- `subprocess.run` / `subprocess.Popen` in `launch.py` unit tests — we don't
  want tests actually opening applications
- `os.path.exists` and filesystem calls when testing config validation logic
  in isolation
- System APIs for hotkey registration in unit tests

### Not acceptable

- Mocking `discover.py`'s filesystem scanning — use `tmp_path` with real
  directory structures instead
- Mocking fzf — integration tests run against the real fzf binary
- Mocking PySide6 widgets to test GUI behaviour — use `QTest` or manual UTs

### Rationale

The real bugs will live at the boundaries: does discovery actually find `.app`
bundles? Does fzf actually receive and return our formatted entries? Does
`open -a` actually launch the app? Mocking these away would test nothing useful.

## Test Categories

### 1. Configuration (`test_config.py`)

| Area | Conditions to cover |
|------|-------------------|
| Default loading | Defaults applied when no user config exists |
| User override | User config values override defaults |
| Partial config | Missing sections fall back to defaults |
| Path expansion | `~` expanded in all path values |
| Validation | Invalid types, out-of-range values, malformed YAML |
| Error messages | Each validation failure produces a specific, actionable message |

### 2. Discovery (`test_discover.py`)

v0.1 MVP covers application discovery only. Script, directory, and custom
entry discovery tests will be added in Phase 4.

| Area | Conditions to cover | Version |
|------|-------------------|---------|
| App discovery | Finds `.app` bundles in configured paths | v0.1 |
| App naming | Extracts CFBundleName from Info.plist; falls back to dir name | v0.1 |
| App exclusion | Configured ignore patterns exclude matching apps | v0.1 |
| Deduplication | Same app in multiple paths appears once | v0.1 |
| Formatting | Output format matches expected fzf input | v0.1 |
| Empty state | No targets found → empty list, no crash | v0.1 |
| Script discovery | Finds executable files in configured paths | Future |
| Script filtering | Skips non-executable, hidden files | Future |
| Directory targets | Configured directories included; missing paths warned, not failed | Future |
| Custom entries | Config-defined entries appear in target list | Future |

Tests use `tmp_path` to construct real directory trees with real `.app` bundle
structures (minimal: `Contents/Info.plist` with `CFBundleName`).

### 3. Launch dispatch (`test_launch.py`)

v0.1 MVP covers application launching only.

| Area | Conditions to cover | Version |
|------|-------------------|---------|
| App launch | `.app` targets dispatched via `open -a` | v0.1 |
| Missing target | Target path no longer exists at launch time → error, not crash | v0.1 |
| Command construction | Constructed commands are safe (no injection) | v0.1 |
| Script launch | Script targets executed directly | Future |
| Directory launch | Directory targets dispatched via `open` | Future |
| Custom launch | Custom entries executed via shell | Future |
| Permission denied | Script not executable → clear error | Future |

`subprocess` is mocked here — we verify the correct command is constructed,
not that macOS `open` works.

### 4. Preview (`test_preview.py`) — Future

Not part of v0.1 MVP. Tests will be added alongside the preview feature
in Phase 4.

| Area | Conditions to cover |
|------|-------------------|
| App preview | Shows name, version, bundle ID from Info.plist |
| Script preview | Shows shebang + ABOUTME comment |
| Directory preview | Shows directory listing summary |
| Custom preview | Shows the command |
| Missing target | Preview for nonexistent path → graceful message |

### 5. Integration (`test_integration.py`)

These tests exercise multiple components together:

| Area | Conditions to cover |
|------|-------------------|
| Discovery → fzf | Discovered targets piped to fzf; fzf receives correct input |
| fzf → launch | fzf selection string correctly parsed and dispatched |
| Config → discovery | Config path changes reflected in discovery results |
| End-to-end (headless) | Config → discover → fzf (with scripted input) → launch dispatch |

Integration tests require fzf to be installed. They should be skipped
(not failed) if fzf is not available:

```python
import shutil
import pytest

fzf_available = shutil.which("fzf") is not None
requires_fzf = pytest.mark.skipif(not fzf_available, reason="fzf not installed")
```

### 6. GUI (User Tests)

GUI behaviour is difficult to test automatically and is best verified manually.
These will be documented as UT-NNN entries in issue AC tables.

| Area | Verified by |
|------|-------------|
| Window appears on hotkey | UT |
| Window is borderless, floating, centred | UT |
| fzf renders correctly (colours, cursor) | UT |
| Escape dismisses window | UT |
| Focus loss dismisses window | UT |
| Selection launches target and dismisses | UT |
| Window reappears on subsequent hotkey press | UT |
| Opacity and size match config | UT |

If we find a reliable way to automate any of these (e.g. `QTest` for widget
interaction), they can be promoted to automated tests.

## Performance Testing

Not part of the standard test suite, but measured during Phase 5:

- **Startup latency:** time from hotkey press to window visible (<200ms target)
- **Discovery time:** time to scan all configured paths (<100ms target)
- **fzf responsiveness:** no perceptible input lag during typing

Measured with `time` and `cProfile`. Results documented in a Phase 5 issue.

## CI Considerations

For now, tests run locally via `make test`. If/when CI is added:

- GitHub Actions, macOS runner
- fzf installed in CI environment
- PySide6 tests may need `QT_QPA_PLATFORM=offscreen` for headless execution
- GUI UTs remain manual

## Makefile Targets

```makefile
test:
    pytest tests/regression/ -v

test-one-off:
ifdef ISSUE
    pytest tests/one_off/ -v -k "$(ISSUE)"
else
    pytest tests/one_off/ -v
endif

lint:
    ruff check src/ tests/

fmt:
    ruff format src/ tests/

typecheck:
    # mypy or pyright — TBD in Phase 1
```

## Coverage

- **Target:** 80% line coverage for all new code
- **Critical paths requiring 100%:**
  - Config validation (malformed config must never crash the app)
  - Launch command construction (injection prevention)
  - Target type dispatch (wrong type → wrong action)
- **Excluded from coverage:**
  - GUI code (`app.py`, `terminal.py`) — covered by UTs
  - Shell shim (`bin/fzflauncher`) — tested manually

## Test ID Sequences

Initial allocation in `tests/NEXT_IDS.txt`:

```
RT 001
OT 001
UT 001
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-04-01 | Initial draft |
| 0.2 | 2026-04-01 | YAML config; scope annotations for v0.1 MVP (apps only); defer preview/script/dir/custom tests |
