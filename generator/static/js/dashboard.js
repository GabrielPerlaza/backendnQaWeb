async function refreshDashboardMetrics() {
  try {
    const response = await fetch("/api/dashboard/metrics/");
    const data = await response.json();

    document.getElementById("kpi-cases").innerText = data.total_cases;
    document.getElementById("kpi-projects").innerText = data.total_projects;
    document.getElementById("kpi-time").innerText = data.time_saved + " min";
    document.getElementById("kpi-accuracy").innerText = data.accuracy + "%";

    if (data.last_activity) {
      document.getElementById("last-activity").innerHTML = `
        <p class="text-slate-300">${data.last_activity.content}</p>
        <p class="text-xs text-slate-500 mt-1">${data.last_activity.created_at}</p>
      `;
    }

  } catch (error) {
    console.error("Error actualizando métricas:", error);
  }
}

// Actualizar cada 10 segundos
setInterval(refreshDashboardMetrics, 10000);
// Cargar métricas al iniciar
refreshDashboardMetrics();