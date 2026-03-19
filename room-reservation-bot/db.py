import sqlite3
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "reservations.db"


@dataclass
class Room:
    id: int
    name: str
    description: str


@dataclass
class Reservation:
    id: int
    room_id: int
    room_name: str
    user_id: int
    username: str
    date: str          # YYYY-MM-DD
    start_time: str    # HH:MM
    end_time: str      # HH:MM
    created_at: str


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS rooms (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS reservations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id     INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                user_id     INTEGER NOT NULL,
                username    TEXT NOT NULL,
                date        TEXT NOT NULL,
                start_time  TEXT NOT NULL,
                end_time    TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)

        # Seed default rooms if table is empty
        existing = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        if existing == 0:
            conn.executemany(
                "INSERT INTO rooms (name, description) VALUES (?, ?)",
                [
                    ("Room A", "Small meeting room, capacity 4"),
                    ("Room B", "Medium conference room, capacity 10"),
                    ("Room C", "Large boardroom, capacity 20"),
                ],
            )


# ── Rooms ─────────────────────────────────────────────────────────────────────

def get_all_rooms() -> list[Room]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM rooms ORDER BY name").fetchall()
    return [Room(**dict(r)) for r in rows]


def get_room(room_id: int) -> Optional[Room]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    return Room(**dict(row)) if row else None


def add_room(name: str, description: str = "") -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO rooms (name, description) VALUES (?, ?)",
                (name, description),
            )
        return True
    except sqlite3.IntegrityError:
        return False  # duplicate name


def remove_room(room_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    return cur.rowcount > 0


# ── Reservations ──────────────────────────────────────────────────────────────

def _row_to_reservation(row: sqlite3.Row) -> Reservation:
    d = dict(row)
    return Reservation(
        id=d["id"],
        room_id=d["room_id"],
        room_name=d.get("room_name", ""),
        user_id=d["user_id"],
        username=d["username"],
        date=d["date"],
        start_time=d["start_time"],
        end_time=d["end_time"],
        created_at=d["created_at"],
    )


def get_reservations_for_room(room_id: int, on_date: str) -> list[Reservation]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.*, rooms.name AS room_name
            FROM reservations r
            JOIN rooms ON rooms.id = r.room_id
            WHERE r.room_id = ? AND r.date = ?
            ORDER BY r.start_time
            """,
            (room_id, on_date),
        ).fetchall()
    return [_row_to_reservation(r) for r in rows]


def get_user_reservations(user_id: int) -> list[Reservation]:
    today = date.today().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.*, rooms.name AS room_name
            FROM reservations r
            JOIN rooms ON rooms.id = r.room_id
            WHERE r.user_id = ? AND r.date >= ?
            ORDER BY r.date, r.start_time
            """,
            (user_id, today),
        ).fetchall()
    return [_row_to_reservation(r) for r in rows]


def get_all_reservations() -> list[Reservation]:
    today = date.today().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.*, rooms.name AS room_name
            FROM reservations r
            JOIN rooms ON rooms.id = r.room_id
            WHERE r.date >= ?
            ORDER BY r.date, r.start_time
            """,
            (today,),
        ).fetchall()
    return [_row_to_reservation(r) for r in rows]


def is_slot_available(room_id: int, on_date: str, start: str, end: str) -> bool:
    """Return True when no existing reservation overlaps the requested slot."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM reservations
            WHERE room_id = ?
              AND date = ?
              AND start_time < ?
              AND end_time > ?
            """,
            (room_id, on_date, end, start),
        ).fetchone()
    return row[0] == 0


def create_reservation(
    room_id: int,
    user_id: int,
    username: str,
    on_date: str,
    start: str,
    end: str,
) -> Optional[int]:
    """Insert a reservation and return its ID, or None if the slot is taken."""
    if not is_slot_available(room_id, on_date, start, end):
        return None
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO reservations (room_id, user_id, username, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (room_id, user_id, username, on_date, start, end),
        )
    return cur.lastrowid


def cancel_reservation(reservation_id: int, user_id: int) -> bool:
    """Delete a reservation owned by user_id."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM reservations WHERE id = ? AND user_id = ?",
            (reservation_id, user_id),
        )
    return cur.rowcount > 0


# Initialise on import
init_db()
