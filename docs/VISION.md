<!-- Version: 0.1 | Last updated: 2026-04-01 -->

# fzfLAUNCHER — Vision

## Purpose

fzfLAUNCHER is a keyboard-driven application launcher for macOS that embeds
[fzf](https://github.com/junegunn/fzf) inside a lightweight PySide6 window.
It provides the speed and familiarity of fzf's fuzzy matching in a floating GUI
that can be summoned with a global hotkey, used, and dismissed — all without
touching the mouse.

## Problem

macOS Spotlight is slow, opaque, and increasingly cluttered with web results
and suggestions. Alfred and Raycast are capable but heavyweight, closed-source,
and opinionated. For users who already live in the terminal, none of these tools
feel native to a keyboard-driven workflow.

What's missing is a launcher that:

- Starts instantly
- Uses a familiar, proven fuzzy-matching interface (fzf)
- Launches apps, scripts, and directories with equal ease
- Is configurable via plain text files
- Is open-source and hackable

## Goals

1. **Fast** — window appears and is usable within 200ms of invocation.
2. **Familiar** — if you know fzf, you know fzfLAUNCHER. Standard fzf
   keybindings and behaviour, no surprises.
3. **Focused** — it launches things. It does not manage clipboard, snippets,
   workflows, or plugins. Scope discipline is a feature.
4. **Configurable** — launch targets, display, keybindings, and fzf options
   are all user-configurable via a single config file.
5. **Scriptable** — every action the GUI performs can also be performed from
   the command line. The GUI is a convenience layer, not a requirement.
6. **Minimal dependencies** — Python 3.12+, PySide6, fzf. Nothing else.

## Non-Goals

- Cross-platform support (macOS only; Linux is a possible future stretch goal)
- Plugin/extension system
- Web search or calculator features
- Tray icon or menu bar presence
- Replacing a window manager or providing window management features

## Launch Targets

The launcher discovers and presents the following target types:

| Type | Source | Launch method |
|------|--------|---------------|
| Applications | `/Applications/`, `~/Applications/`, configurable paths | `open -a` |
| Scripts | User-configured directories (e.g. `~/.local/bin/`) | Direct execution |
| Directories | User-configured list | `open` (Finder) |
| Custom entries | Config file (label → command mappings) | Shell execution |

Future candidates (post-v1): bookmarks/URLs, SSH hosts, recent documents.

## User Experience

1. User presses global hotkey (e.g. `⌥Space`)
2. A borderless, floating, semi-transparent window appears centre-screen
3. fzf is running inside the window with all discovered targets listed
4. User types to fuzzy-filter, navigates with standard fzf keys
5. User presses Enter — the selected target launches, the window dismisses
6. Pressing Escape dismisses the window without action

The window has no title bar, no chrome, no menu. It appears and disappears.

## Technical Approach

- **Python 3.12+** — application logic, configuration, target discovery
- **PySide6** — GUI window, embedded pseudo-terminal, global hotkey
- **fzf** — fuzzy matching engine, run as a subprocess inside the terminal widget
- **Bash shim** — `bin/fzflauncher` entry point that manages venv activation

The application logic is cleanly separated from the GUI layer so that:
- Discovery and launch can be tested without a display
- The fzf interaction can be tested against a real fzf process
- A future alternative frontend (e.g. Hammerspoon, terminal-only) could reuse
  the same core

## Principles

- **CLI-first** — the GUI wraps the CLI, not the other way around
- **Plain text configuration** — no databases, no binary formats, no GUIs for settings
- **Fail fast, fail loud** — if fzf is missing, say so. Don't degrade silently
- **Respect the user's system** — never modify shell configs, launch agents, or
  system settings without explicit permission

## Success Criteria

fzfLAUNCHER is successful when:

- It can be installed with `make install` and invoked with a hotkey
- It launches an application faster than opening Spotlight and typing the same query
- It requires no mouse interaction for any workflow
- Its configuration can be version-controlled in a dotfiles repo

## Licence

MIT — Copyright Taḋg Paul
