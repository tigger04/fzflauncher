# ABOUTME: Build system for fzfLAUNCHER.
# ABOUTME: Provides standard targets: install, uninstall, test, lint, fmt, release, sync.

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
SYMLINK := $(HOME)/.local/bin/fzflauncher

.PHONY: init build install uninstall test test-one-off lint fmt release sync clean help

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip -q

init:
	cp hooks/* .git/hooks/

build: $(VENV) init
	$(PIP) install -r requirements.txt -q

install: build
	@mkdir -p "$(HOME)/.local/bin"
	@ln -sf "$(CURDIR)/bin/fzflauncher" "$(SYMLINK)"
	@echo "Installed: $(SYMLINK) -> $(CURDIR)/bin/fzflauncher"

uninstall:
	@if [ -L "$(SYMLINK)" ]; then \
		rm -f "$(SYMLINK)"; \
		echo "Removed: $(SYMLINK)"; \
	else \
		echo "No symlink found at $(SYMLINK)"; \
	fi

test: $(VENV)
	$(PYTEST) tests/regression/ -v

test-one-off: $(VENV)
ifdef ISSUE
	$(PYTEST) tests/one_off/ -v -k "$(ISSUE)"
else
	$(PYTEST) tests/one_off/ -v
endif

lint: $(VENV)
	$(RUFF) check src/ tests/

fmt: $(VENV)
	$(RUFF) format src/ tests/

clean:
	trash -- $(VENV) build/ dist/ *.egg-info 2>/dev/null; true
	find . -type d -name __pycache__ -print0 | xargs -0 trash -- 2>/dev/null; true

release:
	@echo "Release not yet configured"

sync:
	git add --all
	git commit -m "sync" || true
	git pull
	git push

help:
	@echo "Targets:"
	@echo "  init          Copy project hooks into .git/hooks/"
	@echo "  install       Install dependencies, hooks, and symlink to ~/.local/bin"
	@echo "  uninstall     Remove symlink from ~/.local/bin"
	@echo "  test          Run regression tests"
	@echo "  test-one-off  Run one-off tests (ISSUE=N to filter)"
	@echo "  lint          Check code with ruff"
	@echo "  fmt           Format code with ruff"
	@echo "  clean         Remove venv and build artifacts"
	@echo "  release       Tag a release (not yet configured)"
	@echo "  sync          Git add, commit, pull, push"
	@echo "  help          Show this help"
