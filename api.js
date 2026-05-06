/**
 * NepSera — Unified API Client
 * Handles auth, stock data, and all backend communication.
 */

const API_BASE = "http://localhost:8000";

// ═══════════════════════════════════════════════════════════════
// TOKEN & SESSION MANAGEMENT
// ═══════════════════════════════════════════════════════════════

const Auth = {
  getToken()   { return localStorage.getItem("nepsera_token"); },
  getUser()    { const u = localStorage.getItem("nepsera_user"); return u ? JSON.parse(u) : null; },
  isLoggedIn() { return !!this.getToken() && !!this.getUser(); },
  isAdmin()    { return this.getUser()?.role === "admin"; },

  _save(data) {
    localStorage.setItem("nepsera_token", data.access_token);
    localStorage.setItem("nepsera_user",  JSON.stringify(data.user));
    localStorage.setItem("nepseraUser",   JSON.stringify(data.user)); // compat with existing pages
  },

  clear() {
    ["nepsera_token", "nepsera_user", "nepseraUser"].forEach(k => localStorage.removeItem(k));
  },

  isTokenExpired() {
    const token = this.getToken();
    if (!token) return true;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  },

  logout(redirect = true) {
    this.clear();
    if (redirect) window.location.href = "signin.html";
  },

  requireAuth(redirectIfNot = true) {
    if (!this.isLoggedIn() || this.isTokenExpired()) {
      if (redirectIfNot) this.logout(true);
      return false;
    }
    return true;
  },

  redirectIfLoggedIn(to = "index.html") {
    if (this.isLoggedIn() && !this.isTokenExpired()) window.location.href = to;
  },
};

// ═══════════════════════════════════════════════════════════════
// BASE FETCH HELPERS
// ═══════════════════════════════════════════════════════════════

