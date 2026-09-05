"""SQLite state: which messages are done, and how far each mailbox scan got."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import cast, final

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_messages (
    message_id   TEXT PRIMARY KEY,
    mailbox      TEXT NOT NULL,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mailbox_cursor (
    mailbox      TEXT PRIMARY KEY,
    uid_validity INTEGER NOT NULL,
    last_uid     INTEGER NOT NULL
);
"""

_SELECT_PROCESSED = "SELECT 1 FROM processed_messages WHERE message_id = ?"

_INSERT_PROCESSED = """
INSERT OR REPLACE INTO processed_messages (message_id, mailbox, processed_at)
VALUES (?, ?, ?)
"""

_SELECT_CURSOR = """
SELECT uid_validity, last_uid FROM mailbox_cursor WHERE mailbox = ?
"""

_INSERT_CURSOR = """
INSERT OR REPLACE INTO mailbox_cursor (mailbox, uid_validity, last_uid)
VALUES (?, ?, ?)
"""


@final
class StateStore:
    """Dedupe keyed on Message-ID, so a mailbox rescan never re-uploads."""

    _conn: sqlite3.Connection

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        _ = self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def is_processed(self, message_id: str) -> bool:
        row = cast(
            "tuple[int] | None",
            self._conn.execute(_SELECT_PROCESSED, (message_id,)).fetchone(),
        )
        return row is not None

    def mark_processed(self, message_id: str, mailbox: str) -> None:
        _ = self._conn.execute(
            _INSERT_PROCESSED,
            (message_id, mailbox, datetime.now(UTC).isoformat()),
        )
        self._conn.commit()

    def get_cursor(self, mailbox: str) -> tuple[int, int] | None:
        """Return (uid_validity, last_uid) for a mailbox, if it was scanned before."""
        row = cast(
            "tuple[int, int] | None",
            self._conn.execute(_SELECT_CURSOR, (mailbox,)).fetchone(),
        )
        return (row[0], row[1]) if row else None

    def set_cursor(self, mailbox: str, uid_validity: int, last_uid: int) -> None:
        _ = self._conn.execute(_INSERT_CURSOR, (mailbox, uid_validity, last_uid))
        self._conn.commit()
