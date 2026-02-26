// frontend/src/pages/Home.jsx
// ─────────────────────────────────────────────────────────────
//  Strona główna — zgodna z projektem graficznym (mockup)
// ─────────────────────────────────────────────────────────────

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const FEATURES = [
  {
    icon: "📄",
    title: "Szybkie obliczenia",
    desc: "Zaoszczędź czas — szczegółowe raporty gotowe w 30 sekund.",
  },
  {
    icon: "📊",
    title: "Raport PDF",
    desc: "Obejmuje szczegółowe analizy z najważniejszymi parametrami.",
  },
  {
    icon: "📋",
    title: "Raport energetyczny",
    desc: "Pełen opis i informacje oraz wytyczne.",
  },
];

const HOW_IT_WORKS = [
  { num: "1", title: "Podajesz dane", desc: "Adres inwestycji, zużycie energii, informacje o dachu." },
  { num: "2", title: "Otrzymujesz analizę", desc: "System liczy 3 scenariusze: Premium, Standard, Economy." },
  { num: "5", title: "Pobierasz raport PDF", desc: "Szczegółowy raport z analizą zwrotu z inwestycji na 25 lat." },
];

const CALC_FEATURES = [
  { icon: "⚡", title: "Szybkie wyniki", desc: "Pełna analiza scenariuszy i szacowanie ceny." },
  { icon: "📄", title: "Raport PDF", desc: "Otwórz każdy wniosek niezależnie z profilu." },
  { icon: "📈", title: "Analiza 25 lat", desc: "Generuj oszczędności tablicy ax 25 k." },
  { icon: "🔬", title: "Wsparcie eksperta", desc: "Skonsultuj nasz analizę ux norme dolia." },
];

