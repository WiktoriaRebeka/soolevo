// frontend/src/components/ScenarioCard.jsx
// Krok 2: typografia 50+, sekcja Efektywność z paskami, spacing, kontrast

import React, { useState } from "react";
import RoofVisualizer from "./RoofVisualizer";
import EnergyCharts from "./EnergyCharts";

// ─── FORMATOWANIE (bez zmian — logika backendu) ───────────────────────────────
const fmtPLN = (value) =>
  new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency: "PLN",
    maximumFractionDigits: 0,
  }).format(value || 0);

const fmtNum = (value, decimals = 2) => {
  if (value == null || isNaN(value)) return "—";
  return Number(value).toFixed(decimals);
};

const fmtPct = (rate) => {
  if (rate == null || isNaN(rate)) return "—";
  return `${Math.round((rate || 0) * 100)}%`;
};

const fmtPctNum = (rate) => {
  if (rate == null || isNaN(rate)) return 0;
  return Math.min(100, Math.max(0, Math.round((rate || 0) * 100)));
};

const renderPaybackRange = (base, opt, pess) => {
  if (!base || isNaN(base)) return "Brak danych";
  const values = [base, opt, pess].filter((v) => v != null && v > 0 && !isNaN(v));
  if (!values.length) return "Brak danych";
  const min = Math.min(...values).toFixed(1);
  const max = Math.max(...values).toFixed(1);
  return min === max ? `${min} lat` : `${min} – ${max} lat`;
};

// ─── PALETA — kolory zsynchronizowane z PDF (report_generator.py) ─────────────
// standard  → C_PRIMARY #1B4F72 / C_ACCENT #2E86C1
// premium   → fiolet (brak w PDF, zachowujemy własny)
// economy   → C_GREEN  #1E8449
const TIER_COLORS = {
  premium: {
    bg:        "bg-white",
    border:    "border-purple-400",
    badge:     "bg-purple-600",
    badgeText: "text-purple-700",
    accent:    "text-purple-700",
    bar:       "bg-purple-500",
    softBox:   "bg-purple-50 border-purple-200",
    heading:   "text-purple-800",
  },
  standard: {
    bg:        "bg-white",
    border:    "border-blue-400",
    badge:     "#1B4F72",          // inline hex — identyczny z PDF C_PRIMARY
    badgeText: "text-blue-800",
    accent:    "text-blue-800",
    bar:       "bg-blue-600",
    softBox:   "bg-blue-50 border-blue-200",
    heading:   "text-blue-900",
  },
  economy: {
    bg:        "bg-white",
    border:    "border-emerald-400",
    badge:     "#1E8449",          // inline hex — identyczny z PDF C_GREEN
    badgeText: "text-emerald-800",
    accent:    "text-emerald-800",
    bar:       "bg-emerald-600",
    softBox:   "bg-emerald-50 border-emerald-200",
    heading:   "text-emerald-900",
  },
};

// ─── PODKOMPONENT: ETYKIETA SEKCJI ────────────────────────────────────────────
// Zastępuje text-[10px] → text-sm dla czytelności 50+
function SectionLabel({ icon, children }) {
  return (
    <h4 className="flex items-center gap-2 text-sm font-black text-gray-800 uppercase tracking-wider mb-3">
      <span>{icon}</span>
      <span>{children}</span>
    </h4>
  );
}

