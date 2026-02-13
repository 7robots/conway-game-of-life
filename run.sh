#!/usr/bin/env bash
cd "$(dirname "$0")"
uv sync --quiet
uv run python conway.py
