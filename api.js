const API_BASE = "http://localhost:8000";

// --- Auth ---

async function register(name, email, password, role = "user") {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password, role }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Registration failed");
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("user", JSON.stringify(data.user));
  return data;
}

async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("user", JSON.stringify(data.user));
  return data;
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.location.href = "/login.html";
}

function getToken() {
  return localStorage.getItem("token");
}

function getCurrentUser() {
  const u = localStorage.getItem("user");
  return u ? JSON.parse(u) : null;
}

function isAdmin() {
  const user = getCurrentUser();
  return user?.role === "admin";
}

// --- Authenticated Fetch ---

async function authFetch(endpoint, options = {}) {
  const token = getToken();
  if (!token) {
    logout();
    return;
  }
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (res.status === 401) {
    logout();
    return;
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// --- Dashboard API calls ---

async function getUserSummary() {
  return await authFetch("/dashboard/summary");
}

async function getAdminStats() {
  return await authFetch("/dashboard/admin/stats");
}

async function getAdminUsers() {
  return await authFetch("/dashboard/admin/users");
}