"""Mekanik Prioritas & Monster — Area: Game Mechanics.

Silakan ubah logika di file ini untuk menentukan:
- skor prioritas tiap tugas,
- tier monster (mis. Boss, Elite, Minion),
- rekomendasi urutan pengerjaan (kerjakan sekarang vs. bisa ditunda).

Input per tugas (dict dari database/db.py):
  {
      "id": int,
      "name": str,
      "course": str,
      "grade_weight": float,   # bobot persentase terhadap nilai semester (0-100)
      "difficulty": int,       # tingkat kesulitan (1-5)
      "deadline": str,         # ISO 8601, mis. "2026-12-09T23:59:00"
      "completed": int,        # 0 = aktif, 1 = sudah dikalahkan
  }
"""
from datetime import datetime


def evaluate_task(task: dict, now: datetime | None = None) -> dict:
    """Hitung skor prioritas & info monster untuk satu tugas.
    (Placeholder sederhana — silakan ganti dengan formula/algoritma tim mekanik.)
    """
    now = now or datetime.now()
    try:
        dl = datetime.fromisoformat(task["deadline"])
        days_left = max((dl - now).total_seconds() / 86400.0, 0.1)
    except ValueError:
        days_left = 7.0

    # Formula placeholder: bobot nilai * kesulitan / urgensi waktu
    urgency = 10.0 / days_left
    score = round((task.get("grade_weight", 0) * 1.5) + (task.get("difficulty", 1) * 5) + urgency, 2)

    if score >= 45:
        monster_tier = "Boss"
        recommendation = "Kerjakan sekarang"
    elif score >= 25:
        monster_tier = "Elite"
        recommendation = "Kerjakan hari ini"
    else:
        monster_tier = "Minion"
        recommendation = "Bisa dikerjakan nanti"

    enriched = dict(task)
    enriched["priority_score"] = score
    enriched["monster_tier"] = monster_tier
    enriched["recommendation"] = recommendation
    return enriched


def rank_tasks(tasks: list[dict], now: datetime | None = None) -> list[dict]:
    """Proses semua tugas dan urutkan dari monster terbesar (prioritas tertinggi)."""
    evaluated = [evaluate_task(t, now=now) for t in tasks]
    # Tugas belum selesai di atas, diurutkan dari skor tertinggi
    return sorted(evaluated, key=lambda t: (t["completed"], -t["priority_score"]))
