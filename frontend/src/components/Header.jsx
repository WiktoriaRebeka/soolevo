// frontend/src/components/Header.jsx
// ─────────────────────────────────────────────────────────────
//  Nagłówek — zgodny z projektem graficznym
// ─────────────────────────────────────────────────────────────

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const NAV_LINKS = [
  { to: "/", label: "Strona główna" },
  { to: "/kalkulator", label: "Kalkulator PV" },
  { to: "/magazyny", label: "Magazyny energii" },
  { to: "/konto", label: "Konto" },
];

export default function Header() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-gray-100 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center shadow-md group-hover:scale-105 transition-transform">
            <span className="text-white text-lg">☀️</span>
          </div>
          <div className="leading-tight">
            <div className="font-black text-gray-900 text-sm">Soolevo</div>
            <div className="text-[10px] text-teal-600 font-semibold -mt-0.5">Kalkulator PV</div>
          </div>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ to, label }) => {
            const active = pathname === to || (to !== "/" && pathname.startsWith(to));
            return (
              <Link
                key={to}
                to={to}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-teal-50 text-teal-700 font-semibold"
                    : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                {label}
              </Link>
            );
          })}

          {user ? (
            <div className="flex items-center gap-2 ml-2 pl-2 border-l border-gray-200">
              <span className="text-xs text-gray-500">{user.email}</span>
              <button
                onClick={logout}
                className="px-3 py-1.5 text-xs text-gray-500 hover:text-red-600 transition-colors"
              >
                Wyloguj
              </button>
            </div>
          ) : (
            <Link
              to="/konto"
              className="ml-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              Zaloguj się
            </Link>
          )}
        </nav>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-gray-100"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Menu"
        >
          <div className="space-y-1.5">
            <span className={`block h-0.5 w-5 bg-gray-600 transition-all ${menuOpen ? "rotate-45 translate-y-2" : ""}`} />
            <span className={`block h-0.5 w-5 bg-gray-600 transition-all ${menuOpen ? "opacity-0" : ""}`} />
            <span className={`block h-0.5 w-5 bg-gray-600 transition-all ${menuOpen ? "-rotate-45 -translate-y-2" : ""}`} />
          </div>
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-4 pb-4">
          {NAV_LINKS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="block py-3 text-sm font-medium text-gray-500 border-b border-gray-50 last:border-0"
              onClick={() => setMenuOpen(false)}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
