// Starter JS — menghubungkan tampilan dengan REST API Flask (/api/tasks)

async function loadTasks() {
  const res = await fetch("/api/tasks");
  const tasks = await res.json();
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
          <div style="font-size: 13px; color: #555; margin-top: 4px;">
            Bobot: ${t.grade_weight}% · Kesulitan: ${t.difficulty}/5 · Deadline: ${t.deadline.replace("T", " ")} · <em>${t.recommendation}</em>
          </div>
        </div>
        <div class="actions">
          <button onclick="toggleTask(${t.id})">${t.completed ? "Aktifkan" : "Kalahkan"}</button>
          <button onclick="deleteTask(${t.id})">Hapus</button>
        </div>
      </div>
    `
    )
    .join("");
}

async function toggleTask(id) {
  await fetch(`/api/tasks/${id}/toggle`, { method: "POST" });
  loadTasks();
}

async function deleteTask(id) {
  await fetch(`/api/tasks/${id}`, { method: "DELETE" });
  loadTasks();
}

document.getElementById("task-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById("name").value,
    course: document.getElementById("course").value,
    grade_weight: parseFloat(document.getElementById("grade_weight").value || 0),
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
