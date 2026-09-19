// بر اساس BudgetSerializer واقعی
const currencyFmt = (n) => Number(n || 0).toLocaleString('fa-IR');

// ⚠️ اگه choices واقعی مدل فرق داره، همین‌جا عوض کن
const PERIOD_VALUES = { monthly: 'ماهانه', yearly: 'سالانه' };

let categories = [];
let editingId = null;

const grid = document.getElementById('budgets-grid');
const modal = document.getElementById('budget-modal');
const form = document.getElementById('budget-form');
const alertsRow = document.getElementById('alerts-row');
const periodSelect = document.getElementById('budget-period');
const monthField = document.getElementById('budget-month-wrap');

periodSelect.addEventListener('change', () => {
  monthField.style.display = periodSelect.value === 'monthly' ? 'flex' : 'none';
});

async function loadCategories() {
  const res = await apiFetch('/expenses/categories/');
  if (!res || !res.ok) return;
  const data = await res.json();
  categories = Array.isArray(data) ? data : (data.results || []);
  const sel = document.getElementById('budget-category');
  sel.innerHTML = '<option value="">انتخاب دسته</option>';
  categories.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat.id;
    opt.textContent = cat.name;
    sel.appendChild(opt);
  });
}

function statusClass(alertLevel) {
  const v = (alertLevel || '').toLowerCase();
  if (v.includes('exceed') || v.includes('over') || v.includes('danger')) return 'exceeded';
  if (v.includes('warn')) return 'warning';
  return 'ok';
}

async function loadSummary() {
  const res = await apiFetch('/budgets/summary/');
  if (!res || !res.ok) return;
  const data = await res.json();
  document.getElementById('sum-total-budget').textContent = currencyFmt(data.total_budget);
  document.getElementById('sum-total-spent').textContent = currencyFmt(data.total_spent);
  document.getElementById('sum-total-remaining').textContent = currencyFmt(data.total_remaining);
  document.getElementById('sum-usage').textContent = `${data.overall_usage_percentage.toFixed(1)}٪`;
  document.getElementById('sum-on-track').textContent = data.budgets_on_track;
  document.getElementById('sum-exceeded').textContent = data.budgets_exceeded;
}

// بر اساس BudgetAlertSerializer: message و alert_level مستقیم از بک‌اند میان
async function loadAlerts() {
  const res = await apiFetch('/budgets/alerts/');
  alertsRow.innerHTML = '';
  if (!res || !res.ok) return;
  const data = await res.json();
  const list = Array.isArray(data) ? data : (data.results || []);
  if (!list.length) {
    alertsRow.innerHTML = '<p class="empty-note">همه‌چیز تحت کنترله، هشداری وجود نداره.</p>';
    return;
  }
  list.forEach(item => {
    const status = statusClass(item.alert_level);
    const chip = document.createElement('div');
    chip.className = `alert-chip ${status}`;
    chip.textContent = `${status === 'exceeded' ? '🔴' : '🟡'} ${item.message}`;
    alertsRow.appendChild(chip);
  });
}

async function loadBudgets() {
  const res = await apiFetch('/budgets/');
  if (!res || !res.ok) return;
  const data = await res.json();
  const list = Array.isArray(data) ? data : (data.results || []);
  renderGrid(list);
}

function renderGrid(list) {
  grid.innerHTML = '';
  if (!list.length) {
    grid.innerHTML = '<p class="empty-note">هنوز بودجه‌ای تعریف نکردی. یکی اضافه کن.</p>';
    return;
  }
  list.forEach(item => {
    const percent = Math.min(item.usage_percentage || 0, 150);
    const status = statusClass(item.alert_level);
    const periodLabel = PERIOD_VALUES[item.period] || item.period;
    const timeLabel = item.month ? `${periodLabel} · ${item.year}/${item.month}` : `${periodLabel} · ${item.year}`;

    const card = document.createElement('div');
    card.className = 'budget-card';
    card.innerHTML = `
      <div class="budget-flap ${status}"></div>
      <p class="budget-cat">${item.category_name}</p>
      <p class="budget-period">${timeLabel}</p>
      <div class="budget-amounts">
        <span class="spent">${currencyFmt(item.spent_amount)}</span>
        <span>از ${currencyFmt(item.amount)} تومان</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill ${status}" style="width:${Math.min(percent, 100)}%"></div>
      </div>
      <div class="budget-percent">
        <span>${item.usage_percentage.toFixed(1)}٪ مصرف‌شده</span>
        <span>باقی‌مانده: ${currencyFmt(item.remaining_amount)}</span>
      </div>
      <div class="budget-card-actions">
        <button class="btn-ghost" data-edit="${item.id}">ویرایش</button>
        <button class="btn-ghost" data-delete="${item.id}">حذف</button>
      </div>`;
    grid.appendChild(card);
  });

  grid.querySelectorAll('[data-edit]').forEach(btn =>
    btn.addEventListener('click', () => openModal(list.find(i => i.id == btn.dataset.edit)))
  );
  grid.querySelectorAll('[data-delete]').forEach(btn =>
    btn.addEventListener('click', () => deleteBudget(btn.dataset.delete))
  );
}

function openModal(item = null) {
  editingId = item ? item.id : null;
  document.getElementById('budget-modal-title').textContent = item ? 'ویرایش بودجه' : 'افزودن بودجه';
  document.getElementById('budget-category').value = item ? item.category : '';
  document.getElementById('budget-amount').value = item ? item.amount : '';
  document.getElementById('budget-period').value = item ? item.period : 'monthly';
  document.getElementById('budget-year').value = item ? item.year : new Date().getFullYear();
  document.getElementById('budget-month').value = item ? (item.month || '') : (new Date().getMonth() + 1);
  monthField.style.display = (item ? item.period : 'monthly') === 'monthly' ? 'flex' : 'none';
  modal.classList.add('open');
}
function closeModal() { modal.classList.remove('open'); form.reset(); editingId = null; }

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const period = document.getElementById('budget-period').value;
  const payload = {
    category: document.getElementById('budget-category').value,
    amount: document.getElementById('budget-amount').value,
    period,
    year: document.getElementById('budget-year').value,
    month: period === 'monthly' ? document.getElementById('budget-month').value : null
  };
  const path = editingId ? `/budgets/${editingId}/` : '/budgets/';
  const method = editingId ? 'PATCH' : 'POST';
  const res = await apiFetch(path, { method, body: JSON.stringify(payload) });
  if (res && res.ok) { closeModal(); loadBudgets(); loadAlerts(); loadSummary(); }
  else alert('ثبت بودجه با خطا مواجه شد (شاید بودجه‌ای برای این دسته/دوره از قبل وجود داره).');
});

async function deleteBudget(id) {
  if (!confirm('این بودجه حذف بشه؟')) return;
  const res = await apiFetch(`/budgets/${id}/`, { method: 'DELETE' });
  if (res && (res.ok || res.status === 204)) { loadBudgets(); loadAlerts(); loadSummary(); }
}

document.getElementById('add-budget-btn').addEventListener('click', () => openModal());
document.getElementById('budget-modal-cancel').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

(async () => {
  await loadCategories();
  await loadBudgets();
  await loadAlerts();
  await loadSummary();
})();