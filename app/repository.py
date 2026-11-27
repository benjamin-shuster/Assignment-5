"""SQLite persistence layer for RoomBook."""

from __future__ import annotations

import contextlib
import sqlite3
from typing import Iterator

FIXED_ROOMS: tuple[tuple[int, str, int], ...] = (
    (1, "Quiet Room A", 2),
    (2, "Quiet Room B", 2),
    (3, "Group Room C", 6),
    (4, "Group Room D", 8),
)

_SQLITE_INT_MIN = -(1 << 63)
_SQLITE_INT_MAX = (1 << 63) - 1


def _is_sqlite_int(value: int) -> bool:
    """Return True if value fits in a signed 64-bit SQLite INTEGER."""
    return _SQLITE_INT_MIN <= value <= _SQLITE_INT_MAX


@contextlib.contextmanager
def _connect(
    db_path: str, *, immediate: bool = False
) -> Iterator[sqlite3.Connection]:
    """Open a fresh SQLite connection for a single repository call."""
    conn = sqlite3.connect(
        db_path,
        timeout=30.0,
        isolation_level=None if immediate else "",
    )
    try:
        conn.row_factory = sqlite3.Row
        if immediate:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                if conn.in_transaction:
                    conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
        else:
            with conn:
                yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    """Create schema tables if missing and idempotently seed the four rooms."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                capacity INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                start TEXT NOT NULL,
                end TEXT NOT NULL,
                booked_by TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT OR IGNORE INTO rooms (id, name, capacity) VALUES (?, ?, ?)",
            FIXED_ROOMS,
        )


def list_rooms(db_path: str) -> list[dict]:
    """Return all rooms ordered by id ascending."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, capacity FROM rooms ORDER BY id ASC"
        ).fetchall()
    return [dict(row) for row in rows]


def room_exists(db_path: str, room_id: int) -> bool:
    """Return True if a room with the given id exists."""
    if not _is_sqlite_int(room_id):
        return False
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM rooms WHERE id = ?",
            (room_id,),
        ).fetchone()
    return row is not None


def list_bookings(
    db_path: str, date: str, room_id: int | None = None
) -> list[dict]:
    """Return bookings for a date (and optional room), ordered by room_id then start."""
    if room_id is not None and not _is_sqlite_int(room_id):
        return []
    with _connect(db_path) as conn:
        if room_id is None:
            rows = conn.execute(
                """
                SELECT id, room_id, date, start, end, booked_by
                FROM bookings
                WHERE date = ?
                ORDER BY room_id ASC, start ASC
                """,
                (date,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, room_id, date, start, end, booked_by
                FROM bookings
                WHERE date = ? AND room_id = ?
                ORDER BY room_id ASC, start ASC
                """,
                (date, room_id),
            ).fetchall()
    return [dict(row) for row in rows]


def create_booking(
    db_path: str,
    room_id: int,
    date: str,
    start: str,
    end: str,
    booked_by: str,
) -> dict | None:
    """Atomically check overlap and insert a booking, returning None on overlap."""
    with _connect(db_path, immediate=True) as conn:
        overlap = conn.execute(
            """
            SELECT 1
            FROM bookings
            WHERE room_id = ? AND date = ? AND start < ? AND ? < end
            LIMIT 1
            """,
            (room_id, date, end, start),
        ).fetchone()
        if overlap is not None:
            conn.execute("ROLLBACK")
            return None
        cursor = conn.execute(
            """
            INSERT INTO bookings (room_id, date, start, end, booked_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (room_id, date, start, end, booked_by),
        )
        booking_id = cursor.lastrowid
    return {
        "id": booking_id,
        "room_id": room_id,
        "date": date,
        "start": start,
        "end": end,
        "booked_by": booked_by,
    }


def delete_booking(db_path: str, booking_id: int) -> bool:
    """Delete a booking by id and return True if a row was removed."""
    if not _is_sqlite_int(booking_id):
        return False
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM bookings WHERE id = ?",
            (booking_id,),
        )
    return cursor.rowcount > 0
