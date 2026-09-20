const API_BASE_URL = ['localhost', '127.0.0.1'].includes(window.location.hostname)
  ? 'http://127.0.0.1:8000/api/v1'
  : 'https://<اسم-سرویس>.onrender.com/api/v1';
  
const TokenStore = {
  getAccess: () => localStorage.getItem('ss_access'),
  getRefresh: () => localStorage.getItem('ss_refresh'),
  set: (access, refresh) => {
    if (access) localStorage.setItem('ss_access', access);
    if (refresh) localStorage.setItem('ss_refresh', refresh);
  },
  clear: () => {
    localStorage.removeItem('ss_access');
    localStorage.removeItem('ss_refresh');
  }
};

let refreshPromise = null;

function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refresh = TokenStore.getRefresh();
      if (!refresh) return false;
      try {
        const res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh })
        });
        if (!res.ok) return false;
        const data = await res.json();
        TokenStore.set(data.access, data.refresh);
        return true;
      } catch {
        return false;
      }
    })().finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

async function apiFetch(path, options = {}, retry = true) {
  const access = TokenStore.getAccess();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
    ...(access ? { Authorization: `Bearer ${access}` } : {})
  };

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiFetch(path, options, false);
    TokenStore.clear();
    window.location.href = 'index.html';
    return null;
  }
  return res;
}

function requireAuth() {
  if (!TokenStore.getAccess()) window.location.href = 'index.html';
}

async function logout() {
  const refresh = TokenStore.getRefresh();
  try {
    await apiFetch('/auth/logout/', { method: 'POST', body: JSON.stringify({ refresh }) });
  } catch {}
  TokenStore.clear();
  window.location.href = 'index.html';
}