async function _fetch(path, options = {}) {
  try {
    const res = await fetch(API_BASE + path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return { ok: true, data };
  } catch (err) {
    console.error("[API]", path, err.message);
    return { ok: false, error: err.message, data: null };
  }
}

async function _authFetch(path, options = {}) {
  if (Auth.isTokenExpired()) {
    Auth.logout(true);
    return { ok: false, error: "Session expired", data: null };
  }
  try {
    const res = await fetch(API_BASE + path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${Auth.getToken()}`,
        ...(options.headers || {}),
      },
    });
    if (res.status === 401) { Auth.logout(true); return { ok: false, error: "Unauthorized", data: null }; }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return { ok: true, data };
  } catch (err) {
    console.error("[API auth]", path, err.message);
    return { ok: false, error: err.message, data: null };
  }
}

// ═══════════════════════════════════════════════════════════════
// AUTH ENDPOINTS
// ═══════════════════════════════════════════════════════════════

const AuthAPI = {
  async register(name, email, password, role = "user") {
    const result = await _fetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password, role }),
    });
    if (result.ok) Auth._save(result.data);
    return result;
  },

  async login(email, password) {
    const result = await _fetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (result.ok) Auth._save(result.data);
    return result;
  },

  logout: (redirect = true) => Auth.logout(redirect),
};

// ═══════════════════════════════════════════════════════════════
// DASHBOARD ENDPOINTS  (auth required)
// ═══════════════════════════════════════════════════════════════

const DashboardAPI = {
  getUserSummary() { return _authFetch("/dashboard/summary"); },
  getAdminStats()  { return _authFetch("/dashboard/admin/stats"); },
  getAdminUsers()  { return _authFetch("/dashboard/admin/users"); },
};

// ═══════════════════════════════════════════════════════════════
// STOCK / MARKET ENDPOINTS  (public)
// ═══════════════════════════════════════════════════════════════

const StockAPI = {
  companies()               { return _fetch("/api/companies"); },
  latestStocks(limit = 200) { return _fetch(`/api/stocks/latest?limit=${limit}`); },

  history(symbol, from, to, limit = 500) {
    const p = new URLSearchParams({ limit });
    if (from) p.set("from_date", from);
    if (to)   p.set("to_date",   to);
    return _fetch(`/api/stocks/${symbol}/history?${p}`);
  },

  summary(symbol) { return _fetch(`/api/stocks/${symbol}/summary`); },

  compare(symbols, from, to) {
    const p = new URLSearchParams({ symbols: symbols.join(",") });
    if (from) p.set("from_date", from);
    if (to)   p.set("to_date",   to);
    return _fetch(`/api/stocks/compare?${p}`);
  },

  gainers(limit = 10, date) {
    const p = new URLSearchParams({ limit });
    if (date) p.set("on_date", date);
    return _fetch(`/api/market/gainers?${p}`);
  },

  losers(limit = 10, date) {
    const p = new URLSearchParams({ limit });
    if (date) p.set("on_date", date);
    return _fetch(`/api/market/losers?${p}`);
  },

  topVolume(limit = 10, date) {
    const p = new URLSearchParams({ limit });
    if (date) p.set("on_date", date);
    return _fetch(`/api/market/top-volume?${p}`);
  },

  overview(date) {
    const p = date ? `?on_date=${date}` : "";
    return _fetch(`/api/market/overview${p}`);
  },

  dates() { return _fetch("/api/market/dates"); },
};

// ═══════════════════════════════════════════════════════════════
// FORMATTERS
// ═══════════════════════════════════════════════════════════════

function fmt(val, decimals = 2) {
  if (val == null || val === "") return "—";
  return Number(val).toLocaleString("en-NP", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtPct(val) {
  if (val == null) return "—";
  const n = Number(val);
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

function fmtVol(val) {
  if (val == null) return "—";
  const n = Number(val);
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000)     return (n / 1_000).toFixed(0) + "K";
  return n.toFixed(0);
}

function fmtTurnover(val) {
  if (val == null) return "—";
  const n = Number(val);
  if (n >= 1_000_000_000) return "NPR " + (n / 1_000_000_000).toFixed(2) + "B";
  if (n >= 1_000_000)     return "NPR " + (n / 1_000_000).toFixed(1) + "M";
  return "NPR " + n.toLocaleString();
}

function badgeHtml(pct) {
  if (pct == null) return '<span style="color:var(--text3)">—</span>';
  const n   = Number(pct);
  const cls = n >= 0 ? "bdg-u" : "bdg-d";
  return `<span class="bdg ${cls}">${n >= 0 ? "+" : ""}${n.toFixed(2)}%</span>`;
}

// ═══════════════════════════════════════════════════════════════
// TOPBAR AUTH BUTTON
// ═══════════════════════════════════════════════════════════════

function initAuthBtn(btnId = "authBtn") {
  const btn  = document.getElementById(btnId);
  if (!btn) return;
  const user = Auth.getUser();

  if (user && !Auth.isTokenExpired()) {
    btn.textContent = "👤 " + (user.name?.split(" ")[0] || "Account");
    btn.style.cssText = "background:rgba(16,201,138,0.1);border-color:rgba(16,201,138,0.3);color:var(--green);";
    btn.onclick = () => {
      if (confirm(`Sign out, ${user.name}?`)) AuthAPI.logout(true);
    };
  } else {
    btn.textContent = "Sign In";
    btn.style.cssText = "background:rgba(61,127,255,0.1);border-color:var(--accent);color:var(--accent2);";
    btn.onclick = () => { window.location.href = "signin.html"; };
  }
}

// ═══════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════

function showToast(message, type = "info", duration = 3500) {
  let container = document.getElementById("_toast_wrap");
  if (!container) {
    container = Object.assign(document.createElement("div"), { id: "_toast_wrap" });
    container.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;";
    document.body.appendChild(container);
  }
  if (!document.getElementById("_toast_css")) {
    const s = document.createElement("style");
    s.id = "_toast_css";
    s.textContent = "@keyframes _tin{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@keyframes _tout{from{opacity:1}to{opacity:0;transform:translateY(8px)}}";
    document.head.appendChild(s);
  }
  const palette = {
    success: ["rgba(16,201,138,0.12)", "rgba(16,201,138,0.3)", "#10c98a"],
    error:   ["rgba(240,82,82,0.12)",  "rgba(240,82,82,0.3)",  "#f05252"],
    info:    ["rgba(61,127,255,0.12)", "rgba(61,127,255,0.3)", "#5b9bff"],
  };
  const [bg, border, color] = palette[type] || palette.info;
  const el = document.createElement("div");
  el.style.cssText = `background:${bg};border:1px solid ${border};color:${color};padding:11px 16px;border-radius:10px;font-size:13px;font-weight:500;font-family:'DM Sans',sans-serif;max-width:300px;box-shadow:0 4px 24px rgba(0,0,0,0.4);animation:_tin .22s ease;pointer-events:all;`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => { el.style.animation = "_tout .22s ease forwards"; setTimeout(() => el.remove(), 230); }, duration);
}