// frontend/src/pages/Account.jsx
// ─────────────────────────────────────────────────────────────
//  Panel konta użytkownika — logowanie, rejestracja, historia
// ─────────────────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { reportsAPI, paymentsAPI } from "../api/client";

// ── Formularz logowania / rejestracji ─────────────────────────
function AuthForm() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Wystąpił błąd. Spróbuj ponownie.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-3xl p-8 shadow-sm">
        <h2 className="text-2xl font-black text-gray-900 mb-2">
          {mode === "login" ? "Zaloguj się" : "Utwórz konto"}
        </h2>
        <p className="text-gray-500 text-sm mb-6">
          {mode === "login"
            ? "Zaloguj się, aby zobaczyć historię raportów."
            : "Konto pozwoli Ci zapisywać i pobierać raporty."}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
              placeholder="twoj@email.pl"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Hasło</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
              placeholder="Minimum 8 znaków"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-white font-bold rounded-xl transition-colors"
          >
            {loading ? "Proszę czekać…" : mode === "login" ? "Zaloguj się" : "Utwórz konto"}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-500">
          {mode === "login" ? (
            <>Nie masz konta?{" "}
              <button onClick={() => setMode("register")} className="text-teal-600 font-semibold hover:underline">
                Zarejestruj się
              </button>
            </>
          ) : (
            <>Masz już konto?{" "}
              <button onClick={() => setMode("login")} className="text-teal-600 font-semibold hover:underline">
                Zaloguj się
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────
function StatusBadge({ status }) {
  const map = {
    pending:   { label: "Oczekuje na płatność", cls: "bg-yellow-50 text-yellow-700" },
    paid:      { label: "Opłacony", cls: "bg-blue-50 text-blue-700" },
    generated: { label: "Gotowy do pobrania", cls: "bg-green-50 text-green-700" },
    failed:    { label: "Błąd generowania", cls: "bg-red-50 text-red-700" },
  };
  const { label, cls } = map[status] || { label: status, cls: "bg-gray-100 text-gray-600" };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>{label}</span>
  );
}

// ── Panel użytkownika ─────────────────────────────────────────
function Dashboard() {
  const { user, logout } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    reportsAPI.myReports()
      .then((res) => setReports(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Sprawdź czy jest token raportu w URL (po powrocie z PayNow)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      // Odśwież status raportu
      paymentsAPI.checkStatus(token).then((res) => {
        if (res.data.pdf_ready) {
          reportsAPI.myReports().then((r) => setReports(r.data));
        }
      }).catch(() => {});
      // Usuń token z URL
      window.history.replaceState({}, "", "/konto/raporty");
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Info o koncie */}
      <div className="bg-white rounded-3xl p-6 shadow-sm flex items-center justify-between">
        <div>
          <div className="text-xs text-gray-400 uppercase font-bold tracking-wide mb-1">Zalogowany jako</div>
          <div className="font-bold text-gray-900">{user.email}</div>
        </div>
        <button
          onClick={logout}
          className="px-4 py-2 text-sm text-gray-500 hover:text-red-600 border border-gray-200 rounded-xl transition-colors"
        >
          Wyloguj
        </button>
      </div>

      {/* Lista raportów */}
      <div className="bg-white rounded-3xl p-6 shadow-sm">
        <h2 className="font-black text-gray-900 text-xl mb-4">Historia raportów</h2>

        {loading && <div className="text-gray-400 text-sm">Ładowanie…</div>}

        {!loading && reports.length === 0 && (
          <div className="text-center py-10">
            <div className="text-5xl mb-3">📄</div>
            <p className="text-gray-500 text-sm">Nie masz jeszcze żadnych raportów.</p>
            <a href="/kalkulator" className="mt-4 inline-block px-5 py-2.5 bg-teal-500 text-white font-bold rounded-xl text-sm hover:bg-teal-600 transition-colors">
              Oblicz pierwszy raport →
            </a>
          </div>
        )}

        {!loading && reports.length > 0 && (
          <div className="space-y-3">
            {reports.map((report) => (
              <div
                key={report.token}
                className="flex items-center justify-between p-4 border border-gray-100 rounded-2xl hover:border-teal-200 transition-colors"
              >
                <div>
                  <div className="text-xs text-gray-400 mb-1">
                    {new Date(report.created_at).toLocaleDateString("pl-PL", {
                      year: "numeric", month: "long", day: "numeric",
                    })}
                  </div>
                  <StatusBadge status={report.status} />
                  {report.amount_pln && (
                    <span className="ml-2 text-xs text-gray-400">{report.amount_pln} zł</span>
                  )}
                </div>

                <div>
                  {report.pdf_ready ? (
                    <a
                      href={reportsAPI.downloadUrl(report.token)}
                      download
                      className="px-4 py-2 bg-teal-500 hover:bg-teal-600 text-white text-sm font-bold rounded-xl transition-colors"
                    >
                      ⬇ Pobierz PDF
                    </a>
                  ) : report.status === "pending" ? (
                    <a
                      href="/kalkulator"
                      className="px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-xl hover:border-teal-300 transition-colors"
                    >
                      Opłać raport
                    </a>
                  ) : (
                    <span className="text-xs text-gray-400">Trwa generowanie…</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Główny eksport ────────────────────────────────────────────
export default function Account() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#EEF9F7] flex items-center justify-center">
        <div className="text-gray-400">Ładowanie…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#EEF9F7]">
      <div className="max-w-3xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-black text-gray-900 mb-6">
          {user ? "Panel konta" : "Konto użytkownika"}
        </h1>
        {user ? <Dashboard /> : <AuthForm />}
      </div>
    </div>
  );
}
