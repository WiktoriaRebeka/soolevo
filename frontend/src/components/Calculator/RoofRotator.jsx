// frontend/src/components/RoofRotator.jsx
import React from 'react';

const RoofRotator = ({ rotation, setRotation }) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 mb-6">
      <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
        <span className="mr-2">🏠</span> Orientacja budynku względem stron świata
      </h3>
      
      <div className="flex flex-col items-center">
        {/* Kompas / Wizualizacja */}
        <div className="relative w-48 h-48 mb-6 transition-transform duration-500" 
             style={{ transform: `rotate(${rotation}deg)` }}>
          {/* Uproszczony kształt domu z góry */}
          <div className="absolute inset-0 border-4 border-teal-600 rounded-lg bg-teal-50 flex items-center justify-center">
            <div className="w-full h-1 bg-teal-600 absolute top-1/2"></div> {/* Kalenica */}
            <span className="text-teal-800 font-bold text-xs uppercase" style={{ transform: `rotate(-${rotation}deg)` }}>
              FRONT
            </span>
          </div>
          {/* Strzałka Północ (zawsze na górze kompasu, więc dom się kręci względem niej) */}
        </div>

        <input 
          type="range" 
          min="0" 
          max="360" 
          value={rotation} 
          onChange={(e) => setRotation(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-teal-600"
        />
        
        <div className="flex justify-between w-full mt-2 text-xs font-bold text-gray-800">
          <span>N (0°)</span>
          <span>E (90°)</span>
          <span>S (180°)</span>
          <span>W (270°)</span>
          <span>N (360°)</span>
        </div>
        
        <p className="mt-4 text-sm text-gray-800">
          Obecny azymut frontu: <span className="font-bold text-teal-600">{rotation}°</span> 
          ({rotation > 135 && rotation < 225 ? 'Południe' : 'Inny kierunek'})
        </p>
      </div>
    </div>
  );
};

export default RoofRotator;