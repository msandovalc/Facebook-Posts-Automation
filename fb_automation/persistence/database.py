"""SQLite connection as a context manager."""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fb_automation import config

logger = logging.getLogger(__name__)

SCHEMA = """
create table if not exists users(
    ID integer primary key,
    USER_NAME text,
    PASSWORD blob
);
create table if not exists posts(
    ID integer primary key,
    MSG text,
    MEDIA text,
    OWNER_ID integer
);
create table if not exists targets(
    ID integer primary key,
    TARGET_URL text,
    OWNER_ID integer
);
create table if not exists tasks(
    ID integer primary key,
    TASK_NAME text not null,
    OWNER_ID integer,
    POST_ID integer,
    TARGETS text not null,
    DATE text not null
);
"""


class Database:
    def __init__(self, path: Path | str = config.DB_PATH):
        self.path = str(path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        logger.info("Schema verified at %s", self.path)

    @contextmanager
    def connect(self):
        """Yield a connection with automatic commit/rollback/close."""
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Rollback due to transaction error")
            raise
        finally:
            conn.close()