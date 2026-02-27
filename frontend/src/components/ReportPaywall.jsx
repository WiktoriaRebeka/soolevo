// frontend/src/components/ReportPaywall.jsx
// ─────────────────────────────────────────────────────────────
//  Paywall raportu PDF — integracja z systemem płatności Soolevo
//  Flow: utwórz raport → utwórz płatność PayNow → webhook → pobierz PDF
//
//  Props:
//    calculatorData  — payload ScenariosRequest (z Calculator.jsx)
// ─────────────────────────────────────────────────────────────

import { useState } from "react";
import { reportsAPI, paymentsAPI } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";

const REPORT_PRICE_PLN = 49;

export default function ReportPaywall({ calculatorData }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleBuy = async () => {
    // Wymagane logowanie
    if (!user) {
      navigate("/konto", { state: { returnTo: "/kalkulator", reason: "paywall" } });
      return;
    }

    setError(null);
    setLoading(true);

    try {
      // 1. Utwórz rekord raportu w bazie
      setStep("Zapisuję raport...");
      const createRes = await reportsAPI.create(calculatorData);
      const reportToken = createRes.data?.report_token;

      if (!reportToken) {
        throw new Error("Nie otrzymano tokenu raportu");
      }

      // 2. Utwórz sesję płatności PayNow
      setStep("Tworzę sesję płatności...");
      const payRes = await paymentsAPI.createPayment(reportToken, user.email);
      const redirectUrl = payRes.data?.redirect_url;

      if (!redirectUrl) {
        throw new Error("Nie otrzymano URL płatności");
      }

      // 3. Przekieruj do PayNow
      setStep("Przekierowuję do płatności...");
      window.location.href = redirectUrl;

    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Błąd systemu płatności";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
      setStep("");
    }
  };

  if (success) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center text-sm">
        <p className="text-green-700 font-bold">✅ Płatność potwierdzona!</p>
        <p className="text-green-600 mt-1">Raport dostępny na koncie.</p>
        <button
          onClick={() => navigate("/konto")}
          className="mt-2 px-4 py-1.5 bg-green-600 text-white rounded-lg text-xs font-bold hover:bg-green-700"
        >
          Przejdź do konta
        </button>
      </div>
    );
  }

  return (
    <div className="mt-3">
      <button
        onClick={handleBuy}
        disabled={loading || !calculatorData}
        className={`w-full flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-bold text-sm transition-all duration-200 ${
          loading || !calculatorData
            ? "bg-gray-100 text-gray-800 cursor-not-allowed"
            : "bg-teal-500 hover:bg-teal-600 text-white shadow hover:shadow-md"
        }`}
      >
        {loading ? (
          <>
            <span className="w-4 h-4 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
            {step || "Ładowanie..."}
          </>
        ) : (
          <>
            🔒 Kup raport premium — {REPORT_PRICE_PLN} zł
          </>
        )}
      </button>

      {!user && !loading && (
        <p className="text-xs text-gray-800 text-center mt-1">
          Wymagane{" "}
          <button
            onClick={() => navigate("/konto")}
            className="text-teal-600 underline"
          >
            zalogowanie
          </button>
        </p>
      )}

      {error && (
        <p className="text-xs text-red-600 mt-2 text-center">{error}</p>
      )}
    </div>
  );
}
