SHELL := /bin/sh

PROJECT_NAME := taskcli
PIPX_STATE_DIR ?= /tmp/taskcli-xdg-state

.PHONY: help install reinstall uninstall clean

help:
	@echo "Targets:"
	@echo "  make install      Install this checkout with pipx (editable)"
	@echo "  make reinstall    Reinstall this checkout with pipx (editable, --force)"
	@echo "  make uninstall    Uninstall pipx package '${PROJECT_NAME}'"
	@echo "  make clean        Remove local build artifacts (build/, dist/, *.egg-info)"

install:
	@command -v pipx >/dev/null 2>&1 || (echo "ERROR: pipx not found. Install pipx first." && exit 1)
	@XDG_STATE_HOME="$(PIPX_STATE_DIR)" pipx install --editable .
	@$(MAKE) clean

reinstall:
	@command -v pipx >/dev/null 2>&1 || (echo "ERROR: pipx not found. Install pipx first." && exit 1)
	@XDG_STATE_HOME="$(PIPX_STATE_DIR)" pipx install --force --editable .
	@$(MAKE) clean

uninstall:
	@command -v pipx >/dev/null 2>&1 || (echo "ERROR: pipx not found. Install pipx first." && exit 1)
	@cd "$$HOME" && XDG_STATE_HOME="$(PIPX_STATE_DIR)" pipx uninstall $(PROJECT_NAME)

clean:
	@rm -rf build dist *.egg-info
