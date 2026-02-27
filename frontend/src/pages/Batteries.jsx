// frontend/src/pages/Batteries.jsx
// ─────────────────────────────────────────────────────────────
//  Porównywarka magazynów energii
// ─────────────────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { batteriesAPI } from "../api/client";

const CHEMISTRY_LABELS = {
  LFP: "LFP (LiFePO₄)",
  NMC: "NMC",
  NCA: "NCA",
};

function BatteryCard({ battery }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow border border-gray-100">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-xs font-bold text-teal-600 uppercase tracking-wide mb-1">
            {battery.brand}
          </div>
          <h3 className="font-black text-gray-900 text-base leading-tight">
            {battery.name}
          </h3>
        </div>
        <div className="bg-teal-50 text-teal-700 font-black text-lg px-3 py-1 rounded-xl whitespace-nowrap">
          {battery.capacity_kwh} kWh
        </div>
      </div>

      {/* Tagi */}
      {battery.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {battery.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Parametry */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        {[
          ["Technologia", battery.chemistry || "—"],
          ["Moc maks.", battery.max_power_kw ? `${battery.max_power_kw} kW` : "—"],
          ["Cykle", battery.cycles ? `${battery.cycles.toLocaleString()}+` : "—"],
          ["DoD", battery.dod_percent ? `${battery.dod_percent}%` : "—"],
          ["Gwarancja", battery.warranty_years ? `${battery.warranty_years} lat` : "—"],
          ["Sprawność", battery.efficiency_percent ? `${battery.efficiency_percent}%` : "—"],
        ].map(([label, value]) => (
          <div key={label} className="bg-gray-50 rounded-lg px-3 py-2">
            <div className="text-[10px] text-gray-800 uppercase font-bold tracking-wide">{label}</div>
            <div className="font-bold text-gray-800 text-sm">{value}</div>
          </div>
        ))}
      </div>

      {/* Opis */}
      {battery.description && (
        <p className="text-xs text-gray-500 mb-4 leading-relaxed">{battery.description}</p>
      )}

      {/* Cena + CTA */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <div>
          {battery.price_pln ? (
            <>
              <div className="text-xs text-gray-800">Cena orientacyjna</div>
              <div className="font-black text-gray-900 text-lg">
                ~{battery.price_pln.toLocaleString()} zł
              </div>
            </>
          ) : (
            <div className="text-sm text-gray-800">Cena na zapytanie</div>
          )}
        </div>
        <button
          className="px-4 py-2 bg-teal-500 hover:bg-teal-600 text-white text-sm font-bold rounded-xl transition-colors"
          onClick={() => window.open(`/kalkulator`, "_self")}
        >
          Oblicz z magazynem →
        </button>
      </div>
    </div>
  );
}

export default function Batteries() {
  const [batteries, setBatteries] = useState([]);
  const [filters, setFilters] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filtry aktywne
  const [activeChemistry, setActiveChemistry] = useState("");
  const [sortBy, setSortBy] = useState("capacity_kwh");
  const [sortDir, setSortDir] = useState("asc");
  const [search, setSearch] = useState("");

  useEffect(() => {
    Promise.all([
      batteriesAPI.list({ sort_by: sortBy, sort_dir: sortDir, chemistry: activeChemistry || undefined }),
      batteriesAPI.filters(),
    ])
      .then(([bRes, fRes]) => {
        setBatteries(bRes.data);
        setFilters(fRes.data);
      })
      .catch((err) => setError("Nie udało się załadować danych."))
      .finally(() => setLoading(false));
  }, [sortBy, sortDir, activeChemistry]);

  const filtered = batteries.filter((b) =>
    search
      ? b.name.toLowerCase().includes(search.toLowerCase()) ||
        b.brand.toLowerCase().includes(search.toLowerCase())
      : true
  );

  return (
    <div className="min-h-screen bg-[#EEF9F7]">
      <div className="max-w-6xl mx-auto px-4 py-10">

        {/* Nagłówek */}
        <div className="bg-white rounded-3xl p-8 shadow-sm mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-black text-gray-900 mb-1">
                🔋 Porównywarka magazynów energii
              </h1>
              <p className="text-gray-500">
                Porównaj {batteries.length} produktów — pojemność, cena, technologia, gwarancja.
              </p>
            </div>
          </div>
        </div>

        {/* Filtry */}
        <div className="bg-white rounded-2xl p-5 shadow-sm mb-6">
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
            {/* Szukaj */}
            <input
              type="text"
              placeholder="Szukaj (nazwa, marka)…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
            />

            {/* Technologia */}
            <select
              value={activeChemistry}
              onChange={(e) => setActiveChemistry(e.target.value)}
              className="px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
            >
              <option value="">Wszystkie technologie</option>
              {(filters.chemistries || []).map((c) => (
                <option key={c} value={c}>{CHEMISTRY_LABELS[c] || c}</option>
              ))}
            </select>

            {/* Sortowanie */}
            <select
              value={`${sortBy}_${sortDir}`}
              onChange={(e) => {
                const [field, dir] = e.target.value.split("_");
                setSortBy(field);
                setSortDir(dir);
              }}
              className="px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
            >
              <option value="capacity_kwh_asc">Pojemność ↑</option>
              <option value="capacity_kwh_desc">Pojemność ↓</option>
              <option value="price_pln_asc">Cena ↑</option>
              <option value="price_pln_desc">Cena ↓</option>
              <option value="warranty_years_desc">Gwarancja ↓</option>
            </select>
          </div>
        </div>

        {/* Grid magazynów */}
        {loading && (
          <div className="text-center py-16 text-gray-800">
            <div className="text-4xl mb-3">⏳</div>
            Ładowanie…
          </div>
        )}
        {error && (
          <div className="text-center py-16 text-red-500">{error}</div>
        )}
        {!loading && !error && (
          <>
            <div className="text-sm text-gray-500 mb-4">
              Znaleziono: <strong>{filtered.length}</strong> produktów
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((battery) => (
                <BatteryCard key={battery.id} battery={battery} />
              ))}
            </div>
            {filtered.length === 0 && (
              <div className="text-center py-16 text-gray-800">
                Brak wyników dla podanych filtrów.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
