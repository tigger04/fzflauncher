<!-- Version: 0.2 | Last updated: 2026-04-01 -->

# fzfLAUNCHER — Implementation Plan

## Overview

The implementation is divided into phases, each delivering a testable
increment. **Phases 1–3 deliver the v0.1 MVP: an application launcher.**
Later phases add additional target types, polish, and distribution.

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
  config/
      default.yaml             # default configuration template
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
  - User config at `~/.config/fzflauncher/config.yaml`
  - User config overrides defaults; missing keys fall back to defaults
  - Validation on load with clear error messages
- Config schema (YAML) — v0.1 MVP fields only:
  ```yaml
  paths:
    applications:
      - /Applications
      - ~/Applications

  display:
    width: 80           # columns
    height: 20          # rows
    opacity: 0.95
    position: center    # center | top | custom
    x_offset: 0         # only used if position = custom
    y_offset: 0

  fzf:
    options: "--reverse --border --margin=1,2"

  hotkey:
    global: alt+space
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

## Phase 2: Application Discovery

**Goal:** Scan the filesystem for `.app` bundles and present them as a list
suitable for piping to fzf.

### Deliverables

- **Application discovery:**
  - Scan configured paths for `.app` bundles
  - Extract display name from `Info.plist` (CFBundleName) with fallback to
    directory name
  - Exclude system/internal apps via configurable ignore patterns
- **Target list:**
  - Each entry: `display_name`, `path`
  - Formatted for fzf: one application name per line
  - Sorted alphabetically
  - Deduplication: same app in multiple paths appears once
- **Caching (optional, decide during implementation):**
  - Cache discovery results with filesystem mtime invalidation
  - Or just re-scan on every invocation if it's fast enough (<100ms)

### Dependencies

- Phase 1 (config system)

### Estimated issues

- Application discovery and formatting (1 issue)

---

## Phase 3: GUI Shell & fzf Integration (MVP complete)

**Goal:** A PySide6 window hosting fzf with the discovered applications.
Selecting an entry launches it. **This completes the v0.1 MVP.**

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
  - Pipe discovered application names to fzf's stdin
  - Read selected entry from fzf's stdout
  - Pass configured fzf options
  - Handle: user selects (exit 0), user cancels (exit 130), fzf error
- **Application launch:**
  - Map selected display name back to `.app` path
  - Launch via `open -a`
  - Window dismisses before/during launch

### Risk: Terminal Emulation

Embedding a terminal emulator that correctly renders fzf is the highest-risk
component. fzf is a full TUI — it uses ANSI escape codes for cursor movement,
colour, line clearing, and screen redraws. A Qt widget doesn't handle any of
that natively, so we need to bridge that gap.

**Approach options (to be spiked in Phase 3):**

- a) QTermWidget — a Qt terminal widget, if available and maintained for PySide6
- b) Custom widget + pty — `QPlainTextEdit` or custom `QWidget` with a pty
  backend, parsing ANSI escape sequences ourselves
- c) Existing Python terminal emulation libraries (e.g. pyte for screen
  buffer parsing) feeding a Qt widget

The spike determines *which* embedding approach works best, not whether to
embed. PySide6 with embedded fzf is the project — an external terminal window
would eliminate the need for PySide6 entirely and is a different product.

### Dependencies

- Phase 2 (application list)

### Estimated issues

- PySide6 window and lifecycle (1 issue)
- Terminal widget / fzf hosting (1–2 issues, depending on spike outcome)
- Application launch dispatch (1 issue)

---

## Phase 4: Additional Target Types

**Goal:** Extend discovery and launch to support scripts, directories, and
custom entries.

### Deliverables

- **Script discovery:**
  - New config section: `paths.scripts`
  - Scan configured paths for executable files
  - Respect `$PATH` ordering for deduplication
  - Skip non-executable files, hidden files
- **Directory targets:**
  - New config section: `paths.directories`
  - Read configured directory list
  - Validate paths exist; warn (don't fail) for missing paths
  - Launch via `open` (Finder)
- **Custom entries:**
  - New config section: `custom` (label → command mappings)
  - No discovery needed — user specifies label and command
  - Launch via shell execution
- **Unified target list:**
  - Category prefixes in fzf: `[app]`, `[script]`, `[dir]`, `[custom]`
  - Sorting: custom first, then apps, scripts, directories
- **Preview pane:**
  - Apps: name, version, bundle ID from Info.plist
  - Scripts: shebang + ABOUTME comment
  - Directories: `ls` summary
  - Custom: the command that will run
- **Launch dispatch generalisation:**
  - `launch.py` dispatch table covers all target types
  - Commands constructed as lists (never strings) for all types

### Dependencies

- Phase 3 (working MVP)

### Estimated issues

- Script and directory discovery (1 issue)
- Custom entries and unified formatting (1 issue)
- Preview pane (1 issue)
- Launch dispatch for all target types (1 issue)

---

## Phase 5: Global Hotkey & System Integration

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

- Phase 3 (working MVP); can be done in parallel with Phase 4

### Estimated issues

- Global hotkey (1 issue)
- Daemon mode and single-instance (1 issue)
- launchd integration (1 issue, optional)

---

## Phase 6: Polish & Distribution

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
- **Notarisation (if distributing .app bundles):**
  - Code signing, hardened runtime, notarytool submission
  - Deferred unless distribution scope expands beyond Homebrew

### Dependencies

- Phases 4 and 5

### Estimated issues

- Error handling and edge cases (1 issue)
- Performance profiling and optimisation (1 issue)
- Homebrew formula and release automation (1 issue)
- README and documentation (1 issue)

---

## Phase Summary

| Phase | Description | Scope | Issues (est.) | Depends on |
|-------|-------------|-------|---------------|------------|
| 1 | Scaffolding & configuration | **MVP** | 2 | — |
| 2 | Application discovery | **MVP** | 1 | Phase 1 |
| 3 | GUI shell & fzf integration | **MVP** | 3–4 | Phase 2 |
| 4 | Additional target types | Post-MVP | 4 | Phase 3 |
| 5 | Global hotkey & system integration | Post-MVP | 2–3 | Phase 3 |
| 6 | Polish & distribution | Post-MVP | 3–4 | Phases 4–5 |
| **Total** | | | **15–18** | |

**v0.1 MVP = Phases 1–3 (~6–7 issues)**

## Open Questions

These should be resolved during or before the relevant phase:

1. **Terminal widget approach** — embedded pty vs external terminal window?
   Spike in Phase 3 will determine this.
2. **Type checking** — mypy or pyright? Decide in Phase 1 based on PySide6
   stub quality.
3. **Caching** — is discovery fast enough without a cache? Measure in Phase 2.
4. **Target sorting** — alphabetical for MVP; frecency (recent + frequency)
   as a Phase 6 enhancement?

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-04-01 | Initial draft |
| 0.2 | 2026-04-01 | YAML config; apps-only MVP front-loaded as Phases 1–3; scripts/dirs/custom deferred to Phase 4; added Phase 6 |
