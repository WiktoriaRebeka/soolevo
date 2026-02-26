// frontend/src/components/ReportPaywall.jsx
// ─────────────────────────────────────────────────────────────
//  Komponent Paywall — zastępuje/rozszerza istniejący ReportButton
//  Integracja z istniejącym kalkulatorem PV:
//
//  1. W miejscu gdzie jest przycisk "Pobierz raport PDF",
//     zamień na <ReportPaywall calculatorData={formData} />
//
//  2. calculatorData to obiekt ScenariosRequest (ten sam co do /calculate/scenarios)
// ─────────────────────────────────────────────────────────────

import { useState } from "react";
import { reportsAPI, paymentsAPI } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

const PRICE = 49;

export default function ReportPaywall({ calculatorData }) {
  const { user } = useAuth();
  const [step, setStep] = useState("idle"); // idle | email | creating | redirecting | error
  const [email, setEmail] = useState(user?.email || "");
  const [error, setError] = useState("");

  const handleBuy = async () => {
    if (!email && !user) {
      setStep("email");
      return;
    }
    await startPayment();
  };

  const startPayment = async (buyerEmail = email) => {
    setStep("creating");
    setError("");
    try {
      // 1. Utwórz rekord raportu w bazie
      const reportRes = await reportsAPI.create(calculatorData);
      const { report_token } = reportRes.data;

      // 2. Utwórz sesję płatności PayNow
      const paymentRes = await paymentsAPI.createPayment(report_token, buyerEmail || user?.email);
      const { redirect_url } = paymentRes.data;

      // 3. Przekieruj na stronę płatności mBank PayNow
      setStep("redirecting");
      window.location.href = redirect_url;

    } catch (err) {
      setStep("error");
      setError(
        err.response?.data?.detail || "Nie udało się uruchomić płatności. Spróbuj ponownie."
      );
    }
  };

  // ── Stany UI ─────────────────────────────────────────────────

  if (step === "redirecting") {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 text-center">
        <div className="text-3xl mb-2">💳</div>
        <p className="font-semibold text-blue-900">Przekierowujemy do płatności mBank…</p>
      </div>
    );
  }

  if (step === "error") {
    return (
      <div className="bg-red-50 border border-red-200 rounded-2xl p-6">
        <p className="text-red-700 mb-3">{error}</p>
        <button
          onClick={() => setStep("idle")}
          className="px-4 py-2 bg-red-600 text-white rounded-xl text-sm font-bold hover:bg-red-700"
        >
          Spróbuj ponownie
        </button>
      </div>
    );
  }

  if (step === "email") {
    return (
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
        <h3 className="font-black text-gray-900 text-lg mb-1">Podaj adres email</h3>
        <p className="text-sm text-gray-500 mb-4">
          Wyślemy na niego link do raportu po opłaceniu.
        </p>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="twoj@email.pl"
          className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-teal-400"
        />
        <button
          onClick={() => startPayment(email)}
          disabled={!email}
          className="w-full py-3 bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-white font-bold rounded-xl transition-colors"
        >
          Przejdź do płatności ({PRICE} zł)
        </button>
        <button
          onClick={() => setStep("idle")}
          className="w-full mt-2 py-2 text-sm text-gray-400 hover:text-gray-600"
        >
          Anuluj
        </button>
      </div>
    );
  }

  // Domyślny stan — przycisk kupna
  return (
    <div className="bg-gradient-to-br from-teal-50 to-teal-100 border border-teal-200 rounded-2xl p-6">
      {/* Co zawiera raport */}
      <h3 className="font-black text-gray-900 text-lg mb-1">📄 Szczegółowy raport PDF</h3>
      <ul className="text-sm text-gray-600 space-y-1 mb-5">
        {[
          "Analiza zwrotu z inwestycji na 25 lat",
          "3 scenariusze: Premium, Standard, Economy",
          "Zestawienie oszczędności vs. ceny instalacji",
          "Rekomendacje i kolejne kroki",
          "Informacje o dofinansowaniach (Mój Prąd i in.)",
        ].map((item) => (
          <li key={item} className="flex items-center gap-2">
            <span className="text-teal-500">✓</span> {item}
          </li>
        ))}
      </ul>

      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-2xl font-black text-gray-900">{PRICE} zł</div>
          <div className="text-xs text-gray-500">jednorazowa płatność, bez subskrypcji</div>
        </div>
        <div className="flex gap-2 text-2xl opacity-60">
          <span title="Karta płatnicza">💳</span>
          <span title="BLIK">📱</span>
          <span title="mBank PayNow">🏦</span>
        </div>
      </div>

      <button
        onClick={handleBuy}
        disabled={step === "creating"}
        className="w-full py-4 bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-white font-black rounded-xl shadow-lg shadow-teal-200 transition-all hover:scale-[1.02] text-lg"
      >
        {step === "creating" ? "Przygotowywanie płatności…" : `Kup raport PDF — ${PRICE} zł`}
      </button>

      <p className="text-[10px] text-gray-400 text-center mt-2">
        Płatność przez mBank PayNow. Bezpieczna transakcja.
      </p>
    </div>
  );
}
