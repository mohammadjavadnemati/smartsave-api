const currencyFmt = (n) => Number(n || 0).toLocaleString('fa-IR');

let sources = [];
let editingId = null;

const tableBody = document.getElementById('incomes-body');
const modal = document.getElementById('income-modal');
const form = document.getElementById('income-form');
const filterSource = document.getElementById('filter-source');
const filterFrom = document.getElementById('filter-from');
const filterTo = document.getElementById('filter-to');

async function loadSources() {
  const res = await apiFetch('/incomes/sources/');
  if (!res || !res.ok) return;
  const data = await res.json();
  sources = Array.isArray(data) ? data : (data.results || []);

  const chipsWrap = document.getElementById('sources-chips');
  chipsWrap.innerHTML = '';
  sources.forEach(src => {
    const chip = document.createElement('span');
    chip.className = 'source-chip';
    chip.innerHTML = `<span class="dot"></span> ${src.name} <span class="frequency-badge">${currencyFmt(src.total_amount)}</span>`;
    chipsWrap.appendChild(chip);
  });

  const selects = [document.getElementById('filter-source'), document.getElementById('income-source')];
  selects.forEach(sel => {
    sel.innerHTML = sel.id === 'filter-source' ? '<option value="">همه منابع</option>' : '<option value="">انتخاب منبع</option>';
    sources.forEach(src => {
      const opt = document.createElement('option');
      opt.value = src.id;
      opt.textContent = src.name;
      sel.appendChild(opt);
    });
  });
}

document.getElementById('add-source-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('new-source-name');
  const name = input.value.trim();
  if (!name) return;
  const res = await apiFetch('/incomes/sources/', { method: 'POST', body: JSON.stringify({ name }) });
  if (res && res.ok) { input.value = ''; loadSources(); }
  else alert('افزودن منبع ناموفق بود.');
});

function buildQuery() {
  const params = new URLSearchParams();
  if (filterSource.value) params.set('source', filterSource.value);
  if (filterFrom.value) params.set('date_from', filterFrom.value);
  if (filterTo.value) params.set('date_to', filterTo.value);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

async function loadIncomes() {
  const res = await apiFetch(`/incomes/${buildQuery()}`);
  if (!res || !res.ok) return;
  const data = await res.json();
  const list = Array.isArray(data) ? data : (data.results || []);
  renderTable(list);
}

function renderTable(list) {
  tableBody.innerHTML = '';
  if (!list.length) {
    tableBody.innerHTML = `<tr class="empty-row"><td colspan="5">هنوز درآمدی ثبت نکردی.</td></tr>`;
    return;
  }
  list.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="date-cell">${item.date}</td>
      <td>${item.description || '—'}${item.is_recurring ? ' <span class="frequency-badge">تکرارشونده</span>' : ''}</td>
      <td><span class="badge" style="background:var(--teal)">${item.source_name || '—'}</span></td>
      <td class="amount-cell income-amount">${currencyFmt(item.amount)} تومان</td>
      <td>
        <div class="row-actions">
          <button class="icon-action" data-edit="${item.id}">✏️</button>
          <button class="icon-action danger" data-delete="${item.id}">🗑️</button>
        </div>
      </td>`;
    tableBody.appendChild(tr);
  });

  tableBody.querySelectorAll('[data-edit]').forEach(btn =>
    btn.addEventListener('click', () => openModal(list.find(i => i.id == btn.dataset.edit)))
  );
  tableBody.querySelectorAll('[data-delete]').forEach(btn =>
    btn.addEventListener('click', () => deleteIncome(btn.dataset.delete))
  );
}

function openModal(item = null) {
  editingId = item ? item.id : null;
  document.getElementById('income-modal-title').textContent = item ? 'ویرایش درآمد' : 'افزودن درآمد';
  document.getElementById('income-description').value = item ? (item.description || '') : '';
  document.getElementById('income-amount').value = item ? item.amount : '';
  document.getElementById('income-date').value = item ? item.date : new Date().toISOString().slice(0, 10);
  document.getElementById('income-source').value = item && item.source ? item.source : '';
  modal.classList.add('open');
}
function closeModal() { modal.classList.remove('open'); form.reset(); editingId = null; }

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    source: document.getElementById('income-source').value || null,
    amount: document.getElementById('income-amount').value,
    date: document.getElementById('income-date').value,
    description: document.getElementById('income-description').value.trim()
  };
  const path = editingId ? `/incomes/${editingId}/` : '/incomes/';
  const method = editingId ? 'PATCH' : 'POST';
  const res = await apiFetch(path, { method, body: JSON.stringify(payload) });
  if (res && res.ok) { closeModal(); loadIncomes(); loadSummaryAndCharts(); }
  else alert('ثبت درآمد با خطا مواجه شد.');
});

async function deleteIncome(id) {
  if (!confirm('این درآمد حذف بشه؟')) return;
  const res = await apiFetch(`/incomes/${id}/`, { method: 'DELETE' });
  if (res && (res.ok || res.status === 204)) { loadIncomes(); loadSummaryAndCharts(); }
}

document.getElementById('add-income-btn').addEventListener('click', () => openModal());
document.getElementById('income-modal-cancel').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
[filterSource, filterFrom, filterTo].forEach(el => el.addEventListener('change', loadIncomes));
document.getElementById('filter-reset').addEventListener('click', () => {
  filterSource.value = ''; filterFrom.value = ''; filterTo.value = '';
  loadIncomes();
});

let compareChart;

async function loadSummaryAndCharts() {
  // بر اساس IncomeSummarySerializer واقعی
  const summaryRes = await apiFetch('/incomes/summary/');
  if (summaryRes && summaryRes.ok) {
    const data = await summaryRes.json();
    document.getElementById('stat-total').textContent = currencyFmt(data.total_amount);
    document.getElementById('stat-average').textContent = currencyFmt(data.average_amount);

    const bySource = data.by_source || [];
    const top = bySource.reduce((max, s) => (Number(s.total_amount) > Number(max?.total_amount || 0) ? s : max), null);
    document.getElementById('stat-top-source').textContent = top ? top.name : '—';
  }

  // بر اساس MonthlyIncomeReportSerializer واقعی
  const reportRes = await apiFetch('/incomes/monthly-report/');
  if (reportRes && reportRes.ok) {
    const data = await reportRes.json();
    const list = Array.isArray(data) ? data : (data.results || []);
    const labels = list.map(i => i.month);
    const totals = list.map(i => Number(i.total_amount));

    const ctx = document.getElementById('compare-chart');
    if (compareChart) compareChart.destroy();
    compareChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: 'درآمد ماهانه', data: totals, backgroundColor: '#0F6B5C', borderRadius: 6 }]
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
}

(async () => {
  await loadSources();
  await loadIncomes();
  await loadSummaryAndCharts();
})();