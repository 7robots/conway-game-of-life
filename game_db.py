"""SQLite persistence layer for game runs and pattern history."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

APP_NAME = "conway-game-of-life"


def _default_data_dir():
    """Return XDG_DATA_HOME/conway-game-of-life, creating it if needed."""
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    data_dir = os.path.join(xdg, APP_NAME)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


class GameDatabase:
    """Wraps sqlite3 for saving/loading game runs and pattern statistics."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(_default_data_dir(), "game_data.db")
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                starting_grid TEXT NOT NULL,
                final_generation INTEGER NOT NULL,
                speed_ms INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS run_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                pattern_name TEXT NOT NULL,
                generation_discovered INTEGER NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE(run_id, pattern_name)
            );

            CREATE TABLE IF NOT EXISTS pattern_stats (
                pattern_name TEXT PRIMARY KEY,
                times_discovered INTEGER NOT NULL DEFAULT 0,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                runs_appeared_in INTEGER NOT NULL DEFAULT 0
            );
        """)
        self._conn.commit()

    @contextmanager
    def _transaction(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def save_run(self, name, starting_grid, discovered_patterns, final_generation, speed_ms):
        """Save a run with its patterns and update cumulative stats.

        Args:
            name: Display name for the run.
            starting_grid: 2D list (the grid at generation 0).
            discovered_patterns: dict of {pattern_name: generation_discovered}.
            final_generation: Last generation reached.
            speed_ms: Speed setting at time of save.

        Returns:
            The new run_id.
        """
        now = datetime.now(timezone.utc).isoformat()
        grid_json = json.dumps(starting_grid)

        with self._transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO runs (name, created_at, starting_grid, final_generation, speed_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, now, grid_json, final_generation, speed_ms),
            )
            run_id = cursor.lastrowid

            for pattern_name, gen in discovered_patterns.items():
                conn.execute(
                    "INSERT INTO run_patterns (run_id, pattern_name, generation_discovered) "
                    "VALUES (?, ?, ?)",
                    (run_id, pattern_name, gen),
                )

                # Upsert pattern_stats
                conn.execute(
                    """INSERT INTO pattern_stats (pattern_name, times_discovered, first_seen_at, last_seen_at, runs_appeared_in)
                       VALUES (?, 1, ?, ?, 1)
                       ON CONFLICT(pattern_name) DO UPDATE SET
                           times_discovered = times_discovered + 1,
                           last_seen_at = excluded.last_seen_at,
                           runs_appeared_in = runs_appeared_in + 1""",
                    (pattern_name, now, now),
                )

        return run_id

    def list_runs(self):
        """Return summary of all runs, newest first."""
        rows = self._conn.execute(
            """SELECT r.run_id, r.name, r.created_at, r.final_generation, r.speed_ms,
                      COUNT(rp.id) AS pattern_count
               FROM runs r
               LEFT JOIN run_patterns rp ON r.run_id = rp.run_id
               GROUP BY r.run_id
               ORDER BY r.created_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]

    def load_run(self, run_id):
        """Load full run details including starting grid and patterns."""
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None

        result = dict(row)
        result["starting_grid"] = json.loads(result["starting_grid"])

        patterns = self._conn.execute(
            "SELECT pattern_name, generation_discovered FROM run_patterns "
            "WHERE run_id = ? ORDER BY generation_discovered",
            (run_id,),
        ).fetchall()
        result["patterns"] = [dict(p) for p in patterns]
        return result

    def delete_run(self, run_id):
        """Delete a run and its associated pattern records."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))

    def get_pattern_stats(self):
        """Return cumulative pattern stats sorted by frequency descending."""
        rows = self._conn.execute(
            "SELECT * FROM pattern_stats ORDER BY times_discovered DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self._conn.close()
