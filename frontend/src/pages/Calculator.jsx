// frontend/src/pages/Calculator.jsx
// ─────────────────────────────────────────────────────────────
//  ŹRÓDŁO: calculator_pv/frontend/src/App.jsx
//
//  Zmiany względem oryginału (tylko te 11 linii):
//  1.  import './App.css'                            ← usunięty
//  2.  import ScenariosComparison from './components/ScenariosComparison'
//      → '../components/Calculator/ScenariosComparison'
//  3.  import ReportButton from './components/ReportButton'
//      → '../components/Calculator/ReportButton'
//  4.  import RoofSchemaDisplay from './components/RoofSchemaDisplay'
//      → '../components/Calculator/RoofSchemaDisplay'
//  5.  NOWY import: ReportPaywall from '../components/ReportPaywall'
//  6.  API_URL = "/api"  →  ""  (pusty — Vite proxy lub VITE_API_URL)
//  7.  axios.post endpoint: /calculate/scenarios  →  /calculator/calculate/scenarios
//  8.  NOWY state: lastPayload  +  setLastPayload(payload) po sukcesie
//  9.  export default App  →  export default Calculator
//  10. W sekcji wyników: ReportPaywall dodany obok ReportButton
//
//  Cała logika formularza, walidacja, budowanie faceta — BEZ ZMIAN.
// ─────────────────────────────────────────────────────────────

import { useState } from 'react';
import axios from 'axios';
// ZMIANA 2-4: ścieżki importów komponentów
import ScenariosComparison from '../components/Calculator/ScenariosComparison';
import ReportButton from '../components/Calculator/ReportButton';
import RoofSchemaDisplay from '../components/Calculator/RoofSchemaDisplay';
// ZMIANA 5: nowy import — paywall do płatnego PDF
import ReportPaywall from '../components/ReportPaywall';
// ZMIANA 1: usunięto import './App.css' — style z Soolevo index.css

// ZMIANA 6: pusty string → Vite proxy przekierowuje /calculator/* do localhost:8000
//           w produkcji VITE_API_URL=https://api.soolevo.com (z .env.production)
const API_URL = import.meta.env.VITE_API_URL || "";

const DIRECTION_TO_AZIMUTH = {
  'south':       180,
  'south_east':  135,
  'south_west':  225,
  'east':        90,
  'west':        270,
};


// ─── TOOLTIP (UJEDNOLICONY + FIX CAPS LOCK) ──────────────────────────────────
function Tooltip({ text }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative inline-block ml-2 align-middle">
      <button
        type="button"
        onClick={(e) => { e.preventDefault(); setOpen(!open); }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="flex items-center justify-center w-5 h-5 text-[10px] font-bold 
                   text-sky-700 bg-sky-100 rounded-full 
                   hover:bg-sky-200 hover:text-sky-900 transition-colors cursor-help"
        aria-label="Informacja"
      >
        ?
      </button>

      {open && (
        <div className="absolute bottom-full left-1/2 z-50 mb-2.5 -translate-x-1/2 w-64">
          {/* DODANO: normal-case (wymusza normalne litery) i tracking-normal (normalne odstępy) */}
          <div className="relative px-3 py-2.5 text-xs font-normal text-left text-white 
                          bg-slate-800 rounded-xl shadow-xl leading-relaxed 
                          normal-case tracking-normal">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 
                            border-4 border-transparent border-t-slate-800"></div>
          </div>
        </div>
      )}
    </div>
  );
}
// ──────────────────────────────────────────────────────────────────────────────

