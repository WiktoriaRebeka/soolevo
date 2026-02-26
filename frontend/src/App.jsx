// frontend/src/App.jsx
// ─────────────────────────────────────────────────────────────
//  Główny komponent — routing i layout
//  UWAGA: Zastępuje istniejące App.jsx — zachowaj backup!
// ─────────────────────────────────────────────────────────────

import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Batteries from "./pages/Batteries";
import Account from "./pages/Account";

// Istniejący kalkulator — zawiń w lazy import żeby nie zepsuć
// Zamień "./components/Calculator" na ścieżkę do aktualnego App/głównego komponentu kalkulatora
import { lazy, Suspense } from "react";
const CalculatorApp = lazy(() => import("./CalculatorApp")); // ← wskazuje na stary App.jsx

function Layout({ children }) {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Layout>
          <Routes>
            {/* Strona główna */}
            <Route path="/" element={<Home />} />

            {/* Kalkulator PV — istniejący komponent */}
            <Route
              path="/kalkulator"
              element={
                <Suspense fallback={<div className="p-8 text-center text-gray-400">Ładowanie kalkulatora…</div>}>
                  <CalculatorApp />
                </Suspense>
              }
            />

            {/* Porównywarka magazynów */}
            <Route path="/magazyny" element={<Batteries />} />

            {/* Panel konta */}
            <Route path="/konto" element={<Account />} />
            <Route path="/konto/raporty" element={<Account />} />

            {/* 404 */}
            <Route
              path="*"
              element={
                <div className="flex flex-col items-center justify-center min-h-[50vh] text-gray-400">
                  <div className="text-6xl mb-4">🔍</div>
                  <h2 className="text-xl font-bold mb-2">Strona nie istnieje</h2>
                  <a href="/" className="text-teal-600 hover:underline">Wróć na stronę główną</a>
                </div>
              }
            />
          </Routes>
        </Layout>
      </AuthProvider>
    </BrowserRouter>
  );
}
