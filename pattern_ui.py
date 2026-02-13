"""UI components for pattern recognition: sidebar and toast notifications."""

import pygame


SIDEBAR_BG = (18, 18, 24)
SIDEBAR_HEADER_COLOR = (100, 200, 255)
SIDEBAR_TEXT_COLOR = (160, 160, 170)
SIDEBAR_HIGHLIGHT = (40, 180, 80)
SIDEBAR_DIVIDER = (40, 40, 50)

TOAST_BG = (30, 60, 30)
TOAST_BORDER = (60, 180, 60)
TOAST_TEXT = (180, 255, 180)


class PatternSidebar:
    """Right-side panel listing discovered patterns."""

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = pygame.font.SysFont("monospace", 12)
        self.header_font = pygame.font.SysFont("monospace", 14, bold=True)
        self.highlight_duration = 3000  # ms to highlight new discoveries

    def draw(self, screen, discovered, current_time):
        """Draw sidebar. discovered: dict[name -> generation], current_time: pygame ticks."""
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
        y += 6

        # Pattern list sorted by discovery order (generation)
        sorted_patterns = sorted(discovered.items(), key=lambda kv: kv[1])
        max_y = self.rect.bottom - 4

        for name, gen in sorted_patterns:
            if y + 16 > max_y:
                remaining = count - sorted_patterns.index((name, gen))
                more = self.font.render(f"  +{remaining} more...", True, SIDEBAR_TEXT_COLOR)
                screen.blit(more, (x, y))
                break

            color = SIDEBAR_TEXT_COLOR
            # Truncate long names
            display = name if len(name) <= 20 else name[:18] + ".."
            surf = self.font.render(display, True, color)
            screen.blit(surf, (x, y))
            y += 16


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
