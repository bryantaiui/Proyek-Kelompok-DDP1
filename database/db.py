"""Lapisan Database (SQLite) — Area: Database (Neil).

Menyimpan daftar tugas bersama untuk semua mahasiswa AI Major, menggabungkan:
1. Tugas otomatis dari berbagai kalender .ics (SCELE, Google Calendar, Apple Calendar, dll)
2. Tugas manual yang ditambahkan langsung di website

Semua fungsi mengembalikan dict/list Python standar agar tim Mekanik (mechanics/priority.py)
tidak perlu menulis SQL sama sekali.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from database import scele

WIB = timezone(timedelta(hours=7))
DB_PATH = os.environ.get("DB_PATH", "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    uid          TEXT UNIQUE,                  -- UID dari .ics; NULL untuk tugas manual
    name         TEXT NOT NULL,                -- nama tugas, mis. "TP 3 DDP1"
    course       TEXT DEFAULT '',              -- mata kuliah / label kalender
    grade_weight REAL NOT NULL DEFAULT 5.0,    -- persentase terhadap nilai akhir semester (0 - 100)
    difficulty   INTEGER NOT NULL DEFAULT 3,   -- tingkat kesulitan (1 = mudah .. 5 = sangat sulit)
    deadline     TEXT NOT NULL,                -- format ISO 8601 WIB, mis. "2026-12-05T23:59:00"
    completed    INTEGER NOT NULL DEFAULT 0,   -- 0 = monster hidup, 1 = monster dikalahkan
    source       TEXT NOT NULL DEFAULT 'manual', -- 'scele', nama kalender, atau 'manual'
    is_edited    INTEGER NOT NULL DEFAULT 0,   -- 1 = pernah diedit di website
    is_deleted   INTEGER NOT NULL DEFAULT 0    -- 1 = dihapus (soft-delete agar sync tidak menambah ulang)
);
CREATE TABLE IF NOT EXISTS calendars (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,                -- mis. "SCELE AI Major", "Google Calendar Neil"
    url          TEXT NOT NULL UNIQUE,         -- link .ics (https:// atau webcal://)
    filter_mode  TEXT NOT NULL DEFAULT 'tasks_only', -- 'tasks_only' atau 'all'
    last_sync_at TEXT
);
CREATE TABLE IF NOT EXISTS sync_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_connection(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path=None):
    with get_connection(path) as conn:
        conn.executescript(SCHEMA)
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(tasks)")]
        if "source" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'")
        if "is_edited" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN is_edited INTEGER NOT NULL DEFAULT 0")
        if "is_deleted" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")


def seed_default_calendar_if_empty(path=None):
    """Jika tabel calendars kosong dan SCELE_ICS_URL ada di .env, daftarkan otomatis."""
    url = (os.environ.get("SCELE_ICS_URL") or "").strip()
    if not url:
        return
    with get_connection(path) as conn:
        if conn.execute("SELECT COUNT(*) FROM calendars").fetchone()[0] == 0:
            conn.execute(
                "INSERT OR IGNORE INTO calendars (name, url, filter_mode) VALUES (?, ?, 'tasks_only')",
                ("SCELE AI Major", url),
            )


def seed_sample_if_empty(path=None):
    """Isi contoh tugas awal hanya jika database kosong dan tidak ada kalender."""
    with get_connection(path) as conn:
        if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] > 0:
            return
        samples = [
            ("Proyek Akhir DDP1", "DDP1", 25.0, 5, "2026-12-09T23:59:00"),
            ("PR Kalkulus Pekan 12", "Kalkulus", 5.0, 3, "2026-11-30T23:59:00"),
            ("Pre-Class Quiz LSD", "LSD", 2.0, 2, "2026-11-28T23:59:00"),
        ]
        conn.executemany(
            "INSERT INTO tasks (name, course, grade_weight, difficulty, deadline, source) "
            "VALUES (?, ?, ?, ?, ?, 'manual')",
            samples,
        )


# ---------- CRUD Kalender (.ics) ----------

def get_calendars(path=None):
    with get_connection(path) as conn:
        rows = conn.execute("SELECT * FROM calendars ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]


def add_calendar(name, url, filter_mode="tasks_only", path=None):
    if filter_mode not in ("tasks_only", "all"):
        filter_mode = "tasks_only"
    clean_url = url.strip()
    with get_connection(path) as conn:
        cur = conn.execute(
            "INSERT INTO calendars (name, url, filter_mode) VALUES (?, ?, ?)",
            (name.strip(), clean_url, filter_mode),
        )
        row = conn.execute("SELECT * FROM calendars WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def delete_calendar(cal_id, path=None):
    with get_connection(path) as conn:
        cur = conn.execute("DELETE FROM calendars WHERE id = ?", (cal_id,))
        return cur.rowcount > 0


# ---------- CRUD Tugas ----------

def get_all_tasks(path=None):
    with get_connection(path) as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE is_deleted = 0 ORDER BY completed ASC, deadline ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def add_task(name, course, grade_weight, difficulty, deadline, uid=None, source="manual", path=None):
    with get_connection(path) as conn:
        cur = conn.execute(
            "INSERT INTO tasks (uid, name, course, grade_weight, difficulty, deadline, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uid, name, course, float(grade_weight), int(difficulty), deadline, source),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def update_task(task_id, name=None, course=None, grade_weight=None, difficulty=None, deadline=None, path=None):
    """Edit atribut tugas (mis. bobot nilai / tingkat kesulitan) dari website."""
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND is_deleted = 0", (task_id,)
        ).fetchone()
        if row is None:
            return None

        new_name = name.strip() if isinstance(name, str) and name.strip() else row["name"]
        new_course = course.strip() if isinstance(course, str) else row["course"]
        new_weight = float(grade_weight) if grade_weight is not None else row["grade_weight"]
        new_diff = int(difficulty) if difficulty is not None else row["difficulty"]
        new_dl = deadline.strip() if isinstance(deadline, str) and deadline.strip() else row["deadline"]

        conn.execute(
            "UPDATE tasks SET name = ?, course = ?, grade_weight = ?, difficulty = ?, "
            "deadline = ?, is_edited = 1 WHERE id = ?",
            (new_name, new_course, new_weight, new_diff, new_dl, task_id),
        )
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(updated)


def toggle_complete(task_id, path=None):
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT completed FROM tasks WHERE id = ? AND is_deleted = 0", (task_id,)
        ).fetchone()
        if row is None:
            return None
        new_val = 0 if row["completed"] else 1
        conn.execute("UPDATE tasks SET completed = ? WHERE id = ?", (new_val, task_id))
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(updated)


def delete_task(task_id, path=None):
    """Hapus tugas. Tugas dari kalender .ics di-soft-delete agar sync tidak menambahkannya lagi."""
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT uid FROM tasks WHERE id = ? AND is_deleted = 0", (task_id,)
        ).fetchone()
        if row is None:
            return False
        if row["uid"] is not None:
            conn.execute("UPDATE tasks SET is_deleted = 1 WHERE id = ?", (task_id,))
        else:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return True


def upsert_scele_tasks(scele_tasks, path=None):
    """Masukkan tugas baru dari .ics; tugas lama hanya diperbarui deadline/nama jika belum diedit.
    Bobot nilai (grade_weight), kesulitan (difficulty), dan status selesai selalu dipertahankan."""
    added = 0
    updated = 0
    with get_connection(path) as conn:
        for t in scele_tasks:
            existing = conn.execute(
                "SELECT id, is_edited, is_deleted FROM tasks WHERE uid = ?",
                (t["uid"],),
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO tasks (uid, name, course, grade_weight, difficulty, deadline, source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (t["uid"], t["name"], t["course"], t["grade_weight"], t["difficulty"], t["deadline"], t["source"]),
                )
                added += 1
            elif not existing["is_deleted"]:
                if existing["is_edited"]:
                    conn.execute(
                        "UPDATE tasks SET deadline = ? WHERE id = ?",
                        (t["deadline"], existing["id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE tasks SET name = ?, course = ?, deadline = ? WHERE id = ?",
                        (t["name"], t["course"], t["deadline"], existing["id"]),
                    )
                updated += 1
    return {"added": added, "updated": updated, "total": len(scele_tasks)}


def sync_scele_if_needed(force=False, path=None):
    """Sinkronkan tugas dari semua kalender di tabel `calendars` (plus SCELE_ICS_FILE jika ada)."""
    seed_default_calendar_if_empty(path=path)
    calendars = get_calendars(path=path)
    file_path = os.environ.get("SCELE_ICS_FILE")

    if not calendars and not file_path:
        return {"synced": False, "reason": "no_url"}

    interval_menit = int(os.environ.get("SYNC_INTERVAL_MINUTES", "15"))
    now_wib = datetime.now(WIB)

    with get_connection(path) as conn:
        row = conn.execute("SELECT value FROM sync_meta WHERE key = 'last_sync_at'").fetchone()
        last_sync_str = row["value"] if row else None

    if not force and last_sync_str:
        try:
            last_dt = datetime.fromisoformat(last_sync_str)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=WIB)
            if (now_wib - last_dt).total_seconds() < interval_menit * 60:
                return {"synced": False, "reason": "throttled", "last_sync_at": last_sync_str}
        except ValueError:
            pass

    now_str = now_wib.strftime("%Y-%m-%dT%H:%M:%S")
    total_added = 0
    total_updated = 0
    total_events = 0
    errors = []

    if file_path:
        try:
            with open(file_path, "rb") as f:
                s = upsert_scele_tasks(scele.parse_ics(f.read()), path=path)
            total_added += s["added"]
            total_updated += s["updated"]
            total_events += s["total"]
        except Exception as e:
            errors.append(f"file: {type(e).__name__}: {e}")

    for cal in calendars:
        try:
            items = scele.fetch_ics_url(
                cal["url"],
                filter_mode=cal["filter_mode"],
                source_name=cal["name"],
            )
            s = upsert_scele_tasks(items, path=path)
            total_added += s["added"]
            total_updated += s["updated"]
            total_events += s["total"]
            with get_connection(path) as conn:
                conn.execute("UPDATE calendars SET last_sync_at = ? WHERE id = ?", (now_str, cal["id"]))
        except Exception as e:
            errors.append(f"{cal['name']}: {type(e).__name__}: {e}")

    with get_connection(path) as conn:
        conn.execute(
            "INSERT INTO sync_meta (key, value) VALUES ('last_sync_at', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (now_str,),
        )

    if errors and total_events == 0:
        return {"synced": False, "error": "; ".join(errors)}

    res = {
        "synced": True,
        "added": total_added,
        "updated": total_updated,
        "total": total_events,
        "last_sync_at": now_str,
    }
    if errors:
        res["warnings"] = errors
    return res
