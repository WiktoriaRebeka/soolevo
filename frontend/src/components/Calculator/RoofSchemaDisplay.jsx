// frontend/src/components/RoofSchemaDisplay.jsx
// KROK 2: Poprawka rysunków SVG — geometria, etykiety, legenda, wymiary

import React from 'react';

// ─── PALETA (bez zmian) ────────────────────────────────────────────────────────
const C = {
  bg:     '#F0F7FF',
  s1:     '#C8E6F5',
  s2:     '#A8D4EC',
  s3:     '#B8DCF0',
  stroke: '#2E86C1',
  ridge:  '#1B4F72',
  dim:    '#1B4F72',
  gold:   '#D4AC0D',
  natBg:  '#FEF9E7',
  natStr: '#D4AC0D',
  muted:  '#6b7280',
};

// ─── Strzałka wymiaru ─────────────────────────────────────────────────────────
// WAŻNE: dla pionowych wymiarów po lewej stronie kształtu:
//   - linia idzie z góry w DÓŁ (y1 < y2)
//   - off = +20  →  linia wymiaru 20px NA LEWO od x1  (nx=-1, ax1=x1-20)  ✓
//   - off = -20  →  linia wymiaru 20px NA PRAWO (wewnątrz kształtu)      ✗
// Dla dolnych poziomych wymiarów: off=+20 → linia PONIŻEJ kształtu        ✓
// Dla górnych poziomych wymiarów: off=-18 → linia POWYŻEJ kształtu        ✓
function Dim({ x1, y1, x2, y2, label, off = 16, color = C.dim, fs = 11 }) {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len < 2) return null;
  const nx = -dy / len, ny = dx / len;
  const ax1 = x1 + nx * off, ay1 = y1 + ny * off;
  const ax2 = x2 + nx * off, ay2 = y2 + ny * off;
  const mx = (ax1 + ax2) / 2, my = (ay1 + ay2) / 2;
  const ux = dx / len, uy = dy / len;
  let angle = Math.atan2(dy, dx) * 180 / Math.PI;
  if (angle > 90 || angle < -90) angle += 180;
  const a = 5;
  return (
    <g>
      <line x1={x1} y1={y1} x2={ax1} y2={ay1} stroke={color} strokeWidth="0.7" strokeDasharray="3,2" opacity="0.5"/>
      <line x1={x2} y1={y2} x2={ax2} y2={ay2} stroke={color} strokeWidth="0.7" strokeDasharray="3,2" opacity="0.5"/>
      <line x1={ax1} y1={ay1} x2={ax2} y2={ay2} stroke={color} strokeWidth="1.4"/>
      <path d={`M${ax1},${ay1} l${ux*a+ny*2.5},${uy*a-nx*2.5} M${ax1},${ay1} l${ux*a-ny*2.5},${uy*a+nx*2.5}`}
            stroke={color} strokeWidth="1.3" fill="none" strokeLinecap="round"/>
      <path d={`M${ax2},${ay2} l${-ux*a+ny*2.5},${-uy*a-nx*2.5} M${ax2},${ay2} l${-ux*a-ny*2.5},${-uy*a+nx*2.5}`}
            stroke={color} strokeWidth="1.3" fill="none" strokeLinecap="round"/>
      <text x={mx+nx*11} y={my+ny*11} textAnchor="middle" dominantBaseline="middle"
            fontSize={fs} fontWeight="bold" fill={color}
            transform={`rotate(${angle},${mx+nx*11},${my+ny*11})`}>{label}</text>
    </g>
  );
}

// Podpis pod rysunkiem — viewBox ma zawsze 220px wysokości, Tip na y=214
function Tip({ text }) {
  return (
    <text x="140" y="214" textAnchor="middle" fontSize="9" fill={C.muted}>{text}</text>
  );
}

// Wskaźnik strony świata — stały (bez rotacji), używany w widokach "z natury"
// Statyczny tekst "Południe" — używany w widokach "z natury" (brak rotacji)
function South() {
  return (
    <text x="140" y="18" textAnchor="middle" fontSize="9" fontWeight="bold" fill={C.dim}>
      ↓ Południe
    </text>
  );
}

