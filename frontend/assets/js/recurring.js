// بر اساس RecurringExpenseSerializer واقعی
const R_FIELDS = {
  title: 'title',
  amount: 'amount',
  category: 'category',
  description: 'description',
  frequency: 'frequency',
  start: 'start_date',
  end: 'end_date',
  active: 'is_active'
};

// ⚠️ اگه choices واقعی مدل با این‌ها فرق داره (مثلاً حروف بزرگ)، همین‌جا عوض کن
const FREQUENCY_LABELS = {
  daily: 'روزانه',
  weekly: 'هفتگی',
  monthly: 'ماهانه',
  yearly: 'سالانه'
};

const rBody = document.getElementById('recurring-body');
const rModal = document.getElementById('recurring-modal');
const rForm = document.getElementById('recurring-form');
let recurringEditingId = null;

async function loadRecurringSummary() {
  const res = await apiFetch('/expenses/recurring/summary/');
  if (!res || !res.ok) return;
  const data = await res.json();
  document.getElementById('r-stat-monthly').textContent = currencyFmt(data.total_monthly_cost);
  document.getElementById('r-stat-annual').textContent = currencyFmt(data.total_annual_cost);
  document.getElementById('r-stat-count').textContent = data.active_count ?? '—';
}

async function loadRecurring() {
  const res = await apiFetch('/expenses/recurring/');
  if (!res || !res.ok) return;
  const data = await res.json();
  const list = Array.isArray(data) ? data : (data.results || []);
  renderRecurring(list);
}

function renderRecurring(list) {
  rBody.innerHTML = '';
  if (!list.length) {
    rBody.innerHTML = `<tr class="empty-row"><td colspan="6">هنوز هزینه‌ی تکرارشونده‌ای ثبت نکردی.</td></tr>`;
    return;
  }
  list.forEach(item => {
    const freq = FREQUENCY_LABELS[item[R_FIELDS.frequency]] || item[R_FIELDS.frequency];
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item[R_FIELDS.title] || '—'}</td>
      <td><span class="badge" style="background:var(--teal)">${item.category_name || '—'}</span></td>
      <td class="amount-cell">${currencyFmt(item[R_FIELDS.amount])} تومان</td>
      <td><span class="frequency-badge">${freq}</span></td>
      <td><div class="toggle-switch ${item[R_FIELDS.active] ? 'on' : ''}" data-toggle="${item.id}" data-state="${item[R_FIELDS.active]}"></div></td>
      <td>
        <div class="row-actions">
          <button class="icon-action" data-edit="${item.id}">✏️</button>
          <button class="icon-action danger" data-delete="${item.id}">🗑️</button>
        </div>
      </td>`;
    rBody.appendChild(tr);
  });

  rBody.querySelectorAll('[data-toggle]').forEach(el =>
    el.addEventListener('click', () => toggleActive(el.dataset.toggle, el.dataset.state === 'true'))
  );
  rBody.querySelectorAll('[data-edit]').forEach(btn =>
    btn.addEventListener('click', () => openRecurringModal(list.find(i => i.id == btn.dataset.edit)))
  );
  rBody.querySelectorAll('[data-delete]').forEach(btn =>
    btn.addEventListener('click', () => deleteRecurring(btn.dataset.delete))
  );
}

async function toggleActive(id, currentState) {
  const res = await apiFetch(`/expenses/recurring/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ [R_FIELDS.active]: !currentState })
  });
  if (res && res.ok) { loadRecurring(); loadRecurringSummary(); }
}

function openRecurringModal(item = null) {
  recurringEditingId = item ? item.id : null;
  document.getElementById('recurring-modal-title').textContent = item ? 'ویرایش هزینه‌ی تکرارشونده' : 'افزودن هزینه‌ی تکرارشونده';
  document.getElementById('r-title').value = item ? item[R_FIELDS.title] : '';
  document.getElementById('r-amount').value = item ? item[R_FIELDS.amount] : '';
  document.getElementById('r-frequency').value = item ? item[R_FIELDS.frequency] : 'monthly';
  document.getElementById('r-start').value = item ? item[R_FIELDS.start] : new Date().toISOString().slice(0, 10);
  document.getElementById('r-end').value = item ? (item[R_FIELDS.end] || '') : '';
  document.getElementById('r-category').value = item && item[R_FIELDS.category] ? item[R_FIELDS.category] : '';
  rModal.classList.add('open');
}
function closeRecurringModal() { rModal.classList.remove('open'); rForm.reset(); recurringEditingId = null; }

rForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    [R_FIELDS.title]: document.getElementById('r-title').value.trim(),
    [R_FIELDS.amount]: document.getElementById('r-amount').value,
    [R_FIELDS.category]: document.getElementById('r-category').value || null,
    [R_FIELDS.frequency]: document.getElementById('r-frequency').value,
    [R_FIELDS.start]: document.getElementById('r-start').value,
    [R_FIELDS.end]: document.getElementById('r-end').value || null
  };
  const path = recurringEditingId ? `/expenses/recurring/${recurringEditingId}/` : '/expenses/recurring/';
  const method = recurringEditingId ? 'PATCH' : 'POST';
  const res = await apiFetch(path, { method, body: JSON.stringify(payload) });
  if (res && res.ok) { closeRecurringModal(); loadRecurring(); loadRecurringSummary(); }
  else alert('ثبت هزینه‌ی تکرارشونده با خطا مواجه شد.');
});

async function deleteRecurring(id) {
  if (!confirm('این هزینه‌ی تکرارشونده حذف بشه؟')) return;
  const res = await apiFetch(`/expenses/recurring/${id}/`, { method: 'DELETE' });
  if (res && (res.ok || res.status === 204)) { loadRecurring(); loadRecurringSummary(); }
}

function populateRecurringCategories(cats) {
  const sel = document.getElementById('r-category');
  if (!sel) return;
  sel.innerHTML = '<option value="">انتخاب دسته</option>';
  cats.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat.id;
    opt.textContent = cat.name;
    sel.appendChild(opt);
  });
}

document.getElementById('add-recurring-btn').addEventListener('click', () => openRecurringModal());
document.getElementById('recurring-modal-cancel').addEventListener('click', closeRecurringModal);
rModal.addEventListener('click', (e) => { if (e.target === rModal) closeRecurringModal(); });