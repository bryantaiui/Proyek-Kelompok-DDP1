// Starter JS — menghubungkan tampilan dengan REST API Flask (/api/tasks & /api/sync)

function updateSyncStatus(sync) {
  const el = document.getElementById("sync-status");
  if (!sync || !el) return;
  if (sync.synced) {
    el.textContent = `Tersinkron SCELE (+${sync.added} baru, ${sync.total} total) pada ${sync.last_sync_at.replace("T", " ")}`;
  } else if (sync.reason === "throttled" && sync.last_sync_at) {
    el.textContent = `Sync terakhir: ${sync.last_sync_at.replace("T", " ")}`;
  } else if (sync.error) {
    el.textContent = `Gagal sync SCELE (${sync.error})`;
  } else if (sync.reason === "no_url") {
    el.textContent = "SCELE_ICS_URL belum diisi di .env";
  }
}

async function loadTasks() {
  const res = await fetch("/api/tasks");
  const data = await res.json();
  const tasks = Array.isArray(data) ? data : data.tasks || [];
  updateSyncStatus(data.sync);

  const list = document.getElementById("task-list");
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
  el.textContent = "Menyinkronkan dengan SCELE...";
  const res = await fetch("/api/sync", { method: "POST" });
  const sync = await res.json();
  updateSyncStatus(sync);
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

loadTasks();
