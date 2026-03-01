// frontend/src/components/Header.jsx
// ─────────────────────────────────────────────────────────────
//  Soolevo — Header v2.0 Premium
//  Styl: ciemny glass/frosted, akcenty cyan, logo navy gradient
//  Zachowuje: strukturę nawigacji, AuthContext, mobile menu
// ─────────────────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const NAV_LINKS = [
  { to: "/",          label: "Strona główna"   },
  { to: "/kalkulator",label: "Kalkulator PV"   },
  { to: "/magazyny",  label: "Magazyny energii"},
  { to: "/konto",     label: "Konto"           },
];

const HEADER_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700;800;900&display=swap');

  .soolevo-header {
    --h-navy:   #0D1B2E;
    --h-primary:#1B4F72;
    --h-accent: #2E86C1;
    --h-cyan:   #00C8DC;
    --h-gold:   #D4AC0D;
    background: rgba(13,27,46,0.92);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255,255,255,0.09);
    position: sticky; top: 0; z-index: 100;
    transition: background .3s ease;
  }

  .soolevo-header.scrolled {
    background: rgba(13,27,46,0.98);
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    border-bottom-color: rgba(0,200,220,0.15);
  }

  .sh-header-inner {
    max-width: 1080px; margin: 0 auto;
    padding: 0 24px; height: 64px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px;
  }

  /* ── LOGO ── */
  .sh-logo {
    display: flex; align-items: center; gap: 10px;
    text-decoration: none; flex-shrink: 0;
  }

  .sh-logo-icon {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, #00C8DC 0%, #1B4F72 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
    box-shadow: 0 2px 10px rgba(0,200,220,0.30);
    transition: transform .18s ease, box-shadow .18s ease;
    flex-shrink: 0;
  }
  .sh-logo:hover .sh-logo-icon {
    transform: scale(1.07);
    box-shadow: 0 4px 16px rgba(0,200,220,0.45);
  }

  .sh-logo-text { line-height: 1; }
  .sh-logo-name {
    font-family: 'Outfit', system-ui, sans-serif;
    font-weight: 800; font-size: 0.97rem;
    color: #fff; letter-spacing: -0.02em;
  }
  .sh-logo-sub  {
    font-size: 0.68rem; color: rgba(0,200,220,0.80);
    font-weight: 600; margin-top: 1px;
  }

  /* ── NAV DESKTOP ── */
  .sh-nav { display: none; align-items: center; gap: 2px; }
  @media (min-width: 768px) { .sh-nav { display: flex; } }

  .sh-nav-link {
    padding: 7px 14px; border-radius: 9px;
    font-size: 0.875rem; font-weight: 500;
    color: rgba(255,255,255,0.60);
    text-decoration: none;
    transition: background .18s, color .18s;
    white-space: nowrap;
  }
  .sh-nav-link:hover {
    background: rgba(255,255,255,0.07);
    color: rgba(255,255,255,0.90);
  }
  .sh-nav-link.active {
    background: rgba(0,200,220,0.12);
    color: #00C8DC; font-weight: 600;
    border: 1px solid rgba(0,200,220,0.22);
  }

  /* ── AUTH AREA ── */
  .sh-auth { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

  .sh-btn-ghost {
    padding: 7px 16px; border-radius: 9px;
    font-size: 0.855rem; font-weight: 600;
    color: rgba(255,255,255,0.65);
    background: transparent; border: 1px solid rgba(255,255,255,0.18);
    text-decoration: none; cursor: pointer;
    transition: all .18s;
    white-space: nowrap;
  }
  .sh-btn-ghost:hover {
    background: rgba(255,255,255,0.07);
    color: #fff; border-color: rgba(255,255,255,0.30);
  }

  .sh-btn-cta {
    padding: 8px 18px; border-radius: 9px;
    font-size: 0.855rem; font-weight: 700;
    background: linear-gradient(135deg, #00C8DC 0%, #2E86C1 100%);
    color: #0D1B2E; text-decoration: none; border: none; cursor: pointer;
    box-shadow: 0 2px 10px rgba(0,200,220,0.25);
    transition: transform .18s, box-shadow .18s;
    white-space: nowrap;
  }
  .sh-btn-cta:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,200,220,0.38);
    color: #0D1B2E;
  }

  .sh-user-badge {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 12px; border-radius: 9px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
  }
  .sh-user-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #00C8DC; flex-shrink: 0;
  }
  .sh-user-email {
    font-size: 0.78rem; color: rgba(255,255,255,0.65);
    max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }

  /* ── MOBILE MENU BUTTON ── */
  .sh-mobile-btn {
    display: flex; align-items: center; justify-content: center;
    width: 38px; height: 38px; border-radius: 9px;
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12);
    color: rgba(255,255,255,0.70); cursor: pointer;
    transition: background .18s; flex-shrink: 0;
    font-size: 1.1rem;
  }
  .sh-mobile-btn:hover { background: rgba(255,255,255,0.12); color: #fff; }
  @media (min-width: 768px) { .sh-mobile-btn { display: none; } }

  /* ── MOBILE DROPDOWN ── */
  .sh-mobile-menu {
    border-top: 1px solid rgba(255,255,255,0.08);
    background: rgba(10,22,40,0.97);
    padding: 12px 24px 16px;
  }
  .sh-mobile-link {
    display: block; padding: 11px 14px; border-radius: 9px;
    font-size: 0.93rem; font-weight: 500; color: rgba(255,255,255,0.65);
    text-decoration: none; transition: background .15s, color .15s;
    margin-bottom: 2px;
  }
  .sh-mobile-link:hover { background: rgba(255,255,255,0.07); color: #fff; }
  .sh-mobile-link.active { color: #00C8DC; background: rgba(0,200,220,0.10); font-weight: 600; }

  .sh-mobile-divider { height: 1px; background: rgba(255,255,255,0.08); margin: 8px 0; }
`;

export default function Header() {
  const { pathname }        = useLocation();
  const { user, logout }    = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  /* Inject CSS once */
  useEffect(() => {
    const el = document.createElement("style");
    el.id = "soolevo-header-css";
    if (!document.getElementById("soolevo-header-css")) {
      el.textContent = HEADER_CSS;
      document.head.appendChild(el);
    }
    return () => { document.getElementById("soolevo-header-css")?.remove(); };
  }, []);

  /* Scroll shadow */
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const isActive = (to) =>
    to === "/" ? pathname === "/" : pathname.startsWith(to);

  return (
    <header className={`soolevo-header ${scrolled ? "scrolled" : ""}`}>
      <div className="sh-header-inner">

        {/* ── LOGO ── */}
        <Link to="/" className="sh-logo">
          <div className="sh-logo-icon">☀️</div>
          <div className="sh-logo-text">
            <div className="sh-logo-name">Soolevo</div>
            <div className="sh-logo-sub">Kalkulator PV</div>
          </div>
        </Link>

        {/* ── NAV DESKTOP ── */}
        <nav className="sh-nav">
          {NAV_LINKS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={`sh-nav-link ${isActive(to) ? "active" : ""}`}
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* ── AUTH + MOBILE TOGGLE ── */}
        <div className="sh-auth">
          {user ? (
            <>
              <div className="sh-user-badge" style={{ display: "none" }} /* hidden on mobile */>
                <span className="sh-user-dot" />
                <span className="sh-user-email">{user.email}</span>
              </div>
              <button className="sh-btn-ghost" onClick={logout}>Wyloguj</button>
            </>
          ) : (
            <>
              <Link to="/konto" className="sh-btn-ghost"
                style={{ display: pathname === "/konto" ? "none" : undefined }}>
                Zaloguj
              </Link>
              <Link to="/kalkulator" className="sh-btn-cta">
                Kalkulator →
              </Link>
            </>
          )}

          {/* Mobile menu toggle */}
          <button
            className="sh-mobile-btn"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Menu"
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
      </div>

      {/* ── MOBILE MENU ── */}
      {menuOpen && (
        <div className="sh-mobile-menu">
          {NAV_LINKS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={`sh-mobile-link ${isActive(to) ? "active" : ""}`}
              onClick={() => setMenuOpen(false)}
            >
              {label}
            </Link>
          ))}
          {!user && (
            <>
              <div className="sh-mobile-divider" />
              <Link to="/kalkulator" className="sh-mobile-link" onClick={() => setMenuOpen(false)}
                style={{ color: "#00C8DC", fontWeight: 700 }}>
                ☀️ Otwórz kalkulator →
              </Link>
            </>
          )}
          {user && (
            <>
              <div className="sh-mobile-divider" />
              <button
                className="sh-mobile-link"
                style={{ background: "none", border: "none", cursor: "pointer", width: "100%", textAlign: "left", color: "rgba(255,255,255,.50)" }}
                onClick={() => { logout(); setMenuOpen(false); }}
              >
                Wyloguj
              </button>
            </>
          )}
        </div>
      )}
    </header>
  );
}
