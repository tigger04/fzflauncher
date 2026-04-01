<!-- Version: 0.2 | Last updated: 2026-04-01 -->

# fzfLAUNCHER — Architecture

## System Overview

fzfLAUNCHER is a macOS application launcher composed of three layers: a core
library (pure Python), a subprocess bridge (fzf), and a GUI shell (PySide6).
The layers communicate through well-defined interfaces so that each can be
tested and, if necessary, replaced independently.

```
┌─────────────────────────────────────────────┐
│              bin/fzflauncher                 │  Shell shim
│         (venv activation, arg parsing)       │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│              GUI Shell (PySide6)             │  Layer 3
│  ┌────────────┐  ┌────────────────────────┐ │
│  │   app.py   │  │    terminal.py         │ │
│  │  (window,  │  │  (pty, fzf subprocess, │ │
│  │   hotkey,  │  │   input/output)        │ │
│  │   lifecycle│  │                        │ │
│  └─────┬──────┘  └───────────┬────────────┘ │
└────────┼─────────────────────┼──────────────┘
         │                     │
┌────────▼─────────────────────▼──────────────┐
│              Core Library (Python)           │  Layer 1–2
│  ┌────────────┐ ┌───────────┐ ┌───────────┐ │
│  │ discover.py│ │ launch.py │ │ preview.py│ │
│  │            │ │           │ │           │ │
│  └─────┬──────┘ └───────────┘ └───────────┘ │
│        │                                     │
│  ┌─────▼──────┐                              │
│  │ config.py  │                              │
│  └────────────┘                              │
└─────────────────────────────────────────────┘
```

## Layers

### Layer 1: Configuration (`config.py`)

The foundation. All other components depend on it; it depends on nothing.

- Loads default configuration shipped with the project
- Loads user configuration from `~/.config/fzflauncher/config.yaml`
- Merges user values over defaults (missing keys fall back to defaults)
- Validates all values on load — type, range, path existence
- Exposes a frozen dataclass (or similar immutable structure) to consumers
- Raises specific, actionable errors on invalid config

**Key constraint:** Config is loaded once at startup and treated as immutable
for the lifetime of that invocation. No hot-reloading.

### Layer 2: Core Logic (`discover.py`, `launch.py`, `preview.py`)

Pure application logic with no GUI or subprocess dependencies (except
`launch.py` which constructs subprocess commands).

**`discover.py`** — Target discovery and formatting.

- Accepts a config object
- v0.1: scans configured paths for `.app` bundles only
- Future: scripts, directories, custom entries (see implementation plan Phase 4)
- Returns a list of `Target` dataclass instances
- Formats the list as fzf-compatible strings
- Handles: deduplication, ignore patterns, missing paths (warn, don't fail)

**`launch.py`** — Launch dispatch.

- Accepts a `Target` and executes the appropriate launch command
- Dispatch table:

  | Target type | Command | Version |
  |-------------|---------|---------|
  | Application | `open -a <path>` | v0.1 |
  | Script | Direct execution | Future |
  | Directory | `open <path>` | Future |
  | Custom | Shell execution of user-defined command | Future |

- Constructs commands as lists (never strings) to prevent injection
- Validates target still exists before launching

**`preview.py`** — Preview text generation for fzf's preview window. (Future —
not part of v0.1 MVP.)

- Accepts a `Target`
- Returns a string suitable for display in fzf's preview pane
- Content varies by type: app metadata, script header, directory listing,
  custom command text

### Layer 3: GUI Shell (`app.py`, `terminal.py`)

The presentation layer. Depends on Layers 1 and 2. No business logic here.

**`app.py`** — Application lifecycle and window management.

- Creates the `QApplication`
- Manages the main window: borderless, floating, always-on-top, centred
- Registers global hotkey (show/hide toggle)
- Handles: Escape to dismiss, focus-loss to dismiss, daemon mode
- Single-instance enforcement

**`terminal.py`** — Embedded pseudo-terminal hosting fzf.

- Creates a pty (pseudo-terminal) via Python's `pty` module
- Spawns fzf as a subprocess connected to the pty
- Pipes discovered targets to fzf's stdin
- Renders fzf's terminal output in a PySide6 widget
- Captures fzf's selection on exit and passes it to `launch.py`
- Handles fzf lifecycle: normal exit (selection), cancel (Escape/Ctrl-C), error

