# CLAUDE.md

## Project Overview

Conway's Game of Life implementation with Pygame, featuring visual enhancements (age coloring, death trails) and automatic pattern recognition from the LifeWiki database.

## Quick Start

```bash
uv sync
uv run python conway.py
```

## Tooling

- **Package manager**: uv (not pip)
- **Dependencies**: pygame, pygame-gui (see pyproject.toml)
- **Python**: 3.13+

## Architecture

### Core files

- `conway.py` -- Main application. Contains grid logic (`make_grid`, `next_generation`, `count_neighbors`), presets, UI controls (pygame_gui buttons/slider), and the game loop. All state is local to `main()`.
- `pattern_db.py` -- Parses `.cells` files, computes SHA-256 hashes for all 8 orientations of each pattern, builds `hash_to_name` lookup dict. `PatternDatabase` class loads on init.
- `pattern_scanner.py` -- `PatternScanner.scan()` runs BFS flood fill (8-connectivity) to extract connected components, normalizes each to origin, hashes, and does dict lookup. Tracks `discovered: dict[name, generation]`.
- `pattern_ui.py` -- `PatternSidebar` renders right-side scrollable discovery panel with mouse wheel support and scrollbar. `PatternPopup` shows clickable pattern detail window with cell visualization and LifeWiki hyperlink. `ToastNotification` renders fade-in/out popups anchored to bottom of sidebar.
- `game_db.py` -- `GameDatabase` class wrapping sqlite3. Manages `runs`, `run_patterns`, and `pattern_stats` tables. Saves/loads game runs with starting grid snapshots and discovered patterns. Updates cumulative pattern statistics atomically. DB stored at `~/.local/share/conway-game-of-life/game_data.db` (XDG standard, respects `XDG_DATA_HOME`).
- `run_browser.py` -- `RunBrowser` modal overlay for browsing saved runs. Left panel: scrollable run list. Right panel: run details with Load/Delete buttons and scrollable cumulative pattern stats (clickable -- opens `PatternPopup`). Drawn on top of the game when open.

### Key constants (conway.py)

- Grid: 50x50 cells, 12px each
- `SIDEBAR_WIDTH = 200` -- added to window width for pattern sidebar
- `STATS_HEIGHT = 36`, `CONTROLS_HEIGHT = 82`
- Speed range: 10-500ms per generation

### Pattern recognition flow

1. `PatternDatabase.__init__()` loads `patterns/*.cells` where bbox <= 10x10 (~914 patterns, ~4700 hashes)
2. `do_scan()` in `main()` calls `scanner.scan(grid, generation)` after every generation advance
3. Scanner uses BFS flood fill -> normalize -> hash -> O(1) dict lookup
4. New discoveries trigger `toasts.add()` for popup notifications
5. Scanner resets on Clear, Random, and Preset actions
6. Clicking a pattern name in the sidebar opens `PatternPopup` with cell visualization and LifeWiki link

### Persistence

- Runs and pattern stats stored in SQLite at `~/.local/share/conway-game-of-life/game_data.db`
- Respects `XDG_DATA_HOME` env var; directory created automatically on first run
- Starting grid snapshot captured on first generation advance, used for deterministic replay on load

### Data directory

- `patterns/` -- 3,557 `.cells` files + 4,968 `.rle` files from conwaylife.com. Only `.cells` with small bounding boxes are loaded.

## Conventions

- No external test framework; verify manually by running the game
- All game state lives in `main()` as local variables (no globals beyond constants)
- Pattern orientation matching covers all 4 rotations x 2 reflections
- Connected components that touch (8-neighbor adjacency) merge into one -- intentional to avoid false positive matches on overlapping patterns
