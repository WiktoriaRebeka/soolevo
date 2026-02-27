// frontend/src/components/EnergyFlowChart.jsx
// Krok 5: kolory PV, większe fonty (50+), czystsza legenda
// Logika danych i dataKey — bez zmian (dane z backendu)

import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

// ─── KOLORY — zsynchronizowane z PDF i index.css ──────────────────────────────
const COLORS = {
  pv:               "#D4AC0D",   // Pozostawiam 'gold' z Twojej palety (spójność z natStr)
  gridImport:       "#E57373",   // Łagodniejszy, pastelowy czerwony (pasuje do s1/s2)
  consumption:      "#2E86C1",   // Twoje 'stroke' – idealnie spaja wykres z UI
  batteryCharge:    "#66BB6A",   // Świeża, "energetyczna" zieleń, ale mniej agresywna
  batteryDischarge: "#A78BFA",   // Miękki fiolet (lawendowy), pasujący do tonacji błękitów
  soc:              "#1B4F72",   // Twoje 'ridge' – ciemny błękit dla stabilności
};

// ─── TOOLTIP WŁASNY — większy font dla 50+ ────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 text-sm">
      <p className="font-bold text-gray-800 mb-2">Godzina {label}:00</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2 py-0.5">
          <span
            className="inline-block w-3 h-3 rounded-sm shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-800">{entry.name}:</span>
          <span className="font-bold text-gray-800">
            {entry.dataKey === "soc"
              ? `${entry.value}%`
              : `${Number(entry.value).toFixed(2)} kW`}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function EnergyFlowChart({ data, id }) {
  if (!data || data.length === 0) {
    return (
      <div
        id={id}
        style={{ height: 260 }}
        className="w-full flex items-center justify-center bg-gray-50 rounded-xl border border-dashed border-gray-200"
      >
        <p className="text-gray-800 text-sm">Brak danych dobowego przepływu energii.</p>
      </div>
    );
  }

  // Sprawdzamy czy są dane baterii — żeby nie rysować pustych serii
  const hasBattery = data.some(
    (d) => (d.batteryCharge ?? 0) > 0 || (d.batteryDischarge ?? 0) > 0 || (d.soc ?? 0) > 0
  );

  return (
    <div
      id={id}
      className="w-full bg-white rounded-xl p-4 border border-gray-100 shadow-sm"
    >
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ top: 8, right: hasBattery ? 10 : 0, left: -15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.25} />

          <XAxis
            dataKey="hour"
            tick={{ fontSize: 12, fill: "#6b7280" }}
            interval={2}
            tickLine={false}
            axisLine={{ stroke: "#e5e7eb" }}
          />

          {/* Oś lewa: kW */}
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 12, fill: "#6b7280" }}
            tickLine={false}
            axisLine={false}
            unit=" kW"
            width={48}
          />

          {/* Oś prawa: % naładowania baterii (tylko gdy jest bateria) */}
          {hasBattery && (
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: COLORS.soc }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
              width={36}
            />
          )}

          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f9fafb" }} />

          <Legend
            wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }}
            iconType="square"
            iconSize={10}
          />

          {/* Słupki energetyczne */}
          <Bar
            yAxisId="left"
            dataKey="pv"
            name="Produkcja PV"
            fill={COLORS.pv}
            stackId="supply"
            radius={[2, 2, 0, 0]}
          />
          <Bar
            yAxisId="left"
            dataKey="gridImport"
            name="Pobór z sieci"
            fill={COLORS.gridImport}
            stackId="supply"
            radius={[2, 2, 0, 0]}
          />
          <Bar
            yAxisId="left"
            dataKey="consumption"
            name="Zużycie domu"
            fill={COLORS.consumption}
            opacity={0.8}
            radius={[2, 2, 0, 0]}
          />

          {/* Serie baterii — tylko gdy istnieją dane */}
          {hasBattery && (
            <Bar
              yAxisId="left"
              dataKey="batteryCharge"
              name="Ładowanie bat."
              fill={COLORS.batteryCharge}
              radius={[2, 2, 0, 0]}
            />
          )}
          {hasBattery && (
            <Bar
              yAxisId="left"
              dataKey="batteryDischarge"
              name="Rozładowanie bat."
              fill={COLORS.batteryDischarge}
              radius={[2, 2, 0, 0]}
            />
          )}

          {/* Linia SOC — poziom naładowania baterii */}
          {hasBattery && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="soc"
              name="Stan baterii (%)"
              stroke={COLORS.soc}
              strokeWidth={2.5}
              dot={false}
              strokeDasharray="4 2"
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
