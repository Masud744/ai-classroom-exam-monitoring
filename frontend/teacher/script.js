let currentFilter = null;
let attChart, suspChart, behavChart;

const user = JSON.parse(localStorage.getItem('user') || 'null');
if (!user) window.location.href = '../index.html';
document.getElementById('welcomeText').textContent =
  user?.user_metadata?.full_name || user?.email || '';

function logout() {
  localStorage.clear();
  window.location.href = '../index.html';
}

function initCharts() {
  const opts = () => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#555', font: { size: 10 } }, grid: { color: '#1e1e2e' } },
      y: { min: 0, max: 100, ticks: { color: '#555' }, grid: { color: '#1e1e2e' } }
    }
  });

  attChart = new Chart(document.getElementById('attentionChart'), {
    type: 'line',
    data: { labels: [], datasets: [{ data: [], borderColor: '#4ade80', backgroundColor: '#4ade8011', tension: 0.4, fill: true, pointRadius: 3 }] },
    options: opts()
  });

  suspChart = new Chart(document.getElementById('suspiciousChart'), {
    type: 'line',
    data: { labels: [], datasets: [{ data: [], borderColor: '#f87171', backgroundColor: '#f8717111', tension: 0.4, fill: true, pointRadius: 3 }] },
    options: opts()
  });

  behavChart = new Chart(document.getElementById('behaviorChart'), {
    type: 'doughnut',
    data: {
      labels: ['Phone Detected', 'Talking', 'Eyes Closed', 'Looking Away'],
      datasets: [{
        data: [0, 0, 0, 0],
        backgroundColor: ['#f87171', '#fbbf24', '#818cf8', '#34d399'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#888', font: { size: 11 }, padding: 12 }
        }
      }
    }
  });
}

function applyFilter() {
  const val = document.getElementById('studentFilter').value.trim();
  if (!val) return;
  currentFilter = val;
  document.getElementById('filterStatus').textContent = `Showing: ${val}`;
  loadData();
}

function clearFilter() {
  currentFilter = null;
  document.getElementById('studentFilter').value = '';
  document.getElementById('filterStatus').textContent = '';
  loadData();
}

async function loadData() {
  document.getElementById('logsBody').innerHTML =
    '<tr><td colspan="9" style="text-align:center;color:#666;padding:24px;">Loading... (first load may take 50s)</td></tr>';
  try {
    const url = currentFilter
      ? `${API}/logs/${encodeURIComponent(currentFilter)}`
      : `${API}/logs`;

    const res  = await fetch(url);
    const data = await res.json();
    const logs = data.logs || [];

    if (logs.length === 0) {
      document.getElementById('logsBody').innerHTML =
        '<tr><td colspan="9" style="text-align:center;color:#666;padding:24px;">No logs found</td></tr>';
      document.getElementById('totalLogs').textContent     = 0;
      document.getElementById('avgAttention').textContent  = '—';
      document.getElementById('avgSuspicious').textContent = '—';
      document.getElementById('highAlerts').textContent    = 0;
      document.getElementById('alertList').innerHTML =
        '<p style="color:#666;font-size:13px;">No suspicious events</p>';
      return;
    }

    document.getElementById('totalLogs').textContent = logs.length;
    const avgAtt  = Math.round(logs.reduce((s, l) => s + l.attention_score, 0) / logs.length);
    const avgSusp = Math.round(logs.reduce((s, l) => s + l.suspicious_score, 0) / logs.length);
    const alerts  = logs.filter(l => l.suspicious_score >= 50).length;
    document.getElementById('avgAttention').textContent  = avgAtt;
    document.getElementById('avgSuspicious').textContent = avgSusp;
    document.getElementById('highAlerts').textContent    = alerts;

    const recent = [...logs].reverse().slice(0, 20);
    const labels = recent.map(l =>
      new Date(l.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    );
    attChart.data.labels = labels;
    attChart.data.datasets[0].data = recent.map(l => l.attention_score);
    attChart.update();
    suspChart.data.labels = labels;
    suspChart.data.datasets[0].data = recent.map(l => l.suspicious_score);
    suspChart.update();

    behavChart.data.datasets[0].data = [
      logs.filter(l => l.phone_detected).length,
      logs.filter(l => l.talking).length,
      logs.filter(l => l.eyes_closed).length,
      logs.filter(l => !l.looking_forward).length,
    ];
    behavChart.update();

    const highSusp = logs.filter(l => l.suspicious_score >= 50).slice(0, 10);
    document.getElementById('alertList').innerHTML = highSusp.length === 0
      ? '<p style="color:#666;font-size:13px;">No suspicious events</p>'
      : highSusp.map(l => `
          <div class="alert-item">
            <div class="alert-info">
              <div>${l.student_id}</div>
              <div class="alert-time">${new Date(l.created_at).toLocaleString()}</div>
            </div>
            <div class="alert-score">${l.suspicious_score}</div>
          </div>`).join('');

    document.getElementById('logsBody').innerHTML = logs.slice(0, 50).map(l => `
      <tr>
        <td style="color:#666">${new Date(l.created_at).toLocaleString()}</td>
        <td>${l.student_id}</td>
        <td><span class="badge ${l.attention_score >= 70 ? 'success' : l.attention_score >= 40 ? 'warning' : 'danger'}">${l.attention_score}</span></td>
        <td><span class="badge ${l.suspicious_score >= 50 ? 'danger' : 'success'}">${l.suspicious_score}</span></td>
        <td><span class="dot ${l.phone_detected ? 'red' : 'green'}"></span>${l.phone_detected ? 'Yes' : 'No'}</td>
        <td>${l.talking ? 'Yes' : 'No'}</td>
        <td>${l.eyes_closed ? 'Closed' : 'Open'}</td>
        <td>${l.looking_forward ? 'Forward' : 'Away'}</td>
        <td>${l.face_count}</td>
      </tr>`).join('');

  } catch(e) {
    console.error(e);
  }
}

initCharts();
loadData();
setInterval(loadData, 10000);
setInterval(() => {
  fetch(`${API.replace('/api', '')}/`).catch(() => {});
}, 30000);
