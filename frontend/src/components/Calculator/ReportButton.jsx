// frontend/src/components/ReportButton.jsx
// ─────────────────────────────────────────────────────────────
//  Przycisk pobierania darmowego raportu PDF
//
//  POPRAWKA KRYTYCZNA:
//  Poprzedni kod używał API_URL = "/api" i wywoływał ${API_URL}/report/pdf
//  → to dawało /api/report/pdf — endpoint który NIE ISTNIEJE w soolevo.
//
//  Prawidłowy endpoint w soolevo to /calculator/report/pdf
//  (zdefiniowany w backend/app/routers/calculator.py jako router prefix="/calculator")
//
//  Używamy instancji `api` z client.js zamiast axios bezpośrednio —
//  identycznie jak Calculator/ReportButton.jsx
// ─────────────────────────────────────────────────────────────

import React, { useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { api } from '../../api/client';

const ReportButton = ({ formData, results, inputFacet }) => {
  const [loading, setLoading]         = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError]             = useState(null);

  const handleDownload = async () => {
    setLoading(true);
    setError(null);

    try {
      setLoadingStep('Przygotowuję dane...');

      // ── 1. Pobierz dane scenariusza i wykresów sezonowych ─────────────────
      const scenarios   = results?.scenarios || [];
      const stdScenario = scenarios.find(s => s.scenario_name === 'standard')
                       || scenarios.find(s => s.tier === 'standard')
                       || scenarios[1]
                       || {};

      const hourlyResult       = stdScenario.hourly_result_with_battery
                              || stdScenario.hourly_result_without_battery
                              || {};
      const seasonalChartsData = hourlyResult.seasonal_charts || {};

      setLoadingStep('Generuję raport PDF...');

      // ── 2. Buduj facet (używamy inputFacet z Calculator.jsx) ──────────────
      // inputFacet jest identyczny z tym co wysłano do /calculate/scenarios
      const facet = { ...(inputFacet || {}) };
      if (!facet.id)        facet.id = '1';
      if (!facet.roof_type) facet.roof_type = formData.roofType || 'rectangular';
      if (!facet.roof_mode) facet.roof_mode = formData.roofMode || 'building_length';

      // Usuń undefined/NaN/null
      Object.keys(facet).forEach(k => {
        if (facet[k] === undefined || facet[k] === null ||
            (typeof facet[k] === 'number' && isNaN(facet[k]))) {
          delete facet[k];
        }
      });

      // ── 3. Buduj payload (identyczny z Calculator/ReportButton.jsx) ───────
      const payload = {
        bill:                       formData.estimatedConsumptionMode ? 0 : (parseFloat(formData.bill) || 0),
        is_annual_bill:             formData.estimatedConsumptionMode ? false : Boolean(formData.isAnnualBill),
        operator:                   formData.operator,
        tariff:                     formData.tariff,
        province:                   formData.province,
        household_size:             parseInt(formData.householdSize) || 4,
        people_home_weekday:        parseInt(formData.peopleHomeWeekday) || 1,
        facets:                     [facet],
        include_battery:            true,
        estimated_consumption_mode: Boolean(formData.estimatedConsumptionMode),
        area_m2:                    formData.area_m2 ? parseFloat(formData.area_m2) : null,
        building_standard:          formData.building_standard || 'WT2021',
        uses_induction:             Boolean(formData.uses_induction),
        has_heat_pump:              Boolean(formData.has_heat_pump),
        has_ac:                     Boolean(formData.has_ac),
        has_ev:                     Boolean(formData.has_ev),
        planned_heat_pump:          Boolean(formData.planned_heat_pump),
        planned_ac:                 Boolean(formData.planned_ac),
        planned_ev:                 Boolean(formData.planned_ev),
        planned_other_kwh:          0.0,
        inflation_rate:             parseFloat(formData.inflationRate) || 0.04,
        scenario_to_highlight:      'standard',
        seasonal_charts_data:       seasonalChartsData,
      };

      // Usuń klucze undefined z payloadu
      Object.keys(payload).forEach(k => payload[k] === undefined && delete payload[k]);

      // ── 4. Wywołaj endpoint /calculator/report/pdf ────────────────────────
      // POPRAWKA: było ${API_URL}/report/pdf → /api/report/pdf (nie istnieje)
      // Teraz:    /calculator/report/pdf (router calculator.py, prefix="/calculator")
      const pdfRes = await api.post('/calculator/report/pdf', payload, {
        responseType: 'blob',
      });

      // ── 5. Pobierz plik ───────────────────────────────────────────────────
      const url  = window.URL.createObjectURL(new Blob([pdfRes.data]));
      const link = document.createElement('a');
      link.href  = url;
      link.setAttribute('download', 'raport_fotowoltaiczny.pdf');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error('Błąd pobierania PDF:', err);
      setError('Nie udało się wygenerować raportu PDF. Sprawdź konsolę backendu.');
    } finally {
      setLoading(false);
      setLoadingStep('');
    }
  };

  const isDisabled = loading || (!formData?.bill && !formData?.estimatedConsumptionMode);

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
          <p className="text-sm text-gray-800 mt-0.5">
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