// ─── RÓŻA WIATRÓW ─────────────────────────────────────────────────────────────
// Umieszczona w prawym górnym rogu SVG (poza rysunkiem dachu).
// Cały element obraca się wokół własnego centrum (cx, cy).
// azimuthDeg=180 → S na dole (bez rotacji)
// azimuthDeg=270 (Zachód) → rotate=-90 → W (lewo) przesuwa się na dół
function CompassRose({ azimuthDeg = 180 }) {
  const cx = 252, cy = 22, r = 15;
  
  // POPRAWKA: Odwrócony kierunek rotacji (180 - azimuth).
  // Dzięki temu przy wyborze Zachodu (270), obrót wynosi -90 (w lewo),
  // co przesuwa literę W (będącą po lewej) na dół (kierunek połaci).
  const rotate = 180 - azimuthDeg;

  // Ramię strzałki: grot (filled) i ogon (outline)
  // Każde ramię = dwie trójkąt-połówki (filled dla kierunku, outline dla przeciwnego)
  const arm = r * 0.78;  // długość ramienia od centrum do grotu
  const hw  = r * 0.22;  // pół-szerokość podstawy trójkąta

  return (
    <g transform={`rotate(${rotate}, ${cx}, ${cy})`}>
      {/* Zewnętrzny krąg */}
      <circle cx={cx} cy={cy} r={r} fill="white" stroke={C.dim} strokeWidth="1.2" opacity="0.92"/>

      {/* ── Ramię S (dół) — wypełnione czerwonym: to jest kierunek POŁACI ── */}
      <polygon
        points={`${cx},${cy+arm} ${cx-hw},${cy+2} ${cx+hw},${cy+2}`}
        fill="#E74C3C" opacity="0.9"
      />
      {/* ── Ramię N (góra) — ciemny kontur ── */}
      <polygon
        points={`${cx},${cy-arm} ${cx-hw},${cy-2} ${cx+hw},${cy-2}`}
        fill={C.dim} opacity="0.75"
      />
      {/* ── Ramię E (prawo) — szary ── */}
      <polygon
        points={`${cx+arm},${cy} ${cx+2},${cy-hw} ${cx+2},${cy+hw}`}
        fill={C.muted} opacity="0.5"
      />
      {/* ── Ramię W (lewo) — szary ── */}
      <polygon
        points={`${cx-arm},${cy} ${cx-2},${cy-hw} ${cx-2},${cy+hw}`}
        fill={C.muted} opacity="0.5"
      />

      {/* Środkowy krążek */}
      <circle cx={cx} cy={cy} r={2.5} fill="white" stroke={C.dim} strokeWidth="1.2"/>

      {/* Opisy kierunków — obracają się RAZEM z różą */}
      <text x={cx}   y={cy - r - 3} textAnchor="middle" fontSize="7.5" fontWeight="900" fill={C.dim}>N</text>
      <text x={cx}   y={cy + r + 9} textAnchor="middle" fontSize="7.5" fontWeight="900" fill="#E74C3C">S</text>
      <text x={cx + r + 4} y={cy + 2.5} textAnchor="start"   fontSize="6.5" fontWeight="700" fill={C.muted}>E</text>
      <text x={cx - r - 4} y={cy + 2.5} textAnchor="end"     fontSize="6.5" fontWeight="700" fill={C.muted}>W</text>
    </g>
  );
}


// ══════════════════════════════════════════════════════════════════════════════
// RZUTY Z GÓRY
// viewBox: 0 0 280 220  (jednolity standard)
// kształt: y od 32, max dół ~150, dim A linia ~170, etykieta ~181, Tip 214
// H po lewej: off=+20 przy linii idącej w DÓŁ → dim linia na x1-20 (poza kształtem)
// ══════════════════════════════════════════════════════════════════════════════

// PROSTOKĄT / GABLE (dwuspadowy)
function GableTop({ azimuthDeg = 180 }) {
  const x = 50, y = 32, w = 180, h = 120, ky = y + h / 2;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      {/* Cały dach — tło */}
      <rect x={x} y={y} width={w} height={h} fill={C.s1} stroke={C.stroke} strokeWidth="2"/>
      {/* ŻÓŁTA POŁAĆ — południowa (dolna), od kalenicy do okapu */}
      <rect x={x} y={ky} width={w} height={h/2} fill={C.natBg} stroke={C.gold} strokeWidth="1.5"/>
      <text x={x+w/2} y={ky+(h/2)/2} textAnchor="middle" dominantBaseline="middle"
            fontSize="9" fontWeight="700" fill="#7d6600">POŁAĆ</text>
      {/* Kalenica pozioma w połowie */}
      <line x1={x} y1={ky} x2={x+w} y2={ky} stroke={C.ridge} strokeWidth="2.5"/>
      <CompassRose azimuthDeg={azimuthDeg}/>
      <Dim x1={x}   y1={y+h} x2={x+w} y2={y+h} label="A" off={20} color={C.gold}/>
      <Dim x1={x}   y1={y}   x2={x}   y2={y+h} label="H" off={20} color={C.dim}/>
      <Tip text="A = szerokość budynku  ·  H = głębokość budynku"/>
    </svg>
  );
}

