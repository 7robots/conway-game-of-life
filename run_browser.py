"""Modal overlay for browsing saved runs and viewing pattern statistics."""

import pygame

# Colors
OVERLAY_COLOR = (0, 0, 0, 160)
PANEL_BG = (24, 24, 32)
PANEL_BORDER = (80, 160, 255)
HEADER_COLOR = (100, 200, 255)
TEXT_COLOR = (180, 180, 190)
DIM_TEXT = (120, 120, 130)
SELECTED_BG = (40, 60, 90)
HOVER_BG = (30, 35, 50)
BTN_BG = (50, 70, 120)
BTN_HOVER = (70, 90, 150)
BTN_TEXT = (220, 220, 230)
BTN_DELETE_BG = (120, 40, 40)
BTN_DELETE_HOVER = (160, 50, 50)
DIVIDER_COLOR = (50, 50, 65)
STAT_NAME_COLOR = (160, 200, 160)
STAT_COUNT_COLOR = (200, 180, 100)
STAT_HOVER_BG = (30, 40, 30)
CLOSE_COLOR = (200, 200, 200)
SCROLLBAR_COLOR = (60, 60, 75)
SCROLLBAR_THUMB = (100, 100, 120)

LINE_H = 22
HEADER_H = 32
PADDING = 12
SCROLLBAR_W = 6


