requireAuth();

const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) logoutBtn.addEventListener('click', logout);

const currentPage = window.location.pathname.split('/').pop();
document.querySelectorAll('.nav-link').forEach(link => {
  if (link.getAttribute('href') === currentPage) link.classList.add('active');
});

// بر اساس UserProfileSerializer واقعی: full_name مستقیم موجوده
(async () => {
  const res = await apiFetch('/auth/profile/');
  if (res && res.ok) {
    const user = await res.json();
    const nameEl = document.getElementById('user-name');
    if (nameEl) nameEl.textContent = user.full_name || user.email || 'کاربر';
  }
})();

const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.getElementById('sidebar');
if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
}