// TRÓJKĄT namiotowy (czterospadowy, szczyt w punkcie)
function TriangleTop({ azimuthDeg = 180 }) {
  const x = 65, y = 32, w = 150, h = 120;
  const cx = x + w / 2, cy = y + h / 2;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      {/* Cały dach — tło */}
      <rect x={x} y={y} width={w} height={h} fill={C.s1} stroke={C.stroke} strokeWidth="2"/>
      {/* ŻÓŁTA POŁAĆ — południowy trójkąt (dół → szczyt) */}
      <polygon points={`${x},${y+h} ${x+w},${y+h} ${cx},${cy}`}
               fill={C.natBg} stroke={C.gold} strokeWidth="1.5"/>
      <text x={cx} y={cy+(y+h-cy)*0.55} textAnchor="middle" dominantBaseline="middle"
            fontSize="9" fontWeight="700" fill="#7d6600">POŁAĆ</text>
      {/* 4 linie od rogów do centralnego szczytu */}
      <line x1={x}   y1={y}   x2={cx} y2={cy} stroke={C.ridge} strokeWidth="2"/>
      <line x1={x+w} y1={y}   x2={cx} y2={cy} stroke={C.ridge} strokeWidth="2"/>
      <line x1={x}   y1={y+h} x2={cx} y2={cy} stroke={C.ridge} strokeWidth="2"/>
      <line x1={x+w} y1={y+h} x2={cx} y2={cy} stroke={C.ridge} strokeWidth="2"/>
      <CompassRose azimuthDeg={azimuthDeg}/>
      <Dim x1={x}   y1={y+h} x2={x+w} y2={y+h} label="A" off={20} color={C.gold}/>
      <Dim x1={x}   y1={y}   x2={x}   y2={y+h} label="H" off={20} color={C.dim}/>
      <Tip text="A = szerokość budynku  ·  H = głębokość budynku"/>
    </svg>
  );
}

// HIP (czterospadowy z kalenicą)
function HipTop({ azimuthDeg = 180 }) {
  const x = 45, y = 32, w = 190, h = 120, ky = y + h / 2;
  const kOff = 42;
  const k1x = x + kOff, k2x = x + w - kOff;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      {/* Cały dach — tło */}
      <rect x={x} y={y} width={w} height={h} fill={C.s1} stroke={C.stroke} strokeWidth="2"/>
      {/* ŻÓŁTA POŁAĆ — południowy trapez (dół → kalenica) */}
      <polygon points={`${x},${y+h} ${x+w},${y+h} ${k2x},${ky} ${k1x},${ky}`}
               fill={C.natBg} stroke={C.gold} strokeWidth="1.5"/>
      <text x={x+w/2} y={ky+(y+h-ky)*0.55} textAnchor="middle" dominantBaseline="middle"
            fontSize="9" fontWeight="700" fill="#7d6600">POŁAĆ</text>
      {/* Ukośne z 4 rogów do końców kalenicy */}
      <line x1={x}   y1={y}   x2={k1x} y2={ky} stroke={C.ridge} strokeWidth="2"/>
      <line x1={x+w} y1={y}   x2={k2x} y2={ky} stroke={C.ridge} strokeWidth="2"/>
      <line x1={x}   y1={y+h} x2={k1x} y2={ky} stroke={C.ridge} strokeWidth="2"/>
      <line x1={x+w} y1={y+h} x2={k2x} y2={ky} stroke={C.ridge} strokeWidth="2"/>
      {/* Krótsza kalenica pozioma */}
      <line x1={k1x} y1={ky} x2={k2x} y2={ky} stroke={C.ridge} strokeWidth="3" strokeLinecap="round"/>
      <CompassRose azimuthDeg={azimuthDeg}/>
      <Dim x1={x}   y1={y+h} x2={x+w} y2={y+h} label="A" off={20} color={C.gold}/>
      <Dim x1={x}   y1={y}   x2={x}   y2={y+h} label="H" off={20} color={C.dim}/>
      <Tip text="A = szerokość budynku  ·  H = głębokość budynku"/>
    </svg>
  );
}

// TRAPEZ równoramienny — rzut identyczny jak HIP
function TrapTop(props) {
  return <HipTop {...props} />;
}

