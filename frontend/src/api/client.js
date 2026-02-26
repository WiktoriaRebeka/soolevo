// frontend/src/api/client.js
// ─────────────────────────────────────────────────────────────
//  Axios instance z auto-refresh tokenów
//  Endpointy kalkulatora: /calculator/...
// ─────────────────────────────────────────────────────────────

import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 90_000, // 90s dla długich obliczeń PV
});

// ── Request interceptor — dołącz token JWT ───────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — auto-refresh przy 401 ─────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE}/api/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = res.data;
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);
          original.headers.Authorization = `Bearer ${access_token}`;
          return api(original);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/konto";
        }
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ─────────────────────────────────────────────────────
export const authAPI = {
  register: (email, password) =>
    api.post("/api/auth/register", { email, password }),
  login: (email, password) =>
    api.post("/api/auth/login", { email, password }),
  refresh: (refresh_token) =>
    api.post("/api/auth/refresh", { refresh_token }),
  me: () => api.get("/api/auth/me"),
};

// ── Reports ──────────────────────────────────────────────────
export const reportsAPI = {
  create: (inputJson) =>
    api.post("/api/reports/create", { input_json: inputJson }),
  myReports: () => api.get("/api/reports/my"),
  downloadUrl: (token) => `${API_BASE}/api/reports/download/${token}`,
};

// ── Payments ─────────────────────────────────────────────────
export const paymentsAPI = {
  createPayment: (reportToken, buyerEmail) =>
    api.post("/api/payments/create", {
      report_token: reportToken,
      buyer_email: buyerEmail,
    }),
  checkStatus: (reportToken) =>
    api.get(`/api/payments/status/${reportToken}`),
};

// ── Batteries ────────────────────────────────────────────────
export const batteriesAPI = {
  list: (params = {}) => api.get("/api/batteries", { params }),
  filters: () => api.get("/api/batteries/filters"),
};

// ── Calculator ───────────────────────────────────────────────
// Prefix: /calculator (router w backend/app/routers/calculator.py)
export const calculatorAPI = {
  // Oblicz scenariusze PV
  calculate: (data) =>
    api.post("/calculator/calculate/scenarios", data),

  // Dane do raportu (pełny ReportData)
  reportData: (data) =>
    api.post("/calculator/report/data", data),

  // PDF blob — używaj bezpośrednio z responseType: 'blob'
  reportPdfUrl: () => `${API_BASE}/calculator/report/pdf`,
};