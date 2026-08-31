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
      x: { 
        ticks: { color: '#6b7280', font: { size: 10, family: 'Inter' } }, 
        grid: { display: false } 
      },
      y: { 
        min: 0, 
        max: 100, 
        ticks: { color: '#6b7280', font: { family: 'Inter' } }, 
        grid: { color: 'rgba(255,255,255,0.04)' } 
      }
    },
    elements: {
      line: { borderWidth: 2.5 },
      point: { radius: 0, hoverRadius: 5 }
    },
    interaction: {
      intersect: false,
      mode: 'index'
    }
  });

  attChart = new Chart(document.getElementById('attentionChart'), {
    type: 'line',
    data: { 
      labels: [], 
      datasets: [{ 
        data: [], 
        borderColor: '#7c3aed', 
        backgroundColor: (context) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 200);
          gradient.addColorStop(0, 'rgba(124, 58, 237, 0.25)');
          gradient.addColorStop(1, 'rgba(124, 58, 237, 0)');
          return gradient;
        },
        tension: 0.4, 
        fill: true, 
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: '#7c3aed',
        pointHoverBorderColor: '#13162a',
        pointHoverBorderWidth: 2
      }] 
    },
    options: opts()
  });

  suspChart = new Chart(document.getElementById('suspiciousChart'), {
    type: 'line',
    data: { 
      labels: [], 
      datasets: [{ 
        data: [], 
        borderColor: '#a78bfa', 
        backgroundColor: (context) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 200);
          gradient.addColorStop(0, 'rgba(167, 139, 250, 0.25)');
          gradient.addColorStop(1, 'rgba(167, 139, 250, 0)');
          return gradient;
        },
        tension: 0.4, 
        fill: true, 
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: '#a78bfa',
        pointHoverBorderColor: '#13162a',
        pointHoverBorderWidth: 2
      }] 
    },
    options: opts()
  });

  behavChart = new Chart(document.getElementById('behaviorChart'), {
    type: 'doughnut',
    data: {
      labels: ['Phone Detected', 'Talking', 'Eyes Closed', 'Looking Away'],
      datasets: [{
        data: [0, 0, 0, 0],
        backgroundColor: ['#7c3aed', '#a78bfa', '#c4b5fd', '#3b82f6'],
        borderWidth: 0,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { 
            color: '#9ca3af', 
            font: { size: 11, family: 'Inter' }, 
            padding: 14,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        }
      },
      cutout: '72%'
    }
  });
}

let allStudentsList = [];
let allLogsCache = [];
let searchQuery = '';

async function loadStudents() {
  try {
    const res  = await fetch(`${API}/students`);
    const data = await res.json();
    allStudentsList = data.students || [];

    const countElem = document.getElementById('totalStudentsCount');
    if (countElem) {
      countElem.textContent = allStudentsList.length;
    }

    renderStudentDropdown();
  } catch(e) {
    console.error(e);
  }
}

function renderStudentDropdown() {
  const select = document.getElementById('studentSelect');
  if (!select) return;

  const currentVal = currentFilter || '';
  select.innerHTML = '<option value="">— All Students —</option>';

  const filtered = searchQuery
    ? allStudentsList.filter(s =>
        (s.name && s.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (s.id && s.id.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : allStudentsList;

  filtered.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = s.name;
    if (s.id === currentVal) opt.selected = true;
    select.appendChild(opt);
  });
}

function handleStudentSearch(val) {
  searchQuery = (val || '').trim();
  renderStudentDropdown();

  if (searchQuery) {
    currentFilter = null;
    const select = document.getElementById('studentSelect');
    if (select) select.value = '';
  }

  applyCurrentFilterAndSearch();
}

function applySelectFilter() {
  const select = document.getElementById('studentSelect');
  const val = select ? select.value : '';
  currentFilter = val || null;

  if (currentFilter) {
    const searchInput = document.getElementById('studentSearch');
    if (searchInput) searchInput.value = '';
    searchQuery = '';
  }

  loadData();
}

function applyCurrentFilterAndSearch() {
  let filteredLogs = [...allLogsCache];

  if (currentFilter) {
    filteredLogs = filteredLogs.filter(l => l.student_id === currentFilter);
  } else if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filteredLogs = filteredLogs.filter(l =>
      (l.student_name && l.student_name.toLowerCase().includes(q)) ||
      (l.student_id && l.student_id.toLowerCase().includes(q))
    );
  }

  updateUI(filteredLogs);
}

