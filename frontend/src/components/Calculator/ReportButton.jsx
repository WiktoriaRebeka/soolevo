// frontend/src/components/ReportButton.jsx

import React, { useState } from 'react';
import axios from 'axios';
import { FileText, Loader2 } from 'lucide-react';

const API_URL = "/api";

const ReportButton = ({ formData, results, inputFacet }) => {
  const [loading, setLoading]         = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError]             = useState(null);

  const handleDownload = async () => {
    setLoading(true);
    setError(null);

    try {
      setLoadingStep("Przygotowuję dane...");

      // ─────────────────────────────────────────────────────────────
      // 1) Pobieramy dane scenariusza i wykresów
      // ─────────────────────────────────────────────────────────────
      const scenarios = results?.scenarios || [];
      const stdScenario =
        scenarios.find((s) => s.scenario_name === "standard") ||
        scenarios.find((s) => s.tier === "standard") ||
        scenarios[1] ||
        {};

      const hourlyResult =
        stdScenario.hourly_result_with_battery ||
        stdScenario.hourly_result_without_battery ||
        {};

      const seasonalChartsData = hourlyResult.seasonal_charts || {};

      setLoadingStep("Generuję raport PDF...");

      // ─────────────────────────────────────────────────────────────
      // 2) Budujemy facet (dach)
      // ─────────────────────────────────────────────────────────────
      const facet = { ...(inputFacet || {}) };

      if (!facet.id)        facet.id = "1";
      if (!facet.roof_type) facet.roof_type = formData.roofType || "rectangular";
      if (!facet.roof_mode) facet.roof_mode = formData.roofMode || "building_length";

      Object.keys(facet).forEach((k) => {
        if (
          facet[k] === undefined ||
          facet[k] === null ||
          (typeof facet[k] === "number" && isNaN(facet[k]))
        ) {
          delete facet[k];
        }
      });

      // ─────────────────────────────────────────────────────────────
      // 3) Budujemy payload dla backendu
      // ─────────────────────────────────────────────────────────────
      const payload = {
        bill: formData.estimatedConsumptionMode
          ? 0
          : parseFloat(formData.bill) || 0,
        is_annual_bill: formData.estimatedConsumptionMode
          ? false
          : Boolean(formData.isAnnualBill),
        operator: formData.operator,
        tariff: formData.tariff,
        province: formData.province,
        household_size: parseInt(formData.householdSize) || 4,
        people_home_weekday: parseInt(formData.peopleHomeWeekday) || 1,
        facets: [facet],
        include_battery: true,
        estimated_consumption_mode: Boolean(formData.estimatedConsumptionMode),
        area_m2: formData.area_m2 ? parseFloat(formData.area_m2) : null,
        building_standard: formData.building_standard || "WT2021",
        uses_induction: Boolean(formData.uses_induction),
        has_heat_pump: Boolean(formData.has_heat_pump),
        has_ac: Boolean(formData.has_ac),
        has_ev: Boolean(formData.has_ev),
        planned_heat_pump: Boolean(formData.planned_heat_pump),
        planned_ac: Boolean(formData.planned_ac),
        planned_ev: Boolean(formData.planned_ev),
        planned_other_kwh: 0.0,
        inflation_rate: parseFloat(formData.inflationRate) || 0.04,
        scenario_to_highlight: "standard",
        seasonal_charts_data: seasonalChartsData,
      };

      Object.keys(payload).forEach(
        (k) => payload[k] === undefined && delete payload[k]
      );

      // ─────────────────────────────────────────────────────────────
      // 4) Tworzymy raport → backend zwraca token
      // ─────────────────────────────────────────────────────────────
      const createRes = await axios.post(`${API_URL}/reports/create`, {
        input_json: payload,
      });

      const token = createRes.data.report_token;
      if (!token) throw new Error("Brak tokena raportu");

      setLoadingStep("Pobieranie PDF...");

      // ─────────────────────────────────────────────────────────────
      // 5) Pobieramy PDF
      // ─────────────────────────────────────────────────────────────
      const pdfRes = await axios.get(`${API_URL}/reports/download/${token}`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([pdfRes.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "raport_fotowoltaiczny.pdf");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error("Błąd pobierania PDF:", err);
      setError("Nie udało się wygenerować raportu PDF.");
    } finally {
      setLoading(false);
      setLoadingStep("");
    }
  };

  const isDisabled = loading || (!formData.bill && !formData.estimatedConsumptionMode);

  return (
    <div
      className="mt-6 p-6 rounded-2xl border-2 shadow-sm"
      style={{ borderColor: '#D6EAF8', backgroundColor: '#EBF5FB' }}
    >
      <div className="flex items-start gap-3 mb-4">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
          style={{ backgroundColor: '#1B4F72' }}
        >
          <FileText className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-base font-black text-gray-800">Pobierz pełny raport PDF</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Szczegółowa analiza wszystkich 3 scenariuszy · 9 sekcji · gotowy do druku
          </p>
        </div>
      </div>

      <button
        onClick={handleDownload}
        disabled={isDisabled}
        className="pv-btn-primary flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>{loadingStep || 'Generuję PDF...'}</span>
          </>
        ) : (
          <>
            <FileText className="h-5 w-5" />
            <span>Pobierz Raport PDF</span>
          </>
        )}
      </button>

      {error && (
        <p className="text-sm text-red-600 mt-3 text-center font-medium">{error}</p>
      )}
    </div>
  );
};

export default ReportButton;