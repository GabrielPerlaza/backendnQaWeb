let dailyChart;
let projectChart;

async function loadDashboardCharts() {
  const response = await fetch("/api/dashboard/charts/");
  const data = await response.json();

  // ===== DAILY CHART =====
  const dailyLabels = data.daily.map(item => item.date);
  const dailyValues = data.daily.map(item => item.cases);

  if (!dailyChart) {
    dailyChart = new Chart(
      document.getElementById("dailyMetricsChart"),
      {
        type: "line",
        data: {
          labels: dailyLabels,
          datasets: [{
            label: "Casos Generados",
            data: dailyValues,
            tension: 0.4,
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } }
        }
      }
    );
  } else {
    dailyChart.data.labels = dailyLabels;
    dailyChart.data.datasets[0].data = dailyValues;
    dailyChart.update();
  }

  // ===== PROJECT CHART =====
  const projectLabels = data.projects.map(p => p["project__name"]);
  const projectValues = data.projects.map(p => p.cases);

  if (!projectChart) {
    projectChart = new Chart(
      document.getElementById("projectMetricsChart"),
      {
        type: "bar",
        data: {
          labels: projectLabels,
          datasets: [{
            label: "Casos por Proyecto",
            data: projectValues,
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } }
        }
      }
    );
  } else {
    projectChart.data.labels = projectLabels;
    projectChart.data.datasets[0].data = projectValues;
    projectChart.update();
  }
}

// Primera carga
loadDashboardCharts();

// Actualizar cada 15 segundos
setInterval(loadDashboardCharts, 15000);