// TRAPEZ PROSTOKĄTNY — konstrukcja geometryczna wg instrukcji:
//
// Budynek L: a=(fL,bBot), b=(lx,bBot), c=(lx,ty), d=(rx,ty), e=(rx,wBot), f=(fL,wBot)
//
// Krok 1-4:
//   midAB = środek odcinka ab = ((lx+fL)/2, bBot)
//   Pionowa linia z midAB przecina cf w punkcie x
//     → x_px = (lx+fL)/2 = 58,  t = 0.5 wzdłuż cf
//     → x_py = ty + t*(wBot-ty) = 89
//     → x = (58, 89)
//   y = środek de = (rx, (ty+wBot)/2) = (240, 89)
//
// POŁAĆ = polygon x,y,e,f = (58,89), (240,89), (240,136), (88,136)
//   — prawy bok ye pionowy → kąty proste przy y i e
//   B = xf (lewy skośny bok), A = ef (dół poziomy), H = de (pełna prawa krawędź)
function TrapRTop({ azimuthDeg = 180 }) {
  const lx=28, ty=42, colW=60, wingW=152, wingH=94, colH=165;
  const rx   = lx+colW+wingW; // 240
  const fL   = lx+colW;       //  88
  const wBot = ty+wingH;       // 136
  const bBot = ty+colH;        // 207

  // x — pionowa z midAB na linię cf
  const xPx = (lx + fL) / 2;                   // 58
  const t   = (xPx - lx) / (fL - lx);          // 0.5
  const xPy = ty + t * (wBot - ty);             // 89
  // y — środek de
  const yPx = rx;                               // 240
  const yPy = (ty + wBot) / 2;                  // 89

  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>

      {/* Budynek L */}
      <path d={`M${lx},${ty} H${rx} V${wBot} H${fL} V${bBot} H${lx} Z`}
            fill={C.s1} stroke={C.stroke} strokeWidth="2"/>

      {/* ŻÓŁTA POŁAĆ — trapez prostokątny: x y e f */}
      <polygon
        points={`${xPx},${xPy} ${yPx},${yPy} ${rx},${wBot} ${fL},${wBot}`}
        fill={C.natBg} stroke={C.gold} strokeWidth="2.5"
      />
      <text x={(xPx+yPx+rx+fL)/4} y={(xPy+wBot)/2+3}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="10" fontWeight="700" fill="#7d6600">POŁAĆ</text>

      {/* Linia dachu kolumny: c → f (nad żółtą połacią) */}
      <line x1={lx} y1={ty} x2={fL} y2={wBot}
            stroke={C.ridge} strokeWidth="2.2" opacity="0.9"/>
      {/* Linia konstrukcyjna x → y (pokazuje górną granicę połaci) */}
      <line x1={xPx} y1={xPy} x2={yPx} y2={yPy}
            stroke={C.ridge} strokeWidth="1.4" strokeDasharray="5,3" opacity="0.55"/>

      <CompassRose azimuthDeg={azimuthDeg}/>
      {/* B = xf (skośny lewy bok) */}
      <Dim x1={xPx} y1={xPy} x2={fL} y2={wBot}  label="B" off={-16} color={C.dim}/>
      {/* A = ef (poziomy dół) */}
      <Dim x1={fL}  y1={wBot} x2={rx} y2={wBot}  label="A" off={20}  color={C.gold}/>
      {/* H = de (pełna prawa krawędź skrzydła) */}
      <Dim x1={rx}  y1={ty}   x2={rx} y2={wBot}  label="H" off={-22} color={C.dim}/>
      <Tip text="B = linia xf (skośna)  ·  A = linia ef (pozioma)  ·  H = linia de"/>
    </svg>
  );
}


// RÓWNOLEGŁOBOK — konstrukcja geometryczna wg instrukcji:
//
// Kroki 1-4: identyczne jak TrapRTop → x=(58,89)
//
// Krok 5: kopiujemy linię xf i przesuwamy wzdłuż ef aż f dotknie e.
//   Przesunięcie = e - f = (rx-fL, 0) = (152, 0)
//   Nowy x-end = x + przesunięcie = (58+152, 89) = (210, 89) — to jest y
//   → y = (210, 89)
//
// Krok 6: linia x→y (pozioma) i linia y→d
//
// POŁAĆ = polygon x,y,e,f = (58,89), (210,89), (240,136), (88,136)
//   Sprawdzenie równoległoboku:
//     xf: (30,47) i ye: (30,47) ✓ równoległe i równe
//     xy: (152,0) i fe: (152,0) ✓ równoległe i równe
//   B = xf (bok skośny), A = ef (dół poziomy), H = de (prawa krawędź)
function RhombTop({ azimuthDeg = 180 }) {
  const lx=28, ty=42, colW=60, wingW=152, wingH=94, colH=165;
  const rx   = lx+colW+wingW; // 240
  const fL   = lx+colW;       //  88
  const wBot = ty+wingH;       // 136
  const bBot = ty+colH;        // 207

  // x — pionowa z midAB na linię cf
  const xPx = (lx + fL) / 2;                   // 58
  const t   = (xPx - lx) / (fL - lx);          // 0.5
  const xPy = ty + t * (wBot - ty);             // 89

  // y — kopiujemy xf i przesuwamy aż f→e: przesunięcie = (rx-fL, 0)
  const yPx = xPx + (rx - fL);                  // 58+152=210
  const yPy = xPy;                              // 89 (poziomo)

  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>

      {/* Budynek L */}
      <path d={`M${lx},${ty} H${rx} V${wBot} H${fL} V${bBot} H${lx} Z`}
            fill={C.s1} stroke={C.stroke} strokeWidth="2"/>

      {/* ŻÓŁTA POŁAĆ — równoległobok: x y e f */}
      <polygon
        points={`${xPx},${xPy} ${yPx},${yPy} ${rx},${wBot} ${fL},${wBot}`}
        fill={C.natBg} stroke={C.gold} strokeWidth="2.5"
      />
      <text x={(xPx+yPx+rx+fL)/4} y={(xPy+wBot)/2+3}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="10" fontWeight="700" fill="#7d6600">POŁAĆ</text>

      {/* Linia dachu kolumny: c → f */}
      <line x1={lx} y1={ty} x2={fL} y2={wBot}
            stroke={C.ridge} strokeWidth="2.2" opacity="0.9"/>
      {/* Linia y → d (krok 6 z instrukcji) */}
      <line x1={yPx} y1={yPy} x2={rx} y2={ty}
            stroke={C.ridge} strokeWidth="1.8" opacity="0.8"/>
      {/* Linia x → y (krok 6, pozioma) */}
      <line x1={xPx} y1={xPy} x2={yPx} y2={yPy}
            stroke={C.ridge} strokeWidth="1.4" strokeDasharray="5,3" opacity="0.5"/>

      <CompassRose azimuthDeg={azimuthDeg}/>
      {/* B = xf (skośny bok równoległoboku) */}
      <Dim x1={xPx} y1={xPy} x2={fL} y2={wBot}  label="B" off={-16} color={C.dim}/>
      {/* A = ef (poziomy dół) */}
      <Dim x1={fL}  y1={wBot} x2={rx} y2={wBot}  label="A" off={20}  color={C.gold}/>
      {/* H = de (pełna prawa krawędź skrzydła) */}
      <Dim x1={rx}  y1={ty}   x2={rx} y2={wBot}  label="H" off={-22} color={C.dim}/>
      <Tip text="B = linia xf (skośna)  ·  A = linia ef (pozioma)  ·  H = linia de"/>
    </svg>
  );
}

