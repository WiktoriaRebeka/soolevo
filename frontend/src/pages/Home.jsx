// frontend/src/pages/Home.jsx
// ─────────────────────────────────────────────────────────────
//  Soolevo — Strona główna v2.1
//  Struktura: oryginalna (czytelna, user-friendly)
//  Skin: premium mesh gradient hero + glassmorphism + czyste sekcje
//  Paleta: zsynchronizowana z report.css (#1B4F72, #00C8DC, #D4AC0D)
// ─────────────────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

/* ── STYLE ────────────────────────────────────────────────── */
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700;800;900&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap');

  .sh-root {
    --navy:    #0D1B2E;
    --primary: #1B4F72;
    --accent:  #2E86C1;
    --cyan:    #00C8DC;
    --gold:    #D4AC0D;
    --green:   #1E8449;
    --purple:  #6D28D9;
    font-family: 'DM Sans', system-ui, sans-serif;
  }

  /* ══ HERO — mesh gradient ══ */
  .sh-hero {
    background-color: var(--navy);
    background-image:
      radial-gradient(ellipse 90% 70% at 10% 0%,   rgba(0,200,220,0.22)  0%, transparent 58%),
      radial-gradient(ellipse 60% 80% at 92% 20%,  rgba(27,79,114,0.60)  0%, transparent 55%),
      radial-gradient(ellipse 50% 45% at 55% 100%, rgba(212,172,13,0.15) 0%, transparent 55%),
      radial-gradient(ellipse 38% 38% at 3% 82%,   rgba(46,134,193,0.18) 0%, transparent 50%);
    padding: clamp(48px,7vw,80px) 24px clamp(40px,6vw,64px);
    position: relative; overflow: hidden;
  }

  /* Złota linia — jak w PDF */
  .sh-hero::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--gold) 28%, var(--cyan) 72%, transparent);
  }

  .sh-hero-inner {
    max-width: 1080px; margin: 0 auto;
    display: flex; flex-direction: column; gap: 24px;
  }

  @media (min-width: 768px) {
    .sh-hero-inner { flex-direction: row; align-items: center; gap: 48px; }
    .sh-hero-left  { flex: 1; }
    .sh-hero-right { flex-shrink: 0; width: 260px; }
  }

  /* Glass card wrapping hero content */
  .sh-hero-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.13);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border-radius: 24px;
    padding: clamp(28px,5vw,44px);
  }

  .sh-h1 {
    font-family: 'Outfit', system-ui, sans-serif;
    font-weight: 800; font-size: clamp(2rem,4.5vw,3.1rem);
    line-height: 1.1; letter-spacing: -0.03em;
    color: #fff; margin: 0 0 16px;
  }
  .sh-h1 .grad {
    background: linear-gradient(90deg, var(--cyan), var(--accent));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  }

  .sh-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
  .sh-pill  {
    padding: 4px 13px; border-radius: 100px;
    font-size: 0.77rem; font-weight: 700;
    display: inline-flex; align-items: center; gap: 5px;
  }
  .sh-pill-eco { background: rgba(30,132,73,.20);  border: 1px solid rgba(30,132,73,.35);  color: #86EFAC; }
  .sh-pill-std { background: rgba(46,134,193,.20); border: 1px solid rgba(46,134,193,.38); color: #93C5FD; }
  .sh-pill-pre { background: rgba(109,40,217,.20); border: 1px solid rgba(109,40,217,.35); color: #C4B5FD; }

  .sh-checks {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px; margin-bottom: 28px;
  }
  .sh-check {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.875rem; color: rgba(255,255,255,0.65);
  }
  .sh-check-icon {
    width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0;
    background: rgba(0,200,220,0.18); border: 1px solid rgba(0,200,220,0.35);
    color: var(--cyan); font-size: 0.6rem; font-weight: 900;
    display: flex; align-items: center; justify-content: center;
  }

  .sh-cta {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 13px 28px; border-radius: 13px;
    background: linear-gradient(135deg, var(--cyan) 0%, var(--accent) 100%);
    color: var(--navy); font-weight: 800; font-size: 0.93rem;
    text-decoration: none; border: none; cursor: pointer;
    box-shadow: 0 4px 18px rgba(0,200,220,0.32);
    transition: transform .18s ease, box-shadow .18s ease;
  }
  .sh-cta:hover {
    transform: translateY(-2px); color: var(--navy);
    box-shadow: 0 8px 28px rgba(0,200,220,0.44);
  }

  .sh-hero-visual {
    background: linear-gradient(135deg, rgba(0,200,220,0.10) 0%, rgba(27,79,114,0.25) 100%);
    border: 1px solid rgba(0,200,220,0.20); border-radius: 20px;
    aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
    font-size: 5rem; position: relative; overflow: hidden;
  }
  .sh-hero-visual::after {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(circle at 30% 30%, rgba(0,200,220,0.12), transparent 60%);
  }

  /* ══ SECTIONS ══ */
  .sh-section { padding: clamp(44px,6vw,72px) 24px; }
  .sh-section-gray  { background: #F8FAFC; }
  .sh-section-white { background: #FFFFFF; }
  .sh-inner { max-width: 1080px; margin: 0 auto; }

  .sh-eyebrow {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.10em;
    text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
  }
  .sh-section-h {
    font-family: 'Outfit', system-ui, sans-serif; font-weight: 800;
    font-size: clamp(1.5rem,3vw,2rem); color: #111827;
    letter-spacing: -0.025em; margin: 0 0 28px;
  }

  /* ══ FEATURE CARDS ══ */
  .sh-cards {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px,1fr)); gap: 16px;
  }
  .sh-card {
    background: #fff; border: 1px solid #E5E7EB; border-radius: 18px; padding: 24px;
    transition: transform .2s, border-color .2s, box-shadow .2s;
    position: relative; overflow: hidden;
  }
  .sh-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--cyan));
    opacity: 0; transition: opacity .2s;
  }
  .sh-card:hover { transform: translateY(-4px); border-color: rgba(46,134,193,.28); box-shadow: 0 12px 32px rgba(46,134,193,.09); }
  .sh-card:hover::before { opacity: 1; }

  .sh-card-icon {
    font-size: 1.7rem; margin-bottom: 12px; width: 48px; height: 48px;
    border-radius: 12px; background: #EFF6FF;
    display: flex; align-items: center; justify-content: center;
  }
  .sh-card-title { font-weight: 700; font-size: 0.93rem; color: #111827; margin-bottom: 5px; }
  .sh-card-desc  { font-size: 0.855rem; color: #6B7280; line-height: 1.55; }

  /* ══ TABS ══ */
  .sh-tabs-wrap {
    background: #fff; border: 1px solid #E5E7EB; border-radius: 20px; overflow: hidden;
    box-shadow: 0 2px 14px rgba(0,0,0,0.05);
  }
  .sh-tabs-nav  { display: flex; border-bottom: 1px solid #E5E7EB; }
  .sh-tab {
    flex: 1; padding: 15px 20px; font-size: 0.9rem; font-weight: 600;
    cursor: pointer; border: none; background: #F9FAFB;
    color: #6B7280; transition: all .18s;
    display: flex; align-items: center; justify-content: center; gap: 8px;
    border-bottom: 2px solid transparent;
  }
  .sh-tab:hover { background: #fff; color: #111827; }
  .sh-tab.active {
    background: #fff; color: #111827; font-weight: 700;
    border-bottom-color: var(--accent);
  }

  .sh-tab-body { padding: 28px; }

  .sh-tab-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr));
    gap: 12px; margin-bottom: 24px;
  }
  .sh-tab-item {
    background: #F8FAFC; border: 1px solid #E5E7EB; border-radius: 13px;
    padding: 16px; transition: border-color .18s;
  }
  .sh-tab-item:hover { border-color: rgba(46,134,193,.32); }
  .sh-tab-item-icon  { font-size: 1.3rem; margin-bottom: 8px; }
  .sh-tab-item-t     { font-weight: 700; font-size: 0.875rem; color: #111827; margin-bottom: 3px; }
  .sh-tab-item-d     { font-size: 0.8rem; color: #6B7280; line-height: 1.45; }

  /* Nieaktywne kafelki w tab magazynów */
  .sh-tab-item.muted { opacity: 0.60; }

  .sh-wip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 100px;
    background: rgba(212,172,13,0.10); border: 1px solid rgba(212,172,13,0.28);
    font-size: 0.72rem; font-weight: 700; color: #92700A;
    letter-spacing: 0.06em; text-transform: uppercase;
    margin-bottom: 16px;
  }

  /* ══ ANIMACJE ══ */
  @keyframes shFU {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .sh-a  { animation: shFU .65s cubic-bezier(.22,.68,0,1.2) both; }
  .sh-d1 { animation-delay: .08s; }
  .sh-d2 { animation-delay: .18s; }
  .sh-d3 { animation-delay: .28s; }
  .sh-d4 { animation-delay: .38s; }
`;

/* ── DANE ─────────────────────────────────────────────────── */
const FEATURES = [
  { icon: "📄", title: "Raport PDF w 60 sekund",   desc: "Kompletny dokument z analizą finansową — gotowy do pobrania natychmiast po płatności 49 zł." },
  { icon: "📊", title: "3 scenariusze w jednym",   desc: "Economy, Standard i Premium — porównujesz moc, koszty i zyski instalacji w jednym miejscu." },
  { icon: "🔋", title: "Analiza magazynu energii", desc: "Kalkulator sprawdza, czy dodanie baterii LFP jest ekonomicznie uzasadnione w Twoim przypadku." },
];

const CALC_ITEMS = [
  { icon: "⚡", title: "Szybkie obliczenia",  desc: "Pełna analiza 3 scenariuszy PV na podstawie Twojego zużycia i dachu." },
  { icon: "📄", title: "Personalizowany PDF", desc: "Raport z Twoimi danymi, adresem i dokładnymi parametrami instalacji." },
  { icon: "📈", title: "Prognoza 25 lat",     desc: "Cash-flow, IRR i zwrot z inwestycji z uwzględnieniem inflacji energii." },
  { icon: "🔋", title: "Kalkulator baterii",  desc: "Sprawdź opłacalność magazynu LFP razem z instalacją PV." },
];

const BAT_ITEMS = [
  { icon: "⚗️", title: "LFP i Solid-state",     desc: "Porównanie technologii baterii dostępnych na rynku w 2026." },
  { icon: "📋", title: "Ranking cena/pojemność", desc: "Zestawienie kosztów, cykli i gwarancji dla każdego modelu." },
  { icon: "🏆", title: "Najlepsze modele 2026",  desc: "Curated lista rekomendowanych magazynów dla instalacji domowych." },
  { icon: "🔗", title: "Integracja z PV",        desc: "Wybierz magazyn i przelicz go od razu z wybraną instalacją." },
];

/* ── KOMPONENT ────────────────────────────────────────────── */
export default function Home() {
  const [activeTab, setActiveTab] = useState("kalkulator");

  useEffect(() => {
    const el = document.createElement("style");
    el.id = "sh-css";
    if (!document.getElementById("sh-css")) {
      el.textContent = CSS;
      document.head.appendChild(el);
    }
    return () => { document.getElementById("sh-css")?.remove(); };
  }, []);

  return (
    <div className="sh-root">

      {/* ══ HERO ══════════════════════════════════════════════ */}
      <section className="sh-hero">
        <div className="sh-hero-inner">

          {/* LEWA — tekst */}
          <div className="sh-hero-left">
            <div className="sh-hero-card">

              <div className="sh-pills sh-a sh-d1">
                <span className="sh-pill sh-pill-eco">🌿 Economy</span>
                <span className="sh-pill sh-pill-std">⚡ Standard</span>
                <span className="sh-pill sh-pill-pre">💎 Premium</span>
              </div>

              <h1 className="sh-h1 sh-a sh-d2">
                Oblicz opłacalność<br />
                <span className="grad">fotowoltaiki</span>
              </h1>

              <div className="sh-checks sh-a sh-d3">
                {["Wyniki w 60 sekund", "Raport PDF A4", "Analiza na 25 lat", "3 warianty mocy"].map(t => (
                  <span key={t} className="sh-check">
                    <span className="sh-check-icon">✓</span>
                    {t}
                  </span>
                ))}
              </div>

              <div className="sh-a sh-d4">
                <Link to="/kalkulator" className="sh-cta">
                  Przejdź do kalkulatora <span style={{ fontSize: "1.1em" }}>→</span>
                </Link>
              </div>
            </div>
          </div>

          {/* PRAWA — wizualizacja */}
          <div className="sh-hero-right sh-a sh-d2">
            <div className="sh-hero-visual">
              <span style={{ position: "relative", zIndex: 1 }}>🏠</span>
            </div>
          </div>

        </div>
      </section>

      {/* ══ 3 KARTY CECH ══════════════════════════════════════ */}
      <section className="sh-section sh-section-gray">
        <div className="sh-inner">
          <p className="sh-eyebrow">Co otrzymujesz</p>
          <h2 className="sh-section-h">Wszystko w jednym raporcie</h2>
          <div className="sh-cards">
            {FEATURES.map(({ icon, title, desc }) => (
              <div key={title} className="sh-card">
                <div className="sh-card-icon">{icon}</div>
                <div className="sh-card-title">{title}</div>
                <p className="sh-card-desc">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ ZAKŁADKI ══════════════════════════════════════════ */}
      <section className="sh-section sh-section-white">
        <div className="sh-inner">
          <p className="sh-eyebrow">Narzędzia Soolevo</p>
          <h2 className="sh-section-h">Wybierz narzędzie</h2>

          <div className="sh-tabs-wrap">
            {/* Nav */}
            <div className="sh-tabs-nav">
              <button
                className={`sh-tab ${activeTab === "kalkulator" ? "active" : ""}`}
                onClick={() => setActiveTab("kalkulator")}
              >
                ☀️ Kalkulator PV
              </button>
              <button
                className={`sh-tab ${activeTab === "magazyny" ? "active" : ""}`}
                onClick={() => setActiveTab("magazyny")}
              >
                🔋 Magazyny energii
              </button>
            </div>

            {/* Tab: Kalkulator */}
            {activeTab === "kalkulator" && (
              <div className="sh-tab-body">
                <div className="sh-tab-grid">
                  {CALC_ITEMS.map(({ icon, title, desc }) => (
                    <div key={title} className="sh-tab-item">
                      <div className="sh-tab-item-icon">{icon}</div>
                      <div className="sh-tab-item-t">{title}</div>
                      <p className="sh-tab-item-d">{desc}</p>
                    </div>
                  ))}
                </div>
                <Link to="/kalkulator" className="sh-cta">
                  Otwórz kalkulator PV →
                </Link>
              </div>
            )}

            {/* Tab: Magazyny */}
            {activeTab === "magazyny" && (
              <div className="sh-tab-body">
                <div className="sh-wip">
                  <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#D4AC0D", display: "inline-block" }} />
                  W przygotowaniu · Sezon 2026
                </div>
                <div className="sh-tab-grid">
                  {BAT_ITEMS.map(({ icon, title, desc }) => (
                    <div key={title} className="sh-tab-item muted">
                      <div className="sh-tab-item-icon">{icon}</div>
                      <div className="sh-tab-item-t">{title}</div>
                      <p className="sh-tab-item-d">{desc}</p>
                    </div>
                  ))}
                </div>
                <Link to="/magazyny" className="sh-cta">
                  Zobacz szczegóły →
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>

    </div>
  );
}