**Implementation note:** Embedding fzf requires bridging its TUI output (ANSI
escape codes for cursor, colour, redraws) into a Qt widget. The Phase 3 spike
will determine the best approach — QTermWidget, custom pty + ANSI parsing, or
a library like pyte for screen buffer emulation. See the implementation plan
for details.

### Shell Shim (`bin/fzflauncher`)

A thin bash script that:

1. Locates the project's Python virtual environment
2. Activates it
3. Passes arguments to the Python entry point
4. Handles `--daemon`, `--no-daemon`, `--help`, `--version`

The shim contains no business logic. It exists so that `fzflauncher` can be
symlinked to `~/.local/bin/` and invoked without the user knowing or caring
about the venv.

## Data Flow

### Normal invocation

```
User presses hotkey
        │
        ▼
  app.py receives hotkey event
        │
        ▼
  app.py shows window
        │
        ▼
  config.py loads configuration (or reuses cached config in daemon mode)
        │
        ▼
  discover.py scans filesystem, returns Target list
        │
        ▼
  terminal.py pipes Target list to fzf subprocess
        │
        ▼
  User interacts with fzf (type, navigate, select)
        │
        ├── Escape / Ctrl-C ──► terminal.py detects cancel ──► app.py hides window
        │
        └── Enter ──► terminal.py reads selection
                            │
                            ▼
                      launch.py dispatches target
                            │
                            ▼
                      app.py hides window
```

### CLI invocation (no GUI)

```
$ fzflauncher --no-daemon
        │
        ▼
  config.py loads configuration
        │
        ▼
  discover.py scans filesystem, returns Target list
        │
        ▼
  Targets printed to stdout, piped to fzf in the user's terminal
        │
        ▼
  User selects ──► launch.py dispatches
```

This mode requires no PySide6 and is useful for testing, scripting, and
environments without a display.

## Key Data Structures

### Target

```python
@dataclass(frozen=True)
class Target:
    type: TargetType          # app | script | directory | custom
    display_name: str         # human-readable name
    path: str                 # filesystem path or command string
    metadata: dict[str, str]  # optional: bundle_id, version, etc.
```

### TargetType

```python
class TargetType(Enum):
    APP = "app"
    SCRIPT = "script"
    DIRECTORY = "dir"
    CUSTOM = "custom"
```

### Config

```python
@dataclass(frozen=True)
class Config:
    paths: PathsConfig
    display: DisplayConfig
    fzf: FzfConfig
    hotkey: HotkeyConfig
    custom: dict[str, str]    # label → command
```

Exact field definitions will be finalised in Phase 1.

## Dependency Graph

```
config.py       ← depends on nothing
discover.py     ← depends on config.py
preview.py      ← depends on config.py (for preview settings)
launch.py       ← depends on nothing (receives Target, not Config)
terminal.py     ← depends on discover.py, launch.py, preview.py, config.py
app.py          ← depends on terminal.py, config.py
bin/fzflauncher ← depends on app.py (or discover.py + launch.py in CLI mode)
```

No circular dependencies. The dependency direction is always upward in the
layer diagram.

## External Dependencies

| Dependency | Role | Required? |
|------------|------|-----------|
| Python 3.12+ | Runtime | Yes |
| PySide6 | GUI window, widgets, event loop | Yes (GUI mode) |
| fzf | Fuzzy matching engine | Yes |
| PyYAML | Config parsing | Yes |

No other runtime dependencies. Build/test dependencies (pytest, ruff) are
development-only.

## Security Considerations

- **Command injection:** Launch commands are constructed as lists, never
  strings. `subprocess.run(["open", "-a", path])`, not
  `subprocess.run(f"open -a {path}", shell=True)`.
- **Custom entries (future):** User-defined commands in config will be
  executed via shell. This is intentional — the user authors them. They are
  never sourced from untrusted input.
- **Path traversal:** Discovery only scans configured paths. It does not
  follow symlinks outside configured directories.
- **Permissions:** The app requests Accessibility permission (for global
  hotkey) and nothing else.

## Filesystem Layout

```
~/.config/fzflauncher/
    config.yaml              # user configuration

~/.local/bin/
    fzflauncher              # symlink to bin/fzflauncher (via make install)

<project>/
    bin/fzflauncher          # shell shim
    src/fzflauncher/         # Python package
    config/default.yaml      # default configuration
    tests/                   # test suite
    docs/                    # documentation
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-04-01 | Initial draft |
| 0.2 | 2026-04-01 | YAML config; scope annotations for v0.1 MVP (apps only) |
