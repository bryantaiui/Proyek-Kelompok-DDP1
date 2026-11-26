"""Lapisan Database (SQLite) — Area: Database (Neil).

Menyimpan daftar tugas kuliah AI Major beserta atribut yang dibutuhkan
untuk perhitungan prioritas/monster (bobot nilai, tingkat kesulitan, deadline).
Nantinya akan diintegrasikan dengan sinkronisasi kalender SCELE (.ics).
"""
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    uid          TEXT UNIQUE,                  -- opsional: UID dari SCELE (.ics) agar tidak duplikat
    name         TEXT NOT NULL,                -- nama tugas, mis. "TP 3 DDP1"
    course       TEXT DEFAULT '',              -- mata kuliah, mis. "DDP1", "Kalkulus"
    grade_weight REAL NOT NULL DEFAULT 0.0,    -- persentase terhadap nilai akhir semester (0 - 100)
    difficulty   INTEGER NOT NULL DEFAULT 3,   -- tingkat kesulitan (1 = mudah .. 5 = sangat sulit)
    deadline     TEXT NOT NULL,                -- format ISO 8601, mis. "2026-12-05T23:59:00"
    completed    INTEGER NOT NULL DEFAULT 0    -- 0 = belum selesai (monster hidup), 1 = selesai (kalah)
);
"""


def get_connection(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path=None):
    with get_connection(path) as conn:
        conn.executescript(SCHEMA)


def seed_sample_if_empty(path=None):
    """Isi 3 contoh tugas awal jika database masih kosong (hanya untuk testing awal)."""
    with get_connection(path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count > 0:
            return
        samples = [
            ("Proyek Akhir DDP1", "DDP1", 25.0, 5, "2026-12-09T23:59:00"),
            ("PR Kalkulus Pekan 12", "Kalkulus", 5.0, 3, "2026-11-30T23:59:00"),
            ("Pre-Class Quiz LSD", "LSD", 2.0, 2, "2026-11-28T23:59:00"),
        ]
        conn.executemany(
            "INSERT INTO tasks (name, course, grade_weight, difficulty, deadline) VALUES (?, ?, ?, ?, ?)",
            samples,
        )


def get_all_tasks(path=None):
    with get_connection(path) as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY completed ASC, deadline ASC").fetchall()
        return [dict(r) for r in rows]


def add_task(name, course, grade_weight, difficulty, deadline, uid=None, path=None):
    with get_connection(path) as conn:
        cur = conn.execute(
            "INSERT INTO tasks (uid, name, course, grade_weight, difficulty, deadline) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uid, name, course, float(grade_weight), int(difficulty), deadline),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def toggle_complete(task_id, path=None):
    with get_connection(path) as conn:
        row = conn.execute("SELECT completed FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        new_val = 0 if row["completed"] else 1
        conn.execute("UPDATE tasks SET completed = ? WHERE id = ?", (new_val, task_id))
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(updated)


def delete_task(task_id, path=None):
    with get_connection(path) as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cur.rowcount > 0
