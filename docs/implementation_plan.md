<!-- Version: 0.1 | Last updated: 2026-04-01 -->

# fzfLAUNCHER — Implementation Plan

## Overview

The implementation is divided into five phases, each delivering a testable
increment. Phases 1–3 produce a functional launcher. Phases 4–5 add polish
and distribution.

Each phase will be tracked as one or more GitHub issues with acceptance
criteria per our standard process.

---

## Phase 1: Project Scaffolding & Configuration

**Goal:** Establish project structure, tooling, and configuration loading.

### Deliverables

- Project directory structure:
  ```
  bin/fzflauncher              # shell shim
  src/fzflauncher/
      __init__.py
      config.py                # config loading and validation
      discover.py              # target discovery
      launch.py                # launch dispatch
      app.py                   # PySide6 application
      terminal.py              # embedded terminal / fzf host
      preview.py               # fzf preview handler
  config/
      default.conf             # default configuration template
  tests/
      regression/
      one_off/
      NEXT_IDS.txt
  docs/
  Makefile
  requirements.txt
  .gitignore
  .python-version
  ```
- `Makefile` with targets: `install`, `uninstall`, `test`, `test-one-off`,
  `lint`, `fmt`, `release`, `sync`
- Configuration system:
  - Default config embedded/shipped with the project
  - User config at `~/.config/fzflauncher/config.toml`
  - User config overrides defaults; missing keys fall back to defaults
  - Validation on load with clear error messages
- Config schema (TOML):
  ```toml
  [paths]
  applications = ["/Applications", "~/Applications"]
  scripts = ["~/.local/bin"]
  directories = ["~/Documents", "~/Projects"]

  [display]
  width = 80          # columns
  height = 20         # rows
  opacity = 0.95
  position = "center" # center | top | custom
  x_offset = 0        # only used if position = "custom"
  y_offset = 0

  [fzf]
  options = "--reverse --border --margin=1,2"
  preview = true
  preview_command = ""  # empty = built-in preview

  [hotkey]
  global = "alt+space"

  [custom]
  # label = "command"
  # e.g.:
  # "Edit Hosts" = "sudo -e /etc/hosts"
  ```
- Linting: Ruff
- Formatting: Ruff
- Type checking: consider mypy or pyright (decide during phase 1)
- Pre-commit hooks: ruff, ruff-format, detect-secrets

### Dependencies

None — this phase has no external blockers.

### Estimated issues

- Scaffolding and Makefile (1 issue)
- Configuration loading and validation (1 issue)

---

## Phase 2: Target Discovery

**Goal:** Scan the filesystem for launchable targets and present them as a
structured list suitable for piping to fzf.

### Deliverables

- **Application discovery:**
  - Scan configured paths for `.app` bundles
  - Extract display name from `Info.plist` (CFBundleName) with fallback to
    directory name
  - Exclude system/internal apps via configurable ignore patterns
- **Script discovery:**
  - Scan configured paths for executable files
  - Respect `$PATH` ordering for deduplication
  - Skip non-executable files, hidden files
- **Directory discovery:**
  - Read configured directory list
  - Validate paths exist; warn (don't fail) for missing paths
- **Custom entries:**
  - Load from `[custom]` config section
  - No discovery needed — user specifies label and command
- **Unified target list:**
  - Each entry: `type`, `display_name`, `path_or_command`
  - Formatted for fzf: `[app] Firefox`, `[script] backup.sh`, `[dir] ~/Projects`
  - Sorted: custom entries first, then apps, scripts, directories (configurable?)
- **Caching (optional, decide during implementation):**
  - Cache discovery results with filesystem mtime invalidation
  - Or just re-scan on every invocation if it's fast enough (<100ms)

### Dependencies

- Phase 1 (config system)

### Estimated issues

- Application discovery (1 issue)
- Script and directory discovery (1 issue)
- Unified target list formatting (1 issue)

---

## Phase 3: GUI Shell & fzf Integration

**Goal:** A PySide6 window hosting a pseudo-terminal that runs fzf with the
discovered targets. Selecting an entry launches it.

### Deliverables

- **PySide6 application:**
  - Borderless, floating, always-on-top window
  - Configurable size, opacity, position
  - Centre-screen by default
  - Dismisses on Escape or focus loss
- **Embedded terminal:**
  - QProcess-backed pseudo-terminal (pty) inside the PySide6 window
  - Renders fzf output with full colour and keybinding support
  - Approach options (decide during implementation):
    - a) QTermWidget (if available and maintained for PySide6)
    - b) Custom QPlainTextEdit + pty via Python `pty` module
    - c) VTE-style approach with raw terminal emulation
  - Must handle fzf's TUI correctly: cursor movement, colour codes, line
    clearing
- **fzf subprocess:**
  - Pipe discovered targets to fzf's stdin
  - Read selected entry from fzf's stdout
  - Pass configured fzf options
  - Handle: user selects (exit 0), user cancels (exit 130), fzf error
