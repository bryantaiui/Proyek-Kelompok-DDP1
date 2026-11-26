"""Pengambil & parser kalender SCELE (.ics) — Area: Database (Neil).

Mengubah event kalender Moodle/SCELE menjadi list of dict yang siap disimpan ke SQLite:
  {"uid", "name", "course", "grade_weight", "difficulty", "deadline", "source"}
"""
import os
import re
import ssl
import urllib.request
from datetime import date, datetime, timedelta, timezone

import certifi
from icalendar import Calendar

WIB = timezone(timedelta(hours=7))

# Event yang menandakan tenggat tugas/ujian
_POLA_TUGAS = re.compile(
    r"\b(is due|closes|due|tugas|tp\b|lab\b|kuis|quiz|proyek|project|pr\b|uts|uas|ujian|deadline)\b",
    re.I,
)
# Event yang BUKAN tugas (jadwal kelas, waktu buka kuis, libur)
_POLA_ABAIKAN = re.compile(r"\b(opens|kelas|kuliah|materi|libur)\b", re.I)


def _bersihkan_nama(nama: str) -> str:
    nama = re.sub(r"\s+(is due|closes|due)$", "", nama.strip(), flags=re.I)
    return re.sub(r"^Pre-Class\s+", "", nama, flags=re.I).strip()


def _bersihkan_matkul(matkul: str | None) -> str:
    if not matkul:
        return ""
    # Contoh: "DDP1-GSL2026" -> "DDP1"
    return re.split(r"[-_ ]", matkul.split(",")[0].strip())[0]


def _ke_wib_iso(nilai) -> str:
    """Ubah DTSTART dari .ics menjadi string ISO 8601 WIB tanpa offset (cocok untuk HTML datetime-local)."""
    if isinstance(nilai, datetime):
        if nilai.tzinfo is None:
            nilai = nilai.replace(tzinfo=timezone.utc)
        return nilai.astimezone(WIB).strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(nilai, date):
        return f"{nilai.year:04d}-{nilai.month:02d}-{nilai.day:02d}T23:59:00"
    raise ValueError(f"Format tanggal .ics tidak dikenal: {nilai!r}")


def estimasi_bobot_kesulitan(nama: str) -> tuple[float, int]:
    """Estimasi awal (grade_weight %, difficulty 1-5) untuk tugas dari SCELE.
    Nilai ini bisa diedit bebas oleh pengguna di website dan tidak akan ditimpa saat sync ulang."""
    n = nama.lower()
    if any(k in n for k in ("proyek", "project", "final")):
        return 25.0, 5
    if any(k in n for k in ("uts", "uas", "ujian", "exam")):
        return 20.0, 5
    if any(k in n for k in ("tp ", "tp-", "tugas", "pr ", "assignment")):
        return 10.0, 4
    if any(k in n for k in ("lab", "praktikum")):
        return 5.0, 3
    if any(k in n for k in ("kuis", "quiz")):
        return 2.0, 2
    return 5.0, 3


def parse_ics(data: bytes) -> list[dict]:
    cal = Calendar.from_ical(data)
    hasil = []
    for ev in cal.walk("VEVENT"):
        if ev.get("UID") is None or ev.get("DTSTART") is None:
            continue
        raw_summary = str(ev.get("SUMMARY", "")).strip()
        if not raw_summary or _POLA_ABAIKAN.search(raw_summary):
            continue
        if not _POLA_TUGAS.search(raw_summary):
            continue

        kategori = ev.get("CATEGORIES")
        matkul_raw = None
        if kategori is not None:
            cats = kategori if isinstance(kategori, list) else [kategori]
            matkul_raw = ", ".join(str(x) for c in cats for x in getattr(c, "cats", [c]))

        nama = _bersihkan_nama(raw_summary)
        bobot, kesulitan = estimasi_bobot_kesulitan(nama)
        hasil.append({
            "uid": str(ev["UID"]),
            "name": nama,
            "course": _bersihkan_matkul(matkul_raw),
            "grade_weight": bobot,
            "difficulty": kesulitan,
            "deadline": _ke_wib_iso(ev["DTSTART"].dt),
            "source": "scele",
        })
    return hasil


def fetch_scele_tasks(timeout: int = 20) -> list[dict]:
    """Ambil tugas dari SCELE_ICS_URL (atau SCELE_ICS_FILE untuk tes offline) di .env."""
    file_path = os.environ.get("SCELE_ICS_FILE")
    if file_path:
        with open(file_path, "rb") as f:
            return parse_ics(f.read())
    url = os.environ.get("SCELE_ICS_URL")
    if not url:
        raise RuntimeError("SCELE_ICS_URL belum diatur di file .env")
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
        return parse_ics(resp.read())
