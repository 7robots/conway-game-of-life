"""UI components for pattern recognition: sidebar, toast notifications, and pattern popup."""

import webbrowser

import pygame

from pattern_db import bounding_box


SIDEBAR_BG = (18, 18, 24)
SIDEBAR_HEADER_COLOR = (100, 200, 255)
SIDEBAR_TEXT_COLOR = (160, 160, 170)
SIDEBAR_HIGHLIGHT = (40, 180, 80)
SIDEBAR_DIVIDER = (40, 40, 50)
SIDEBAR_HOVER_BG = (30, 30, 40)
SCROLLBAR_COLOR = (60, 60, 75)
SCROLLBAR_THUMB = (100, 100, 120)

TOAST_BG = (30, 60, 30)
TOAST_BORDER = (60, 180, 60)
TOAST_TEXT = (180, 255, 180)

POPUP_OVERLAY = (0, 0, 0, 160)
POPUP_BG = (24, 24, 32)
POPUP_BORDER = (80, 160, 255)
POPUP_TITLE_COLOR = (100, 200, 255)
POPUP_CELL_COLOR = (57, 255, 20)
POPUP_CLOSE_COLOR = (200, 200, 200)
POPUP_LINK_COLOR = (100, 180, 255)
POPUP_LINK_HOVER = (150, 210, 255)

LINE_HEIGHT = 16
HEADER_HEIGHT = 28
SCROLLBAR_WIDTH = 6


class PatternSidebar:
    """Right-side panel listing discovered patterns with scrolling and click support."""

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = pygame.font.SysFont("monospace", 12)
        self.header_font = pygame.font.SysFont("monospace", 14, bold=True)
        self.scroll_offset = 0
        self._item_rects = []  # list of (name, pygame.Rect) for click detection

    def reset(self):
        self.scroll_offset = 0

    def _list_area(self):
        """Return the rect for the scrollable list area (below header)."""
        top = self.rect.top + HEADER_HEIGHT + 6
        return pygame.Rect(self.rect.left, top, self.rect.width, self.rect.bottom - top)

    def _content_height(self, count):
        return count * LINE_HEIGHT

    def _max_scroll(self, count):
        list_area = self._list_area()
        return max(0, self._content_height(count) - list_area.height)

    def handle_scroll(self, event, discovered):
        """Handle MOUSEWHEEL event. Call only when mouse is over sidebar."""
        if event.type != pygame.MOUSEWHEEL:
            return
        self.scroll_offset -= event.y * LINE_HEIGHT * 2
        self.scroll_offset = max(0, min(self.scroll_offset, self._max_scroll(len(discovered))))

    def handle_click(self, pos, discovered):
        """Check if a pattern name was clicked. Returns name or None."""
        for name, rect in self._item_rects:
            if rect.collidepoint(pos):
                return name
        return None

    def draw(self, screen, discovered, current_time):
        """Draw sidebar with scrollable pattern list."""
        pygame.draw.rect(screen, SIDEBAR_BG, self.rect)
        pygame.draw.line(screen, SIDEBAR_DIVIDER,
                         (self.rect.left, self.rect.top),
                         (self.rect.left, self.rect.bottom))

        x = self.rect.left + 8
        y = self.rect.top + 8

        # Header
        count = len(discovered)
        header = self.header_font.render(f"Discovered: {count}", True, SIDEBAR_HEADER_COLOR)
        screen.blit(header, (x, y))
        y += 22

        pygame.draw.line(screen, SIDEBAR_DIVIDER,
                         (self.rect.left + 4, y),
                         (self.rect.right - 4, y))

        # List area with clipping
        list_area = self._list_area()
        self.scroll_offset = max(0, min(self.scroll_offset, self._max_scroll(count)))

        sorted_patterns = sorted(discovered.items(), key=lambda kv: kv[1])
        content_h = self._content_height(count)

        # Get mouse position for hover highlight
        mx, my = pygame.mouse.get_pos()

        # Clip to list area
        screen.set_clip(list_area)
        self._item_rects = []

        for i, (name, gen) in enumerate(sorted_patterns):
            item_y = list_area.top + i * LINE_HEIGHT - self.scroll_offset
            if item_y + LINE_HEIGHT < list_area.top or item_y > list_area.bottom:
                continue

            item_rect = pygame.Rect(self.rect.left, item_y, self.rect.width - SCROLLBAR_WIDTH - 2, LINE_HEIGHT)
            self._item_rects.append((name, item_rect))

            # Hover highlight
            if item_rect.collidepoint(mx, my):
                pygame.draw.rect(screen, SIDEBAR_HOVER_BG, item_rect)

            display = name if len(name) <= 20 else name[:18] + ".."
            surf = self.font.render(display, True, SIDEBAR_TEXT_COLOR)
            screen.blit(surf, (x, item_y))

        screen.set_clip(None)

        # Scrollbar
        if content_h > list_area.height:
            sb_x = self.rect.right - SCROLLBAR_WIDTH - 2
            # Track
            pygame.draw.rect(screen, SCROLLBAR_COLOR,
                             (sb_x, list_area.top, SCROLLBAR_WIDTH, list_area.height),
                             border_radius=3)
            # Thumb
            thumb_ratio = list_area.height / content_h
            thumb_h = max(20, int(list_area.height * thumb_ratio))
            scroll_ratio = self.scroll_offset / self._max_scroll(count) if self._max_scroll(count) > 0 else 0
            thumb_y = list_area.top + int(scroll_ratio * (list_area.height - thumb_h))
            pygame.draw.rect(screen, SCROLLBAR_THUMB,
                             (sb_x, thumb_y, SCROLLBAR_WIDTH, thumb_h),
                             border_radius=3)


