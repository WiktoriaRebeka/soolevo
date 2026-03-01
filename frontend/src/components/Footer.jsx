// frontend/src/components/Footer.jsx
// ─────────────────────────────────────────────────────────────
//  Soolevo — Footer v2.0 Premium
//  Styl: ciemny navy, spójna paleta z Header + Home
//  Zachowuje: strukturę linków, treści
// ─────────────────────────────────────────────────────────────

import { Link } from "react-router-dom";
import { useEffect } from "react";

const FOOTER_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700;800;900&display=swap');

  .soolevo-footer {
    --f-navy:   #080F1A;
    --f-mid:    #0D1B2E;
    --f-primary:#1B4F72;
    --f-accent: #2E86C1;
    --f-cyan:   #00C8DC;
    --f-gold:   #D4AC0D;

    background: var(--f-navy);
    color: rgba(255,255,255,0.50);
    position: relative; overflow: hidden;
  }

  /* Złota linia górna — lustro hero */
  .soolevo-footer::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--f-gold) 28%, var(--f-cyan) 72%, transparent);
  }

  /* Dekoracyjny orb w tle */
  .soolevo-footer::after {
    content: '';
    position: absolute; bottom: -80px; right: -80px;
    width: 320px; height: 320px; border-radius: 50%;
    background: radial-gradient(circle, rgba(0,200,220,0.06) 0%, transparent 65%);
    pointer-events: none;
  }

  .sf-inner {
    max-width: 1080px; margin: 0 auto;
    padding: 48px 24px 0;
    position: relative; z-index: 1;
  }

  .sf-grid {
    display: flex; flex-direction: column; gap: 36px;
  }
  @media (min-width: 640px) {
    .sf-grid { flex-direction: row; justify-content: space-between; gap: 48px; }
    .sf-brand { max-width: 300px; }
  }

  /* ── Brand column ── */
  .sf-logo {
    display: flex; align-items: center; gap: 10px;
    text-decoration: none; margin-bottom: 14px;
  }
  .sf-logo-icon {
    width: 34px; height: 34px; border-radius: 9px;
    background: linear-gradient(135deg, #00C8DC 0%, #1B4F72 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(0,200,220,0.22);
  }
  .sf-logo-name {
    font-family: 'Outfit', system-ui, sans-serif;
    font-weight: 800; font-size: 0.93rem; color: #fff;
    letter-spacing: -0.02em;
  }
  .sf-logo-sub {
    font-size: 0.66rem; color: rgba(0,200,220,0.75);
    font-weight: 600; margin-top: 1px;
  }

  .sf-tagline {
    font-size: 0.855rem; line-height: 1.6;
    color: rgba(255,255,255,0.42); margin-bottom: 20px;
  }

  /* CTA w footerze */
  .sf-cta {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 9px 20px; border-radius: 10px;
    background: linear-gradient(135deg, rgba(0,200,220,0.20) 0%, rgba(46,134,193,0.20) 100%);
    border: 1px solid rgba(0,200,220,0.28);
    color: #00C8DC; font-size: 0.82rem; font-weight: 700;
    text-decoration: none;
    transition: background .18s, border-color .18s, transform .18s;
  }
  .sf-cta:hover {
    background: rgba(0,200,220,0.14);
    border-color: rgba(0,200,220,0.42);
    transform: translateY(-1px);
    color: #00C8DC;
  }

  /* ── Link columns ── */
  .sf-links { display: flex; gap: 36px; }

  .sf-col-title {
    font-size: 0.75rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: rgba(255,255,255,0.75); margin-bottom: 12px;
  }

  .sf-col-links { display: flex; flex-direction: column; gap: 8px; }

  .sf-link {
    font-size: 0.855rem; color: rgba(255,255,255,0.42);
    text-decoration: none; transition: color .15s;
    white-space: nowrap;
  }
  .sf-link:hover { color: rgba(255,255,255,0.80); }

  .sf-link-wip {
    display: inline-flex; align-items: center; gap: 5px;
  }
  .sf-wip-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--f-gold); opacity: 0.70; flex-shrink: 0;
  }

  /* ── Bottom bar ── */
  .sf-bottom {
    border-top: 1px solid rgba(255,255,255,0.07);
    margin-top: 40px;
    padding: 16px 24px;
    display: flex; flex-direction: column; gap: 8px; align-items: center;
    position: relative; z-index: 1;
  }
  @media (min-width: 640px) {
    .sf-bottom { flex-direction: row; justify-content: space-between; }
  }

  .sf-copyright {
    font-size: 0.78rem; color: rgba(255,255,255,0.25);
  }

  .sf-bottom-links {
    display: flex; gap: 16px;
  }
  .sf-bottom-link {
    font-size: 0.78rem; color: rgba(255,255,255,0.25);
    text-decoration: none; transition: color .15s;
  }
  .sf-bottom-link:hover { color: rgba(255,255,255,0.55); }

  /* Report price badge */
  .sf-price-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 10px; border-radius: 100px;
    background: rgba(212,172,13,0.12); border: 1px solid rgba(212,172,13,0.25);
    font-size: 0.70rem; font-weight: 700; color: rgba(212,172,13,0.80);
    letter-spacing: 0.05em;
  }
`;

export default function Footer() {
  useEffect(() => {
    const el = document.createElement("style");
    el.id = "soolevo-footer-css";
    if (!document.getElementById("soolevo-footer-css")) {
      el.textContent = FOOTER_CSS;
      document.head.appendChild(el);
    }
    return () => { document.getElementById("soolevo-footer-css")?.remove(); };
  }, []);

  return (
    <footer className="soolevo-footer">
      <div className="sf-inner">
        <div className="sf-grid">

          {/* ── BRAND ── */}
          <div className="sf-brand">
            <Link to="/" className="sf-logo">
              <div className="sf-logo-icon">☀️</div>
              <div>
                <div className="sf-logo-name">Soolevo</div>
                <div className="sf-logo-sub">Kalkulator PV</div>
              </div>
            </Link>

            <p className="sf-tagline">
              Kalkulator fotowoltaiki i porównywarka magazynów energii dla polskiego rynku.
              Personalizowany raport PDF w 60 sekund.
            </p>

            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <Link to="/kalkulator" className="sf-cta">
                ☀️ Otwórz kalkulator →
              </Link>
              
            </div>
          </div>

          {/* ── LINK COLUMNS ── */}
          <div className="sf-links">
            <div>
              <div className="sf-col-title">Narzędzia</div>
              <div className="sf-col-links">
                <Link to="/kalkulator" className="sf-link">Kalkulator PV</Link>
                <Link to="/magazyny"   className="sf-link sf-link-wip">
                  <span className="sf-wip-dot" />
                  Magazyny energii
                </Link>
                <Link to="/konto"      className="sf-link">Moje konto</Link>
              </div>
            </div>

            <div>
              <div className="sf-col-title">Prawne</div>
              <div className="sf-col-links">
                <a href="/regulamin"    className="sf-link">Regulamin</a>
                <a href="/prywatnosc"   className="sf-link">Polityka prywatności</a>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── BOTTOM BAR ── */}
      <div className="sf-bottom">
        <span className="sf-copyright">
          © {new Date().getFullYear()} Soolevo. Wszelkie prawa zastrzeżone.
        </span>
        <div className="sf-bottom-links">
          <a href="/regulamin"  className="sf-bottom-link">Regulamin</a>
          <a href="/prywatnosc" className="sf-bottom-link">Prywatność</a>
        </div>
      </div>
    </footer>
  );
}