class RunBrowser:
    """Modal overlay for browsing saved game runs."""

    def __init__(self, screen_width, screen_height, db):
        self.db = db
        self.open = True
        self._load_to_run_id = None  # set when user clicks Load
        self._clicked_pattern = None  # set when user clicks a pattern stat

        # Layout: centered panel taking 80% of screen
        margin_x = screen_width // 10
        margin_y = screen_height // 10
        self.panel_rect = pygame.Rect(
            margin_x, margin_y,
            screen_width - 2 * margin_x,
            screen_height - 2 * margin_y,
        )

        # Fonts
        self.title_font = pygame.font.SysFont("monospace", 16, bold=True)
        self.font = pygame.font.SysFont("monospace", 12)
        self.small_font = pygame.font.SysFont("monospace", 11)
        self.close_font = pygame.font.SysFont("monospace", 18, bold=True)

        # State
        self.runs = []
        self.pattern_stats = []
        self.selected_idx = -1
        self.scroll_offset = 0
        self.stats_scroll_offset = 0
        self._btn_rects = {}  # "load", "delete" -> Rect
        self._close_rect = None
        self._item_rects = []  # list of (idx, Rect) for run list
        self._stat_item_rects = []  # list of (pattern_name, Rect) for stats

        self.refresh()

    def refresh(self):
        self.runs = self.db.list_runs()
        self.pattern_stats = self.db.get_pattern_stats()
        if self.selected_idx >= len(self.runs):
            self.selected_idx = len(self.runs) - 1

    def get_load_request(self):
        """Return run_id to load and clear it, or None."""
        rid = self._load_to_run_id
        self._load_to_run_id = None
        return rid

    def get_pattern_click(self):
        """Return clicked pattern name and clear it, or None."""
        name = self._clicked_pattern
        self._clicked_pattern = None
        return name

    def _left_panel_rect(self):
        """Left half: run list."""
        r = self.panel_rect
        half_w = (r.width - PADDING) // 2
        return pygame.Rect(r.left + PADDING, r.top + HEADER_H + PADDING, half_w - PADDING, r.height - HEADER_H - PADDING * 2)

    def _right_panel_rect(self):
        """Right half: details + stats."""
        r = self.panel_rect
        half_w = (r.width - PADDING) // 2
        right_x = r.left + half_w + PADDING
        return pygame.Rect(right_x, r.top + HEADER_H + PADDING, half_w - PADDING, r.height - HEADER_H - PADDING * 2)

    def _max_scroll(self, count, panel_height):
        content = count * LINE_H
        return max(0, content - panel_height)

    def _stats_area_rect(self):
        """Return the scrollable area for pattern stats (cached from last draw)."""
        return getattr(self, '_cached_stats_area', None)

    def handle_event(self, event):
        """Process events. Returns True if browser consumed the event."""
        if not self.open:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.open = False
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Close button
            if self._close_rect and self._close_rect.collidepoint(pos):
                self.open = False
                return True

            # Outside panel closes
            if not self.panel_rect.collidepoint(pos):
                self.open = False
                return True

            # Run list items
            for idx, rect in self._item_rects:
                if rect.collidepoint(pos):
                    self.selected_idx = idx
                    return True

            # Pattern stat items
            for name, rect in self._stat_item_rects:
                if rect.collidepoint(pos):
                    self._clicked_pattern = name
                    return True

            # Load button
            if "load" in self._btn_rects and self._btn_rects["load"].collidepoint(pos):
                if 0 <= self.selected_idx < len(self.runs):
                    self._load_to_run_id = self.runs[self.selected_idx]["run_id"]
                    self.open = False
                return True

            # Delete button
            if "delete" in self._btn_rects and self._btn_rects["delete"].collidepoint(pos):
                if 0 <= self.selected_idx < len(self.runs):
                    run_id = self.runs[self.selected_idx]["run_id"]
                    self.db.delete_run(run_id)
                    self.refresh()
                return True

            return True

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            left = self._left_panel_rect()

            if left.collidepoint(mx, my):
                self.scroll_offset -= event.y * LINE_H * 2
                self.scroll_offset = max(0, min(self.scroll_offset, self._max_scroll(len(self.runs), left.height)))
                return True

            stats_area = self._stats_area_rect()
            if stats_area and stats_area.collidepoint(mx, my):
                self.stats_scroll_offset -= event.y * LINE_H * 2
                self.stats_scroll_offset = max(0, min(self.stats_scroll_offset, self._max_scroll(len(self.pattern_stats), stats_area.height)))
                return True

        return self.panel_rect.collidepoint(*pygame.mouse.get_pos())

    def draw(self, screen):
        if not self.open:
            return

        sw, sh = screen.get_size()

        # Overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        screen.blit(overlay, (0, 0))

        # Panel background
        pygame.draw.rect(screen, PANEL_BG, self.panel_rect, border_radius=8)
        pygame.draw.rect(screen, PANEL_BORDER, self.panel_rect, 2, border_radius=8)

        # Title
        title = self.title_font.render("Saved Runs", True, HEADER_COLOR)
        screen.blit(title, (self.panel_rect.left + PADDING, self.panel_rect.top + 8))

        # Close button
        close_text = self.close_font.render("X", True, CLOSE_COLOR)
        cx = self.panel_rect.right - 28
        cy = self.panel_rect.top + 8
        self._close_rect = pygame.Rect(cx - 4, cy - 2, close_text.get_width() + 8, close_text.get_height() + 4)
        screen.blit(close_text, (cx, cy))

        left = self._left_panel_rect()
        right = self._right_panel_rect()

        # Divider
        div_x = (left.right + right.left) // 2
        pygame.draw.line(screen, DIVIDER_COLOR, (div_x, self.panel_rect.top + HEADER_H), (div_x, self.panel_rect.bottom - PADDING))

        self._draw_run_list(screen, left)
        self._draw_details(screen, right)

    def _draw_scrollbar(self, screen, area, count, scroll_offset):
        """Draw a scrollbar if content overflows."""
        content_h = count * LINE_H
        if content_h <= area.height:
            return
        sb_x = area.right - SCROLLBAR_W - 1
        pygame.draw.rect(screen, SCROLLBAR_COLOR, (sb_x, area.top, SCROLLBAR_W, area.height), border_radius=2)
        thumb_ratio = area.height / content_h
        thumb_h = max(16, int(area.height * thumb_ratio))
        max_s = self._max_scroll(count, area.height)
        scroll_ratio = scroll_offset / max_s if max_s > 0 else 0
        thumb_y = area.top + int(scroll_ratio * (area.height - thumb_h))
        pygame.draw.rect(screen, SCROLLBAR_THUMB, (sb_x, thumb_y, SCROLLBAR_W, thumb_h), border_radius=2)

    def _draw_run_list(self, screen, area):
        """Draw scrollable list of runs in the left panel."""
        mx, my = pygame.mouse.get_pos()
        self._item_rects = []

        if not self.runs:
            msg = self.font.render("No saved runs yet.", True, DIM_TEXT)
            screen.blit(msg, (area.left + 8, area.top + 8))
            return

        screen.set_clip(area)
        for i, run in enumerate(self.runs):
            item_y = area.top + i * LINE_H - self.scroll_offset
            if item_y + LINE_H < area.top or item_y > area.bottom:
                continue

            item_rect = pygame.Rect(area.left, item_y, area.width - SCROLLBAR_W - 2, LINE_H)
            self._item_rects.append((i, item_rect))

            # Background: selected or hover
            if i == self.selected_idx:
                pygame.draw.rect(screen, SELECTED_BG, item_rect)
            elif item_rect.collidepoint(mx, my):
                pygame.draw.rect(screen, HOVER_BG, item_rect)

            # Run name + metadata
            name = run["name"]
            if len(name) > 24:
                name = name[:22] + ".."
            gen = run["final_generation"]
            pcount = run["pattern_count"]
            text = f"{name}  (gen {gen}, {pcount}p)"
            surf = self.font.render(text, True, TEXT_COLOR)
            screen.blit(surf, (area.left + 6, item_y + 3))

        screen.set_clip(None)
        self._draw_scrollbar(screen, area, len(self.runs), self.scroll_offset)

    def _draw_details(self, screen, area):
        """Draw run details and pattern stats in the right panel."""
        y = area.top

        if 0 <= self.selected_idx < len(self.runs):
            run = self.runs[self.selected_idx]
            self._draw_run_detail(screen, area, run, y)
        else:
            msg = self.font.render("Select a run to view details.", True, DIM_TEXT)
            screen.blit(msg, (area.left + 8, y + 8))

        # Pattern stats section at bottom
        stats_y = area.top + area.height // 2
        pygame.draw.line(screen, DIVIDER_COLOR, (area.left, stats_y), (area.right, stats_y))
        stats_y += 6

        header = self.title_font.render("Pattern Stats (All Time)", True, HEADER_COLOR)
        screen.blit(header, (area.left + 6, stats_y))
        stats_y += 24

        stats_area = pygame.Rect(area.left, stats_y, area.width, area.bottom - stats_y)
        self._cached_stats_area = stats_area
        self._draw_pattern_stats(screen, stats_area)

    def _draw_run_detail(self, screen, area, run, y):
        """Draw details for the selected run with action buttons."""
        # Name
        name_surf = self.title_font.render(run["name"], True, TEXT_COLOR)
        screen.blit(name_surf, (area.left + 6, y + 4))
        y += 26

        # Metadata
        created = run["created_at"][:16].replace("T", " ")
        for label, val in [("Date", created), ("Generation", run["final_generation"]),
                           ("Speed", f"{run['speed_ms']}ms"), ("Patterns", run["pattern_count"])]:
            surf = self.small_font.render(f"{label}: {val}", True, DIM_TEXT)
            screen.blit(surf, (area.left + 6, y))
            y += 16

        y += 8

        # Buttons
        mx, my = pygame.mouse.get_pos()
        btn_w, btn_h = 70, 26

        # Load button
        load_rect = pygame.Rect(area.left + 6, y, btn_w, btn_h)
        self._btn_rects["load"] = load_rect
        hover = load_rect.collidepoint(mx, my)
        pygame.draw.rect(screen, BTN_HOVER if hover else BTN_BG, load_rect, border_radius=4)
        load_text = self.font.render("Load", True, BTN_TEXT)
        screen.blit(load_text, (load_rect.x + (btn_w - load_text.get_width()) // 2, load_rect.y + 5))

        # Delete button
        del_rect = pygame.Rect(area.left + 6 + btn_w + 8, y, btn_w, btn_h)
        self._btn_rects["delete"] = del_rect
        hover = del_rect.collidepoint(mx, my)
        pygame.draw.rect(screen, BTN_DELETE_HOVER if hover else BTN_DELETE_BG, del_rect, border_radius=4)
        del_text = self.font.render("Delete", True, BTN_TEXT)
        screen.blit(del_text, (del_rect.x + (btn_w - del_text.get_width()) // 2, del_rect.y + 5))

    def _draw_pattern_stats(self, screen, area):
        """Draw scrollable, clickable pattern statistics."""
        self._stat_item_rects = []

        if not self.pattern_stats:
            msg = self.small_font.render("No patterns discovered yet.", True, DIM_TEXT)
            screen.blit(msg, (area.left + 6, area.top + 4))
            return

        mx, my = pygame.mouse.get_pos()
        self.stats_scroll_offset = max(0, min(self.stats_scroll_offset, self._max_scroll(len(self.pattern_stats), area.height)))

        screen.set_clip(area)
        for i, stat in enumerate(self.pattern_stats):
            item_y = area.top + i * LINE_H - self.stats_scroll_offset
            if item_y + LINE_H < area.top or item_y > area.bottom:
                continue

            full_name = stat["pattern_name"]
            item_rect = pygame.Rect(area.left, item_y, area.width - SCROLLBAR_W - 2, LINE_H)
            self._stat_item_rects.append((full_name, item_rect))

            # Hover highlight
            if item_rect.collidepoint(mx, my):
                pygame.draw.rect(screen, STAT_HOVER_BG, item_rect)

            display_name = full_name if len(full_name) <= 18 else full_name[:16] + ".."
            count = stat["times_discovered"]
            runs = stat["runs_appeared_in"]

            name_surf = self.small_font.render(display_name, True, STAT_NAME_COLOR)
            count_surf = self.small_font.render(f"x{count} ({runs}r)", True, STAT_COUNT_COLOR)
            screen.blit(name_surf, (area.left + 6, item_y + 3))
            screen.blit(count_surf, (area.right - count_surf.get_width() - SCROLLBAR_W - 6, item_y + 3))

        screen.set_clip(None)
        self._draw_scrollbar(screen, area, len(self.pattern_stats), self.stats_scroll_offset)
