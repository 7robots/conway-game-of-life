"""Pattern database: loads .cells files and builds a hash-based lookup table."""

import hashlib
import os


def parse_cells_file(path):
    """Parse a .cells file into a name and frozenset of (row, col) tuples."""
    name = os.path.splitext(os.path.basename(path))[0]
    cells = []
    row = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("!"):
                if line.startswith("!Name:"):
                    name = line[6:].strip()
                continue
            for col, ch in enumerate(line):
                if ch == "O":
                    cells.append((row, col))
            row += 1
    return name, frozenset(cells)


def normalize(cells):
    """Translate cells so the minimum row and col are both 0."""
    if not cells:
        return frozenset()
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return frozenset((r - min_r, c - min_c) for r, c in cells)


def rotate90(cells):
    """Rotate cells 90 degrees clockwise: (r, c) -> (c, -r)."""
    return frozenset((c, -r) for r, c in cells)


def reflect_h(cells):
    """Reflect cells horizontally: (r, c) -> (r, -c)."""
    return frozenset((r, -c) for r, c in cells)


def all_orientations(cells):
    """Return up to 8 unique normalized orientations (4 rotations x 2 reflections)."""
    seen = set()
    results = []
    current = cells
    for _ in range(4):
        for variant in (current, reflect_h(current)):
            n = normalize(variant)
            if n not in seen:
                seen.add(n)
                results.append(n)
        current = rotate90(current)
    return results


def hash_cells(cells):
    """Hash a normalized frozenset of cells to a short hex string."""
    data = str(sorted(cells)).encode()
    return hashlib.sha256(data).hexdigest()[:16]


def bounding_box(cells):
    """Return (height, width) of the bounding box."""
    if not cells:
        return 0, 0
    max_r = max(r for r, c in cells)
    max_c = max(c for r, c in cells)
    return max_r + 1, max_c + 1


class PatternDatabase:
    """Loads small .cells patterns and provides hash-based lookup."""

    def __init__(self, patterns_dir="patterns", max_bbox=10):
        self.hash_to_name = {}
        self.pattern_count = 0
        self._load(patterns_dir, max_bbox)

    def _load(self, patterns_dir, max_bbox):
        if not os.path.isdir(patterns_dir):
            return
        for fname in os.listdir(patterns_dir):
            if not fname.endswith(".cells"):
                continue
            path = os.path.join(patterns_dir, fname)
            try:
                name, cells = parse_cells_file(path)
            except Exception:
                continue
            if not cells:
                continue
            norm = normalize(cells)
            h, w = bounding_box(norm)
            if h > max_bbox or w > max_bbox:
                continue
            self.pattern_count += 1
            for orient in all_orientations(norm):
                key = hash_cells(orient)
                if key not in self.hash_to_name:
                    self.hash_to_name[key] = name

    def lookup(self, cells_normalized):
        """Look up a normalized cell set. Returns pattern name or None."""
        key = hash_cells(cells_normalized)
        return self.hash_to_name.get(key)