// ─── PODKOMPONENT: PASEK PROGRESU ─────────────────────────────────────────────
function ProgressBar({ value, color = "bg-blue-500", label, sublabel }) {
  const pct = Math.min(100, Math.max(0, value || 0));
  return (
    <div>
      <div className="flex justify-between items-baseline mb-1.5">
        <span className="text-sm font-semibold text-gray-800">{label}</span>
        <span className="text-lg font-black text-gray-800">{pct}%</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
        <div
          className={`${color} h-3 rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {sublabel && (
        <p className="text-xs text-gray-800 mt-1">{sublabel}</p>
      )}
    </div>
  );
}

// ─── PODKOMPONENT: WIERSZ TABELI PARAMETRÓW ───────────────────────────────────
function ParamRow({ label, value, highlight = false, purple = false }) {
  return (
    <div
      className={`flex justify-between items-center py-2.5 px-1 border-b border-gray-100 last:border-0 ${
        highlight ? "font-bold text-gray-800" : "text-gray-800"
      }`}
    >
      <span className="text-sm">{label}</span>
      <span
        className={`text-sm font-semibold text-right max-w-[55%] ${
          purple ? "text-purple-700" : highlight ? "text-gray-900" : "text-gray-700"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

// ─── GŁÓWNY KOMPONENT ─────────────────────────────────────────────────────────
function ScenarioCard({ scenario, inputData }) {
  const [showCharts, setShowCharts] = useState(false);

  if (!scenario) return null;

  const c = TIER_COLORS[scenario.tier] || TIER_COLORS.standard;

  // Panele — bez zmian (dane z backendu)
  const allPanels = scenario.facet_layouts
    ? scenario.facet_layouts.flatMap((f) => f.layout || [])
    : [];

  const firstPanel = allPanels[0];
  const panelArea =
    firstPanel && scenario.panels_count
      ? (
          (scenario.panels_count || 0) *
          (firstPanel.width || 0) *
          (firstPanel.height || 0)
        ).toFixed(1)
      : "—";

  // Finansowe — dane z backendu, bez przeliczania
  const pvCost    = scenario.pv_cost_gross_pln || 0;
  const withBatCost =
    scenario.with_battery_total_cost_pln ||
    scenario.total_cost_with_battery_pln || 0;
  const pv25y     = scenario.pv_total_savings_25y_pln || 0;
  const bat25y    = scenario.battery_total_savings_25y_pln || 0;
  const savings1y = scenario.pv_savings_pln || 0;

  // Efektywność — dane z backendu
  const acNoBat   = scenario.autoconsumption_rate || 0;
  const acBat     = scenario.autoconsumption_rate_with_battery || 0;
  const ssNoBat   = scenario.self_sufficiency_rate || 0;
  const ssBat     = (scenario.self_sufficiency_percent_with_battery || 0) / 100;
  const coverage  = (scenario.coverage_percent || 0) / 100;

  const hasBattery = withBatCost > 0;
  const batJustified = scenario.is_economically_justified;
  const rationale = scenario.rationale || null;

  // Badge inline style (hex z PDF)
  const badgeStyle =
    scenario.tier !== "premium"
      ? { backgroundColor: c.badge, color: "#fff" }
      : {};
  const badgeClass =
    scenario.tier === "premium" ? `${c.badge} text-white` : "";

  return (
    <div className={`${c.bg} p-6 md:p-8 flex flex-col gap-6`}>

      {/* ── NAGŁÓWEK ────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span
              className={`${badgeClass} text-xs font-black px-3 py-1.5 rounded-full uppercase tracking-widest`}
              style={badgeStyle}
            >
              {scenario.tier}
            </span>
            {scenario.limited_by_roof && (
              <span className="text-xs bg-amber-400 text-amber-900 font-bold px-2.5 py-1 rounded-full">
                ⚠ Limit dachu
              </span>
            )}
          </div>
          <h3 className={`text-2xl md:text-3xl font-black ${c.heading} leading-tight mb-1`}>
            {scenario.label}
          </h3>
          <p className="text-sm text-gray-800 leading-snug">{scenario.description}</p>
        </div>
      </div>

      {/* ── 1. INWESTYCJA ──────────────────────────────────────────────────── */}
      <section>
        <SectionLabel icon="💰">Inwestycja</SectionLabel>

        <div className="space-y-3">
          {/* Karta: Sama PV */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-center justify-between gap-4">
            <div>
              <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
                ☀️ Tylko panele PV
              </div>
              <div className="text-2xl md:text-3xl font-black text-gray-900">
                {fmtPLN(pvCost)}
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
                Zwrot
              </div>
              <div className={`text-base font-black ${c.accent}`}>
                {renderPaybackRange(
                  scenario.pv_payback_years,
                  scenario.pv_payback_optimistic_years,
                  scenario.pv_payback_pessimistic_years
                )}
              </div>
            </div>
          </div>

          {/* Karta: PV + Magazyn (jeśli istnieje) */}
          {hasBattery && (
            <div
              className={`rounded-xl p-4 flex items-center justify-between gap-4 border-2 relative overflow-hidden ${
                batJustified
                  ? "bg-purple-50 border-purple-300"
                  : "bg-gray-50 border-gray-200"
              }`}
            >
              {batJustified && (
                <div className="absolute top-0 left-0 right-0 h-1 bg-purple-500" />
              )}
              <div>
                <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
                  {batJustified ? "🔋 PV + Magazyn energii (zalecany)" : "🔋 Magazyn (opcjonalny)"}
                </div>
                <div className="text-2xl md:text-3xl font-black text-gray-900">
                  {fmtPLN(withBatCost)}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
                  Zwrot
                </div>
                <div
                  className={`text-base font-black ${
                    batJustified ? "text-purple-700" : "text-gray-800"
                  }`}
                >
                  {renderPaybackRange(
                    scenario.battery_payback_years,
                    scenario.battery_payback_optimistic_years,
                    scenario.battery_payback_pessimistic_years
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── 2. ZYSK PO 25 LATACH ──────────────────────────────────────────── */}
      <section>
        <SectionLabel icon="📈">Zysk po 25 latach</SectionLabel>

        <div className={`grid gap-3 ${bat25y > 0 ? "grid-cols-2" : "grid-cols-1"}`}>
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
            <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-2">
              Sama PV
            </div>
            <div className={`text-xl md:text-2xl font-black ${c.accent}`}>
              {fmtPLN(pv25y)}
            </div>
            {savings1y > 0 && (
              <div className="text-xs text-gray-800 mt-1">
                ok. {fmtPLN(savings1y)} / rok 1
              </div>
            )}
          </div>

          {bat25y > 0 && (
            <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 text-center">
              <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-2">
                PV + Magazyn
              </div>
              <div className="text-xl md:text-2xl font-black text-purple-700">
                {fmtPLN(bat25y)}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── 3. EFEKTYWNOŚĆ (połączone: Autokonsumpcja + Samowystarczalność) ── */}
      <section>
        <SectionLabel icon="⚡">Efektywność instalacji</SectionLabel>

        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 md:p-5 space-y-4">

          {/* Autokonsumpcja — ile wyprodukowanej energii zużywasz na miejscu */}
          <ProgressBar
            value={fmtPctNum(acNoBat)}
            color={c.bar}
            label="Autokonsumpcja"
            sublabel="Ile wyprodukowanej energii zużywasz na miejscu (bez magazynu)"
          />

          {acBat > 0 && (
            <ProgressBar
              value={fmtPctNum(acBat)}
              color="bg-purple-500"
              label="Autokonsumpcja z magazynem"
              sublabel="To samo, ale ze zgromadzoną energią w baterii"
            />
          )}

          {/* Separator */}
          <div className="border-t border-gray-200 pt-4 space-y-4">
            {/* Samowystarczalność — ile swojego zapotrzebowania pokrywa PV */}
            <ProgressBar
              value={fmtPctNum(ssNoBat)}
              color={c.bar}
              label="Samowystarczalność"
              sublabel="Ile Twojego zapotrzebowania pokrywa PV (bez magazynu)"
            />

            {ssBat > 0 && (
              <ProgressBar
                value={fmtPctNum(ssBat)}
                color="bg-purple-500"
                label="Samowystarczalność z magazynem"
                sublabel="To samo, ale z baterią"
              />
            )}

            {/* Pokrycie zapotrzebowania */}
            {coverage > 0 && (
              <ProgressBar
                value={fmtPctNum(coverage)}
                color="bg-teal-500"
                label="Pokrycie zapotrzebowania"
                sublabel="Roczna produkcja PV vs roczne zużycie domu"
              />
            )}
          </div>
        </div>
      </section>

      {/* ── 4. REKOMENDACJA EKSPERTA ───────────────────────────────────────── */}
      {rationale && (
        <section>
          <SectionLabel icon="🤖">Rekomendacja eksperta</SectionLabel>
          <div className="bg-amber-50 border-l-4 border-amber-400 rounded-r-xl p-4 text-sm text-amber-900 leading-relaxed whitespace-pre-line">
            {rationale}
          </div>
        </section>
      )}

      {/* ── 5. PARAMETRY SYSTEMU ───────────────────────────────────────────── */}
      <section>
        <SectionLabel icon="🔧">Parametry systemu</SectionLabel>

        {/* Dwie liczby wyróżnione */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className={`${c.softBox} border rounded-xl p-4 text-center`}>
            <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
              Moc systemu
            </div>
            <div className={`text-xl font-black ${c.accent}`}>
              {fmtNum(scenario.total_power_kwp, 2)} kWp
            </div>
          </div>
          <div className={`${c.softBox} border rounded-xl p-4 text-center`}>
            <div className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-1">
              Produkcja roczna
            </div>
            <div className={`text-xl font-black ${c.accent}`}>
              {Math.round(scenario.annual_production_kwh || 0).toLocaleString("pl-PL")}
              <span className="text-sm font-semibold"> kWh</span>
            </div>
          </div>
        </div>

        {/* Tabela detali */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-1">
          <ParamRow
            label="Liczba paneli"
            value={`${scenario.panels_count || "—"} szt.`}
          />
          <ParamRow
            label="Model paneli"
            value={`${scenario.panel_brand || ""} ${scenario.panel_model || "—"}`.trim()}
          />
          {scenario.panel_power_wp && (
            <ParamRow
              label="Moc panela"
              value={`${scenario.panel_power_wp} Wp`}
            />
          )}
          <ParamRow
            label="Falownik"
            value={`${scenario.inverter_brand || ""} ${scenario.inverter_model || "—"}`.trim()}
          />
          <ParamRow label="Pow. paneli" value={`${panelArea} m²`} />

          {scenario.battery_recommended && scenario.battery_capacity_kwh > 0 && (
            <ParamRow
              label="Magazyn energii"
              value={`${(scenario.battery_model || "").split("(")[0] || "—"} · ${fmtNum(
                scenario.battery_capacity_kwh,
                1
              )} kWh`}
              purple
            />
          )}

          <ParamRow
            label="Koszt instalacji PV"
            value={fmtPLN(pvCost)}
            highlight
          />
        </div>
      </section>

      {/* ── 6. WIZUALIZACJA DACHU ─────────────────────────────────────────── */}
      <section>
        <SectionLabel icon="🏠">Rozmieszczenie paneli na dachu</SectionLabel>

        <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 overflow-x-auto">
          <RoofVisualizer
            width={inputData?.roof_width}
            length={inputData?.roof_real_length}
            panels={allPanels}
            roofType={inputData?.roof_type}
            triangle_base={inputData?.triangle_base}
            triangle_height={inputData?.triangle_height}
            trapezoid_base_a={inputData?.trapezoid_base_a}
            trapezoid_base_b={inputData?.trapezoid_base_b}
            trapezoid_height={inputData?.trapezoid_height}
            rhombus_diagonal_1={inputData?.rhombus_diagonal_1}
            rhombus_diagonal_2={inputData?.rhombus_diagonal_2}
            rhombus_offset_x={scenario.facet_layouts?.[0]?.rhombus_side_b || 0}
            azimuthDeg={inputData?.azimuth_deg}
          />
        </div>

        {/* Legenda — NOWA, czytelna dla 50+ */}
        <div className="mt-3 flex flex-wrap gap-4 justify-center">
          {[
            {
              color: "#e8f4f3",
              border: "#569793",
              label: "Powierzchnia dachu",
            },
            {
              color: "#FFD700",
              border: "#B8860B",
              label: "Panele fotowoltaiczne",
            },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <span
                className="inline-block w-5 h-4 rounded-sm shrink-0"
                style={{
                  backgroundColor: item.color,
                  border: `2px solid ${item.border}`,
                }}
              />
              <span className="text-sm text-gray-800 font-medium">{item.label}</span>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-800">
              Paneli: <strong className="text-gray-800">{allPanels.length} szt.</strong>
            </span>
          </div>
        </div>
      </section>

      {/* ── 7. WYKRESY ENERGETYCZNE (zwijane — leniwe ładowanie) ─────────── */}
      <section>
        <button
          onClick={() => setShowCharts((p) => !p)}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-100 hover:bg-gray-200 border border-gray-200 rounded-xl text-left transition-colors"
        >
          <SectionLabel icon="📊">
            <span className="normal-case font-bold text-gray-800 tracking-normal">
              Analiza energetyczna (wykresy)
            </span>
          </SectionLabel>
          <span
            className={`text-gray-800 text-lg transition-transform duration-300 ml-2 shrink-0 ${
              showCharts ? "rotate-180" : ""
            }`}
          >
            ▾
          </span>
        </button>

        {showCharts && (
          <div className="mt-3 bg-gray-50 border border-gray-200 rounded-xl p-3">
            <EnergyCharts scenario={scenario} />
          </div>
        )}
      </section>

    </div>
  );
}

export default ScenarioCard;