// DACH PŁASKI
function FlatTop({ azimuthDeg = 180 }) {
  const x = 50, y = 32, w = 180, h = 118;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      <rect x={x} y={y} width={w} height={h} fill={C.s1} stroke={C.stroke} strokeWidth="2" rx="2"/>
      <text x="140" y={y+h/2} textAnchor="middle" dominantBaseline="middle"
            fontSize="13" fontWeight="bold" fill={C.stroke} opacity="0.22">PŁASKI</text>
      <CompassRose azimuthDeg={azimuthDeg}/>
      <Dim x1={x}   y1={y+h} x2={x+w} y2={y+h} label="A" off={20} color={C.gold}/>
      <Dim x1={x}   y1={y}   x2={x}   y2={y+h} label="H" off={20} color={C.dim}/>
      <Tip text="A = szerokość budynku  ·  H = głębokość budynku"/>
    </svg>
  );
}

// INSTALACJA NAZIEMNA
function GroundTop({ azimuthDeg = 180 }) {
  const x = 42, y = 34, w = 188, h = 116;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      <rect x={x} y={y} width={w} height={h}
            fill="#EBF5EB" stroke="#5D8A5E" strokeWidth="2" strokeDasharray="8,4" rx="3"/>
      {/* Miniaturki paneli */}
      {[0,1,2].map(row => [0,1,2,3].map(col => (
        <rect key={`${row}-${col}`}
              x={x+14+col*43} y={y+14+row*32} width={34} height={22}
              fill="#2E86C1" opacity="0.55" rx="2" stroke="#1B4F72" strokeWidth="0.8"/>
      )))}
      <Dim x1={x}   y1={y+h} x2={x+w} y2={y+h} label="A" off={20} color={C.gold}/>
      <Dim x1={x}   y1={y}   x2={x}   y2={y+h} label="H" off={20} color={C.dim}/>
      <Tip text="A = szerokość terenu  ·  H = długość terenu"/>
    </svg>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// WYMIARY Z NATURY
// Żółty prostokąt/wielokąt = mierzona połać
// Widok od strony: połać POŁUDNIOWA zawsze dolna/frontowa
// ══════════════════════════════════════════════════════════════════════════════

// GABLE NAT — POPRAWIONY
// Mierzona połać: DOLNA połowa = południowa (bliżej obserwatora)
// A = szerokość okapu (szerokość budynku — pozioma)
// h = DŁUGOŚĆ POŁACI DACHOWEJ (od rynny do kalenicy wzdłuż dachu)
function GableNat() {
  const x = 50, y = 35, w = 180, h = 122, ky = y + h / 2; // ky = poziom kalenicy
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      {/* Cały zarys dachu (przerywany) — kontekst */}
      <rect x={x} y={y} width={w} height={h}
            fill={C.s1} stroke={C.stroke} strokeWidth="1.5" strokeDasharray="5,3" opacity="0.5"/>
      {/* Kalenica */}
      <line x1={x} y1={ky} x2={x+w} y2={ky} stroke={C.ridge} strokeWidth="2.5"/>
      <text x={x+w/2} y={ky-8} textAnchor="middle" fontSize="8" fill={C.ridge} fontWeight="bold">
        kalenica
      </text>
      {/* MIERZONA POŁAĆ — DOLNA (południowa) — wyróżniona kolorem */}
      <rect x={x} y={ky} width={w} height={h/2}
            fill={C.natBg} stroke={C.natStr} strokeWidth="2.5"/>
      {/* Opis okapu przy dolnej krawędzi */}
      <text x={x+w/2} y={y+h+10} textAnchor="middle" fontSize="8" fill={C.muted}>
        rynna / okap
      </text>
      {/* A = szerokość okapu (górna krawędź = kalenica, dolna = okap — tutaj mierzymy poziom) */}
      {/* Faktycznie A to szerokość budynku, mierzymy górną krawędź (okap) */}
      <Dim x1={x}     y1={y}     x2={x+w}    y2={y}     label="A" off={-18} color={C.dim}/>
      {/* h = długość połaci dachowej od rynny do kalenicy */}
      {/* Dim idzie od dołu (rynna y+h) W GÓRĘ do kalenicy (ky): dy<0 → nx=+1 */}
      {/* off=-22 przy nx=+1: ax = x1+(-22) = w prawo → prawa strona ✓ */}
      <Dim x1={x+w/2} y1={y+h}   x2={x+w/2}  y2={ky}   label="h" off={-22} color={C.natStr}/>
      <Tip text="A = szerokość budynku (mierz wzdłuż rynny)  ·  h = długość połaci dachowej"/>
    </svg>
  );
}

