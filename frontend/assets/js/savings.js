// بر اساس SavingsGoalSerializer واقعی
const currencyFmt = (n) => Number(n || 0).toLocaleString('fa-IR');

let editingId = null;
let goalsCache = [];

const grid = document.getElementById('goals-grid');
const modal = document.getElementById('goal-modal');
const form = document.getElementById('goal-form');
const depositModal = document.getElementById('deposit-modal');
const depositForm = document.getElementById('deposit-form');

function jarSvg(id, percent) {
  const fillHeight = Math.max(0, Math.min(percent, 100)) / 100 * 108;
  const y = 116 - fillHeight;
  const jarPath = 'M38,4 L62,4 L62,28 L83,28 Q90,28 90,36 L90,104 Q90,116 78,116 L22,116 Q10,116 10,104 L10,36 Q10,28 17,28 L38,28 Z';
  return `
    <svg viewBox="0 0 100 120" class="goal-jar">
      <defs><clipPath id="clip-${id}"><path d="${jarPath}"/></clipPath></defs>
      <path d="${jarPath}" fill="none" stroke="var(--line)" stroke-width="4"/>
      <rect x="8" y="${y}" width="84" height="${fillHeight}" style="fill:var(--gold)" clip-path="url(#clip-${id})"/>
      <path d="${jarPath}" fill="none" stroke="var(--ink)" stroke-width="2" opacity="0.15"/>
    </svg>`;
}

const STATUS_LABELS = { ACTIVE: 'فعال', COMPLETED: 'تکمیل‌شده', CANCELLED: 'لغوشده' };

async function loadOverall() {
  const res = await apiFetch('/savings/goals/progress/');
  if (!res || !res.ok) return;
  const data = await res.json();
  document.getElementById('overall-goals-count').textContent = data.total_goals;
  document.getElementById('overall-total-target').textContent = currencyFmt(data.total_target);
  document.getElementById('overall-total-saved').textContent = currencyFmt(data.total_saved);
}

async function loadGoals() {
  const res = await apiFetch('/savings/goals/');
  if (!res || !res.ok) return;
  const data = await res.json();
  goalsCache = Array.isArray(data) ? data : (data.results || []);
  renderGoals();
}

function renderGoals() {
  grid.innerHTML = '';
  if (!goalsCache.length) {
    grid.innerHTML = '<p class="empty-note">هنوز هدفی نساختی. یکی اضافه کن تا شروع کنی.</p>';
    return;
  }
  goalsCache.forEach(goal => {
    const percent = goal.progress_percentage || 0;
    const statusLabel = STATUS_LABELS[goal.status] || goal.status;

    const depositsHtml = (goal.recent_deposits || []).slice(0, 3).map(d =>
      `<div class="breakdown-row"><span>${d.date}</span><span class="mono">${currencyFmt(d.amount)}</span></div>`
    ).join('');

    const card = document.createElement('div');
    card.className = 'goal-card';
    card.innerHTML = `
      <div class="goal-top">
        ${jarSvg(goal.id, percent)}
        <div class="goal-info">
          <p class="goal-name">${goal.title}</p>
          <p class="goal-deadline">${goal.deadline ? 'مهلت: ' + goal.deadline : 'بدون مهلت'} · <span class="frequency-badge">${statusLabel}</span></p>
        </div>
      </div>

      <div class="goal-amounts">
        <span class="current">${currencyFmt(goal.current_amount)}</span>
        <span>از ${currencyFmt(goal.target_amount)} تومان</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill ${goal.is_completed ? 'ok' : percent >= 80 ? 'warning' : 'ok'}" style="width:${Math.min(percent, 100)}%"></div>
      </div>
      <p class="goal-percent-label">${percent.toFixed(1)}٪ تکمیل‌شده · باقی‌مانده: ${currencyFmt(goal.remaining_amount)}</p>
      ${goal.months_to_goal ? `<p class="goal-percent-label">با روند فعلی، حدود <strong>${goal.months_to_goal} ماه</strong> دیگه مونده</p>` : ''}

      ${depositsHtml ? `<div class="predict-box"><span class="eyebrow">آخرین واریزها</span>${depositsHtml}</div>` : ''}

      <div class="predict-box">
        <span class="eyebrow">اگه پس‌انداز ماهانه‌ات فرق کنه چی؟</span>
        <div class="predict-row">
          <input type="number" placeholder="پس‌انداز ماهانه فرضی" data-predict-input="${goal.id}">
          <button data-predict-btn="${goal.id}">محاسبه</button>
        </div>
        <div class="predict-result" id="predict-result-${goal.id}"></div>
      </div>

      <div class="goal-card-actions">
        <button class="btn-primary" data-deposit="${goal.id}" style="flex:1;justify-content:center;">+ واریز</button>
        <button class="btn-ghost" data-edit="${goal.id}">ویرایش</button>
        <button class="btn-ghost" data-delete="${goal.id}">حذف</button>
      </div>`;
    grid.appendChild(card);
  });

  grid.querySelectorAll('[data-predict-btn]').forEach(btn =>
    btn.addEventListener('click', () => runPrediction(btn.dataset.predictBtn))
  );
  grid.querySelectorAll('[data-deposit]').forEach(btn =>
    btn.addEventListener('click', () => openDepositModal(btn.dataset.deposit))
  );
  grid.querySelectorAll('[data-edit]').forEach(btn =>
    btn.addEventListener('click', () => openModal(goalsCache.find(g => g.id == btn.dataset.edit)))
  );
  grid.querySelectorAll('[data-delete]').forEach(btn =>
    btn.addEventListener('click', () => deleteGoal(btn.dataset.delete))
  );
}

