// frontend/src/components/Footer.jsx
export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-400 py-10 mt-auto">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between gap-8">
          <div>
            <div className="text-white font-black text-lg mb-2">☀️ Soolevo</div>
            <p className="text-sm max-w-xs">
              Kalkulator fotowoltaiki i porównywarka magazynów energii dla polskiego rynku.
            </p>
          </div>
          <div className="flex gap-12">
            <div>
              <div className="text-white font-semibold mb-3 text-sm">Narzędzia</div>
              <div className="space-y-2 text-sm">
                <a href="/kalkulator" className="block hover:text-teal-400 transition-colors">Kalkulator PV</a>
                <a href="/magazyny" className="block hover:text-teal-400 transition-colors">Magazyny energii</a>
                <a href="/konto" className="block hover:text-teal-400 transition-colors">Moje konto</a>
              </div>
            </div>
            <div>
              <div className="text-white font-semibold mb-3 text-sm">Prawne</div>
              <div className="space-y-2 text-sm">
                <a href="/regulamin" className="block hover:text-teal-400 transition-colors">Regulamin</a>
                <a href="/prywatnosc" className="block hover:text-teal-400 transition-colors">Polityka prywatności</a>
              </div>
            </div>
          </div>
        </div>
        <div className="border-t border-gray-800 mt-8 pt-6 text-xs text-center">
          © {new Date().getFullYear()} Soolevo. Wszelkie prawa zastrzeżone.
        </div>
      </div>
    </footer>
  );
}
