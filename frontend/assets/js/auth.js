// بر اساس accounts/serializers.py واقعی: لاگین با email انجام می‌شه
const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorBox = document.getElementById('form-error');
    errorBox.textContent = '';

    const email = document.getElementById('identifier').value.trim();
    const password = document.getElementById('password').value;
    const btn = loginForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'در حال ورود...';

    try {
      const res = await fetch(`${API_BASE_URL}/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();

      if (!res.ok) {
        errorBox.textContent = data.detail || 'ایمیل یا رمز عبور اشتباهه.';
        return;
      }

      TokenStore.set(data.access, data.refresh);
      // یوزر مستقیم تو ریسپانس لاگین برمی‌گرده، ذخیره‌اش می‌کنیم تا نیاز به فراخوانی اضافه نباشه
      if (data.user) localStorage.setItem('ss_user', JSON.stringify(data.user));
      window.location.href = 'dashboard.html';
    } catch {
      errorBox.textContent = 'ارتباط با سرور برقرار نشد.';
    } finally {
      btn.disabled = false;
      btn.textContent = 'ورود به حساب';
    }
  });
}

const registerForm = document.getElementById('register-form');
if (registerForm) {
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorBox = document.getElementById('form-error');
    errorBox.textContent = '';

    const payload = {
      first_name: document.getElementById('first_name').value.trim(),
      last_name: document.getElementById('last_name').value.trim(),
      email: document.getElementById('email').value.trim(),
      password: document.getElementById('password').value,
      password_confirm: document.getElementById('password_confirm').value
    };

    const btn = registerForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'در حال ثبت‌نام...';

    try {
      const res = await fetch(`${API_BASE_URL}/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok) {
        errorBox.textContent = Object.values(data).flat().join(' | ') || 'ثبت‌نام ناموفق بود.';
        return;
      }
      window.location.href = 'index.html?registered=1';
    } catch {
      errorBox.textContent = 'ارتباط با سرور برقرار نشد.';
    } finally {
      btn.disabled = false;
      btn.textContent = 'ساخت حساب';
    }
  });
}