# Dev convenience wrapper. Run `make` or `make help` for the target list.
# Override BUILDDIR=... to change the Meson build directory.

BUILDDIR    ?= _build
PREFIX      ?= $(HOME)/.local
FLATPAK_DIR ?= build-flatpak
MANIFEST    := pkgs/flatpak/io.github.jeffshee.Hidamari.json

.DEFAULT_GOAL := help

# --- Python dev environment (uv) --------------------------------------------

sync: ## Create/refresh the uv dev environment (uses system PyGObject)
	uv venv --system-site-packages
	uv sync

run: install ## Install into PREFIX and run it in debug mode (via the uv env)
	uv run python $(PREFIX)/bin/hidamari -d

lint: ## Lint the sources with ruff
	uv run ruff check src/

format: ## Auto-format the sources with ruff
	uv run ruff format src/

# --- Meson build ------------------------------------------------------------

$(BUILDDIR):
	meson setup --prefix=$(PREFIX) $(BUILDDIR)

build: $(BUILDDIR) ## Configure (if needed) and compile
	meson compile -C $(BUILDDIR)

install: $(BUILDDIR) ## Install into PREFIX (default ~/.local, no sudo)
	meson install -C $(BUILDDIR)

uninstall: $(BUILDDIR) ## Remove a previous install from PREFIX
	@test -f $(BUILDDIR)/meson-logs/install-log.txt || meson install -C $(BUILDDIR) >/dev/null
	ninja -C $(BUILDDIR) uninstall

# --- Translations (gettext, via Meson) --------------------------------------

pot: $(BUILDDIR) ## Regenerate po/hidamari.pot (with a filled-in header)
	meson compile -C $(BUILDDIR) hidamari-pot
	sed -i \
		-e "s/SOME DESCRIPTIVE TITLE\./Hidamari - Video wallpaper for Linux/" \
		-e "s/Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER/Copyright (C) 2022 Jeff Shee (jeffshee8969@gmail.com)/" \
		po/hidamari.pot

update-po: $(BUILDDIR) ## Merge the template into the per-language .po files
	meson compile -C $(BUILDDIR) hidamari-update-po

# --- Flatpak ----------------------------------------------------------------

pypi-deps: ## Regenerate pkgs/flatpak/pypi-deps.json from pyproject.toml
	./pkgs/flatpak/generate-pypi-deps.sh

flatpak: ## Build & install the Flatpak (pulls SDK/Platform from flathub)
	flatpak-builder --user --install --force-clean \
		--install-deps-from=flathub $(FLATPAK_DIR) $(MANIFEST)

# --- Housekeeping -----------------------------------------------------------

clean: ## Remove build directories and tool caches
	rm -rf $(BUILDDIR) $(FLATPAK_DIR) .flatpak-builder .ruff_cache

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.PHONY: sync run lint format build install uninstall pot update-po pypi-deps flatpak clean help
