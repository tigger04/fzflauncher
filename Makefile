# ABOUTME: Build system for fzfLAUNCHER.
# ABOUTME: Provides standard targets: install, uninstall, test, lint, fmt, release, sync.

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
SYMLINK := $(HOME)/.local/bin/fzflauncher
FONTS_DIR := resources/fonts
IOSEVKA_REPO ?= $(HOME)/tfont/Iosevka

.PHONY: init build install uninstall test test-manual test-one-off build-fonts lint fmt release sync clean help

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

test-manual: build
	PYTHONPATH=src $(PYTHON) -m fzflauncher

test-one-off: $(VENV)
ifdef ISSUE
	$(PYTEST) tests/one_off/ -v -k "$(ISSUE)"
else
	$(PYTEST) tests/one_off/ -v
endif

build-fonts:
	@if [ ! -d "$(IOSEVKA_REPO)" ]; then \
		echo "Iosevka repo not found at $(IOSEVKA_REPO)"; \
		echo "Clone it with: git clone https://github.com/be5invis/Iosevka $(IOSEVKA_REPO)"; \
		exit 1; \
	fi
	cp "$(FONTS_DIR)/private-build-plans.toml" "$(IOSEVKA_REPO)/"
	cd "$(IOSEVKA_REPO)" && npm install -q && npm run build -- contents::FzfiraCode
	cp "$(IOSEVKA_REPO)/dist/FzfiraCode/TTF/"*.ttf "$(FONTS_DIR)/"
	@echo "Fzfira Code TTFs built in $(FONTS_DIR)/"

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
	@echo "  test-manual   Launch window for manual UT verification (UT-4.1-4.4)"
	@echo "  test-one-off  Run one-off tests (ISSUE=N to filter)"
	@echo "  build-fonts   Build Fzfira Code TTFs (requires Iosevka repo at IOSEVKA_REPO)"
	@echo "  lint          Check code with ruff"
	@echo "  fmt           Format code with ruff"
	@echo "  clean         Remove venv and build artifacts"
	@echo "  release       Tag a release (not yet configured)"
	@echo "  sync          Git add, commit, pull, push"
	@echo "  help          Show this help"
