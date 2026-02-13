import pygame
import pygame_gui
import random
import copy

from pattern_db import PatternDatabase
from pattern_scanner import PatternScanner
from pattern_ui import PatternSidebar, ToastNotification

# --- Constants ---
ROWS, COLS = 50, 50
CELL_SIZE = 12
GRID_WIDTH = COLS * CELL_SIZE
GRID_HEIGHT = ROWS * CELL_SIZE

STATS_HEIGHT = 36
CONTROLS_HEIGHT = 100
SIDEBAR_WIDTH = 200
WINDOW_WIDTH = GRID_WIDTH + SIDEBAR_WIDTH
WINDOW_HEIGHT = STATS_HEIGHT + GRID_HEIGHT + CONTROLS_HEIGHT

BG_COLOR = (10, 10, 10)
DEAD_COLOR = (17, 17, 17)
GRID_LINE_COLOR = (26, 26, 26)
STATS_BG = (15, 15, 15)
STATS_TEXT_COLOR = (180, 180, 180)

# Age-based color gradient for alive cells (young -> old)
# Bright green -> cyan -> blue -> purple -> magenta
ALIVE_COLORS = [
    (57, 255, 20),    # age 0: neon green (just born)
    (0, 230, 118),    # age 1: emerald
    (0, 200, 200),    # age 2: teal
    (0, 180, 255),    # age 3: sky blue
    (80, 140, 255),   # age 4: cornflower
    (120, 100, 255),  # age 5: indigo
    (170, 70, 255),   # age 6: violet
    (210, 50, 210),   # age 7: magenta
    (255, 50, 150),   # age 8: hot pink
    (255, 80, 80),    # age 9+: warm red (elder)
]
MAX_AGE = len(ALIVE_COLORS) - 1

# Fading trail colors for recently dead cells
TRAIL_COLORS = [
    (50, 30, 15),     # just died: warm ember
    (35, 20, 12),
    (25, 14, 10),
    (20, 11, 9),
]
TRAIL_LENGTH = len(TRAIL_COLORS)

DEFAULT_SPEED_MS = 100


# --- Game Logic ---
def make_grid():
    return [[0] * COLS for _ in range(ROWS)]


def make_age_grid():
    return [[0] * COLS for _ in range(ROWS)]


def make_trail_grid():
    """Trail grid stores countdown: 0 = no trail, TRAIL_LENGTH..1 = fading."""
    return [[0] * COLS for _ in range(ROWS)]


def count_neighbors(grid, r, c):
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                count += grid[nr][nc]
    return count


def next_generation(grid, age_grid, trail_grid):
    new = make_grid()
    new_age = make_age_grid()
    for r in range(ROWS):
        for c in range(COLS):
            n = count_neighbors(grid, r, c)
            if grid[r][c]:
                alive = n in (2, 3)
                new[r][c] = 1 if alive else 0
                if alive:
                    new_age[r][c] = min(age_grid[r][c] + 1, MAX_AGE)
                else:
                    trail_grid[r][c] = TRAIL_LENGTH  # start fade
            else:
                born = n == 3
                new[r][c] = 1 if born else 0
                new_age[r][c] = 0
                # Decay trails for dead cells
                if not born and trail_grid[r][c] > 0:
                    trail_grid[r][c] -= 1
    return new, new_age


def population(grid):
    return sum(cell for row in grid for cell in row)


def randomize_grid(grid, age_grid):
    for r in range(ROWS):
        for c in range(COLS):
            grid[r][c] = 1 if random.random() < 0.3 else 0
            age_grid[r][c] = 0