// ZMIANA 9: function App → export default function Calculator
export default function Calculator() {
  const [formData, setFormData] = useState({
    estimatedConsumptionMode: false,
    area_m2: '',
    building_standard: 'WT2021',
    uses_induction: false,
    bill: '',
    isAnnualBill: false,
    operator: 'pge',
    tariff: 'g11',
    roofType: 'rectangular',
    roofMode: 'building_length',
    roofWidth: '',
    buildingLength: '',
    real_roof_length: '',
    angle: '30',
    ridgeHeight: '',
    triangleBase: '',
    triangleHeight: '',
    trapezoidBaseA: '',
    trapezoidBaseB: '',
    trapezoidHeight: '',
    rhombusDiagonal1: '',
    rhombusDiagonal2: '',
    rhombusSideB: '',
    obstaclesCount: '0',
    direction: 'south',
    hasShading: false,
    shadingDirection: '',
    province: 'mazowieckie',
    householdSize: '4',
    peopleHomeWeekday: '1',
    has_heat_pump: false,
    has_ac: false,
    has_ev: false,
    planned_heat_pump: false,
    planned_ac: false,
    planned_ev: false,
    netBillingFactor: '0.30',
    inflationRate: '0.04'
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [lastFacet, setLastFacet] = useState(null);
  // ZMIANA 8a: nowy state — payload przekazywany do ReportPaywall
  const [lastPayload, setLastPayload] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      if (!formData.estimatedConsumptionMode && !formData.bill) {
        throw new Error('Podaj kwotę rachunku!');
      }

      if (formData.estimatedConsumptionMode && !formData.area_m2) {
        throw new Error('Podaj powierzchnię domu!');
      }

      const roofType = formData.roofType;

      if (['rectangular', 'flat', 'gable', 'hip', 'ground'].includes(roofType)) {
        if (!formData.roofWidth) throw new Error('Podaj szerokość dachu!');

        const lengthValue = ['flat', 'ground'].includes(roofType) || formData.roofMode === 'real_roof_length'
          ? formData.real_roof_length
          : formData.buildingLength;

        if (!lengthValue) {
          throw new Error(['flat', 'ground'].includes(roofType) ? 'Podaj długość dachu!' : 'Podaj długość budynku!');
        }
      }

      if (['gable', 'hip'].includes(roofType)) {
        if (!formData.ridgeHeight) {
          throw new Error('Podaj wysokość kalenicy!');
        }
      }

      if (roofType === 'triangle') {
        if (!formData.triangleBase) throw new Error('Podaj podstawę trójkąta!');
        if (formData.roofMode === 'building_length' && !formData.triangleHeight) throw new Error('Podaj wysokość rzutu trójkąta!');
        if (formData.roofMode === 'real_roof_length' && !formData.real_roof_length) throw new Error('Podaj długość połaci dachowej trójkąta!');
      }

      if (['trapezoid', 'trapezoid_right'].includes(roofType)) {
        if (!formData.trapezoidBaseA || !formData.trapezoidBaseB) throw new Error('Podaj obie podstawy trapezu!');
        const hField = formData.roofMode === 'real_roof_length' ? formData.real_roof_length : formData.trapezoidHeight;
        if (!hField) throw new Error('Podaj wysokość trapezu!');
      }

      if (roofType === 'rhombus') {
        if (!formData.rhombusDiagonal1 || !formData.rhombusSideB) {
          throw new Error('Podaj podstawę (a) i bok skośny (b) równoległoboku!');
        }

        const h_val_raw = formData.roofMode === 'real_roof_length' ? formData.real_roof_length : formData.rhombusDiagonal2;

        if (!h_val_raw) {
          throw new Error(formData.roofMode === 'real_roof_length' ? 'Podaj długość połaci dachowej (h)!' : 'Podaj wysokość rzutu (h)!');
        }

        const h_val = parseFloat(h_val_raw);
        const b_val = parseFloat(formData.rhombusSideB);
        const h_to_compare = formData.roofMode === 'building_length' ? h_val / 2 : h_val;

        if (b_val < h_to_compare) {
          throw new Error(`Błąd geometrii: Bok skośny b (${b_val}m) nie może być krótszy niż rzut wysokości h (${h_to_compare.toFixed(2)}m)!`);
        }
      }

      if (formData.hasShading && !formData.shadingDirection) {
        throw new Error('Podaj kierunek zacienienia!');
      }

      let real_length = undefined;
      if (formData.roofMode === "real_roof_length") {
        real_length = parseFloat(formData.real_roof_length);
      }

      const effectiveLength = (['flat', 'ground'].includes(roofType) || formData.roofMode === 'real_roof_length')
        ? parseFloat(formData.real_roof_length)
        : parseFloat(formData.buildingLength);

      const effectiveAngle = roofType === 'flat' ? 15 : (roofType === 'ground' ? 35 : parseFloat(formData.angle));

      let facet = {
        id: '1',
        roof_type: roofType,
        roof_mode: formData.roofMode,
        azimuth_deg: DIRECTION_TO_AZIMUTH[formData.direction] || 180,
        angle: effectiveAngle,
        width: parseFloat(formData.roofWidth) || 0,
        length: effectiveLength || 0,
        obstacles_count: parseInt(formData.obstaclesCount) || 0,
        has_shading: formData.hasShading || false,
      };

      if (formData.roofMode === 'real_roof_length' || ['flat', 'ground'].includes(roofType)) {
        facet.real_roof_length = parseFloat(formData.real_roof_length);
      }
      if (roofType === 'triangle') {
        facet.triangle_base = parseFloat(formData.triangleBase);
        if (formData.roofMode === 'real_roof_length') {
          facet.real_roof_length = parseFloat(formData.real_roof_length);
        } else {
          facet.triangle_height = parseFloat(formData.triangleHeight);
        }
      }

      if (['trapezoid', 'trapezoid_right'].includes(roofType)) {
        facet.trapezoid_base_a = parseFloat(formData.trapezoidBaseA);
        facet.trapezoid_base_b = parseFloat(formData.trapezoidBaseB);
        if (formData.roofMode === 'real_roof_length') {
          facet.real_roof_length = parseFloat(formData.real_roof_length);
        } else {
          facet.trapezoid_height = parseFloat(formData.trapezoidHeight);
        }
      }

      if (roofType === 'rhombus') {
        facet.rhombus_diagonal_1 = parseFloat(formData.rhombusDiagonal1);
        facet.rhombus_side_b = parseFloat(formData.rhombusSideB);
        if (formData.roofMode === 'real_roof_length') {
          facet.real_roof_length = parseFloat(formData.real_roof_length);
        } else {
          facet.rhombus_diagonal_2 = parseFloat(formData.rhombusDiagonal2);
        }
      }

      if (['gable', 'hip'].includes(roofType)) {
        facet.ridge_height = parseFloat(formData.ridgeHeight);
      }

      if (formData.hasShading && formData.shadingDirection) {
        facet.shading_direction = formData.shadingDirection;
      }

      Object.keys(facet).forEach(key => {
        if (facet[key] === undefined || facet[key] === null || (typeof facet[key] === 'number' && isNaN(facet[key]))) {
          delete facet[key];
        }
      });

      setLastFacet(facet);

      const payload = {
        bill: formData.estimatedConsumptionMode ? 0 : (parseFloat(formData.bill) || 0),
        is_annual_bill: formData.estimatedConsumptionMode ? false : Boolean(formData.isAnnualBill),
        operator: formData.operator,
        tariff: formData.tariff,
        province: formData.province,
        household_size: parseInt(formData.householdSize) || 4,
        people_home_weekday: parseInt(formData.peopleHomeWeekday) || 1,
        facets: [facet],
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
        inflation_rate: parseFloat(formData.inflationRate) || 0.04
      };

      console.log('Wysyłam payload do backendu:', JSON.stringify(payload, null, 2));

      // ZMIANA 7: endpoint /api/calculate/scenarios → /calculator/calculate/scenarios
      const response = await axios.post(`${API_URL}/calculator/calculate/scenarios`, payload);

      console.log('Odpowiedź z backendu:', response.data);

      setResults(response.data);
      // ZMIANA 8b: zapisz payload — potrzebny przez ReportPaywall do zapisu raportu
      setLastPayload(payload);

      setTimeout(() => {
        const resultsSection = document.getElementById('results');
        if (resultsSection) {
          resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);

    } catch (err) {
      console.error('Pełny błąd:', err);
      console.error('Response data:', err.response?.data);

      let errorMessage = 'Wystąpił błąd podczas obliczeń';

      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map(e => {
            if (typeof e === 'string') return e;
            if (e.msg) return `${e.loc?.join('.') || 'Pole'}: ${e.msg}`;
            return JSON.stringify(e);
          }).join('; ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const currentAzimuth = DIRECTION_TO_AZIMUTH[formData.direction] || 180;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50 to-blue-50">
      <div className="max-w-5xl mx-auto p-4 md:p-6">
        <div className="bg-white rounded-2xl shadow-2xl p-6 md:p-8 mb-8">

          {/* ── NAGŁÓWEK ── */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-black mb-3" style={{ color: '#1B4F72' }}>
              Kalkulator Fotowoltaiki
            </h1>
            <p className="text-gray-500 text-base">
              Oblicz opłacalność instalacji PV w 3 wersjach: Premium, Standard, Economy
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">

            {/* ── SEKCJA 1: ZUŻYCIE ENERGII ── */}
            <div className="pv-section-block">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <span className="text-2xl mr-2">💡</span>
                Twoje zużycie energii
              </h3>

              {/* Wybór trybu */}
              <p className="text-xs text-gray-500 mb-3">
                Skąd mamy policzyć ile prądu zużywasz?
                <Tooltip text="Na podstawie rachunków kalkulator dokładnie wylicza Twoje obecne koszty i dopasowuje moc instalacji. Jeśli dopiero budujesz dom lub nie masz rachunków — oszacujemy zużycie z metrażu." />
              </p>
              <div className="flex flex-col sm:flex-row gap-4 mb-6">
                <label className={`flex items-center gap-3 cursor-pointer p-4 border-2 rounded-xl transition-all ${!formData.estimatedConsumptionMode ? 'border-[#1B4F72] bg-white shadow-md' : 'border-gray-200 bg-gray-50 opacity-70'}`}>
                  <input type="radio" name="consumptionMode" checked={!formData.estimatedConsumptionMode}
                    onChange={() => setFormData(prev => ({ ...prev, estimatedConsumptionMode: false }))}
                    className="w-4 h-4 accent-[#1B4F72]" />
                  <div className="flex flex-col">
                    <span className="font-bold text-gray-800 text-sm">Chcę podać rachunki</span>
                    <span className="text-xs text-gray-500">Na podstawie obecnych opłat — najdokładniejsza metoda</span>
                  </div>
                </label>

                <label className={`flex items-center gap-3 cursor-pointer p-4 border-2 rounded-xl transition-all ${formData.estimatedConsumptionMode ? 'border-[#1B4F72] bg-white shadow-md' : 'border-gray-200 bg-gray-50 opacity-70'}`}>
                  <input type="radio" name="consumptionMode" checked={formData.estimatedConsumptionMode}
                    onChange={() => setFormData(prev => ({ ...prev, estimatedConsumptionMode: true }))}
                    className="w-4 h-4 accent-[#1B4F72]" />
                  <div className="flex flex-col">
                    <span className="font-bold text-gray-800 text-sm">Nie znam rachunków / Planuję budowę</span>
                    <span className="text-xs text-gray-500">Szacunek z metrażu — wystarczający do wstępnej analizy</span>
                  </div>
                </label>
              </div>

              {formData.estimatedConsumptionMode ? (
                /* TRYB: ESTYMACJA (METRAŻ) */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Powierzchnia domu (m²) *
                      <Tooltip text="Podaj całkowitą powierzchnię użytkową domu. Na tej podstawie szacujemy roczne zużycie energii elektrycznej — im większy dom, tym więcej prądu potrzeba do oświetlenia, ogrzewania wody i urządzeń." />
                    </label>
                    <input type="number" name="area_m2" value={formData.area_m2} onChange={handleChange}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all"
                      placeholder="np. 120" required />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Standard budynku
                      <Tooltip text="Nowsze domy są lepiej ocieplone i zużywają mniej energii. WT 2021 = dom budowany po 2021 r. (bardzo niskie zużycie). WT 2014 = budowany 2014–2020. Stary dom = starsze budownictwo z ociepleniem." />
                    </label>
                    <select name="building_standard" value={formData.building_standard} onChange={handleChange}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all">
                      <option value="WT2021">WT 2021 (nowy dom)</option>
                      <option value="WT2014">WT 2014 (dom 2014–2020)</option>
                      <option value="old">Stary dom (ocieplony)</option>
                    </select>
                  </div>
                  <div className="col-span-2">
                    <label className="flex items-center space-x-3 cursor-pointer bg-white p-3 rounded-lg border border-gray-200 hover:border-[#2E86C1] transition-colors">
                      <input type="checkbox" name="uses_induction" checked={formData.uses_induction} onChange={handleChange}
                        className="w-5 h-5 rounded accent-[#1B4F72]" />
                      <span className="text-sm font-medium text-gray-700">Używam płyty indukcyjnej (gotowanie na prądzie)</span>
                      <Tooltip text="Zaznacz jeśli gotujesz na prądzie zamiast gazu. Płyta indukcyjna zużywa ok. 500–800 kWh/rok — kalkulator uwzględni to w obliczeniach." />
                    </label>
                  </div>
                </div>
              ) : (
                /* TRYB: RACHUNKI (PLN) */
                <div className="space-y-6">
                  <div className="flex flex-col sm:flex-row gap-3">
                    <label className={`flex-1 flex items-center gap-2 cursor-pointer p-3 border-2 rounded-lg transition-all ${!formData.isAnnualBill ? 'border-[#1B4F72] bg-[#1B4F72]/5' : 'border-gray-200 bg-white opacity-70'}`}>
                      <input type="radio" name="billPeriod" checked={!formData.isAnnualBill}
                        onChange={() => setFormData(prev => ({ ...prev, isAnnualBill: false }))}
                        className="w-4 h-4 accent-[#1B4F72]" />
                      <span className="text-sm font-bold text-gray-700">Rachunek miesięczny</span>
                    </label>
                    <label className={`flex-1 flex items-center gap-2 cursor-pointer p-3 border-2 rounded-lg transition-all ${formData.isAnnualBill ? 'border-[#1B4F72] bg-[#1B4F72]/5' : 'border-gray-200 bg-white opacity-70'}`}>
                      <input type="radio" name="billPeriod" checked={formData.isAnnualBill}
                        onChange={() => setFormData(prev => ({ ...prev, isAnnualBill: true }))}
                        className="w-4 h-4 accent-[#1B4F72]" />
                      <span className="text-sm font-bold text-gray-700">Rachunek roczny</span>
                    </label>
                    <Tooltip text="Jeśli Twój operator wystawia rachunki kwartalnie lub rocznie — podaj roczną sumę. Przy rachunkach miesięcznych podaj typowy miesiąc (najlepiej z ostatnich 3 miesięcy, nie letni)." />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Kwota rachunku ({formData.isAnnualBill ? 'PLN / rok' : 'PLN / miesiąc'}) *
                        <Tooltip text="Wpisz łączną kwotę z rachunku za prąd — razem z opłatami dystrybucyjnymi. Znajdziesz ją w podsumowaniu na rachunku od swojego operatora." />
                      </label>
                      <div className="relative">
                        <input type="number" name="bill" value={formData.bill} onChange={handleChange}
                          className="w-full pl-4 pr-14 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all text-lg font-bold text-gray-800"
                          placeholder={formData.isAnnualBill ? "np. 5000" : "np. 450"} required />
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold text-sm">PLN</span>
                      </div>
                    </div>
                  </div>

                  {/* ── CHECKBOX INDUKCJA — dostępny też w trybie rachunki ── */}
                  <div>
                    <label className="flex items-center gap-3 cursor-pointer bg-white p-3 rounded-lg border border-gray-200 hover:border-[#2E86C1] transition-colors">
                      <input
                        type="checkbox"
                        name="uses_induction"
                        checked={formData.uses_induction}
                        onChange={handleChange}
                        className="w-5 h-5 rounded accent-[#1B4F72]"
                      />
                      <span className="text-sm font-medium text-gray-700">
                        Zamierzam używać płyty indukcyjnej (gotowanie na prądzie)
                      </span>
                      <Tooltip text="Zaznacz jeśli planujesz gotować na prądzie zamiast gazu. Płyta indukcyjna zużywa ok. 500–800 kWh/rok — kalkulator uwzględni to w obliczeniach." />
                    </label>
                  </div>

                </div>
              )}

              {/* Operator i taryfa */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Operator
                    <Tooltip text="Twój dostawca energii elektrycznej. Znajdziesz go w prawym górnym rogu rachunku za prąd (np. PGE, Tauron, Energa, Enea)." />
                  </label>
                  <select name="operator" value={formData.operator} onChange={handleChange}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all">
                    <option value="pge">PGE</option>
                    <option value="tauron">Tauron</option>
                    <option value="energa">Energa</option>
                    <option value="enea">Enea</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Taryfa
                    <Tooltip text="G11 = jedna cena prądu przez całą dobę (najpopularniejsza). G12 = tańszy prąd w nocy i weekendy — jeśli masz licznik dwustrefowy. Sprawdź na rachunku lub w umowie." />
                  </label>
                  <select name="tariff" value={formData.tariff} onChange={handleChange}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all">
                    <option value="g11">G11 (jednostrefowa)</option>
                    <option value="g12">G12 (dwustrefowa)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* ── SEKCJA 2: RODZINA I LOKALIZACJA ── */}
            <div className="bg-gray-50 border-l-4 border-gray-400 rounded-xl p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <span className="text-2xl mr-2">🏠</span>
                Rodzina i lokalizacja
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Województwo
                    <Tooltip text="Nasłonecznienie różni się w zależności od regionu Polski — południe kraju produkuje nieco więcej energii niż północ." />
                  </label>
                  <select name="province" value={formData.province} onChange={handleChange}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all">
                    <option value="mazowieckie">Mazowieckie</option>
                    <option value="pomorskie">Pomorskie</option>
                    <option value="slaskie">Śląskie</option>
                    <option value="dolnoslaskie">Dolnośląskie</option>
                    <option value="wielkopolskie">Wielkopolskie</option>
                    <option value="malopolskie">Małopolskie</option>
                    <option value="lubelskie">Lubelskie</option>
                    <option value="podkarpackie">Podkarpackie</option>
                    <option value="lodzkie">Łódzkie</option>
                    <option value="zachodniopomorskie">Zachodniopomorskie</option>
                    <option value="kujawskopomorskie">Kujawsko-pomorskie</option>
                    <option value="warminsko_mazurskie">Warmińsko-mazurskie</option>
                    <option value="podlaskie">Podlaskie</option>
                    <option value="lubuskie">Lubuskie</option>
                    <option value="swietokrzyskie">Świętokrzyskie</option>
                    <option value="opolskie">Opolskie</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Liczba domowników
                    <Tooltip text="Całkowita liczba osób mieszkających w domu. Wpływa na szacowane roczne zużycie energii elektrycznej." />
                  </label>
                  <input type="number" name="householdSize" value={formData.householdSize} onChange={handleChange}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all"
                    min="1" max="10" />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Ile osób jest w domu w dzień?
                    <Tooltip text="Osoby w domu w ciągu dnia (emeryci, dzieci, praca zdalna) zużywają prąd gdy świeci słońce — co zwiększa opłacalność instalacji, bo mniej energii trafia do sieci." />
                  </label>
                  <input type="number" name="peopleHomeWeekday" value={formData.peopleHomeWeekday} onChange={handleChange}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-[#2E86C1] focus:outline-none transition-all"
                    min="0" max="10" />
                </div>
              </div>

              {/* Urządzenia */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-8 bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <div className="space-y-4">
                  <p className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-1">
                    A. Posiadam (wliczone w rachunek)
                    <Tooltip text="Zaznacz urządzenia które już masz w domu — ich zużycie jest już wliczone w Twój rachunek. Kalkulator uwzględni to przy analizie opłacalności i autokonsumpcji." />
                  </p>
                  <div className="flex flex-col gap-3">
                    <label className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all cursor-pointer ${formData.has_heat_pump ? 'border-orange-500 bg-orange-50' : 'border-gray-100 hover:border-orange-200'}`}>
                      <div>
                        <span className="text-sm font-bold text-gray-700 block">Pompa ciepła</span>
                      </div>
                      <input type="checkbox" name="has_heat_pump" checked={formData.has_heat_pump} onChange={handleChange} className="w-5 h-5 accent-orange-500" />
                    </label>
                    <label className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all cursor-pointer ${formData.has_ac ? 'border-blue-500 bg-blue-50' : 'border-gray-100 hover:border-blue-200'}`}>
                      <div>
                        <span className="text-sm font-bold text-gray-700 block">Klimatyzacja</span>
                      </div>
                      <input type="checkbox" name="has_ac" checked={formData.has_ac} onChange={handleChange} className="w-5 h-5 accent-blue-500" />
                    </label>
                    <label className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all cursor-pointer ${formData.has_ev ? 'border-green-500 bg-green-50' : 'border-gray-100 hover:border-green-200'}`}>
                      <div>
                        <span className="text-sm font-bold text-gray-700 block">Samochód elektryczny (EV)</span>
                      </div>
                      <input type="checkbox" name="has_ev" checked={formData.has_ev} onChange={handleChange} className="w-5 h-5 accent-green-500" />
                    </label>
                  </div>
                </div>

                <div className="space-y-4">
                  <p className="text-xs font-black uppercase tracking-widest flex items-center gap-1" style={{ color: '#1B4F72' }}>
                    B. Planuję (dolicz do rachunku)
                    <Tooltip text="Zaznacz urządzenia które planujesz kupić w najbliższym czasie. Kalkulator dobierze większą instalację, która pokryje też ich przyszłe zużycie — żebyś nie musiał dopłacać za prąd po zakupie." />
                  </p>
                  <div className="flex flex-col gap-3">
                    <label className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all cursor-pointer ${formData.planned_heat_pump ? 'border-[#1B4F72] bg-[#1B4F72]/5' : 'border-gray-100 hover:border-[#2E86C1]/50'}`}>
                      <div>
                        <span className="text-sm font-bold text-gray-700 block">Pompa ciepła</span>
                      </div>
                      <input type="checkbox" name="planned_heat_pump" checked={formData.planned_heat_pump} onChange={handleChange} className="w-5 h-5 accent-[#1B4F72]" />
                    </label>
                    <label className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all cursor-pointer ${formData.planned_ac ? 'border-[#1B4F72] bg-[#1B4F72]/5' : 'border-gray-100 hover:border-[#2E86C1]/50'}`}>
                      <div>
                        <span className="text-sm font-bold text-gray-700 block">Klimatyzacja</span>
                      </div>
                      <input type="checkbox" name="planned_ac" checked={formData.planned_ac} onChange={handleChange} className="w-5 h-5 accent-[#1B4F72]" />
                    </label>
                    <label className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all cursor-pointer ${formData.planned_ev ? 'border-[#1B4F72] bg-[#1B4F72]/5' : 'border-gray-100 hover:border-[#2E86C1]/50'}`}>
                      <div>
                        <span className="text-sm font-bold text-gray-700 block">Samochód elektryczny (EV)</span>
                      </div>
                      <input type="checkbox" name="planned_ev" checked={formData.planned_ev} onChange={handleChange} className="w-5 h-5 accent-[#1B4F72]" />
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* ── SEKCJA 3: PARAMETRY DACHU ── */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8 mb-8">
              <h3 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                <span className="bg-orange-500 text-white rounded-full w-8 h-8 flex items-center justify-center mr-3 text-sm">2</span>
                Parametry dachu
              </h3>

              {/* KROK 1: WYBÓR WIZUALNY */}
              <div className="mb-10">
                <p className="text-sm font-semibold text-gray-500 mb-4 uppercase tracking-wider flex items-center gap-1">
                  Krok 1: Wybierz rodzaj swojej połaci
                  <Tooltip text="Połać to jedna płaska część dachu. Jeśli Twój dach ma 2 skosy — wybierz Prostokąt (podasz wymiary jednego skosu, od kalenicy do okapu). Dach czterospadowy = Hip. Nie jesteś pewny? Spójrz na swój dach z zewnątrz lub zapytaj instalatora." />
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
                  {[
                    { id: 'rectangular',    img: '/images/roof01.png', label: 'Prostokąt' },
                    { id: 'triangle',       img: '/images/roof02.png', label: 'Trójkąt' },
                    { id: 'trapezoid',      img: '/images/roof03.png', label: 'Trapez' },
                    { id: 'trapezoid_right',img: '/images/roof04.png', label: 'Trapez pr.' },
                    { id: 'rhombus',        img: '/images/roof05.png', label: 'Równoległobok' },
                    { id: 'flat',           img: '/images/roof06.png', label: 'Dach płaski' },
                    { id: 'ground',         img: '/images/roof07.png', label: 'Grunt' },
                  ].map((roof, index) => (
                    <div key={index}
                      onClick={() => setFormData(prev => ({ ...prev, roofType: roof.id }))}
                      className={`group cursor-pointer p-2 rounded-xl border-2 transition-all ${formData.roofType === roof.id ? 'border-orange-500 bg-orange-50 shadow-md' : 'border-gray-100 hover:border-orange-200 bg-white'}`}>
                      <div className="aspect-square overflow-hidden rounded-lg mb-2">
                        <img src={roof.img} alt={roof.label} className="w-full h-full object-cover group-hover:scale-110 transition-transform" />
                      </div>
                      <p className={`text-[9px] font-black text-center uppercase ${formData.roofType === roof.id ? 'text-orange-600' : 'text-gray-400'}`}>
                        {roof.label}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* KROK 2: WYMIARY TECHNICZNE */}
              {formData.roofType && (
                <div className="animate-fadeIn">
                  <p className="text-sm font-semibold text-gray-500 mb-4 uppercase tracking-wider">Krok 2: Podaj wymiary</p>
                  <div className="bg-gray-50 rounded-2xl p-6 border-2 border-gray-100 flex flex-col lg:flex-row gap-8 items-center">

                    {/* Schemat SVG */}
                    <div className="w-full lg:w-1/3 flex flex-col items-center">
                      <RoofSchemaDisplay
                        roofType={formData.roofType}
                        roofMode={formData.roofMode}
                        azimuthDeg={currentAzimuth}
                      />
                    </div>

                    {/* POLA INPUTÓW */}
                    <div className="flex-1 w-full grid grid-cols-1 sm:grid-cols-2 gap-6">

                      {/* Wybór trybu pomiaru */}
                      {!['flat', 'ground'].includes(formData.roofType) && (
                        <div className="col-span-2 mb-2">
                          <label className="text-[10px] font-black text-gray-400 uppercase mb-2 flex items-center gap-1 tracking-widest">
                            Metoda pomiaru wysokości / długości
                            <Tooltip text="Rzut z góry = podajesz głębokość budynku na mapie (np. z Google Maps lub projektu). Kalkulator sam przeliczy długość połaci dachowej. Wymiar z natury = podajesz zmierzoną taśmą długość samego dachu — od kalenicy do okapu. Ta metoda jest dokładniejsza jeśli masz możliwość pomiaru." />
                          </label>
                          <div className="flex gap-4">
                            <label className={`flex-1 p-3 border-2 rounded-xl cursor-pointer transition-all ${formData.roofMode === 'building_length' ? 'border-[#1B4F72] bg-[#1B4F72]/5 shadow-sm' : 'border-gray-100 bg-white hover:border-[#2E86C1]/50'}`}>
                              <input type="radio" name="roofMode" value="building_length" checked={formData.roofMode === 'building_length'} onChange={handleChange} className="hidden" />
                              <span className="block text-sm font-bold text-center">Rzut z góry</span>
                              <span className="block text-[9px] text-center text-gray-500 uppercase">System przeliczy długość połaci</span>
                            </label>
                            <label className={`flex-1 p-3 border-2 rounded-xl cursor-pointer transition-all ${formData.roofMode === 'real_roof_length' ? 'border-orange-500 bg-orange-50 shadow-sm' : 'border-gray-100 bg-white hover:border-orange-200'}`}>
                              <input type="radio" name="roofMode" value="real_roof_length" checked={formData.roofMode === 'real_roof_length'} onChange={handleChange} className="hidden" />
                              <span className="block text-sm font-bold text-center">Wymiar z natury</span>
                              <span className="block text-[9px] text-center text-gray-500 uppercase">Podajesz długość połaci dachowej</span>
                            </label>
                          </div>
                        </div>
                      )}

                      {/* Pola dla prostokąta / flat / gable / hip / ground */}
                      {['rectangular', 'flat', 'gable', 'hip', 'ground'].includes(formData.roofType) && (
                        <>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              {formData.roofType === 'ground' ? 'Szerokość terenu (m)' : 'Szerokość dachu — A (m)'}
                              <Tooltip text={formData.roofType === 'ground'
                                ? "Szerokość działki lub obszaru przeznaczonego pod instalację naziemną. Mierz prostopadle do kierunku południa."
                                : "Szerokość połaci mierzona wzdłuż okapu — od lewej do prawej krawędzi dachu. Jeśli połać jest szersza niż głęboka, to właśnie ta miara."} />
                            </label>
                            <input type="number" name="roofWidth" value={formData.roofWidth} onChange={handleChange}
                              className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 10" />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              {formData.roofType === 'ground'  ? 'Długość terenu (m)' :
                               formData.roofType === 'flat'    ? 'Długość dachu (m)' :
                               formData.roofMode === 'real_roof_length' ? 'Długość połaci dachowej — h (m)' : 'Głębokość budynku — H (m)'}
                              <Tooltip text={formData.roofType === 'ground'
                                ? "Długość terenu w kierunku północ–południe (głębokość działki)."
                                : formData.roofType === 'flat'
                                  ? "Długość dachu płaskiego od frontu do tyłu budynku."
                                  : formData.roofMode === 'real_roof_length'
                                    ? "Długość połaci zmierzona taśmą — od kalenicy (szczytu) do okapu (dolnej krawędzi dachu)."
                                    : "Głębokość budynku — wymiar od frontu do tyłu budynku widoczny na rzucie z góry (np. z projektu lub Google Maps)."} />
                            </label>
                            {formData.roofMode === 'real_roof_length' || ['flat', 'ground'].includes(formData.roofType) ? (
                              <input type="number" name="real_roof_length" value={formData.real_roof_length} onChange={handleChange}
                                className="w-full p-3 border-2 border-orange-300 bg-orange-50 rounded-xl focus:border-orange-500 outline-none font-bold text-orange-900" placeholder="np. 6.5" />
                            ) : (
                              <input type="number" name="buildingLength" value={formData.buildingLength} onChange={handleChange}
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 8" />
                            )}
                          </div>

                          {/* Kalenica dla gable/hip */}
                          {['gable', 'hip'].includes(formData.roofType) && (
                            <div className="space-y-2">
                              <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                                Wysokość kalenicy (m)
                                <Tooltip text="Pionowa odległość od podłogi strychu (lub sufitu najwyższego piętra) do najwyższego punktu kalenicy. Potrzebna do obliczenia kąta nachylenia połaci. Możesz zapytać kierownika budowy lub odczytać z projektu." />
                              </label>
                              <input type="number" name="ridgeHeight" value={formData.ridgeHeight} onChange={handleChange}
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 3.5" />
                            </div>
                          )}
                        </>
                      )}

                      {/* Pola dla trójkąta */}
                      {formData.roofType === 'triangle' && (
                        <>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              Podstawa — b (m)
                              <Tooltip text="Długość dolnej krawędzi trójkątnej połaci — mierzona wzdłuż okapu. To szerokość dachu w najniższym punkcie." />
                            </label>
                            <input type="number" name="triangleBase" value={formData.triangleBase} onChange={handleChange}
                              className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 12" />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              {formData.roofMode === 'real_roof_length' ? 'Długość połaci dachowej — H (m)' : 'Wysokość rzutu — H (m)'}
                              <Tooltip text={formData.roofMode === 'real_roof_length'
                                ? "Długość zmierzona taśmą wzdłuż powierzchni dachu — od okapu do szczytu (wierzchołka trójkąta)."
                                : "Pionowa wysokość trójkąta na rzucie z góry — od podstawy do wierzchołka. Możesz odczytać z projektu budowlanego lub Google Maps."} />
                            </label>
                            {formData.roofMode === 'real_roof_length' ? (
                              <input type="number" name="real_roof_length" value={formData.real_roof_length} onChange={handleChange}
                                className="w-full p-3 border-2 border-orange-300 bg-orange-50 rounded-xl focus:border-orange-500 outline-none font-bold text-orange-900" placeholder="np. 8.5" />
                            ) : (
                              <input type="number" name="triangleHeight" value={formData.triangleHeight} onChange={handleChange}
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 7" />
                            )}
                          </div>
                        </>
                      )}

                      {/* Pola dla trapezu */}
                      {['trapezoid', 'trapezoid_right'].includes(formData.roofType) && (
                        <>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              Krawędź dłuższa — A (m)
                              <Tooltip text="Długość dłuższej krawędzi równoległobocznej połaci — zazwyczaj dolna krawędź (okap). Mierz wzdłuż najdłuższego boku trapezu." />
                            </label>
                            <input type="number" name="trapezoidBaseA" value={formData.trapezoidBaseA} onChange={handleChange}
                              className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 12" />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              Krawędź krótsza — B (m)
                              <Tooltip text="Długość krótszej krawędzi trapezu — zazwyczaj górna (przy kalenicy). Jeśli trapez jest symetryczny, oba boki równoległe są do siebie." />
                            </label>
                            <input type="number" name="trapezoidBaseB" value={formData.trapezoidBaseB} onChange={handleChange}
                              className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 6" />
                          </div>
                          <div className="col-span-2 space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              {formData.roofMode === 'real_roof_length' ? 'Długość połaci dachowej — h (m)' : 'Wysokość rzutu — h (m)'}
                              <Tooltip text={formData.roofMode === 'real_roof_length'
                                ? "Długość zmierzona taśmą prostopadle do krawędzi — od dolnego okapu do górnej krawędzi trapezu."
                                : "Głębokość trapezu na rzucie z góry — pionowa odległość między dwiema równoległymi krawędziami."} />
                            </label>
                            {formData.roofMode === 'real_roof_length' ? (
                              <input type="number" name="real_roof_length" value={formData.real_roof_length} onChange={handleChange}
                                className="w-full p-3 border-2 border-orange-300 bg-orange-50 rounded-xl focus:border-orange-500 outline-none font-bold text-orange-900" placeholder="np. 6.5" />
                            ) : (
                              <input type="number" name="trapezoidHeight" value={formData.trapezoidHeight} onChange={handleChange}
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 6" />
                            )}
                          </div>
                        </>
                      )}

                      {/* Pola dla równoległoboku */}
                      {formData.roofType === 'rhombus' && (
                        <>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              Podstawa — A (m)
                              <Tooltip text="Długość poziomej podstawy równoległoboku — dolna krawędź połaci mierzona wzdłuż okapu." />
                            </label>
                            <input type="number" name="rhombusDiagonal1" value={formData.rhombusDiagonal1} onChange={handleChange}
                              className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 10" />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              {formData.roofMode === 'real_roof_length' ? 'Długość połaci dachowej — h (m)' : 'Wysokość rzutu — H (m)'}
                              <Tooltip text={formData.roofMode === 'real_roof_length'
                                ? "Długość połaci zmierzona taśmą prostopadle do dolnej krawędzi — od okapu do górnej krawędzi."
                                : "Pionowa wysokość równoległoboku na rzucie z góry — odległość między dolną a górną krawędzią."} />
                            </label>
                            {formData.roofMode === 'real_roof_length' ? (
                              <input type="number" name="real_roof_length" value={formData.real_roof_length} onChange={handleChange}
                                className="w-full p-3 border-2 border-orange-300 bg-orange-50 rounded-xl focus:border-orange-500 outline-none font-bold text-orange-900" placeholder="np. 6.5" />
                            ) : (
                              <input type="number" name="rhombusDiagonal2" value={formData.rhombusDiagonal2} onChange={handleChange}
                                className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 6" />
                            )}
                          </div>
                          <div className="col-span-2 space-y-2">
                            <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                              Bok skośny — b (m)
                              <Tooltip text="Długość skośnej krawędzi równoległoboku — bok który nie jest poziomy. Mierz wzdłuż nachylonej krawędzi połaci. Musi być dłuższy niż połowa wysokości rzutu." />
                            </label>
                            <input type="number" name="rhombusSideB" value={formData.rhombusSideB} onChange={handleChange}
                              className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none font-bold" placeholder="np. 7" />
                          </div>
                        </>
                      )}

                      {/* Wspólne: kąt, kierunek */}
                      <div className="col-span-2 grid grid-cols-2 gap-4 border-t pt-4 mt-2">
                        <div className="space-y-2">
                          <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                            Kąt nachylenia (°)
                            <Tooltip text="Kąt między połacią a poziomem. Typowe dachy: 30–45°. Możesz zapytać wykonawcę lub zmierzyć kątomierzem. Optymalny dla Polski to ok. 35°." />
                          </label>
                          <input type="number" name="angle"
                            value={formData.roofType === 'flat' ? 15 : (formData.roofType === 'ground' ? 35 : formData.angle)}
                            onChange={handleChange}
                            disabled={['flat', 'ground'].includes(formData.roofType)}
                            className={`w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none ${['flat', 'ground'].includes(formData.roofType) ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`}
                          />
                          {['flat', 'ground'].includes(formData.roofType) && (
                            <p className="text-[9px] font-bold uppercase mt-1" style={{ color: '#1B4F72' }}>Kąt stały dla stelaży</p>
                          )}
                        </div>
                        <div className="space-y-2">
                          <label className="text-xs font-bold text-gray-600 uppercase flex items-center gap-1">
                            Orientacja połaci
                            <Tooltip text="Kierunek na który &quot;patrzy&quot; połać dachowa. Południe = maksimum energii. Odchylenie o 45° (Płd-Wschód/Płd-Zachód) zmniejsza produkcję o ok. 5–10%." />
                          </label>
                          <select name="direction" value={formData.direction} onChange={handleChange}
                            className="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 outline-none bg-white">
                            <option value="south">Południe</option>
                            <option value="south_east">Płd-Wschód</option>
                            <option value="south_west">Płd-Zachód</option>
                            <option value="east">Wschód</option>
                            <option value="west">Zachód</option>
                          </select>
                        </div>
                      </div>

                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* ── SEKCJA 4: NASŁONECZNIENIE ── */}
            <div className="mb-6 bg-yellow-50 border-l-4 border-yellow-400 p-6 rounded-xl">
              <h4 className="text-lg font-bold text-gray-800 mb-3">
                Warunki nasłonecznienia
              </h4>
              <div className="mb-4">
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input type="checkbox" name="hasShading" checked={formData.hasShading} onChange={handleChange}
                    className="w-5 h-5 accent-yellow-500 rounded" />
                  <span className="text-gray-700 font-semibold">
                    Dach jest zacieniony przez drzewo lub budynek
                  </span>
                  <Tooltip text="Zacienienie nawet przez kilka godzin dziennie może obniżyć produkcję energii o 10–30%. Przy silnym zacienieniu kalkulator uwzględni to w obliczeniach i może zalecić mikroinwertery zamiast centralnego falownika." />
                </label>
              </div>
              {formData.hasShading && (
                <div className="mt-4 ml-8">
                  <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                    Z której strony pada cień?
                    <Tooltip text="Cień od południa jest najgroźniejszy — słońce jest najwyżej właśnie od południa, więc blokuje najwięcej produkcji. Cień od północy prawie nie wpływa na instalację (słońce nigdy nie świeci od północy)." />
                  </label>
                  <select name="shadingDirection" value={formData.shadingDirection} onChange={handleChange}
                    className="w-full md:w-1/2 px-4 py-3 border border-yellow-300 rounded-xl focus:ring-2 focus:ring-yellow-400 focus:outline-none bg-white">
                    <option value="">Wybierz...</option>
                    <option value="south">Od południa (największy wpływ)</option>
                    <option value="east">Od wschodu</option>
                    <option value="west">Od zachodu</option>
                    <option value="north">Od północy (najmniejszy wpływ)</option>
                  </select>
                  <p className="text-xs text-gray-600 mt-2">
                    Przy silnym zacienieniu możemy rekomendować mikroinwertery
                  </p>
                </div>
              )}
            </div>

            {/* ── PRZYCISK SUBMIT ── */}
            <button type="submit" disabled={loading} className="pv-btn-primary">
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                  Obliczam...
                </span>
              ) : (
                'Oblicz scenariusze'
              )}
            </button>

          </form>

          {/* ── BŁĄD ── */}
          {error && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 mt-6 mb-4 rounded-xl">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* ── WYNIKI ── */}
          {results && (
            <div id="results" className="mt-8">
              <ScenariosComparison data={results} inputFacet={lastFacet} />

              {/* ZMIANA 10: ReportButton (darmowy PDF) + ReportPaywall (płatny) obok siebie */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                {/* Darmowy PDF — stary ReportButton bez zmian */}
                <ReportButton formData={formData} results={results} inputFacet={lastFacet} />

                {/* Płatny PDF — nowy paywall Soolevo */}
                <div className="p-6 rounded-2xl border-2 shadow-sm" style={{ borderColor: '#D5EEF8', backgroundColor: '#EAF4FB' }}>
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center shrink-0">
                      <span className="text-white text-lg">🔒</span>
                    </div>
                    <div>
                      <h3 className="text-base font-black text-gray-800">Raport Premium — 49 zł</h3>
                      <p className="text-sm text-gray-500 mt-0.5">
                        Zapisany na koncie · Możliwość ponownego pobrania
                      </p>
                    </div>
                  </div>
                  <ReportPaywall calculatorData={lastPayload} />
                </div>

              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