// TRÓJKĄT NAT
function TriangleNat() {
  const cx = 140, bY = 158, bW = 180, tY = 50;
  const x1 = cx - bW/2, x2 = cx + bW/2;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      <polygon points={`${cx},${tY} ${x1},${bY} ${x2},${bY}`}
               fill={C.natBg} stroke={C.natStr} strokeWidth="2.5"/>
      {/* Linia wysokości prostopadłej */}
      <line x1={cx} y1={tY} x2={cx} y2={bY}
            stroke={C.dim} strokeWidth="1.5" strokeDasharray="5,3"/>
      <rect x={cx} y={bY-11} width={11} height={11} fill="none" stroke={C.dim} strokeWidth="1.3"/>
      <Dim x1={x1} y1={bY} x2={x2}  y2={bY} label="b" off={20} color={C.natStr}/>
      <Dim x1={cx} y1={tY} x2={cx}  y2={bY} label="H" off={-22} color={C.dim}/>
      <Tip text="b = podstawa połaci dachowej  ·  H = wysokość prostopadle do podstawy"/>
    </svg>
  );
}

// HIP NAT — POPRAWIONY
// h = DŁUGOŚĆ POŁACI DACHOWEJ (nie "skos połaci") — od rynny do kalenicy
function HipNat() {
  const cx = 140, oY = 152, oW = 188, kY = 65, kW = 105;
  const pts = `${cx-oW/2},${oY} ${cx+oW/2},${oY} ${cx+kW/2},${kY} ${cx-kW/2},${kY}`;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      <polygon points={pts} fill={C.natBg} stroke={C.natStr} strokeWidth="2.5"/>
      <line x1={cx-kW/2} y1={kY} x2={cx+kW/2} y2={kY}
            stroke={C.ridge} strokeWidth="3" strokeLinecap="round"/>
      <text x={cx} y={kY-9}  textAnchor="middle" fontSize="9" fill={C.ridge} fontWeight="bold">kalenica</text>
      <text x={cx} y={oY+12} textAnchor="middle" fontSize="9" fill={C.muted}>okap / rynna</text>
      {/* A = szerokość okapu (dolna krawędź) */}
      <Dim x1={cx-oW/2} y1={oY} x2={cx+oW/2} y2={oY} label="A" off={20} color={C.natStr}/>
      {/* b = długość kalenicy (górna krawędź) */}
      <Dim x1={cx-kW/2} y1={kY} x2={cx+kW/2} y2={kY} label="b" off={-18} color={C.dim}/>
      {/* h = długość połaci dachowej (od rynny do kalenicy) — lewa krawędź pionowa */}
      <Dim x1={cx-oW/2} y1={oY} x2={cx-kW/2} y2={kY} label="h" off={-22} color={C.dim}/>
      <Tip text="A = szerokość rynny  ·  b = długość kalenicy  ·  h = długość połaci dachowej"/>
    </svg>
  );
}

// TRAPEZ NAT (równoramienny)
function TrapNat() {
  const cx = 140, y1 = 45, h = 118, aB = 175, aT = 105;
  const pts = `${cx-aT/2},${y1} ${cx+aT/2},${y1} ${cx+aB/2},${y1+h} ${cx-aB/2},${y1+h}`;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      <polygon points={pts} fill={C.natBg} stroke={C.natStr} strokeWidth="2.5"/>
      <Dim x1={cx-aT/2} y1={y1}   x2={cx+aT/2} y2={y1}   label="B" off={-18} color={C.dim}/>
      <Dim x1={cx-aB/2} y1={y1+h} x2={cx+aB/2} y2={y1+h} label="A" off={20}  color={C.natStr}/>
      <Dim x1={cx-aB/2} y1={y1}   x2={cx-aB/2} y2={y1+h} label="H" off={20}  color={C.dim}/>
      <Tip text="A = podstawa dłuższa  ·  B = podstawa krótsza  ·  H = wysokość prostopadle"/>
    </svg>
  );
}