class PatternPopup:
    """Centered overlay showing a pattern's cell layout."""

    def __init__(self, name, cells):
        self.name = name
        self.cells = cells
        self.wiki_url = "https://conwaylife.com/wiki/" + name.replace(" ", "_")
        self.font = pygame.font.SysFont("monospace", 15, bold=True)
        self.link_font = pygame.font.SysFont("monospace", 11)
        self.close_font = pygame.font.SysFont("monospace", 18, bold=True)

        h, w = bounding_box(cells)
        self.pattern_h = h
        self.pattern_w = w

        # Scale cells to fit in a reasonable popup
        max_draw = 200
        if h > 0 and w > 0:
            self.cell_px = min(max_draw // max(h, w), 20)
            self.cell_px = max(self.cell_px, 4)
        else:
            self.cell_px = 10

        draw_w = self.pattern_w * self.cell_px
        draw_h = self.pattern_h * self.cell_px
        padding = 24
        title_h = 36
        link_h = 22
        self.popup_w = max(draw_w + padding * 2, 180)
        self.popup_h = title_h + draw_h + padding * 2 + link_h
        self.popup_rect = None  # set in draw() based on screen size
        self.close_rect = None
        self.link_rect = None

    def draw(self, screen):
        sw, sh = screen.get_size()

        # Overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill(POPUP_OVERLAY)
        screen.blit(overlay, (0, 0))

        # Center popup
        px = (sw - self.popup_w) // 2
        py = (sh - self.popup_h) // 2
        self.popup_rect = pygame.Rect(px, py, self.popup_w, self.popup_h)

        # Background + border
        pygame.draw.rect(screen, POPUP_BG, self.popup_rect, border_radius=8)
        pygame.draw.rect(screen, POPUP_BORDER, self.popup_rect, 2, border_radius=8)

        # Title
        title = self.font.render(self.name, True, POPUP_TITLE_COLOR)
        screen.blit(title, (px + 12, py + 10))

        # Close button
        close_text = self.close_font.render("X", True, POPUP_CLOSE_COLOR)
        cx = px + self.popup_w - 28
        cy = py + 8
        self.close_rect = pygame.Rect(cx - 4, cy - 2, close_text.get_width() + 8, close_text.get_height() + 4)
        screen.blit(close_text, (cx, cy))

        # Draw pattern cells
        title_h = 36
        grid_x = px + (self.popup_w - self.pattern_w * self.cell_px) // 2
        grid_y = py + title_h + 12

        for r, c in self.cells:
            rect = pygame.Rect(
                grid_x + c * self.cell_px,
                grid_y + r * self.cell_px,
                self.cell_px - 1,
                self.cell_px - 1,
            )
            pygame.draw.rect(screen, POPUP_CELL_COLOR, rect)

        # Wiki link
        mx, my = pygame.mouse.get_pos()
        link_text = "View on LifeWiki"
        hovering = self.link_rect is not None and self.link_rect.collidepoint(mx, my)
        color = POPUP_LINK_HOVER if hovering else POPUP_LINK_COLOR
        link_surf = self.link_font.render(link_text, True, color)
        link_x = px + (self.popup_w - link_surf.get_width()) // 2
        link_y = py + self.popup_h - 26
        screen.blit(link_surf, (link_x, link_y))
        # Underline
        pygame.draw.line(screen, color,
                         (link_x, link_y + link_surf.get_height()),
                         (link_x + link_surf.get_width(), link_y + link_surf.get_height()))
        self.link_rect = pygame.Rect(link_x, link_y, link_surf.get_width(), link_surf.get_height() + 2)

    def handle_event(self, event):
        """Handle events. Returns True if popup should stay open, False to close."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_rect and self.close_rect.collidepoint(event.pos):
                return False
            if self.link_rect and self.link_rect.collidepoint(event.pos):
                webbrowser.open(self.wiki_url)
                return True
            if self.popup_rect and not self.popup_rect.collidepoint(event.pos):
                return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False
        return True


class ToastNotification:
    """Brief popup when a new pattern type is first discovered."""

    def __init__(self, x, y, bottom_y):
        self.base_x = x
        self.base_y = y
        self.bottom_y = bottom_y
        self.font = pygame.font.SysFont("monospace", 13, bold=True)
        self.queue = []  # list of (name, start_time)
        self.duration = 2500  # ms
        self.max_visible = 3

    def add(self, name, current_time):
        """Queue a toast for a newly discovered pattern."""
        self.queue.append((name, current_time))

    def draw(self, screen, current_time):
        """Draw active toasts, removing expired ones."""
        # Remove expired
        self.queue = [(n, t) for n, t in self.queue
                      if current_time - t < self.duration]

        # Show most recent up to max_visible
        visible = self.queue[-self.max_visible:]
        for i, (name, start_time) in enumerate(visible):
            elapsed = current_time - start_time
            # Fade: full opacity for first 1.5s, then fade out
            if elapsed < 1500:
                alpha = 255
            else:
                alpha = max(0, 255 - int(255 * (elapsed - 1500) / 1000))

            y = self.bottom_y - (len(visible) - i) * 32
            text = f"  Found: {name}  "
            surf = self.font.render(text, True, TOAST_TEXT)

            # Background rect
            bg_rect = pygame.Rect(self.base_x, y, surf.get_width() + 12, 26)

            # Create transparent surface
            toast_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            toast_surf.fill((*TOAST_BG, alpha))
            pygame.draw.rect(toast_surf, (*TOAST_BORDER, alpha), toast_surf.get_rect(), 1, border_radius=4)

            screen.blit(toast_surf, bg_rect.topleft)

            text_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            text_surf.blit(surf, (0, 0))
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (self.base_x + 6, y + 5))
