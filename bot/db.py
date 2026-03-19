import sqlite3
from config import DB_FILE, MACHINES


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        # Laundry machines
        conn.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                machine_id  TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'free',
                user_id     TEXT,
                user_name   TEXT,
                end_time    TEXT
            )
        """)
        for mid in MACHINES:
            conn.execute(
                "INSERT OR IGNORE INTO machines (machine_id) VALUES (?)", (mid,)
            )

        # Room bookings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id     TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                user_name   TEXT NOT NULL,
                date        TEXT NOT NULL,
                start_time  TEXT NOT NULL,
                end_time    TEXT NOT NULL
            )
        """)
        conn.commit()


# ── laundry ───────────────────────────────────────────────────────────────────

def get_machine(mid: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM machines WHERE machine_id = ?", (mid,)
        ).fetchone()
    return dict(row) if row else {}


def set_machine(mid: str, status: str, user_id=None, user_name=None, end_time=None):
    with get_db() as conn:
        conn.execute(
            "UPDATE machines SET status=?, user_id=?, user_name=?, end_time=? WHERE machine_id=?",
            (status, user_id, user_name, end_time, mid)
        )
        conn.commit()


def all_machines() -> list:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM machines").fetchall()
    return [dict(r) for r in rows]


# ── room bookings ─────────────────────────────────────────────────────────────

def get_bookings_for_room(room_id: str, date: str) -> list:
    """All bookings for a room on a given date (YYYY-MM-DD), sorted by start."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM bookings WHERE room_id=? AND date=? ORDER BY start_time",
            (room_id, date)
        ).fetchall()
    return [dict(r) for r in rows]


def get_bookings_for_user(user_id: str) -> list:
    """Upcoming bookings for a user."""
    from datetime import date
    today = date.today().isoformat()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM bookings WHERE user_id=? AND date>=? ORDER BY date, start_time",
            (str(user_id), today)
        ).fetchall()
    return [dict(r) for r in rows]


def has_overlap(room_id: str, date: str, start: str, end: str, exclude_id=None) -> bool:
    """Returns True if the proposed slot overlaps any existing booking."""
    with get_db() as conn:
        query = """
            SELECT 1 FROM bookings
            WHERE room_id=? AND date=?
              AND start_time < ? AND end_time > ?
        """
        params = [room_id, date, end, start]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        row = conn.execute(query, params).fetchone()
    return row is not None


def add_booking(room_id: str, user_id: str, user_name: str, date: str, start: str, end: str) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO bookings (room_id, user_id, user_name, date, start_time, end_time) VALUES (?,?,?,?,?,?)",
            (room_id, str(user_id), user_name, date, start, end)
        )
        conn.commit()
        return cur.lastrowid


def delete_booking(booking_id: int, user_id: str) -> bool:
    """Delete a booking. Returns True if a row was actually deleted."""
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM bookings WHERE id=? AND user_id=?",
            (booking_id, str(user_id))
        )
        conn.commit()
    return cur.rowcount > 0