# --- Presets ---
PRESETS = {
    "Glider": {
        "offset": (2, 2),
        "cells": [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
    },
    "Blinker": {
        "offset": (23, 24),
        "cells": [(0, 0), (0, 1), (0, 2)],
    },
    "Toad": {
        "offset": (23, 23),
        "cells": [(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2)],
    },
    "Beacon": {
        "offset": (22, 23),
        "cells": [
            (0, 0), (0, 1), (1, 0), (1, 1),
            (2, 2), (2, 3), (3, 2), (3, 3),
        ],
    },
    "Pulsar": {
        "offset": (18, 18),
        "cells": [
            (0, 2), (0, 3), (0, 4), (0, 8), (0, 9), (0, 10),
            (2, 0), (2, 5), (2, 7), (2, 12),
            (3, 0), (3, 5), (3, 7), (3, 12),
            (4, 0), (4, 5), (4, 7), (4, 12),
            (5, 2), (5, 3), (5, 4), (5, 8), (5, 9), (5, 10),
            (7, 2), (7, 3), (7, 4), (7, 8), (7, 9), (7, 10),
            (8, 0), (8, 5), (8, 7), (8, 12),
            (9, 0), (9, 5), (9, 7), (9, 12),
            (10, 0), (10, 5), (10, 7), (10, 12),
            (12, 2), (12, 3), (12, 4), (12, 8), (12, 9), (12, 10),
        ],
    },
    "Gosper Gun": {
        "offset": (10, 1),
        "cells": [
            (0, 24),
            (1, 22), (1, 24),
            (2, 12), (2, 13), (2, 20), (2, 21), (2, 34), (2, 35),
            (3, 11), (3, 15), (3, 20), (3, 21), (3, 34), (3, 35),
            (4, 0), (4, 1), (4, 10), (4, 16), (4, 20), (4, 21),
            (5, 0), (5, 1), (5, 10), (5, 14), (5, 16), (5, 17), (5, 22), (5, 24),
            (6, 10), (6, 16), (6, 24),
            (7, 11), (7, 15),
            (8, 12), (8, 13),
        ],
    },
}


def load_preset(name):
    grid = make_grid()
    preset = PRESETS[name]
    or_, oc = preset["offset"]
    for dr, dc in preset["cells"]:
        r, c = or_ + dr, oc + dc
        if 0 <= r < ROWS and 0 <= c < COLS:
            grid[r][c] = 1
    return grid


# --- Main Application ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Conway's Game of Life")
    clock = pygame.time.Clock()

    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))

    # State
    grid = make_grid()
    age_grid = make_age_grid()
    trail_grid = make_trail_grid()
    generation = 0
    running = False
    speed_ms = DEFAULT_SPEED_MS
    last_step_time = pygame.time.get_ticks()
    is_dragging = False
    drag_value = 0

    # Pattern recognition
    pattern_db = PatternDatabase()
    scanner = PatternScanner(pattern_db)
    sidebar = PatternSidebar(GRID_WIDTH, 0, SIDEBAR_WIDTH, STATS_HEIGHT + GRID_HEIGHT)
    toasts = ToastNotification(GRID_WIDTH + 4, STATS_HEIGHT + 10, STATS_HEIGHT + GRID_HEIGHT)

    def do_scan():
        new = scanner.scan(grid, generation)
        now_t = pygame.time.get_ticks()
        for name in new:
            toasts.add(name, now_t)

    # --- UI Controls ---
    ctrl_y = STATS_HEIGHT + GRID_HEIGHT + 8
    btn_h = 30
    btn_w = 68
    gap = 6

    # Row 1: main controls + speed slider
    x = gap
    btn_start = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(x, ctrl_y, btn_w, btn_h),
        text="Start", manager=manager,
    )
    x += btn_w + gap
    btn_step = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(x, ctrl_y, btn_w, btn_h),
        text="Step", manager=manager,
    )
    x += btn_w + gap
    btn_clear = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(x, ctrl_y, btn_w, btn_h),
        text="Clear", manager=manager,
    )
    x += btn_w + gap
    btn_random = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(x, ctrl_y, btn_w, btn_h),
        text="Random", manager=manager,
    )
    x += btn_w + gap + 10

    # Speed slider
    slider_w = WINDOW_WIDTH - x - gap
    if slider_w < 80:
        slider_w = 80
    speed_slider = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect(x, ctrl_y, slider_w, btn_h),
        start_value=speed_ms,
        value_range=(10, 500),
        manager=manager,
    )

    # Row 2: preset buttons
    row2_y = ctrl_y + btn_h + gap
    preset_buttons = {}
    px = gap
    for name in PRESETS:
        pw = max(btn_w, len(name) * 9 + 12)
        preset_buttons[name] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px, row2_y, pw, btn_h),
            text=name, manager=manager,
        )
        px += pw + gap

    # Stats font
    stats_font = pygame.font.SysFont("monospace", 15)

    # --- Helpers ---
    def grid_pos_from_mouse(mx, my):
        gy = my - STATS_HEIGHT
        if 0 <= mx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT:
            return gy // CELL_SIZE, mx // CELL_SIZE
        return None, None

    def draw():
        screen.fill(BG_COLOR)

        # Draw cells
        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c]:
                    color = ALIVE_COLORS[age_grid[r][c]]
                elif trail_grid[r][c] > 0:
                    idx = TRAIL_LENGTH - trail_grid[r][c]
                    color = TRAIL_COLORS[idx]
                else:
                    color = DEAD_COLOR
                rect = pygame.Rect(
                    c * CELL_SIZE, STATS_HEIGHT + r * CELL_SIZE,
                    CELL_SIZE, CELL_SIZE,
                )
                pygame.draw.rect(screen, color, rect)

        # Grid lines
        for r in range(ROWS + 1):
            y = STATS_HEIGHT + r * CELL_SIZE
            pygame.draw.line(screen, GRID_LINE_COLOR, (0, y), (GRID_WIDTH, y))
        for c in range(COLS + 1):
            x = c * CELL_SIZE
            pygame.draw.line(screen, GRID_LINE_COLOR, (x, STATS_HEIGHT), (x, STATS_HEIGHT + GRID_HEIGHT))

        # Stats bar
        pygame.draw.rect(screen, STATS_BG, (0, 0, WINDOW_WIDTH, STATS_HEIGHT))
        gen_surf = stats_font.render(f"Gen: {generation}", True, (100, 200, 255))
        pop_surf = stats_font.render(f"Pop: {population(grid)}", True, (0, 230, 118))
        status_color = (57, 255, 20) if running else (255, 160, 50)
        status_surf = stats_font.render("Running" if running else "Paused", True, status_color)
        sx = 8
        screen.blit(gen_surf, (sx, 10))
        sx += gen_surf.get_width() + 20
        screen.blit(pop_surf, (sx, 10))
        sx += pop_surf.get_width() + 20
        screen.blit(status_surf, (sx, 10))

        # Pattern sidebar and toasts
        now_t = pygame.time.get_ticks()
        sidebar.draw(screen, scanner.discovered, now_t)
        toasts.draw(screen, now_t)

    # --- Main Loop ---
    running_app = True
    while running_app:
        dt = clock.tick(60) / 1000.0
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_app = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    running = not running
                    btn_start.set_text("Pause" if running else "Start")
                elif event.key == pygame.K_n:
                    grid, age_grid = next_generation(grid, age_grid, trail_grid)
                    generation += 1
                    do_scan()
                elif event.key == pygame.K_c:
                    grid = make_grid()
                    age_grid = make_age_grid()
                    trail_grid = make_trail_grid()
                    generation = 0
                    running = False
                    btn_start.set_text("Start")
                    scanner.reset()
                elif event.key == pygame.K_r:
                    grid = make_grid()
                    age_grid = make_age_grid()
                    trail_grid = make_trail_grid()
                    randomize_grid(grid, age_grid)
                    generation = 0
                    scanner.reset()
                    do_scan()

            # Mouse drawing on grid (when paused)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                r, c = grid_pos_from_mouse(*event.pos)
                if r is not None and not running:
                    is_dragging = True
                    drag_value = 0 if grid[r][c] else 1
                    grid[r][c] = drag_value

            if event.type == pygame.MOUSEMOTION and is_dragging and not running:
                r, c = grid_pos_from_mouse(*event.pos)
                if r is not None:
                    grid[r][c] = drag_value

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                is_dragging = False

            # pygame_gui events
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == btn_start:
                    running = not running
                    btn_start.set_text("Pause" if running else "Start")
                elif event.ui_element == btn_step:
                    grid, age_grid = next_generation(grid, age_grid, trail_grid)
                    generation += 1
                    do_scan()
                elif event.ui_element == btn_clear:
                    grid = make_grid()
                    age_grid = make_age_grid()
                    trail_grid = make_trail_grid()
                    generation = 0
                    running = False
                    btn_start.set_text("Start")
                    scanner.reset()
                elif event.ui_element == btn_random:
                    grid = make_grid()
                    age_grid = make_age_grid()
                    trail_grid = make_trail_grid()
                    randomize_grid(grid, age_grid)
                    generation = 0
                    scanner.reset()
                    do_scan()
                else:
                    for name, btn in preset_buttons.items():
                        if event.ui_element == btn:
                            grid = load_preset(name)
                            age_grid = make_age_grid()
                            trail_grid = make_trail_grid()
                            generation = 0
                            running = False
                            btn_start.set_text("Start")
                            scanner.reset()
                            do_scan()
                            break

            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == speed_slider:
                    speed_ms = int(event.value)

            manager.process_events(event)

        manager.update(dt)

        # Simulation step
        if running and now - last_step_time >= speed_ms:
            grid, age_grid = next_generation(grid, age_grid, trail_grid)
            generation += 1
            last_step_time = now
            do_scan()

        draw()
        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
