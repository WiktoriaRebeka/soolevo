// frontend/src/components/ScenariosComparison.jsx
// Krok 1: Werdykt + layout 1 główna + 2 zwinięte

import React, { useState } from 'react';
import ScenarioCard from './ScenarioCard';

// ─── PALETA — identyczna z report_generator.py ────────────────────────────────
// C_PRIMARY = #1B4F72, C_ACCENT = #2E86C1, C_GREEN = #1E8449
// C_YELLOW = #D4AC0D, C_RED = #C0392B
// Używamy inline Tailwind + ewentualne klasy custom (patrz: tailwind.config.js krok 3)

const fmtPLN = (v) =>
  v ? Math.round(v).toLocaleString('pl-PL') + ' zł' : '—';

const fmtNum = (value, decimals = 0) => {
  if (value === 0) return '0';
  if (!value || isNaN(value)) return '—';
  return new Intl.NumberFormat('pl-PL', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

const renderPaybackRange = (base, opt, pess) => {
  if (!base || isNaN(base)) return 'brak danych';
  const values = [base, opt, pess].filter((v) => v != null && v > 0 && !isNaN(v));
  if (!values.length) return 'brak danych';
  const min = Math.min(...values).toFixed(1);
  const max = Math.max(...values).toFixed(1);
  return min === max ? `${min} lat` : `${min}–${max} lat`;
};

// ─── KOMPONENT: WERDYKT ───────────────────────────────────────────────────────
// Logika identyczna z S1 w report_generator.py
function VerdictBanner({ standard, economy }) {
  const payback =
    economy?.pv_payback_years ||
    standard?.pv_payback_years;
  const profit25 = standard?.pv_total_savings_25y_pln || 0;
  const savings1y = standard?.pv_savings_pln || 0;
  const paybackRange = renderPaybackRange(
    standard?.pv_payback_years,
    standard?.pv_payback_optimistic_years,
    standard?.pv_payback_pessimistic_years
  );

  // Progi identyczne jak w report_generator.py — nie zmieniać!
  let cfg;
  if (payback && payback < 12 && profit25 > 0) {
    cfg = {
      label: 'TAK — Fotowoltaika jest opłacalna',
      icon: '✅',
      bg: 'bg-green-50',
      border: 'border-green-400',
      titleColor: 'text-green-800',
      badgeBg: 'bg-green-600',
      barColor: 'bg-green-500',
    };
  } else if (payback && payback < 20) {
    cfg = {
      label: 'WARUNKOWO — Sprawdź zastrzeżenia',
      icon: '⚠️',
      bg: 'bg-amber-50',
      border: 'border-amber-400',
      titleColor: 'text-amber-800',
      badgeBg: 'bg-amber-500',
      barColor: 'bg-amber-400',
    };
  } else {
    cfg = {
      label: 'NIE — Inwestycja jest ryzykowna',
      icon: '❌',
      bg: 'bg-red-50',
      border: 'border-red-400',
      titleColor: 'text-red-800',
      badgeBg: 'bg-red-600',
      barColor: 'bg-red-500',
    };
  }

  return (
    <div
      className={`${cfg.bg} border-2 ${cfg.border} rounded-2xl overflow-hidden shadow-md`}
    >
      {/* Pasek kolorowy na górze — jak w PDF warning_box */}
      <div className={`${cfg.barColor} h-2 w-full`} />

      <div className="p-6 md:p-8">
        {/* Nagłówek werdyktu */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-5">
          <span className="text-4xl leading-none">{cfg.icon}</span>
          <h3 className={`text-2xl md:text-3xl font-black ${cfg.titleColor} leading-tight`}>
            {cfg.label}
          </h3>
        </div>

        {/* Uzasadnienie */}
        <p className="text-gray-700 text-base md:text-lg leading-relaxed mb-6">
          Instalacja zwróci się w{' '}
          <strong className={cfg.titleColor}>{paybackRange}</strong> i przyniesie{' '}
          <strong className={cfg.titleColor}>
            {profit25 ? fmtPLN(profit25) : '—'}
          </strong>{' '}
          zysku przez 25 lat. Roczne oszczędności w pierwszym roku:{' '}
          <strong className={cfg.titleColor}>
            {savings1y ? fmtPLN(savings1y) : '—'}
          </strong>
          .
        </p>
        
        {/* Trzy kluczowe liczby */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
            <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
              Zwrot inwestycji
            </div>
            <div className={`text-xl font-black ${cfg.titleColor}`}>
              {paybackRange}
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
            <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
              Zysk po 25 latach
            </div>
            <div className={`text-xl font-black ${cfg.titleColor}`}>
              {fmtPLN(profit25)}
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
            <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
              Oszczędności rok 1
            </div>
            <div className={`text-xl font-black ${cfg.titleColor}`}>
              {fmtPLN(savings1y)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── KOMPONENT: ZWINIĘTA KARTA ALTERNATYWY ────────────────────────────────────
const TIER_COLORS = {
  premium: {
    bg: 'bg-purple-50',
    border: 'border-purple-400',
    text: 'text-purple-800',
    badge: 'bg-purple-600',
    hover: 'hover:bg-purple-100',
  },
  economy: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-400',
    text: 'text-emerald-800',
    badge: 'bg-emerald-600',
    hover: 'hover:bg-emerald-100',
  },
};

function CollapsedAlternative({ scenario, isOpen, onToggle, inputData }) {
  if (!scenario) return null;
  const c = TIER_COLORS[scenario.tier] || TIER_COLORS.economy;
  const pvCost = scenario.pv_cost_gross_pln || 0;
  const paybackRange = renderPaybackRange(
    scenario.pv_payback_years,
    scenario.pv_payback_optimistic_years,
    scenario.pv_payback_pessimistic_years
  );

  return (
    <div className={`border-2 ${c.border} rounded-2xl overflow-hidden shadow-sm transition-shadow hover:shadow-md`}>
      {/* Nagłówek — klikalny */}
      <button
        onClick={onToggle}
        className={`w-full ${c.bg} ${c.hover} p-5 flex items-center justify-between text-left transition-colors`}
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-4">
          <span
            className={`${c.badge} text-white text-xs font-black px-3 py-1.5 rounded-full uppercase tracking-widest`}
          >
            {scenario.tier}
          </span>
          <div>
            <div className={`text-lg font-black ${c.text}`}>{scenario.label}</div>
            <div className="text-sm text-gray-500 mt-0.5">
              {fmtPLN(pvCost)} · zwrot {paybackRange}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 ml-4 shrink-0">
          <span className="text-sm text-gray-800 hidden sm:block">
            {isOpen ? 'Zwiń' : 'Rozwiń szczegóły'}
          </span>
          <span
            className={`text-xl text-gray-800 transition-transform duration-300 ${
              isOpen ? 'rotate-180' : ''
            }`}
          >
            ▾
          </span>
        </div>
      </button>

      {/* Rozwinięta treść */}
      {isOpen && (
        <div className="border-t-2 border-gray-100">
          <ScenarioCard scenario={scenario} inputData={inputData} />
        </div>
      )}
    </div>
  );
}

// ─── GŁÓWNY KOMPONENT ─────────────────────────────────────────────────────────
function ScenariosComparison({ data, inputFacet }) {
  const [expandedTier, setExpandedTier] = useState(null);

  const premium = data.scenarios?.find((s) => s.scenario_name === 'premium');
  const standard = data.scenarios?.find((s) => s.scenario_name === 'standard');
  const economy = data.scenarios?.find((s) => s.scenario_name === 'economy');

  const input_demand_kwh = data.input_data?.annual_consumption_kwh || 0;
  const input_province = data.input_data?.province || '—';
  const input_roof_area_m2 = data.input_data?.roof_area_m2;

  if (!premium || !standard || !economy) {
    return (
      <div className="p-8 text-center text-red-600 font-bold">
        Błąd: Nie udało się załadować scenariuszy.
      </div>
    );
  }

  const facet = inputFacet || {};
  const roofLength = data.input_data?.roof_slope_length_m || 0;
  const roofWidth =
    data.input_data?.roof_width ||
    facet.width ||
    facet.triangle_base ||
    facet.rhombus_diagonal_1 ||
    facet.trapezoid_base_a ||
    0;

  const inputDataForCard = {
    roof_width: roofWidth,
    roof_real_length: roofLength,
    roof_type: facet.roof_type || data.input_data?.roof_type,
    triangle_base: facet.triangle_base || roofWidth,
    triangle_height: roofLength,
    trapezoid_base_a: facet.trapezoid_base_a || 0,
    trapezoid_base_b: facet.trapezoid_base_b || 0,
    trapezoid_height: roofLength,
    rhombus_diagonal_1: facet.rhombus_diagonal_1 || 0,
    rhombus_diagonal_2: roofLength,
  };

  const toggleTier = (tier) =>
    setExpandedTier((prev) => (prev === tier ? null : tier));

  return (
    <div className="space-y-6">

      {/* ── 1. NAGŁÓWEK KONTEKSTU ──────────────────────────────────────────── */}
      <div
        style={{ background: 'linear-gradient(135deg, #1B4F72 0%, #2E86C1 100%)' }}
        className="text-white rounded-2xl p-6 md:p-8 shadow-lg"
      >
        <h2 className="text-2xl md:text-3xl font-black mb-1 leading-tight">
          ☀️ Twoja Instalacja Fotowoltaiczna
        </h2>
        <p className="text-blue-100 text-sm mb-5">
          Przeanalizowaliśmy Twój dach i przygotowaliśmy 3 gotowe rozwiązania.
        </p>

        {/* Trzy dane kontekstowe */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            {
              label: 'Twoje zapotrzebowanie',
              value: `${fmtNum(input_demand_kwh)} kWh/rok`,
            },
            {
              label: 'Powierzchnia dachu',
              value: input_roof_area_m2
                ? `${input_roof_area_m2.toFixed(1)} m²`
                : '— m²',
            },
            {
              label: 'Lokalizacja',
              value: String(input_province).charAt(0).toUpperCase() + String(input_province).slice(1),
            },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-white/15 backdrop-blur-sm rounded-xl px-4 py-3"
            >
              <div className="text-xs text-blue-200 font-semibold uppercase tracking-wider mb-1">
                {item.label}
              </div>
              <div className="text-lg md:text-xl font-black">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 2. WERDYKT ────────────────────────────────────────────────────── */}
      <VerdictBanner standard={standard} economy={economy} />

      {/* ── 3. SCENARIUSZ REKOMENDOWANY (Standard — zawsze rozwinięty) ──── */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <div className="h-px flex-1 bg-gray-200" />
          <span className="text-xs font-black text-gray-800 uppercase tracking-widest px-3">
            Scenariusz rekomendowany
          </span>
          <div className="h-px flex-1 bg-gray-200" />
        </div>

        {/* Obramowanie wyróżniające główną kartę */}
        <div className="border-2 border-blue-400 rounded-2xl overflow-hidden shadow-lg">
          {/* Mini-nagłówek wskazujący że to Standard */}
          <div
            style={{ background: '#1B4F72' }}
            className="flex items-center justify-between px-5 py-3"
          >
            <div className="flex items-center gap-3">
              <span className="bg-white/20 text-white text-xs font-black px-3 py-1 rounded-full uppercase tracking-widest">
                Standard
              </span>
              <span className="text-blue-100 text-sm font-semibold">
                Rekomendowany kompromis jakości i ceny
              </span>
            </div>
            <span className="text-white/60 text-xs hidden sm:block">
              Pełne szczegóły poniżej
            </span>
          </div>

          <ScenarioCard scenario={standard} inputData={inputDataForCard} />
        </div>
      </div>

      {/* ── 4. ALTERNATYWY (Premium + Economy — zwinięte) ─────────────────── */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <div className="h-px flex-1 bg-gray-200" />
          <span className="text-xs font-black text-gray-800 uppercase tracking-widest px-3">
            Alternatywne scenariusze
          </span>
          <div className="h-px flex-1 bg-gray-200" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CollapsedAlternative
            scenario={premium}
            isOpen={expandedTier === 'premium'}
            onToggle={() => toggleTier('premium')}
            inputData={inputDataForCard}
          />
          <CollapsedAlternative
            scenario={economy}
            isOpen={expandedTier === 'economy'}
            onToggle={() => toggleTier('economy')}
            inputData={inputDataForCard}
          />
        </div>
      </div>

      {/* ── 5. TABELA PORÓWNAWCZA (zwijana) ───────────────────────────────── */}
      <ComparisonTable
        premium={premium}
        standard={standard}
        economy={economy}
        fmtNum={fmtNum}
        renderPaybackRange={renderPaybackRange}
      />

      {/* ── 6. STOPKA Z ZASTRZEŻENIAMI ────────────────────────────────────── */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 text-sm text-gray-500">
        <p className="font-semibold text-gray-800 mb-2">📋 Ważne informacje:</p>
        <ul className="space-y-1 list-disc list-inside leading-relaxed">
          <li>Obliczenia zakładają bazową inflację cen energii na poziomie 4% rocznie</li>
          <li>Net-billing: nadwyżki rozliczane wg stawki RCEm (~30% ceny detalicznej)</li>
          <li>Zwrot inwestycji podawany jako przedział: optymistyczny – pesymistyczny</li>
          <li>Produkcja uwzględnia straty systemowe (×0.83)</li>
          <li>Koszty nie uwzględniają dotacji (Mój Prąd, Czyste Powietrze)</li>
          <li>Ostateczną ofertę przygotujemy po wizji lokalnej</li>
        </ul>
      </div>

    </div>
  );
}

// ─── TABELA PORÓWNAWCZA (osobny komponent, zwijana) ───────────────────────────
function ComparisonTable({ premium, standard, economy, fmtNum, renderPaybackRange }) {
  const [open, setOpen] = useState(false);

  const fmtPLN2 = (v) =>
    v ? Math.round(v).toLocaleString('pl-PL') + ' zł' : '—';

  const rows = [
    {
      label: 'Moc systemu',
      vals: [
        `${fmtNum(premium?.total_power_kwp, 2)} kWp`,
        `${fmtNum(standard?.total_power_kwp, 2)} kWp`,
        `${fmtNum(economy?.total_power_kwp, 2)} kWp`,
      ],
    },
    {
      label: 'Liczba paneli',
      vals: [
        `${premium?.panels_count || '—'} szt.`,
        `${standard?.panels_count || '—'} szt.`,
        `${economy?.panels_count || '—'} szt.`,
      ],
    },
    {
      label: 'Produkcja roczna',
      vals: [
        `${Math.round(premium?.annual_production_kwh || 0).toLocaleString('pl-PL')} kWh`,
        `${Math.round(standard?.annual_production_kwh || 0).toLocaleString('pl-PL')} kWh`,
        `${Math.round(economy?.annual_production_kwh || 0).toLocaleString('pl-PL')} kWh`,
      ],
    },
    {
      label: 'Koszt instalacji PV',
      vals: [
        fmtPLN2(premium?.pv_cost_gross_pln || premium?.cost_total_gross_pln),
        fmtPLN2(standard?.pv_cost_gross_pln || standard?.cost_total_gross_pln),
        fmtPLN2(economy?.pv_cost_gross_pln || economy?.cost_total_gross_pln),
      ],
    },
    {
      label: 'Zwrot inwestycji',
      vals: [
        renderPaybackRange(premium?.payback_years, premium?.payback_optimistic_years, premium?.payback_pessimistic_years),
        renderPaybackRange(standard?.payback_years, standard?.payback_optimistic_years, standard?.payback_pessimistic_years),
        renderPaybackRange(economy?.payback_years, economy?.payback_optimistic_years, economy?.payback_pessimistic_years),
      ],
    },
    {
      label: 'Zysk po 25 latach',
      vals: [
        fmtPLN2(premium?.pv_total_savings_25y_pln),
        fmtPLN2(standard?.pv_total_savings_25y_pln),
        fmtPLN2(economy?.pv_total_savings_25y_pln),
      ],
    },
    {
      label: 'PV + Magazyn (koszt)',
      vals: [
        fmtPLN2(premium?.with_battery_total_cost_pln),
        fmtPLN2(standard?.with_battery_total_cost_pln),
        fmtPLN2(economy?.with_battery_total_cost_pln),
      ],
    },
  ];

  const headers = [
    { label: 'Premium', color: 'text-purple-700', bg: 'bg-purple-50' },
    { label: 'Standard', color: 'text-blue-700', bg: 'bg-blue-50' },
    { label: 'Economy', color: 'text-emerald-700', bg: 'bg-emerald-50' },
  ];

  return (
    <div className="border border-gray-200 rounded-2xl overflow-hidden shadow-sm">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center justify-between px-5 py-4 bg-gray-800 text-white hover:bg-gray-700 transition-colors"
      >
        <span className="font-bold text-base">📊 Szczegółowe porównanie scenariuszy</span>
        <span className={`text-lg transition-transform duration-300 ${open ? 'rotate-180' : ''}`}>
          ▾
        </span>
      </button>

      {open && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-100 border-b border-gray-200">
                <th className="text-left px-4 py-3 font-bold text-gray-800 min-w-[160px]">
                  Parametr
                </th>
                {headers.map((h) => (
                  <th
                    key={h.label}
                    className={`text-center px-4 py-3 font-black ${h.color} ${h.bg}`}
                  >
                    {h.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={row.label}
                  className={`border-b border-gray-100 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}
                >
                  <td className="px-4 py-3 font-semibold text-gray-800">{row.label}</td>
                  {row.vals.map((val, j) => (
                    <td
                      key={j}
                      className={`px-4 py-3 text-center font-semibold ${headers[j].color}`}
                    >
                      {val}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ScenariosComparison;
