// Starter JS — menghubungkan tampilan dengan REST API Flask (/api/tasks, /api/calendars, /api/sync)

function updateSyncStatus(sync) {
  const el = document.getElementById("sync-status");
  if (!sync || !el) return;
  if (sync.synced) {
    el.textContent = `Tersinkron (+${sync.added} baru, ${sync.total} total) pada ${sync.last_sync_at.replace("T", " ")}`;
  } else if (sync.reason === "throttled" && sync.last_sync_at) {
    el.textContent = `Sync terakhir: ${sync.last_sync_at.replace("T", " ")}`;
  } else if (sync.error) {
    el.textContent = `Gagal sync (${sync.error})`;
  } else if (sync.reason === "no_url") {
    el.textContent = "Belum ada kalender .ics terdaftar";
  }
}

async function loadCalendars() {
  const res = await fetch("/api/calendars");
  const cals = await res.json();
  const box = document.getElementById("cal-list");
  if (!cals.length) {
    box.textContent = "Belum ada kalender terhubung.";
    return;
  }
  box.innerHTML = cals
    .map(
      (c) => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #eee;">
        <span>
          <strong>${c.name}</strong>
          <span style="color: #777;">(${c.filter_mode === "all" ? "semua event" : "filter tugas/deadline"})</span>
          ${c.last_sync_at ? `· sync: ${c.last_sync_at.replace("T", " ")}` : ""}
        </span>
        <button onclick="deleteCalendar(${c.id})" style="padding: 3px 8px; cursor: pointer;">Hapus</button>
      </div>
    `
    )
    .join("");
}

async function deleteCalendar(id) {
  await fetch(`/api/calendars/${id}`, { method: "DELETE" });
  loadCalendars();
}

async function loadTasks() {
  const list = document.getElementById("task-list");
  const res = await fetch("/api/tasks");
  if (!res.ok) {
    list.innerHTML = `<p style="color:#b91c1c;">Gagal memuat tugas (HTTP ${res.status}). Cek log terminal.</p>`;
    return;
  }
  const data = await res.json();
  const tasks = Array.isArray(data) ? data : data.tasks || [];
  updateSyncStatus(data.sync);

  if (!tasks.length) {
    list.innerHTML = "<p>Belum ada tugas.</p>";
    return;
  }

  list.innerHTML = tasks
    .map(
      (t) => `
      <div class="task-item ${t.completed ? "done" : ""}">
        <div>
          <span class="badge ${t.monster_tier}">${t.monster_tier} (${t.priority_score})</span>
          <strong>${t.name}</strong> ${t.course ? `· ${t.course}` : ""}
          <span style="font-size: 11px; color: #777;">[${t.source}]</span>
          <div style="font-size: 13px; color: #555; margin-top: 4px;">
            Bobot: ${t.grade_weight}% · Kesulitan: ${t.difficulty}/5 · Deadline: ${t.deadline.replace("T", " ")} · <em>${t.recommendation}</em>
          </div>
        </div>
        <div class="actions">
          <button onclick="editTask(${t.id}, ${t.grade_weight}, ${t.difficulty})">Edit Bobot/Kesulitan</button>
          <button onclick="toggleTask(${t.id})">${t.completed ? "Aktifkan" : "Kalahkan"}</button>
          <button onclick="deleteTask(${t.id})">Hapus</button>
        </div>
      </div>
    `
    )
    .join("");
}

async function editTask(id, currentWeight, currentDifficulty) {
  const wStr = prompt("Bobot nilai terhadap semester (%):", currentWeight);
  if (wStr === null) return;
  const dStr = prompt("Tingkat kesulitan (1 - 5):", currentDifficulty);
  if (dStr === null) return;

  const grade_weight = parseFloat(wStr);
  const difficulty = parseInt(dStr, 10);
  if (Number.isNaN(grade_weight) || Number.isNaN(difficulty)) {
    alert("Masukkan angka yang valid.");
    return;
  }

  await fetch(`/api/tasks/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grade_weight, difficulty }),
  });
  loadTasks();
}

async function toggleTask(id) {
  await fetch(`/api/tasks/${id}/toggle`, { method: "POST" });
  loadTasks();
}

async function deleteTask(id) {
  await fetch(`/api/tasks/${id}`, { method: "DELETE" });
  loadTasks();
}

document.getElementById("sync-btn").addEventListener("click", async () => {
  const el = document.getElementById("sync-status");
  el.textContent = "Menyinkronkan kalender...";
  const res = await fetch("/api/sync", { method: "POST" });
  const sync = await res.json();
  updateSyncStatus(sync);
  loadCalendars();
  loadTasks();
});

document.getElementById("cal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const res = await fetch("/api/calendars", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: document.getElementById("cal-name").value,
      url: document.getElementById("cal-url").value,
      filter_mode: document.getElementById("cal-filter").value,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.error || "Gagal menambah kalender");
    return;
  }
  e.target.reset();
  loadCalendars();
  loadTasks();
});

document.getElementById("task-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById("name").value,
    course: document.getElementById("course").value,
    grade_weight: parseFloat(document.getElementById("grade_weight").value || 5),
    difficulty: parseInt(document.getElementById("difficulty").value || 3, 10),
    deadline: document.getElementById("deadline").value,
  };
  await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  e.target.reset();
  loadTasks();
});

loadCalendars();
loadTasks();
