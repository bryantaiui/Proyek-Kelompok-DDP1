"""Entry point website (Flask) — menghubungkan Database, Mekanik Prioritas, dan Desain."""
from flask import Flask, jsonify, render_template, request

from database import db
from mechanics import priority

app = Flask(__name__)

# Inisialisasi database saat server dimulai
db.init_db()
db.seed_sample_if_empty()


@app.route("/")
def index():
    """Halaman utama (template berada di templates/index.html)."""
    return render_template("index.html")


# ---------- REST API untuk Frontend & Integrasi ----------

@app.route("/api/tasks", methods=["GET"])
def api_get_tasks():
    """Ambil semua tugas yang sudah diproses skor prioritas & tier monsternya."""
    raw_tasks = db.get_all_tasks()
    ranked = priority.rank_tasks(raw_tasks)
    return jsonify(ranked)


@app.route("/api/tasks", methods=["POST"])
def api_add_task():
    """Tambah tugas baru ke database."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    deadline = (data.get("deadline") or "").strip()
    if not name or not deadline:
        return jsonify({"error": "name dan deadline wajib diisi"}), 400

    task = db.add_task(
        name=name,
        course=(data.get("course") or "").strip(),
        grade_weight=data.get("grade_weight", 0),
        difficulty=data.get("difficulty", 3),
        deadline=deadline,
    )
    return jsonify(priority.evaluate_task(task)), 201


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


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
