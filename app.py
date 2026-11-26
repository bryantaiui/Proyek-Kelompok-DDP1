"""Entry point website (Flask) — menghubungkan Database, Mekanik Prioritas, dan Desain."""
import os
import sqlite3

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from database import db
from mechanics import priority

app = Flask(__name__)

# Inisialisasi database saat server dimulai
db.init_db()
db.seed_default_calendar_if_empty()
if not db.get_calendars() and not os.environ.get("SCELE_ICS_FILE"):
    db.seed_sample_if_empty()


@app.route("/")
def index():
    """Halaman utama (template berada di templates/index.html)."""
    return render_template("index.html")


# ---------- REST API Tugas ----------

@app.route("/api/tasks", methods=["GET"])
def api_get_tasks():
    """Auto-sync kalender (jika perlu), ambil semua tugas, lalu urutkan lewat mechanics/priority.py."""
    sync_info = db.sync_scele_if_needed(force=False)
    raw_tasks = db.get_all_tasks()
    ranked = priority.rank_tasks(raw_tasks)
    return jsonify({"tasks": ranked, "sync": sync_info})


@app.route("/api/tasks", methods=["POST"])
def api_add_task():
    """Tambah tugas baru secara manual (terlihat semua pengguna)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    deadline = (data.get("deadline") or "").strip()
    if not name or not deadline:
        return jsonify({"error": "name dan deadline wajib diisi"}), 400

    task = db.add_task(
        name=name,
        course=(data.get("course") or "").strip(),
        grade_weight=data.get("grade_weight", 5.0),
        difficulty=data.get("difficulty", 3),
        deadline=deadline,
        source="manual",
    )
    return jsonify(priority.evaluate_task(task)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def api_update_task(task_id):
    """Edit nama, matkul, bobot nilai, tingkat kesulitan, atau deadline suatu tugas."""
    data = request.get_json(silent=True) or {}
    task = db.update_task(
        task_id,
        name=data.get("name"),
        course=data.get("course"),
        grade_weight=data.get("grade_weight"),
        difficulty=data.get("difficulty"),
        deadline=data.get("deadline"),
    )
    if task is None:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    return jsonify(priority.evaluate_task(task))


@app.route("/api/tasks/<int:task_id>/toggle", methods=["POST"])
def api_toggle_task(task_id):
    """Tandai tugas selesai (kalahkan monster) atau aktifkan kembali."""
    task = db.toggle_complete(task_id)
    if task is None:
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    return jsonify(priority.evaluate_task(task))


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    """Hapus tugas dari database."""
    if not db.delete_task(task_id):
        return jsonify({"error": "Tugas tidak ditemukan"}), 404
    return jsonify({"deleted": True})


# ---------- REST API Sumber Kalender (.ics) ----------

@app.route("/api/calendars", methods=["GET"])
def api_get_calendars():
    return jsonify(db.get_calendars())


@app.route("/api/calendars", methods=["POST"])
def api_add_calendar():
    """Tambahkan link .ics baru (Google Calendar, Apple Calendar, SCELE, dll) langsung dari web."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    url = (data.get("url") or "").strip()
    filter_mode = data.get("filter_mode", "tasks_only")
    if not name or not url:
        return jsonify({"error": "Nama kalender dan URL .ics wajib diisi"}), 400
    try:
        cal = db.add_calendar(name=name, url=url, filter_mode=filter_mode)
    except sqlite3.IntegrityError:
        return jsonify({"error": "URL kalender tersebut sudah terdaftar"}), 409
    sync_info = db.sync_scele_if_needed(force=True)
    return jsonify({"calendar": cal, "sync": sync_info}), 201


@app.route("/api/calendars/<int:cal_id>", methods=["DELETE"])
def api_delete_calendar(cal_id):
    if not db.delete_calendar(cal_id):
        return jsonify({"error": "Kalender tidak ditemukan"}), 404
    return jsonify({"deleted": True})


@app.route("/api/sync", methods=["POST"])
def api_sync_scele():
    """Paksa sinkronisasi semua kalender .ics sekarang juga."""
    result = db.sync_scele_if_needed(force=True)
    status = 500 if "error" in result else 200
    return jsonify(result), status


if __name__ == "__main__":
    # Pakai port 5001 agar tidak bentrok dengan AirPlay Receiver macOS di port 5000
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="127.0.0.1", port=port)