- **Launch dispatch:**
  - Parse selected entry to determine type and target
  - Dispatch to appropriate launch method (see Phase 2 target types)
  - Window dismisses before/during launch
- **Preview pane (if `preview = true`):**
  - Apps: name, version, bundle ID
  - Scripts: first 10 lines (ABOUTME comment + shebang)
  - Directories: `ls` summary
  - Custom: the command that will run

### Risk: Terminal Emulation

Embedding a fully functional terminal emulator that correctly renders fzf is
the highest-risk component. If QTermWidget is unavailable or too heavy, the
fallback is:

1. Pipe targets to fzf running in an external minimal terminal window
   (kitty `--class`, alacritty `--class`) as a subprocess
2. PySide6 becomes the orchestrator rather than the host
3. This trades some visual polish for reliability

**Decision point:** Spike the embedded terminal approach first. If it takes
more than a day to get fzf rendering correctly, fall back to the external
terminal approach. Document the decision.

### Dependencies

- Phase 2 (target list)

### Estimated issues

- PySide6 window and lifecycle (1 issue)
- Terminal widget / fzf hosting (1–2 issues, depending on spike outcome)
- Launch dispatch (1 issue)
- Preview pane (1 issue)

---

## Phase 4: Global Hotkey & System Integration

**Goal:** Summon and dismiss the launcher with a system-wide hotkey, even when
fzfLAUNCHER is not the focused application.

### Deliverables

- **Global hotkey registration:**
  - Register configurable hotkey (default `⌥Space`)
  - Options:
    - a) PySide6 native via `QShortcut` + accessibility permissions
    - b) PyObjC bridge to `CGEventTap` or `NSEvent.addGlobalMonitorForEvents`
    - c) Carbon `RegisterEventHotKey` via ctypes (deprecated but functional)
  - Must work when another app has focus
  - Require accessibility permission; guide user if not granted
- **Background daemon mode:**
  - `fzflauncher --daemon` keeps the process alive, listening for hotkey
  - Window is hidden/shown rather than created/destroyed (faster response)
  - Single-instance enforcement (socket or PID file)
- **Shell shim (`bin/fzflauncher`):**
  - If daemon running: signal it to show window
  - If not running: launch daemon
  - `--no-daemon` flag for one-shot mode (useful for testing / terminal use)
- **launchd integration (optional):**
  - `make install` can optionally install a launchd plist to start daemon at
    login
  - `make uninstall` removes it

### Dependencies

- Phase 3 (working GUI)

### Estimated issues

- Global hotkey (1 issue)
- Daemon mode and single-instance (1 issue)
- launchd integration (1 issue, optional)

---

## Phase 5: Polish & Distribution

**Goal:** Make it installable, reliable, and pleasant.

### Deliverables

- **Error handling hardening:**
  - fzf not installed → clear error message with install instructions
  - Config file malformed → specific error with line number
  - Target not found at launch time → notification, don't crash
- **Performance:**
  - Profile startup time; target <200ms to visible window
  - Cache discovery if scan exceeds 50ms
- **Homebrew formula:**
  - Formula in a tap repo (e.g. `tigoss/homebrew-tools`)
  - `brew install tigoss/tools/fzflauncher`
  - `make release` updates version, SHA256, pushes tag
- **README overhaul:**
  - Quickstart, screenshots/gif, configuration reference, troubleshooting
- **Accessibility:**
  - VoiceOver support for the target list (if feasible with terminal widget)
  - High-contrast config option

### Dependencies

- Phase 4 (feature-complete)

### Estimated issues

- Error handling and edge cases (1 issue)
- Performance profiling and optimisation (1 issue)
- Homebrew formula and release automation (1 issue)
- README and documentation (1 issue)

---

## Phase Summary

| Phase | Description | Issues (est.) | Depends on |
|-------|-------------|---------------|------------|
| 1 | Scaffolding & configuration | 2 | — |
| 2 | Target discovery | 3 | Phase 1 |
| 3 | GUI shell & fzf integration | 4–5 | Phase 2 |
| 4 | Global hotkey & system integration | 2–3 | Phase 3 |
| 5 | Polish & distribution | 3–4 | Phase 4 |
| **Total** | | **14–17** | |

## Open Questions

These should be resolved during or before the relevant phase:

1. **Terminal widget approach** — embedded pty vs external terminal window?
   Spike in Phase 3 will determine this.
2. **Type checking** — mypy or pyright? Decide in Phase 1 based on PySide6
   stub quality.
3. **Caching** — is discovery fast enough without a cache? Measure in Phase 2.
4. **Target sorting** — alphabetical within category, or frecency (recent +
   frequency)? Start with alphabetical, consider frecency in Phase 5.
5. **Config format** — TOML is proposed. INI is simpler but less expressive.
   JSON is too noisy. YAML adds a dependency. TOML is in the stdlib since
   3.11.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-04-01 | Initial draft |
