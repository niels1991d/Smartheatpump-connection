"""Temperatuurgeschiedenis bewaren in een klein SQLite-bestand."""

from __future__ import annotations

import sqlite3
import threading
import time

from .client import Status


class History:
    def __init__(self, path: str = "history.db", keep_days: int = 30):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._keep = keep_days * 86400
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS samples ("
            "ts INTEGER PRIMARY KEY, power INTEGER, current REAL, target REAL)"
        )
        self._db.commit()

    def add(self, s: Status, ts: float | None = None) -> None:
        ts = int(ts or time.time())
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO samples VALUES (?, ?, ?, ?)",
                (ts, None if s.power is None else int(s.power), s.current_temp, s.target_temp),
            )
            self._db.execute("DELETE FROM samples WHERE ts < ?", (ts - self._keep,))
            self._db.commit()

    def since(self, seconds: int) -> list[dict]:
        cutoff = int(time.time()) - seconds
        with self._lock:
            rows = self._db.execute(
                "SELECT ts, power, current, target FROM samples WHERE ts >= ? ORDER BY ts", (cutoff,)
            ).fetchall()
        return [{"ts": ts, "power": p, "current": c, "target": t} for ts, p, c, t in rows]
