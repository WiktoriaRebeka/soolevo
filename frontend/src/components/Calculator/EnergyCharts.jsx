// frontend/src/components/EnergyCharts.jsx
// Krok 5: zakładki Lato/Zima, kolory PV palette, większe fonty
// Logika obliczeń (CashflowChart25) — bez zmian

import React, { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

import EnergyFlowChart from "./EnergyFlowChart";

// ─── FORMATOWANIE ─────────────────────────────────────────────────────────────
const formatPLN = (value) =>
  new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency: "PLN",
    maximumFractionDigits: 0,
  }).format(value || 0);

// ─── WYKRES: PROGNOZA ZYSKU 25 LAT ────────────────────────────────────────────
// Logika obliczeń bez zmian — dane z backendu
function CashflowChart25({ scenario }) {
  if (!scenario) return null;

  const pvCost    = scenario.pv_cost_gross_pln || 0;
  const batCost   = scenario.with_battery_total_cost_pln || scenario.total_cost_with_battery_pln || 0;
  const pvAnnual  = scenario.pv_savings_pln || 0;
  const batAnnual = scenario.total_savings_with_battery_pln || 0;
  const hasBat    = batAnnual > 0 && batCost > 0;

  // Budujemy tablicę danych — bez zmian
  const data = [];
  let pvCum  = -pvCost;
  let batCum = hasBat ? -batCost : null;

  for (let y = 1; y <= 25; y++) {
    const factor = Math.pow(1.04, y - 1);
    pvCum += pvAnnual * factor;
    const entry = { rok: y, pvNet: Math.round(pvCum) };
    if (hasBat && batCum !== null) {
      batCum += batAnnual * factor;
      entry.batNet = Math.round(batCum);
    }
    data.push(entry);
  }

  // Rok zwrotu — pierwsza wartość dodatnia
  const paybackYear = data.find((d) => d.pvNet >= 0)?.rok;

  return (
    <div className="w-full bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
      <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
        <h4 className="text-sm font-black text-gray-700 uppercase tracking-wide">
          📈 Prognoza zysku netto (25 lat)
        </h4>
        {paybackYear && (
          <span
            className="text-xs font-bold px-3 py-1 rounded-full"
            style={{ backgroundColor: "#D5F5E3", color: "#1E8449" }}
          >
            Zwrot w ~{paybackYear}. roku
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.25} />

          <XAxis
            dataKey="rok"
            tick={{ fontSize: 12, fill: "#6b7280" }}
            interval={4}
            tickLine={false}
            axisLine={{ stroke: "#e5e7eb" }}
            label={{ value: "rok", position: "insideBottomRight", offset: -5, fontSize: 11, fill: "#9ca3af" }}
          />

          <YAxis
            tick={{ fontSize: 12, fill: "#6b7280" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            width={42}
          />

          <Tooltip
            formatter={(v, name) => [formatPLN(v), name]}
            contentStyle={{ fontSize: "13px", borderRadius: "10px", border: "1px solid #e5e7eb" }}
          />

          {/* Linia zera — próg opłacalności */}
          <ReferenceLine
            y={0}
            stroke="#94a3b8"
            strokeWidth={1.5}
            strokeDasharray="4 2"
            label={{ value: "próg zwrotu", position: "insideTopLeft", fontSize: 10, fill: "#94a3b8" }}
          />

          {/* PV bez magazynu — C_YELLOW #D4AC0D */}
          <Area
            type="monotone"
            dataKey="pvNet"
            name="Zysk — sama PV"
            stroke="#D4AC0D"
            fill="#FEF9E7"
            strokeWidth={2.5}
          />

          {/* PV + magazyn — fiolet */}
          {hasBat && (
            <Area
              type="monotone"
              dataKey="batNet"
              name="Zysk — PV + Magazyn"
              stroke="#8b5cf6"
              fill="#f5f3ff"
              strokeWidth={2.5}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>

      <p className="text-xs text-gray-400 mt-2 text-center">
        Założenie: inflacja cen energii +4% rocznie · Net-billing
      </p>
    </div>
  );
}

// ─── GŁÓWNY KOMPONENT ─────────────────────────────────────────────────────────
function EnergyCharts({ scenario }) {
  const [activeTab, setActiveTab] = useState("summer");

  if (!scenario) return null;

  const result      = scenario.hourly_result_with_battery || scenario.hourly_result_without_battery;
  const summerData  = result?.seasonal_charts?.summer || result?.energy_flow_chart_data || null;
  const winterData  = result?.seasonal_charts?.winter || null;
  const hasWinter   = Boolean(winterData && winterData.length > 0);

  return (
    <div className="space-y-6">

      {/* ── WYKRES DOBOWY — z zakładkami Lato / Zima ────────────────────── */}
      <div>
        {/* Nagłówek z zakładkami */}
        <div className="flex items-center gap-1 mb-3">
          <button
            onClick={() => setActiveTab("summer")}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-t-xl text-sm font-bold border-b-2 transition-colors ${
              activeTab === "summer"
                ? "border-amber-400 text-amber-700 bg-amber-50"
                : "border-transparent text-gray-400 hover:text-gray-600"
            }`}
          >
            ☀️ Szczyt letni
          </button>

          {hasWinter && (
            <button
              onClick={() => setActiveTab("winter")}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-t-xl text-sm font-bold border-b-2 transition-colors ${
                activeTab === "winter"
                  ? "border-blue-400 text-blue-700 bg-blue-50"
                  : "border-transparent text-gray-400 hover:text-gray-600"
              }`}
            >
              ❄️ Minimum zimowe
            </button>
          )}

          {/* Separator — wypełnia resztę */}
          <div className="flex-1 border-b-2 border-gray-100" />
        </div>

        {/* Opis aktywnej zakładki */}
        <p className="text-xs text-gray-400 italic mb-3">
          {activeTab === "summer"
            ? "Czerwiec — wysoka irradiancja. Magazyn gromadzi nadwyżki na wieczór."
            : "Styczeń — niska produkcja. PV pokrywa tylko bazowe potrzeby dzienne."}
        </p>

        {/* Wykres */}
        {activeTab === "summer" && (
          <EnergyFlowChart data={summerData} id="chart-daily-summer" />
        )}
        {activeTab === "winter" && hasWinter && (
          <EnergyFlowChart data={winterData} id="chart-daily-winter" />
        )}

        {/* Fallback gdy brak danych letnich */}
        {activeTab === "summer" && !summerData && (
          <div className="bg-gray-50 border border-dashed border-gray-200 rounded-xl p-8 text-center text-gray-400 text-sm">
            Brak danych dobowych dla tego scenariusza.
          </div>
        )}
      </div>

      {/* ── PROGNOZA 25 LAT ─────────────────────────────────────────────── */}
      <CashflowChart25 scenario={scenario} />

    </div>
  );
}

export default EnergyCharts;
