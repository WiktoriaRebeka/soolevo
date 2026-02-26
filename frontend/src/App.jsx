// frontend/src/App.jsx
// ─────────────────────────────────────────────────────────────
//  Soolevo — Główny routing aplikacji
//  Trasy: / | /kalkulator | /magazyny | /konto
// ─────────────────────────────────────────────────────────────

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Calculator from "./pages/Calculator";
import Batteries from "./pages/Batteries";
import Account from "./pages/Account";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="flex flex-col min-h-screen">
          <Header />

          <main className="flex-1">
            <Routes>
              <Route path="/"           element={<Home />} />
              <Route path="/kalkulator" element={<Calculator />} />
              <Route path="/magazyny"   element={<Batteries />} />
              <Route path="/konto"      element={<Account />} />
              {/* Fallback */}
              <Route path="*"           element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          <Footer />
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