// TRAPEZ PROSTOKĄTNY NAT — B (górna krawędź) dłuższa niż A (dolna), spójne z TrapRTop
function TrapRNat() {
  const lx = 45, y1 = 35, h = 120;
  const B = 180; // dłuższa — góra
  const A = 112; // krótsza — dół
  const sq = 10;
  // Lewa krawędź pionowa (kąt prosty lewy), prawa krawędź skośna
  const pts = `${lx},${y1} ${lx+B},${y1} ${lx+A},${y1+h} ${lx},${y1+h}`;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      <polygon points={pts} fill={C.natBg} stroke={C.natStr} strokeWidth="2.5"/>
      {/* Kąt prosty lewy-dół */}
      <polyline
        points={`${lx+sq},${y1+h} ${lx+sq},${y1+h-sq} ${lx},${y1+h-sq}`}
        fill="none" stroke={C.natStr} strokeWidth="1.4" opacity="0.7"
      />
      {/* B = dłuższa podstawa (góra) */}
      <Dim x1={lx}    y1={y1}   x2={lx+B} y2={y1}   label="B" off={-18} color={C.dim}/>
      {/* A = krótsza podstawa (dół) */}
      <Dim x1={lx}    y1={y1+h} x2={lx+A} y2={y1+h} label="A" off={20}  color={C.natStr}/>
      {/* H = lewa krawędź pionowa */}
      <Dim x1={lx}    y1={y1}   x2={lx}   y2={y1+h} label="H" off={20}  color={C.dim}/>
      <Tip text="B = podstawa dłuższa (góra)  ·  A = podstawa krótsza (dół)  ·  H = lewa krawędź pionowa"/>
    </svg>
  );
}

