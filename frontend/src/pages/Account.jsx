// frontend/src/pages/Account.jsx
// ─────────────────────────────────────────────────────────────
//  Panel konta — logowanie, rejestracja, historia raportów
//  Skin v2.0: ciemny mesh gradient + glassmorphism
//  Logika: bez zmian (AuthContext, reportsAPI, paymentsAPI)
// ─────────────────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Link }                 from "react-router-dom";
import { useAuth }              from "../contexts/AuthContext";
import { reportsAPI, paymentsAPI } from "../api/client";

/* ══════════════════════════════════════════════════════════════
   STYLE
══════════════════════════════════════════════════════════════ */
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800;900&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap');

  .sa-root {
    --navy:    #0D1B2E;
    --primary: #1B4F72;
    --accent:  #2E86C1;
    --cyan:    #00C8DC;
    --gold:    #D4AC0D;
    --green:   #1E8449;
    --red:     #C0392B;
    font-family: 'DM Sans', system-ui, sans-serif;
    min-height: 100vh;

    background-color: #0D1B2E;
    background-image:
      radial-gradient(ellipse 80% 55% at 10% 0%,   rgba(0,200,220,0.20)  0%, transparent 58%),
      radial-gradient(ellipse 55% 70% at 90% 20%,  rgba(27,79,114,0.55)  0%, transparent 55%),
      radial-gradient(ellipse 45% 45% at 55% 100%, rgba(212,172,13,0.13) 0%, transparent 55%);
  }

  /* ── SHARED HEADINGS ── */
  .sa-heading {
    font-family: 'Outfit', system-ui, sans-serif;
    font-weight: 800; letter-spacing: -0.025em; color: #fff;
  }

  /* ── GLASS CARD ── */
  .sa-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.13);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: 22px;
  }

  /* ── GOLD LINE ── */
  .sa-gold-line {
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--gold) 28%, var(--cyan) 72%, transparent);
    margin-bottom: 32px;
  }

  /* ══════════════
     FORMULARZ LOGOWANIA
  ══════════════ */
  .sa-auth-wrap {
    display: flex; align-items: center; justify-content: center;
    min-height: calc(100vh - 64px); padding: 40px 24px;
  }

  .sa-auth-card {
    width: 100%; max-width: 440px;
  }

  .sa-auth-logo {
    text-align: center; margin-bottom: 28px;
  }
  .sa-auth-logo-icon {
    width: 52px; height: 52px; border-radius: 14px;
    background: linear-gradient(135deg, #00C8DC 0%, #1B4F72 100%);
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1.5rem; margin-bottom: 10px;
    box-shadow: 0 4px 18px rgba(0,200,220,0.30);
  }
  .sa-auth-logo-name {
    font-family: 'Outfit', system-ui, sans-serif;
    font-weight: 800; font-size: 1.05rem; color: #fff;
    letter-spacing: -0.02em;
  }

  .sa-auth-title {
    font-family: 'Outfit', system-ui, sans-serif;
    font-weight: 800; font-size: 1.65rem;
    color: #fff; margin: 0 0 6px; letter-spacing: -0.025em;
  }
  .sa-auth-sub {
    font-size: 0.875rem; color: rgba(255,255,255,0.45); margin: 0 0 26px;
  }

  /* INPUT FIELDS */
  .sa-field { margin-bottom: 16px; }
  .sa-label {
    display: block; font-size: 0.78rem; font-weight: 700;
    color: rgba(255,255,255,0.55); letter-spacing: 0.05em;
    text-transform: uppercase; margin-bottom: 7px;
  }
  .sa-input {
    width: 100%; padding: 12px 16px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 11px; color: #fff; font-size: 0.93rem;
    outline: none; transition: border-color .18s, box-shadow .18s;
    box-sizing: border-box;
    font-family: 'DM Sans', system-ui, sans-serif;
  }
  .sa-input::placeholder { color: rgba(255,255,255,0.25); }
  .sa-input:focus {
    border-color: var(--cyan);
    box-shadow: 0 0 0 3px rgba(0,200,220,0.18);
    background: rgba(0,200,220,0.06);
  }

  /* ERROR BOX */
  .sa-error {
    background: rgba(192,57,43,0.14); border: 1px solid rgba(192,57,43,0.30);
    border-radius: 10px; padding: 11px 14px;
    font-size: 0.855rem; color: #FCA5A5; margin-bottom: 14px;
  }

  /* SUBMIT BUTTON */
  .sa-btn-primary {
    width: 100%; padding: 13px 20px;
    background: linear-gradient(135deg, var(--cyan) 0%, var(--accent) 100%);
    color: var(--navy); font-weight: 800; font-size: 0.95rem;
    border: none; border-radius: 11px; cursor: pointer;
    box-shadow: 0 4px 18px rgba(0,200,220,0.30);
    transition: transform .18s, box-shadow .18s, opacity .18s;
    font-family: 'DM Sans', system-ui, sans-serif;
  }
  .sa-btn-primary:hover:not(:disabled) {
    transform: translateY(-2px); box-shadow: 0 8px 28px rgba(0,200,220,0.40);
  }
  .sa-btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }

  /* MODE SWITCH */
  .sa-mode-switch {
    margin-top: 18px; text-align: center;
    font-size: 0.855rem; color: rgba(255,255,255,0.40);
  }
  .sa-mode-switch button {
    color: var(--cyan); font-weight: 700; background: none;
    border: none; cursor: pointer; text-decoration: underline;
    font-family: 'DM Sans', system-ui, sans-serif;
  }
  .sa-mode-switch button:hover { color: #fff; }

  /* ══════════════
     DASHBOARD
  ══════════════ */
  .sa-dash-wrap {
    max-width: 720px; margin: 0 auto; padding: 48px 24px;
  }

  .sa-dash-title {
    font-size: 1.6rem; margin: 0 0 24px;
  }

  /* Info konta */
  .sa-account-info {
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; padding: 20px 24px; margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .sa-account-info-left { display: flex; align-items: center; gap: 14px; }
  .sa-avatar {
    width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg, rgba(0,200,220,0.25), rgba(27,79,114,0.40));
    border: 1px solid rgba(0,200,220,0.30);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; flex-shrink: 0;
  }
  .sa-account-label {
    font-size: 0.70rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: rgba(255,255,255,0.35); margin-bottom: 3px;
  }
  .sa-account-email { font-weight: 700; color: #fff; font-size: 0.93rem; }

  .sa-btn-logout {
    padding: 8px 18px; border-radius: 9px;
    background: transparent; border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.50); font-size: 0.82rem; font-weight: 600;
    cursor: pointer; transition: all .18s;
    font-family: 'DM Sans', system-ui, sans-serif;
  }
  .sa-btn-logout:hover {
    border-color: rgba(192,57,43,0.45); color: #FCA5A5;
    background: rgba(192,57,43,0.08);
  }

  /* Raporty sekcja */
  .sa-reports-card { padding: 24px; margin-bottom: 0; }
  .sa-reports-title {
    font-size: 1.05rem; font-weight: 700; color: #fff; margin: 0 0 20px;
    display: flex; align-items: center; gap: 8px;
  }
  .sa-reports-count {
    background: rgba(0,200,220,0.15); border: 1px solid rgba(0,200,220,0.25);
    color: var(--cyan); font-size: 0.72rem; font-weight: 800;
    padding: 2px 8px; border-radius: 100px;
  }

  /* Pusty stan */
  .sa-empty {
    text-align: center; padding: 48px 20px;
  }
  .sa-empty-icon { font-size: 2.8rem; margin-bottom: 12px; opacity: 0.50; }
  .sa-empty-text { color: rgba(255,255,255,0.38); font-size: 0.875rem; margin-bottom: 20px; }

  /* Raport row */
  .sa-report-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 16px; border-radius: 12px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 10px; gap: 12px; flex-wrap: wrap;
    transition: border-color .18s;
  }
  .sa-report-row:hover { border-color: rgba(0,200,220,0.22); }

  .sa-report-date {
    font-size: 0.75rem; color: rgba(255,255,255,0.35); margin-bottom: 5px;
  }

  /* STATUS BADGES */
  .sa-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 100px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.03em;
  }
  .sa-badge-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
  .sa-badge-pending  { background: rgba(212,172,13,0.14); border: 1px solid rgba(212,172,13,0.28); color: #F0C040; }
  .sa-badge-pending .sa-badge-dot  { background: #F0C040; }
  .sa-badge-paid     { background: rgba(46,134,193,0.14); border: 1px solid rgba(46,134,193,0.28); color: #93C5FD; }
  .sa-badge-paid .sa-badge-dot     { background: #93C5FD; }
  .sa-badge-generated{ background: rgba(30,132,73,0.14);  border: 1px solid rgba(30,132,73,0.28);  color: #86EFAC; }
  .sa-badge-generated .sa-badge-dot{ background: #86EFAC; }
  .sa-badge-failed   { background: rgba(192,57,43,0.14);  border: 1px solid rgba(192,57,43,0.28);  color: #FCA5A5; }
  .sa-badge-failed .sa-badge-dot   { background: #FCA5A5; }

  /* REPORT ACTION BUTTONS */
  .sa-btn-download {
    padding: 8px 18px; border-radius: 9px;
    background: linear-gradient(135deg, var(--cyan), var(--accent));
    color: var(--navy); font-weight: 700; font-size: 0.82rem;
    text-decoration: none; display: inline-flex; align-items: center; gap: 6px;
    transition: transform .18s, box-shadow .18s;
    box-shadow: 0 2px 10px rgba(0,200,220,0.22);
    white-space: nowrap;
  }
  .sa-btn-download:hover {
    transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,200,220,0.35);
    color: var(--navy);
  }

  .sa-btn-pay {
    padding: 8px 18px; border-radius: 9px;
    background: rgba(212,172,13,0.12); border: 1px solid rgba(212,172,13,0.28);
    color: #F0C040; font-weight: 700; font-size: 0.82rem;
    text-decoration: none; display: inline-flex; align-items: center; gap: 6px;
    transition: all .18s; white-space: nowrap;
  }
  .sa-btn-pay:hover { background: rgba(212,172,13,0.20); color: #F0C040; }

  .sa-generating {
    font-size: 0.78rem; color: rgba(255,255,255,0.30);
    display: flex; align-items: center; gap: 6px;
  }

  @keyframes saSpinDot {
    0%,100%{ opacity:.3; transform:scale(1); }
    50%     { opacity:1;  transform:scale(1.4); }
  }
  .sa-spin-dot {
    width:6px; height:6px; border-radius:50%; background:var(--cyan);
    animation: saSpinDot 1.4s ease-in-out infinite;
  }

  /* LOADING STATE */
  .sa-loading {
    display: flex; align-items: center; justify-content: center;
    min-height: calc(100vh - 64px); gap: 10px;
    color: rgba(255,255,255,0.40); font-size: 0.875rem;
  }

  /* CTA w pustym stanie */
  .sa-cta {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 11px 24px; border-radius: 11px;
    background: linear-gradient(135deg, var(--cyan), var(--accent));
    color: var(--navy); font-weight: 800; font-size: 0.875rem;
    text-decoration: none;
    box-shadow: 0 3px 14px rgba(0,200,220,0.28);
    transition: transform .18s, box-shadow .18s;
  }
  .sa-cta:hover {
    transform: translateY(-2px); box-shadow: 0 6px 22px rgba(0,200,220,0.38);
    color: var(--navy);
  }

  /* ANIMACJE */
  @keyframes saFU {
    from { opacity:0; transform:translateY(16px); }
    to   { opacity:1; transform:translateY(0); }
  }
  .sa-a  { animation: saFU .6s cubic-bezier(.22,.68,0,1.2) both; }
  .sa-d1 { animation-delay:.06s; }
  .sa-d2 { animation-delay:.14s; }
  .sa-d3 { animation-delay:.22s; }
`;

/* ══════════════════════════════════════════════════════════════
   STATUS BADGE
══════════════════════════════════════════════════════════════ */
function StatusBadge({ status }) {
  const map = {
    pending:   { label: "Oczekuje na płatność", cls: "sa-badge-pending"   },
    paid:      { label: "Opłacony",              cls: "sa-badge-paid"      },
    generated: { label: "Gotowy do pobrania",    cls: "sa-badge-generated" },
    failed:    { label: "Błąd generowania",      cls: "sa-badge-failed"    },
  };
  const { label, cls } = map[status] || { label: status, cls: "sa-badge-paid" };
  return (
    <span className={`sa-badge ${cls}`}>
      <span className="sa-badge-dot" />
      {label}
    </span>
  );
}

/* ══════════════════════════════════════════════════════════════
   FORMULARZ LOGOWANIA / REJESTRACJI
══════════════════════════════════════════════════════════════ */
function AuthForm() {
  const { login, register }       = useAuth();
  const [mode, setMode]           = useState("login");
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else                  await register(email, password);
    } catch (err) {
      setError(err.response?.data?.detail || "Wystąpił błąd. Spróbuj ponownie.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sa-auth-wrap">
      <div className="sa-auth-card">

        {/* Logo */}
        <div className="sa-auth-logo sa-a sa-d1">
          <div className="sa-auth-logo-icon">☀️</div>
          <div className="sa-auth-logo-name">Soolevo</div>
        </div>

        <div className="sa-card" style={{ padding: "32px" }}>

          <div className="sa-a sa-d1">
            <h2 className="sa-auth-title">
              {mode === "login" ? "Zaloguj się" : "Utwórz konto"}
            </h2>
            <p className="sa-auth-sub">
              {mode === "login"
                ? "Zaloguj się, aby zobaczyć historię raportów."
                : "Konto pozwoli Ci zapisywać i pobierać raporty."}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="sa-a sa-d2">
            <div className="sa-field">
              <label className="sa-label">Email</label>
              <input
                type="email" required
                className="sa-input"
                placeholder="twoj@email.pl"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="sa-field">
              <label className="sa-label">Hasło</label>
              <input
                type="password" required minLength={8}
                className="sa-input"
                placeholder="Minimum 8 znaków"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            {error && <div className="sa-error">{error}</div>}

            <button type="submit" disabled={loading} className="sa-btn-primary">
              {loading
                ? "Proszę czekać…"
                : mode === "login" ? "Zaloguj się →" : "Utwórz konto →"}
            </button>
          </form>

          <div className="sa-mode-switch sa-a sa-d3">
            {mode === "login" ? (
              <>Nie masz konta?{" "}
                <button onClick={() => setMode("register")}>Zarejestruj się</button>
              </>
            ) : (
              <>Masz już konto?{" "}
                <button onClick={() => setMode("login")}>Zaloguj się</button>
              </>
            )}
          </div>
        </div>

        {/* Hint pod kartą */}
        <p style={{ textAlign: "center", marginTop: "18px", fontSize: "0.75rem", color: "rgba(255,255,255,0.22)" }}>
          Chronione przez JWT · soolevo.com
        </p>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   DASHBOARD — po zalogowaniu
══════════════════════════════════════════════════════════════ */
function Dashboard() {
  const { user, logout }      = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    reportsAPI.myReports()
      .then((res) => setReports(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  /* Sprawdź token raportu w URL (powrót z PayNow) */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token  = params.get("token");
    if (token) {
      paymentsAPI.checkStatus(token).then((res) => {
        if (res.data.pdf_ready) {
          reportsAPI.myReports().then((r) => setReports(r.data));
        }
      }).catch(() => {});
      window.history.replaceState({}, "", "/konto");
    }
  }, []);

  return (
    <div className="sa-dash-wrap">

      {/* ── Nagłówek ── */}
      <h1 className="sa-heading sa-dash-title sa-a sa-d1">Panel konta</h1>
      <div className="sa-gold-line sa-a sa-d1" />

      {/* ── Info konta ── */}
      <div className="sa-card sa-account-info sa-a sa-d1" style={{ marginBottom: "16px" }}>
        <div className="sa-account-info-left">
          <div className="sa-avatar">👤</div>
          <div>
            <div className="sa-account-label">Zalogowany jako</div>
            <div className="sa-account-email">{user.email}</div>
          </div>
        </div>
        <button className="sa-btn-logout" onClick={logout}>
          Wyloguj
        </button>
      </div>

      {/* ── Historia raportów ── */}
      <div className="sa-card sa-reports-card sa-a sa-d2">
        <div className="sa-reports-title">
          Historia raportów
          {reports.length > 0 && (
            <span className="sa-reports-count">{reports.length}</span>
          )}
        </div>

        {loading && (
          <div style={{ color: "rgba(255,255,255,0.35)", fontSize: "0.875rem", padding: "20px 0" }}>
            Ładowanie raportów…
          </div>
        )}

        {!loading && reports.length === 0 && (
          <div className="sa-empty">
            <div className="sa-empty-icon">📄</div>
            <p className="sa-empty-text">Nie masz jeszcze żadnych raportów.</p>
            <Link to="/kalkulator" className="sa-cta">
              ☀️ Oblicz pierwszy raport →
            </Link>
          </div>
        )}

        {!loading && reports.length > 0 && (
          <div>
            {reports.map((report) => (
              <div key={report.token} className="sa-report-row">
                {/* Lewa: data + status */}
                <div>
                  <div className="sa-report-date">
                    {new Date(report.created_at).toLocaleDateString("pl-PL", {
                      year: "numeric", month: "long", day: "numeric",
                    })}
                    {report.amount_pln && (
                      <span style={{ marginLeft: "8px", color: "rgba(255,255,255,0.30)" }}>
                        · {report.amount_pln} zł
                      </span>
                    )}
                  </div>
                  <StatusBadge status={report.status} />
                </div>

                {/* Prawa: akcja */}
                <div>
                  {report.pdf_ready ? (
                    <a
                      href={reportsAPI.downloadUrl(report.token)}
                      download
                      className="sa-btn-download"
                    >
                      ⬇ Pobierz PDF
                    </a>
                  ) : report.status === "pending" ? (
                    <Link to="/kalkulator" className="sa-btn-pay">
                      💳 Opłać raport
                    </Link>
                  ) : (
                    <span className="sa-generating">
                      <span className="sa-spin-dot" />
                      Trwa generowanie…
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── CTA: nowy raport ── */}
      {!loading && reports.length > 0 && (
        <div className="sa-a sa-d3" style={{ textAlign: "center", marginTop: "24px" }}>
          <Link to="/kalkulator" className="sa-cta">
            ☀️ Oblicz nowy raport →
          </Link>
        </div>
      )}

    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   GŁÓWNY EKSPORT
══════════════════════════════════════════════════════════════ */
export default function Account() {
  const { user, loading } = useAuth();

  useEffect(() => {
    const el = document.createElement("style");
    el.id = "sa-css";
    if (!document.getElementById("sa-css")) {
      el.textContent = CSS;
      document.head.appendChild(el);
    }
    return () => { document.getElementById("sa-css")?.remove(); };
  }, []);

  if (loading) {
    return (
      <div className="sa-root">
        <div className="sa-loading">
          <span className="sa-spin-dot" />
          Ładowanie…
        </div>
      </div>
    );
  }

  return (
    <div className="sa-root">
      {user ? <Dashboard /> : <AuthForm />}
    </div>
  );
}