function updateUI(logs) {
  if (logs.length === 0) {
    document.getElementById('logsBody').innerHTML =
      '<tr><td colspan="9" style="text-align:center;color:#666;padding:24px;">No logs found</td></tr>';
    document.getElementById('totalLogs').textContent     = 0;
    document.getElementById('avgAttention').textContent  = '—';
    document.getElementById('avgSuspicious').textContent = '—';
    document.getElementById('highAlerts').textContent    = 0;
    document.getElementById('alertList').innerHTML =
      '<p style="color:#666;font-size:13px;">No suspicious events</p>';
    attChart.data.labels = [];
    attChart.data.datasets[0].data = [];
    attChart.update();
    suspChart.data.labels = [];
    suspChart.data.datasets[0].data = [];
    suspChart.update();
    return;
  }

  // Stats
  document.getElementById('totalLogs').textContent = logs.length;
  const avgAtt  = Math.round(logs.reduce((s, l) => s + l.attention_score, 0) / logs.length);
  const avgSusp = Math.round(logs.reduce((s, l) => s + l.suspicious_score, 0) / logs.length);
  const alerts  = logs.filter(l => l.suspicious_score >= 50).length;
  document.getElementById('avgAttention').textContent  = avgAtt;
  document.getElementById('avgSuspicious').textContent = avgSusp;
  document.getElementById('highAlerts').textContent    = alerts;

  // Charts
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

  // Behavior
  behavChart.data.datasets[0].data = [
    logs.filter(l => l.phone_detected).length,
    logs.filter(l => l.talking).length,
    logs.filter(l => l.eyes_closed).length,
    logs.filter(l => !l.looking_forward).length,
  ];
  behavChart.update();

  // Alert list
  const highSusp = logs.filter(l => l.suspicious_score >= 50).slice(0, 10);
  document.getElementById('alertList').innerHTML = highSusp.length === 0
    ? '<p style="color:#666;font-size:13px;">No suspicious events</p>'
    : highSusp.map(l => `
        <div class="alert-item">
          <div class="alert-info">
            <div>${l.student_name || l.student_id}</div>
            <div class="alert-time">${new Date(l.created_at).toLocaleString()}</div>
          </div>
          <div class="alert-score">${l.suspicious_score}</div>
        </div>`).join('');

  // Table
  document.getElementById('logsBody').innerHTML = logs.slice(0, 50).map(l => `
    <tr>
      <td style="color:#666">${new Date(l.created_at).toLocaleString()}</td>
      <td>${l.student_name || l.student_id}</td>
      <td><span class="badge ${l.attention_score >= 70 ? 'success' : l.attention_score >= 40 ? 'warning' : 'danger'}">${l.attention_score}</span></td>
      <td><span class="badge ${l.suspicious_score >= 50 ? 'danger' : 'success'}">${l.suspicious_score}</span></td>
      <td><span class="dot ${l.phone_detected ? 'red' : 'green'}"></span>${l.phone_detected ? 'Yes' : 'No'}</td>
      <td>${l.talking ? 'Yes' : 'No'}</td>
      <td>${l.eyes_closed ? 'Closed' : 'Open'}</td>
      <td>${l.looking_forward ? 'Forward' : 'Away'}</td>
      <td>${l.face_count}</td>
    </tr>`).join('');
}

async function loadData() {
  const refreshBtn = document.querySelector('.refresh-btn');
  if (refreshBtn) refreshBtn.textContent = '↻ Loading...';

  try {
    const url = currentFilter
      ? `${API}/logs/${encodeURIComponent(currentFilter)}`
      : `${API}/logs`;

    const res  = await fetch(url);
    const data = await res.json();
    allLogsCache = data.logs || [];

    applyCurrentFilterAndSearch();

  } catch(e) {
    console.error(e);
    document.getElementById('logsBody').innerHTML =
      '<tr><td colspan="9" style="text-align:center;color:#f87171;padding:24px;">Server error. Retrying...</td></tr>';
  } finally {
    if (refreshBtn) refreshBtn.textContent = '↻ Refresh';
  }
}

initCharts();
loadStudents();
loadData();
setInterval(loadData, 10000);
setInterval(loadStudents, 30000);
setInterval(() => {
  fetch(`${API.replace('/api', '')}/`).catch(() => {});
}, 30000);