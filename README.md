# Proyek Kelompok DDP1 — Homework Monster Game

Starter website berbasis **Python (Flask) + SQLite** untuk proyek akhir Dasar-Dasar Pemrograman 1 (AI Major, Fasilkom UI).

## Pembagian Folder Tim

Struktur dipisah agar tiap anggota bisa bekerja di **branch masing-masing** tanpa saling konflik:

| Peran | Folder / File | Tanggung Jawab |
|---|---|---|
| **Desain (Frontend)** | `templates/`, `static/` | Tampilan website, animasi/visual monster, layout game |
| **Mekanik (Priority)** | `mechanics/priority.py` | Rumus prioritas, tier monster (Boss/Elite/Minion), rekomendasi urutan kerja |
| **Database & Integrasi** | `database/db.py` | Skema SQLite, CRUD data tugas, dan sinkronisasi kalender SCELE (`.ics`) |
| **Penghubung Server** | `app.py` | Routing Flask & REST API (`/api/tasks`) |

## Cara Menjalankan di Localhost

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka di browser: **http://127.0.0.1:5000**

## Alur Kerja Git (Branch per Anggota)

```bash
git pull origin main
git checkout -b nama/fitur       # contoh: neil/database-scele, daffa/mechanic, teman/design
# ... edit bagian masing-masing ...
git add .
git commit -m "Jelaskan perubahan"
git push -u origin nama/fitur
```