// RÓWNOLEGŁOBOK NAT — POPRAWIONY (dodane oznaczenie B = bok skośny)
function RhombNat() {
  const lx = 42, y1 = 42, w = 155, h = 108, off = 32;
  // punkty: góra-lewy, góra-prawy, dół-prawy, dół-lewy
  const pts = `${lx+off},${y1} ${lx+off+w},${y1} ${lx+w},${y1+h} ${lx},${y1+h}`;
  return (
    <svg viewBox="0 0 280 220" width="100%" style={{ height: 'auto' }}>
      <rect width="280" height="220" fill={C.bg} rx="8"/>
      <polygon points={pts} fill={C.natBg} stroke={C.natStr} strokeWidth="2.5"/>
      {/* A = górna podstawa (i dolna = równa) */}
      <Dim x1={lx+off} y1={y1}   x2={lx+off+w} y2={y1}   label="A" off={-18} color={C.natStr}/>
      {/* B = lewy bok skośny — od dół-lewy do góra-lewy */}
      <Dim x1={lx}     y1={y1+h} x2={lx+off}   y2={y1}   label="B" off={-16} color={C.dim} fs={10}/>
      {/* H = wysokość prostopadła (pomocnicza przerywana) */}
      <line x1={lx+off} y1={y1} x2={lx+off} y2={y1+h}
            stroke={C.dim} strokeWidth="1.1" strokeDasharray="4,3" opacity="0.5"/>
      <Dim x1={lx+off} y1={y1}   x2={lx+off}   y2={y1+h} label="H" off={-18} color={C.dim}/>
      <Tip text="A = podstawa  ·  B = bok skośny  ·  H = wysokość prostopadła"/>
    </svg>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// KONFIGURACJA — poprawiona terminologia (bez "skos")
// ══════════════════════════════════════════════════════════════════════════════
const CONFIG = {
  rectangular: {
    label: 'Dach dwuspadowy',
    top:    { Svg: GableTop,  dims: { A: 'szerokość budynku na rzucie', H: 'głębokość budynku na rzucie' } },
    nature: { Svg: GableNat,  dims: { A: 'szerokość budynku (wzdłuż rynny/okapu)', H: 'długość połaci dachowej (od rynny do kalenicy, mierz wzdłuż powierzchni dachu)' } },
  },
  gable: {
    label: 'Dach dwuspadowy',
    top:    { Svg: GableTop,  dims: { A: 'szerokość budynku na rzucie', H: 'głębokość budynku na rzucie' } },
    nature: { Svg: GableNat,  dims: { A: 'szerokość budynku (wzdłuż rynny/okapu)', H: 'długość połaci dachowej (od rynny do kalenicy, mierz wzdłuż powierzchni dachu)' } },
  },
  triangle: {
    label: 'Dach czterospadowy namiotowy',
    top:    { Svg: TriangleTop, dims: { A: 'szerokość budynku na rzucie', H: 'głębokość budynku na rzucie' } },
    nature: { Svg: TriangleNat, dims: { A: 'szerokość budynku (wzdłuż rynny/okapu)', H: 'długość połaci dachowej (od rynny do kalenicy, mierz wzdłuż powierzchni dachu)' } },
  },
  hip: {
    label: 'Dach czterospadowy (z kalenicą)',
    top:    { Svg: HipTop,  dims: { A: 'szerokość budynku na rzucie', H: 'głębokość budynku na rzucie' } },
    nature: { Svg: HipNat,  dims: { A: 'szerokość budynku (wzdłuż rynny/okapu)', B: 'długość kalenicy', h: 'długość połaci dachowej (od rynny do kalenicy, mierz wzdłuż powierzchni dachu)' } },
  },
  flat: {
    label: 'Dach płaski',
    top:    { Svg: FlatTop, dims: { A: 'szerokość budynku na rzucie', H: 'długość dachu' } },
    nature: { Svg: FlatTop, dims: { A: 'szerokość budynku (wzdłuż rynny/okapu)', H: 'długość dachu' } },
  },
  trapezoid: {
    label: 'Dach na rzucie trapezu',
    top:    { Svg: TrapTop,  dims: { A: 'szerokość budynku na rzucie', H: 'głębokość budynku' } },
    nature: { Svg: TrapNat,  dims: { A: 'podstawa dłuższa', B: 'podstawa krótsza', H: 'wysokość prostopadle między podstawami' } },
  },
  trapezoid_right: {
    label: 'Dach na rzucie trapezu prostokątnego',
    top:    { Svg: TrapRTop, dims: {
      B: 'długość kalenicy',
      A: 'krótsza krawędź dolna — A jest krótsze niż B',
      H: 'wysokość — prawa pionowa krawędź skrzydła',
    }},
    nature: { Svg: TrapRNat, dims: {
      B: 'dłuższa podstawa trapeza (mierz po kalenicy/górze)',
      A: 'krótsza podstawa trapeza (mierz po rynnie/dole) — A < B',
      H: 'długość połaci dachowej (od rynny do kalenicy, mierz wzdłuż dachu)',
    }},
  },
  rhombus: {
    label: 'Dach na rzucie równoległoboku',
    top:    { Svg: RhombTop, dims: {
      A: 'długość dolnej podstawy budynku',
      B: 'przesunięcie poziome między górą a dołem (offset)',
      H: 'wysokość prostopadła między podstawami',
    }},
    nature: { Svg: RhombNat, dims: {
      A: 'długość podstawy połaci dachowej',
      B: 'długość boku skośnego połaci',
      H: 'wysokość prostopadła do podstawy',
    }},
  },
  ground: {
    label: 'Instalacja naziemna',
    top:    { Svg: GroundTop, dims: { A: 'szerokość dostępnego terenu', H: 'długość dostępnego terenu' } },
    nature: { Svg: GroundTop, dims: { A: 'szerokość dostępnego terenu', H: 'długość dostępnego terenu' } },
  },
};

// ══════════════════════════════════════════════════════════════════════════════
// GŁÓWNY KOMPONENT — bez zmian w logice, poprawiona treść podpowiedzi
// ══════════════════════════════════════════════════════════════════════════════
const RoofSchemaDisplay = ({ roofType, roofMode = 'building_length', azimuthDeg = 180 }) => {
  const config = CONFIG[roofType];
  if (!config) {
    return (
      <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600">
        Nieznany typ dachu: <strong>{roofType}</strong>
      </div>
    );
  }

  const isNature = roofMode === 'real_roof_length';
  const { Svg, dims } = isNature ? config.nature : config.top;
  const modeLabel = isNature ? 'Wymiary z natury' : 'Rzut z góry';

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
      {/* Nagłówek */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100"
           style={{ backgroundColor: '#EBF5FB' }}>
        <span className="text-xs font-bold" style={{ color: '#1B4F72' }}>📐 {config.label}</span>
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ backgroundColor: isNature ? '#FEF3C7' : '#D6EAF8',
                       color: isNature ? '#92400E' : '#1B4F72' }}>
          {modeLabel}
        </span>
      </div>

      {/* Schemat SVG */}
      <div className="p-1.5 bg-gray-50"><Svg azimuthDeg={isNature ? 180 : azimuthDeg} /></div>

      {/* Legenda wymiarów */}
      <div className="px-3 py-2 border-t border-gray-100 bg-white space-y-1.5">
        <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Co mierzyć:</p>
        {Object.entries(dims).map(([sym, desc], i) => (
          <div key={sym} className="flex items-start gap-2">
            <span
              className="shrink-0 w-5 h-5 rounded flex items-center justify-center text-[10px] font-black leading-none"
              style={{
                backgroundColor: i === 0 ? '#FEF3C7' : '#EBF5FB',
                color: i === 0 ? '#D4AC0D' : '#1B4F72',
              }}
            >
              {sym}
            </span>
            <span className="text-[11px] text-gray-500 leading-4">{desc}</span>
          </div>
        ))}

        {/* Podpowiedź dla trybu "z natury" */}
        {isNature && (
          <div className="mt-1 flex gap-1.5 p-2 rounded-lg bg-yellow-50 border border-yellow-100">
            <span className="text-[10px] shrink-0">💡</span>
            <p className="text-[10px] text-yellow-800 leading-4">
              Mierz <strong>rzeczywistą długość połaci dachowej</strong>: przyłóż taśmę mierniczą
              od rynny (okapu) do kalenicy, wzdłuż powierzchni dachu —
              nie w pionie ani po ziemi.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default RoofSchemaDisplay;