// ⚠️ ریسپانس این endpoint رو ندارم، فیلدهاش حدسیه — اگه views.py مربوطه رو بفرستی دقیقش می‌کنم
async function runPrediction(goalId) {
  const input = document.querySelector(`[data-predict-input="${goalId}"]`);
  const monthly = input.value;
  if (!monthly) return;
  const res = await apiFetch(`/savings/goals/${goalId}/predict/?monthly_saving=${monthly}`);
  const box = document.getElementById(`predict-result-${goalId}`);
  if (!res || !res.ok) {
    box.textContent = 'محاسبه ممکن نشد.';
    box.classList.add('show');
    return;
  }
  const data = await res.json();
  const months = data.months_remaining ?? data.months;
  const date = data.estimated_date ?? data.completion_date;
  box.innerHTML = date
    ? `با این روند، تقریباً <strong>${date}</strong> به هدف می‌رسی.`
    : `با این روند، حدود <strong>${months} ماه</strong> دیگه به هدف می‌رسی.`;
  box.classList.add('show');
}

function openModal(goal = null) {
  editingId = goal ? goal.id : null;
  document.getElementById('goal-modal-title').textContent = goal ? 'ویرایش هدف' : 'هدف جدید';
  document.getElementById('goal-title').value = goal ? goal.title : '';
  document.getElementById('goal-description').value = goal ? (goal.description || '') : '';
  document.getElementById('goal-target').value = goal ? goal.target_amount : '';
  document.getElementById('goal-deadline').value = goal ? (goal.deadline || '') : '';
  modal.classList.add('open');
}
function closeModal() { modal.classList.remove('open'); form.reset(); editingId = null; }

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    title: document.getElementById('goal-title').value.trim(),
    description: document.getElementById('goal-description').value.trim(),
    target_amount: document.getElementById('goal-target').value,
    deadline: document.getElementById('goal-deadline').value || null
  };
  const path = editingId ? `/savings/goals/${editingId}/` : '/savings/goals/';
  const method = editingId ? 'PATCH' : 'POST';
  const res = await apiFetch(path, { method, body: JSON.stringify(payload) });
  if (res && res.ok) { closeModal(); loadGoals(); loadOverall(); }
  else alert('ثبت هدف با خطا مواجه شد.');
});

async function deleteGoal(id) {
  if (!confirm('این هدف حذف بشه؟')) return;
  const res = await apiFetch(`/savings/goals/${id}/`, { method: 'DELETE' });
  if (res && (res.ok || res.status === 204)) { loadGoals(); loadOverall(); }
}

let depositGoalId = null;
function openDepositModal(goalId) {
  depositGoalId = goalId;
  depositForm.reset();
  document.getElementById('deposit-date').value = new Date().toISOString().slice(0, 10);
  depositModal.classList.add('open');
}
function closeDepositModal() { depositModal.classList.remove('open'); depositGoalId = null; }

depositForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    goal: depositGoalId,
    amount: document.getElementById('deposit-amount').value,
    date: document.getElementById('deposit-date').value,
    note: document.getElementById('deposit-note').value.trim()
  };
  const res = await apiFetch('/savings/deposits/', { method: 'POST', body: JSON.stringify(payload) });
  if (res && res.ok) { closeDepositModal(); loadGoals(); loadOverall(); }
  else alert('ثبت واریز با خطا مواجه شد. (شاید هدف تکمیل/لغوشده باشه)');
});

document.getElementById('add-goal-btn').addEventListener('click', () => openModal());
document.getElementById('goal-modal-cancel').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
document.getElementById('deposit-modal-cancel').addEventListener('click', closeDepositModal);
depositModal.addEventListener('click', (e) => { if (e.target === depositModal) closeDepositModal(); });

(async () => {
  await loadGoals();
  await loadOverall();
})();