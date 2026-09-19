(() => {
  const fa = (n) => Number(n || 0).toLocaleString('fa-IR');
  const $ = (id) => document.getElementById(id);

  const LEVELS = { Excellent: 'عالی', Good: 'خوب', Fair: 'متوسط', Poor: 'ضعیف' };
  const IMPACTS = { positive: 'مثبت', negative: 'منفی', neutral: 'خنثی' };
  // کلیدهای breakdown از calculate_financial_health_score در analytics/views.py
  const HEALTH_PARTS = [
    ['savings_rate_score', 'نرخ پس‌انداز', 30],
    ['budget_adherence_score', 'پایبندی به بودجه', 30],
    ['income_stability_score', 'ثبات درآمد', 20],
    ['expense_ratio_score', 'نسبت هزینه به درآمد', 20],
  ];
  const PALETTE = ['#0F6B5C', '#C9A227', '#E15252', '#5B6472', '#16997F', '#E0BE4C', '#8892A0'];

  let trendChart, categoryChart;
  let categoryPeriod = 'monthly';

  /* ---------- کمکی‌ها ---------- */
  async function getJSON(path) {
    const res = await apiFetch(path);
    if (!res) throw new Error('redirect');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
  const asList = (d) => (Array.isArray(d) ? d : (d.results || []));

  function getPeriod() {
    const m = /^(\d{4})-(\d{2})$/.exec($('period').value);
    if (m && +m[2] >= 1 && +m[2] <= 12) return { year: +m[1], month: +m[2] };
    const d = new Date();
    return { year: d.getFullYear(), month: d.getMonth() + 1 };
  }

  // اگر داده‌ای نبود، به‌جای کانواس خالی یک پیام نشان می‌دهد
  function setNote(canvas, text) {
    const card = canvas.parentElement;
    let note = card.querySelector('.empty-note');
    if (!text) {
      if (note) note.remove();
      canvas.style.display = '';
      return;
    }
    if (!note) {
      note = document.createElement('p');
      note.className = 'empty-note';
      card.appendChild(note);
    }
    note.textContent = text;
    canvas.style.display = 'none';
  }

  /* ---------- امتیاز سلامت ---------- */
  function renderHealth(data) {
    const score = Math.max(0, Math.min(100, Number(data.score) || 0));
    const circle = $('health-arc');
    const circumference = 2 * Math.PI * 70;
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = circumference - (score / 100) * circumference;
    circle.style.stroke = score >= 75 ? 'var(--teal)' : score >= 45 ? 'var(--gold)' : 'var(--coral)';
    $('health-score-num').textContent = fa(Math.round(score));
    $('health-level').textContent = LEVELS[data.level] || data.level || '';

    const breakdownEl = $('health-breakdown');
    breakdownEl.innerHTML = '';
    HEALTH_PARTS.forEach(([key, label, max]) => {
      const row = document.createElement('div');
      row.className = 'breakdown-row';
      const name = document.createElement('span');
      name.textContent = label;
      const val = document.createElement('span');
      val.className = 'mono';
      val.textContent = `${fa((data.breakdown || {})[key])} / ${fa(max)}`;
      row.append(name, val);
      breakdownEl.appendChild(row);
    });

    const suggestionsEl = $('health-suggestions');
    suggestionsEl.innerHTML = '';
    (data.suggestions || []).forEach((text) => {
      const item = document.createElement('div');
      item.className = 'suggestion-item';
      item.textContent = `💡 ${text}`;
      suggestionsEl.appendChild(item);
    });
  }

  async function loadHealth() {
    try {
      renderHealth(await getJSON(`/analytics/health/?months=${$('health-months').value}`));
    } catch (e) {
      if (e.message === 'redirect') return;
      $('health-score-num').textContent = '—';
      $('health-level').textContent = 'خطا در دریافت امتیاز';
    }
  }

  /* ---------- روند ماهانه ---------- */
  async function loadTrends() {
    const canvas = $('trend-chart');
    try {
      const rows = asList(await getJSON(`/analytics/trends/?months=${$('trend-months').value}`));
      if (trendChart) { trendChart.destroy(); trendChart = null; }
      if (!rows.length) { setNote(canvas, 'هنوز درآمد یا هزینه‌ای ثبت نشده.'); return; }
      setNote(canvas, '');

      trendChart = new Chart(canvas, {
        type: 'line',
        data: {
          labels: rows.map((r) => String(r.month).slice(0, 7)),
          datasets: [
            { label: 'درآمد', data: rows.map((r) => Number(r.income)), borderColor: '#0F6B5C', backgroundColor: 'rgba(15,107,92,.12)', tension: .35, fill: true },
            { label: 'هزینه', data: rows.map((r) => Number(r.expense)), borderColor: '#E15252', backgroundColor: 'rgba(225,82,82,.10)', tension: .35, fill: true },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { rtl: true, labels: { font: { family: 'Vazirmatn' } } },
            tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fa(c.parsed.y)}` } },
          },
          scales: {
            x: { ticks: { font: { family: 'JetBrains Mono', size: 11 } } },
            y: { ticks: { font: { family: 'JetBrains Mono', size: 11 }, callback: (v) => fa(v) } },
          },
        },
      });
    } catch (e) {
      if (e.message === 'redirect') return;
      if (trendChart) { trendChart.destroy(); trendChart = null; }
      setNote(canvas, 'خطا در دریافت روند ماهانه.');
    }
  }

  /* ---------- هزینه بر اساس دسته ---------- */
  async function loadCategories() {
    const canvas = $('category-chart');
    try {
      const { year, month } = getPeriod();
      const rows = asList(await getJSON(
        `/analytics/categories/?year=${year}&month=${month}&period=${categoryPeriod}`
      ));
      if (categoryChart) { categoryChart.destroy(); categoryChart = null; }
      if (!rows.length) {
        setNote(canvas, categoryPeriod === 'monthly' ? 'در این ماه هزینه‌ای ثبت نشده.' : 'در این سال هزینه‌ای ثبت نشده.');
        return;
      }
      setNote(canvas, '');

      categoryChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels: rows.map((r) => r.category_name),
          datasets: [{
            data: rows.map((r) => Number(r.total_amount)),
            backgroundColor: rows.map((_, i) => PALETTE[i % PALETTE.length]),
            borderWidth: 0,
          }],
        },
        options: {
          responsive: true,
          cutout: '68%',
          plugins: {
            legend: { position: 'bottom', rtl: true, labels: { font: { family: 'Vazirmatn', size: 12 } } },
            tooltip: {
              callbacks: {
                label: (c) => `${c.label}: ${fa(c.parsed)} (${fa(Math.round(rows[c.dataIndex].percentage))}٪)`,
              },
            },
          },
        },
      });
    } catch (e) {
      if (e.message === 'redirect') return;
      if (categoryChart) { categoryChart.destroy(); categoryChart = null; }
      setNote(canvas, 'خطا در دریافت دسته‌بندی‌ها.');
    }
  }

  /* ---------- بینش‌ها ---------- */
  async function loadInsights() {
    const wrap = $('insights-list');
    try {
      const { year, month } = getPeriod();
      const data = asList(await getJSON(`/analytics/insights/?year=${year}&month=${month}`));
      wrap.innerHTML = '';
      if (!data.length) {
        wrap.innerHTML = '<p class="empty-note">فعلاً بینشی برای نمایش نیست.</p>';
        return;
      }
      data.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'insight-item';

        const dot = document.createElement('span');
        dot.className = 'insight-dot';

        const body = document.createElement('span');
        const title = document.createElement('strong');
        title.textContent = item.title;
        const impact = document.createElement('span');
        impact.className = 'insight-impact';
        impact.textContent = IMPACTS[item.impact] || item.impact || '';
        body.append(title, ` — ${item.message} `, impact);

        row.append(dot, body);
        wrap.appendChild(row);
      });
    } catch (e) {
      if (e.message === 'redirect') return;
      wrap.innerHTML = '<p class="empty-note">خطا در دریافت بینش‌ها.</p>';
    }
  }

  /* ---------- فیلترها ---------- */
  const now = new Date();
  $('period').value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

  $('period').addEventListener('change', () => { loadCategories(); loadInsights(); });
  $('trend-months').addEventListener('change', loadTrends);
  $('health-months').addEventListener('change', loadHealth);

  document.querySelectorAll('.an-seg button').forEach((btn) => {
    btn.addEventListener('click', () => {
      categoryPeriod = btn.dataset.period;
      document.querySelectorAll('.an-seg button').forEach((b) =>
        b.setAttribute('aria-pressed', String(b === btn)));
      loadCategories();
    });
  });

  Promise.allSettled([loadHealth(), loadTrends(), loadCategories(), loadInsights()]);
})();