export default function Home() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("kalkulator");

  return (
    <div className="min-h-screen bg-[#EEF9F7]">

      {/* ── HERO ─────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 pt-10 pb-6">
        <div className="bg-white rounded-3xl p-8 md:p-12 shadow-sm flex flex-col md:flex-row items-center gap-8">
          {/* Left */}
          <div className="flex-1">
            <h1 className="text-4xl md:text-5xl font-black text-gray-900 leading-tight mb-4">
              Oblicz opłacalność fotowoltaiki
            </h1>

            {/* Tiers */}
            <div className="flex items-center gap-3 mb-5">
              {["Premium", "Standard", "Economy"].map((t) => (
                <span key={t} className="font-bold text-gray-700 text-sm">{t}</span>
              ))}
            </div>

            {/* Bullets */}
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 mb-8 text-sm text-gray-600">
              {[
                ["⏱", "Szybkie obliczenia"],
                ["📅", "Gwarancja 25 lat"],
                ["📈", "Analiza na 25 lat"],
                ["🔋", "Magazyn energii"],
              ].map(([icon, text]) => (
                <div key={text} className="flex items-center gap-2">
                  <span>{icon}</span>
                  <span>{text}</span>
                </div>
              ))}
            </div>

            <Link
              to="/kalkulator"
              className="inline-flex items-center gap-2 px-7 py-3.5 bg-teal-500 hover:bg-teal-600 text-white font-bold rounded-xl shadow-lg shadow-teal-200 transition-all hover:scale-105 text-base"
            >
              Przejdź do kalkulatora
              <span>›</span>
            </Link>
          </div>

          {/* Right — ilustracja */}
          <div className="flex-shrink-0 w-64 h-56 md:w-80 md:h-64">
            <div className="w-full h-full bg-gradient-to-br from-teal-50 to-teal-100 rounded-2xl flex items-center justify-center">
              <div className="text-8xl">🏠</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3 KARTY CECH ──────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 pb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {FEATURES.map(({ icon, title, desc }) => (
            <div key={title} className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="text-2xl mb-3">{icon}</div>
              <h3 className="font-bold text-gray-900 mb-1">{title}</h3>
              <p className="text-sm text-gray-500">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── GŁÓWNA SEKCJA: Kalkulator + Porównywarka (zakładki) ── */}
      <section className="max-w-6xl mx-auto px-4 pb-8">
        <div className="bg-white rounded-3xl shadow-sm overflow-hidden">
          {/* Zakładki */}
          <div className="flex border-b border-gray-100">
            <button
              onClick={() => setActiveTab("kalkulator")}
              className={`flex-1 py-4 font-semibold text-sm transition-colors ${
                activeTab === "kalkulator"
                  ? "text-gray-900 border-b-2 border-teal-500 bg-white"
                  : "text-gray-400 bg-gray-50 hover:text-gray-600"
              }`}
            >
              Kalkulator PV
            </button>
            <button
              onClick={() => setActiveTab("magazyny")}
              className={`flex-1 py-4 font-semibold text-sm transition-colors ${
                activeTab === "magazyny"
                  ? "text-gray-900 border-b-2 border-teal-500 bg-white"
                  : "text-gray-400 bg-gray-50 hover:text-gray-600"
              }`}
            >
              Porównywarka Magazynów
            </button>
          </div>

          {/* Kalkulator preview */}
          {activeTab === "kalkulator" && (
            <div className="p-8">
              <div className="flex flex-col md:flex-row gap-6 items-center">
                <div className="flex-1 space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 p-3.5 border border-gray-200 rounded-xl text-gray-400 text-sm">
                      <span className="text-gray-300">○</span>
                      Adres inwestycji
                    </div>
                    <div className="flex items-center gap-3 p-3.5 border border-gray-200 rounded-xl text-gray-400 text-sm">
                      <span className="text-gray-300">○</span>
                      Roczne zużycie (kWh)
                    </div>
                    <div className="flex items-center gap-4">
                      <button className="flex-1 p-3.5 border border-gray-200 rounded-xl text-gray-500 text-sm flex items-center justify-between">
                        Nachylenie dachu <span>›</span>
                      </button>
                      <button className="flex-1 p-3.5 border border-gray-200 rounded-xl text-gray-500 text-sm flex items-center justify-between">
                        Nachylenie dachii <span>›</span>
                      </button>
                      <Link
                        to="/kalkulator"
                        className="px-6 py-3.5 bg-teal-500 hover:bg-teal-600 text-white font-bold rounded-xl transition-colors whitespace-nowrap text-sm"
                      >
                        Oblicz oszczędzi!
                      </Link>
                    </div>
                  </div>
                </div>

                {/* Mini wykres */}
                <div className="w-32 h-20 flex-shrink-0">
                  <svg viewBox="0 0 128 64" className="w-full h-full">
                    <polyline
                      fill="none"
                      stroke="#0D9488"
                      strokeWidth="2"
                      points="0,60 20,55 40,45 60,30 80,20 100,25 128,10"
                    />
                    <polyline
                      fill="rgba(13,148,136,0.1)"
                      stroke="none"
                      points="0,60 20,55 40,45 60,30 80,20 100,25 128,10 128,64 0,64"
                    />
                  </svg>
                </div>
              </div>

              {/* 4 karty pod kalkulatorem */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
                {CALC_FEATURES.map(({ icon, title, desc }) => (
                  <div key={title} className="bg-[#EEF9F7] rounded-xl p-4">
                    <div className="text-xl mb-2">{icon}</div>
                    <div className="font-bold text-gray-900 text-sm mb-1">{title}</div>
                    <div className="text-xs text-gray-500">{desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Porównywarka preview */}
          {activeTab === "magazyny" && (
            <div className="p-8">
              <p className="text-gray-600 mb-4 text-sm">
                Porównaj magazyny energii — pojemność, cena, gwarancja, technologia.
              </p>
              <Link
                to="/magazyny"
                className="inline-flex items-center gap-2 px-6 py-3 bg-teal-500 hover:bg-teal-600 text-white font-bold rounded-xl transition-colors"
              >
                🔋 Porównaj magazyny
                <span>›</span>
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* ── JAK TO DZIAŁA? ────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 pb-12">
        <div className="bg-white rounded-3xl p-8 md:p-12 shadow-sm">
          <h2 className="text-2xl font-black text-gray-900 mb-8">Jak to działa?</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {HOW_IT_WORKS.map(({ num, title, desc }) => (
              <div key={num} className="flex gap-4 items-start">
                <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center flex-shrink-0">
                  <span className="font-black text-teal-600">{num}</span>
                </div>
                <div>
                  <div className="font-bold text-gray-900 mb-1">{title}</div>
                  <div className="text-sm text-gray-500">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
