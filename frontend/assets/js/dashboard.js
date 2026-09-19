const currencyFmt = (n) => Number(n || 0).toLocaleString('fa-IR');

async function loadDashboard() {
  const [overviewRes, healthRes, trendsRes, categoriesRes, insightsRes] = await Promise.all([
    apiFetch('/analytics/dashboard/'),
    apiFetch('/analytics/health/'),
    apiFetch('/analytics/trends/'),
    apiFetch('/analytics/categories/'),
    apiFetch('/analytics/insights/')
  ]);

  if (overviewRes && overviewRes.ok) renderStats(await overviewRes.json());
  if (healthRes && healthRes.ok) renderHealth(await healthRes.json());
  if (trendsRes && trendsRes.ok) renderTrends(await trendsRes.json());
  if (categoriesRes && categoriesRes.ok) renderCategories(await categoriesRes.json());
  if (insightsRes && insightsRes.ok) renderInsights(await insightsRes.json());
}

function changeBadge(percent) {
  if (percent === undefined || percent === null) return '';
  const cls = percent >= 0 ? 'up' : 'down';
  const arrow = percent >= 0 ? '▲' : '▼';
  return `<span class="change-badge ${cls}">${arrow} ${Math.abs(percent).toFixed(1)}٪ نسبت به ماه قبل</span>`;
}

// بر اساس DashboardSerializer واقعی — فیلدها دقیقاً همینا هستن
function renderStats(data) {
  document.getElementById('stat-income').innerHTML =
    `${currencyFmt(data.total_income)}<br>${changeBadge(data.income_change_percentage)}`;
  document.getElementById('stat-expense').innerHTML =
    `${currencyFmt(data.total_expense)}<br>${changeBadge(data.expense_change_percentage)}`;
  document.getElementById('stat-net').innerHTML =
    `${currencyFmt(data.total_savings)}<br>${changeBadge(data.savings_change_percentage)}`;

  document.getElementById('mini-savings-rate').textContent = `${data.savings_rate.toFixed(1)}٪`;
  document.getElementById('mini-budget-usage').textContent = `${data.budget_usage_percentage.toFixed(1)}٪`;
  document.getElementById('mini-budgets-exceeded').textContent = data.budgets_exceeded;
  document.getElementById('mini-goals').textContent = `${data.active_goals} فعال / ${data.completed_goals} تکمیل‌شده`;
  document.getElementById('mini-alerts').textContent = data.alerts_count;
}

// بر اساس FinancialHealthSerializer: score, level, breakdown (dict آزاد), suggestions
function renderHealth(data) {
  const score = data.score;
  const circle = document.getElementById('health-arc');
  const circumference = 2 * Math.PI * 70;
  const offset = circumference - (score / 100) * circumference;
  circle.style.strokeDasharray = circumference;
  circle.style.strokeDashoffset = offset;
  circle.style.stroke = score >= 75 ? 'var(--teal)' : score >= 45 ? 'var(--gold)' : 'var(--coral)';
  document.getElementById('health-score-num').textContent = Math.round(score);
  document.getElementById('health-level').textContent = data.level || '';

  // breakdown یه دیکشنری آزاده، کلیدهاش رو نمی‌دونیم، پس عمومی رندر می‌کنیم
  const breakdownEl = document.getElementById('health-breakdown');
  breakdownEl.innerHTML = '';
  Object.entries(data.breakdown || {}).forEach(([key, val]) => {
    const row = document.createElement('div');
    row.className = 'breakdown-row';
    const label = key.replace(/_/g, ' ');
    row.innerHTML = `<span>${label}</span><span class="mono">${val}</span>`;
    breakdownEl.appendChild(row);
  });

  const suggestionsEl = document.getElementById('health-suggestions');
  suggestionsEl.innerHTML = '';
  (data.suggestions || []).forEach(text => {
    const item = document.createElement('div');
    item.className = 'suggestion-item';
    item.textContent = `💡 ${text}`;
    suggestionsEl.appendChild(item);
  });
}

let trendChart, categoryChart;

// بر اساس MonthlyTrendSerializer: month, income, expense, savings, savings_rate
function renderTrends(list) {
  const data = Array.isArray(list) ? list : (list.results || []);
  const labels = data.map(i => i.month);
  const incomes = data.map(i => Number(i.income));
  const expenses = data.map(i => Number(i.expense));

  const ctx = document.getElementById('trend-chart');
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'درآمد', data: incomes, borderColor: '#0F6B5C', backgroundColor: 'rgba(15,107,92,.12)', tension: .35, fill: true },
        { label: 'هزینه', data: expenses, borderColor: '#E15252', backgroundColor: 'rgba(225,82,82,.10)', tension: .35, fill: true }
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { rtl: true, labels: { font: { family: 'Vazirmatn' } } } },
      scales: {
        x: { ticks: { font: { family: 'JetBrains Mono', size: 11 } } },
        y: { ticks: { font: { family: 'JetBrains Mono', size: 11 } } }
      }
    }
  });
}

// بر اساس CategoryExpenseSerializer: category_name, total_amount, percentage
function renderCategories(list) {
  const data = Array.isArray(list) ? list : (list.results || []);
  const labels = data.map(i => i.category_name);
  const totals = data.map(i => Number(i.total_amount));
  const palette = ['#0F6B5C', '#C9A227', '#E15252', '#5B6472', '#16997F', '#E0BE4C', '#8892A0'];

  const ctx = document.getElementById('category-chart');
  if (categoryChart) categoryChart.destroy();
  categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: totals, backgroundColor: palette, borderWidth: 0 }] },
    options: {
      responsive: true,
      cutout: '68%',
      plugins: { legend: { position: 'bottom', rtl: true, labels: { font: { family: 'Vazirmatn', size: 12 } } } }
    }
  });
}

// بر اساس SmartInsightSerializer: type, title, message, impact
function renderInsights(list) {
  const data = Array.isArray(list) ? list : (list.results || []);
  const wrap = document.getElementById('insights-list');
  wrap.innerHTML = '';
  if (!data.length) {
    wrap.innerHTML = '<p class="empty-note">فعلاً بینشی برای نمایش نیست.</p>';
    return;
  }
  data.forEach(item => {
    const li = document.createElement('div');
    li.className = 'insight-item';
    li.innerHTML = `
      <span class="insight-dot"></span>
      <span>
        <strong>${item.title}</strong> — ${item.message}
        <span class="insight-impact">${item.impact}</span>
      </span>`;
    wrap.appendChild(li);
  });
}

loadDashboard();