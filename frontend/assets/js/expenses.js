// بر اساس expenses/serializers.py واقعی
const FIELDS = {
  description: 'description',
  amount: 'amount',
  category: 'category',
  date: 'date'
};

const currencyFmt = (n) => Number(n || 0).toLocaleString('fa-IR');
function pick(obj, keys, fallback = null) {
  for (const k of keys) if (obj && obj[k] !== undefined && obj[k] !== null) return obj[k];
  return fallback;
}

let categories = [];
let editingId = null;

const tableBody = document.getElementById('expenses-body');
const modal = document.getElementById('expense-modal');
const form = document.getElementById('expense-form');
const filterCategory = document.getElementById('filter-category');
const filterSearch = document.getElementById('filter-search');
const filterFrom = document.getElementById('filter-from');
const filterTo = document.getElementById('filter-to');

async function loadCategories() {
  const res = await apiFetch('/expenses/categories/');
  if (!res || !res.ok) return;
  const data = await res.json();
  categories = Array.isArray(data) ? data : (data.results || []);

  const selects = [document.getElementById('filter-category'), document.getElementById('expense-category')];
  selects.forEach(sel => {
    sel.innerHTML = sel.id === 'filter-category' ? '<option value="">همه دسته‌ها</option>' : '<option value="">انتخاب دسته</option>';
    categories.forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat.id;
      opt.textContent = cat.name;
      sel.appendChild(opt);
    });
  });

  // برای تب هزینه‌های تکرارشونده (تو recurring.js)
  if (typeof populateRecurringCategories === 'function') populateRecurringCategories(categories);
}

function buildQuery() {
  const params = new URLSearchParams();
  if (filterCategory.value) params.set('category', filterCategory.value);
  if (filterSearch.value.trim()) params.set('search', filterSearch.value.trim());
  if (filterFrom.value) params.set('date_from', filterFrom.value);
  if (filterTo.value) params.set('date_to', filterTo.value);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

async function loadExpenses() {
  const res = await apiFetch(`/expenses/${buildQuery()}`);
  if (!res || !res.ok) return;
  const data = await res.json();
  const list = Array.isArray(data) ? data : (data.results || []);
  renderTable(list);
}

function renderTable(list) {
  tableBody.innerHTML = '';
  if (!list.length) {
    tableBody.innerHTML = `<tr class="empty-row"><td colspan="5">هیچ هزینه‌ای پیدا نشد. اولین هزینه رو اضافه کن.</td></tr>`;
    return;
  }
  list.forEach(item => {
    const catName = item.category_name || '—';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="date-cell">${item[FIELDS.date] || '—'}</td>
      <td>${item[FIELDS.description] || '—'}${item.is_recurring ? ' <span class="frequency-badge">تکرارشونده</span>' : ''}</td>
      <td><span class="badge" style="background:${colorFor(catName)}">${catName}</span></td>
      <td class="amount-cell">${currencyFmt(item[FIELDS.amount])} تومان</td>
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
    btn.addEventListener('click', () => deleteExpense(btn.dataset.delete))
  );
}

const PALETTE = ['#0F6B5C', '#C9A227', '#E15252', '#5B6472', '#16997F', '#E0BE4C', '#8892A0'];
function colorFor(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i++) hash = text.charCodeAt(i) + ((hash << 5) - hash);
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

function openModal(item = null) {
  editingId = item ? item.id : null;
  document.getElementById('modal-title').textContent = item ? 'ویرایش هزینه' : 'افزودن هزینه';
  document.getElementById('expense-description').value = item ? item[FIELDS.description] : '';
  document.getElementById('expense-amount').value = item ? item[FIELDS.amount] : '';
  document.getElementById('expense-date').value = item ? item[FIELDS.date] : new Date().toISOString().slice(0, 10);
  document.getElementById('expense-category').value = item && item[FIELDS.category] ? item[FIELDS.category] : '';
  modal.classList.add('open');
}
function closeModal() { modal.classList.remove('open'); form.reset(); editingId = null; }

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    [FIELDS.description]: document.getElementById('expense-description').value.trim(),
    [FIELDS.amount]: document.getElementById('expense-amount').value,
    [FIELDS.category]: document.getElementById('expense-category').value || null,
    [FIELDS.date]: document.getElementById('expense-date').value
  };
  const path = editingId ? `/expenses/${editingId}/` : '/expenses/';
  const method = editingId ? 'PATCH' : 'POST';
  const res = await apiFetch(path, { method, body: JSON.stringify(payload) });
  if (res && res.ok) { closeModal(); loadExpenses(); }
  else alert('ثبت هزینه با خطا مواجه شد. مقادیر فرم رو چک کن.');
});

async function deleteExpense(id) {
  if (!confirm('این هزینه حذف بشه؟')) return;
  const res = await apiFetch(`/expenses/${id}/`, { method: 'DELETE' });
  if (res && (res.ok || res.status === 204)) loadExpenses();
}

document.getElementById('add-expense-btn').addEventListener('click', () => openModal());
document.getElementById('modal-cancel').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

[filterCategory, filterSearch, filterFrom, filterTo].forEach(el => el.addEventListener('change', loadExpenses));
document.getElementById('filter-reset').addEventListener('click', () => {
  filterCategory.value = ''; filterSearch.value = ''; filterFrom.value = ''; filterTo.value = '';
  loadExpenses();
});

// ماشین‌حساب تاثیر پس‌انداز — بر اساس SavingsImpactSerializer واقعی
document.getElementById('impact-search-btn').addEventListener('click', async () => {
  const q = document.getElementById('impact-input').value.trim();
  if (!q) return;
  const res = await apiFetch(`/expenses/savings-impact/?q=${encodeURIComponent(q)}`);
  const box = document.getElementById('impact-results');
  if (!res || !res.ok) {
    box.innerHTML = '<p class="empty-note">چیزی پیدا نشد.</p>';
    return;
  }
  const data = await res.json();
  const total = data.total_spent;
  const monthly = data.monthly_average;
  const count = data.transaction_count;
  const impact = data.savings_impact || {};
  // savings_impact یه DictField آزاده؛ چند اسم کلید محتمل رو امتحان می‌کنیم
  const m1 = pick(impact, ['one_month', '1_month'], monthly);
  const m6 = pick(impact, ['six_months', '6_months'], monthly * 6);
  const y1 = pick(impact, ['one_year', '1_year'], monthly * 12);
  const y5 = pick(impact, ['five_years', '5_years'], monthly * 60);

  box.innerHTML = `
    <span class="eyebrow">${count} تراکنش پیدا شد</span>
    <p class="impact-total">${currencyFmt(total)} تومان</p>
    <div class="impact-grid">
      <div class="impact-box"><span>۱ ماهه</span><strong>${currencyFmt(m1)}</strong></div>
      <div class="impact-box"><span>۶ ماهه</span><strong>${currencyFmt(m6)}</strong></div>
      <div class="impact-box"><span>۱ ساله</span><strong>${currencyFmt(y1)}</strong></div>
      <div class="impact-box"><span>۵ ساله</span><strong>${currencyFmt(y5)}</strong></div>
    </div>`;
});

// تب‌ها
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'panel-recurring') { loadRecurring(); loadRecurringSummary(); }
  });
});

(async () => {
  await loadCategories();
  await loadExpenses();
})();