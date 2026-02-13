"""Grid scanner: extracts connected components and identifies known patterns."""

from collections import deque
from pattern_db import normalize, hash_cells, bounding_box


class PatternScanner:
    """Scans a grid each generation, identifying known patterns via hash lookup."""

    def __init__(self, database):
        self.db = database
        self.discovered = {}  # name -> generation first seen

    def scan(self, grid, generation):
        """Scan grid for known patterns. Returns list of newly discovered names."""
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        visited = [[False] * cols for _ in range(rows)]
        new_discoveries = []

        for r in range(rows):
            for c in range(cols):
                if grid[r][c] and not visited[r][c]:
                    component = self._flood_fill(grid, visited, r, c, rows, cols)
                    norm = normalize(component)
                    h, w = bounding_box(norm)
                    if h > 10 or w > 10:
                        continue
                    name = self.db.lookup(norm)
                    if name and name not in self.discovered:
                        self.discovered[name] = generation
                        new_discoveries.append(name)

        return new_discoveries

    def _flood_fill(self, grid, visited, start_r, start_c, rows, cols):
        """BFS flood fill with 8-connectivity. Returns frozenset of (r, c)."""
        queue = deque()
        queue.append((start_r, start_c))
        visited[start_r][start_c] = True
        cells = []

        while queue:
            r, c = queue.popleft()
            cells.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and grid[nr][nc]:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

        return frozenset(cells)

    def reset(self):
        """Clear all discoveries."""
        self.discovered.clear()
