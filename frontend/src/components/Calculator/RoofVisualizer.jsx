// frontend/src/components/Calculator/RoofVisualizer.jsx
// Zmiany wizualne v5.1:
//   - Panele PV: ciemny gradient (#0A0F14 → #1A1F24) + siatka ogniw + cień
//   - Dach: pattern dachówki + cień drop-shadow + linia kalenicy (rectangular/flat)
//   - CompassRose: ujednolicona z RoofSchemaDisplay.jsx (stałe cx/cy → dynamiczne x,y,r)
//
// ZASADY — nie naruszamy:
// - Pozycje paneli (x, y, width, height) pobierane WYŁĄCZNIE z backendu
// - panel.width / panel.height (nie panelWidth/panelHeight)
// - Pozycje w metrach × scale → px
// - Backend: y=0 jest w LEWYM GÓRNYM rogu (zgodnie z PanelPosition)
// - panelSvgX, panelSvgY, scale — bez zmian

import React from "react";

// ─── KOLORY WSPÓLNE (zsynchronizowane z RoofSchemaDisplay.jsx) ──────────────
const C = { dim: "#1B4F72", muted: "#6b7280" };

// ══════════════════════════════════════════════════════════════════════════════
// KOMPONENT RÓŻY WIATRÓW
// ─────────────────────────────────────────────────────────────────────────────
// Struktura IDENTYCZNA z RoofSchemaDisplay.jsx:
//   • Wewnętrzny viewBox: "0 0 70 70"  (centrum = 35,35  r=15 jak w SchemaDisplay)
//   • preserveAspectRatio="xMidYMid meet" — skaluje się proporcjonalnie
//   • Pozycjonowanie: zagnieżdżony <svg x= y= width= height=> w głównym SVG
//     (nested SVG — standard W3C, działa we wszystkich przeglądarkach)
//   • Rotacja: identyczna logika rotate = 180 - azimuthDeg
//
// API bez zmian: <CompassRose x={cx} y={cy} r={cr} azimuthDeg={azimuthDeg} />
//   x, y  → lewy górny róg zagnieżdżonego SVG (środek róży = x+r*extraFactor)
//   r     → rozmiar wynikowy w pikselach głównego SVG (width = height = r * 4.67)
// ══════════════════════════════════════════════════════════════════════════════
function CompassRose({ x, y, r = 22, azimuthDeg = 180 }) {
  // ── Wewnętrzny viewBox — identyczny z RoofSchemaDisplay ──────────────────
  // W SchemaDisplay: cx=252, cy=22, r=15, etykiety do cy+r+9=46 → viewport ~70h
  // Centrum w viewBox = (35, 35), r_vb = 15 → proporcje 1:1 z oryginałem
  const VB_SIZE = 70;   // viewBox "0 0 70 70"
  const VB_CX   = 35;   // centrum X w viewBox
  const VB_CY   = 35;   // centrum Y w viewBox
  const VB_R    = 15;   // promień w viewBox (jak w RoofSchemaDisplay)

  // Rozmiar zagnieżdżonego SVG w px głównego SVG
  // r=22 → svgSize ≈ 68px (zachowuje proporcje VB_SIZE/VB_R = 70/15 ≈ 4.67)
  const svgSize = r * (VB_SIZE / VB_R);

  // Pozycja: x,y to środek róży w głównym SVG → przesuwamy o pół svgSize
  const svgX = x - svgSize / 2;
  const svgY = y - svgSize / 2;

  // ── Logika rotacji — IDENTYCZNA z RoofSchemaDisplay.jsx ──────────────────
  const rotate = 180 - azimuthDeg;

  // ── Stałe wewnętrzne viewBox (jak w RoofSchemaDisplay) ────────────────────
  const cx  = VB_CX;
  const cy  = VB_CY;
  const rv  = VB_R;
  const arm = rv * 0.78;
  const hw  = rv * 0.22;

  return (
    // Zagnieżdżony SVG — własny viewBox, niezależny od pikselowych wartości głównego
    <svg
      x={svgX}
      y={svgY}
      width={svgSize}
      height={svgSize}
      viewBox={`0 0 ${VB_SIZE} ${VB_SIZE}`}
      preserveAspectRatio="xMidYMid meet"
      overflow="visible"
    >
      {/* Rotacja wokół centrum viewBox — identyczna z RoofSchemaDisplay */}
      <g transform={`rotate(${rotate}, ${cx}, ${cy})`}>
        {/* Zewnętrzny krąg — identyczny z RoofSchemaDisplay */}
        <circle cx={cx} cy={cy} r={rv} fill="white" stroke={C.dim} strokeWidth="1.2" opacity="0.92"/>

        {/* ── Ramię S (dół) — czerwone = kierunek połaci ── */}
        <polygon
          points={`${cx},${cy + arm} ${cx - hw},${cy + 2} ${cx + hw},${cy + 2}`}
          fill="#E74C3C" opacity="0.9"
        />
        {/* ── Ramię N (góra) — ciemny navy ── */}
        <polygon
          points={`${cx},${cy - arm} ${cx - hw},${cy - 2} ${cx + hw},${cy - 2}`}
          fill={C.dim} opacity="0.75"
        />
        {/* ── Ramię E (prawo) — szary ── */}
        <polygon
          points={`${cx + arm},${cy} ${cx + 2},${cy - hw} ${cx + 2},${cy + hw}`}
          fill={C.muted} opacity="0.5"
        />
        {/* ── Ramię W (lewo) — szary ── */}
        <polygon
          points={`${cx - arm},${cy} ${cx - 2},${cy - hw} ${cx - 2},${cy + hw}`}
          fill={C.muted} opacity="0.5"
        />

        {/* Środkowy krążek */}
        <circle cx={cx} cy={cy} r={2.5} fill="white" stroke={C.dim} strokeWidth="1.2"/>

        {/* Opisy kierunków — IDENTYCZNE z RoofSchemaDisplay (stałe fonty 7.5/6.5) */}
        <text x={cx}          y={cy - rv - 3}  textAnchor="middle" fontSize="7.5" fontWeight="900" fill={C.dim}>N</text>
        <text x={cx}          y={cy + rv + 9}  textAnchor="middle" fontSize="7.5" fontWeight="900" fill="#E74C3C">S</text>
        <text x={cx + rv + 4} y={cy + 2.5}     textAnchor="start"  fontSize="6.5" fontWeight="700" fill={C.muted}>E</text>
        <text x={cx - rv - 4} y={cy + 2.5}     textAnchor="end"    fontSize="6.5" fontWeight="700" fill={C.muted}>W</text>
      </g>
    </svg>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// GŁÓWNY KOMPONENT
// ══════════════════════════════════════════════════════════════════════════════
const RoofVisualizer = ({
  width,
  length,
  panels = [],
  roofType,
  triangle_base,
  triangle_height,
  trapezoid_base_a,
  trapezoid_base_b,
  trapezoid_height,
  rhombus_diagonal_1,
  rhombus_diagonal_2,
  rhombus_offset_x,
  azimuthDeg = 180,
}) => {
  // ─── STAŁE OBSZARU ROBOCZEGO — bez zmian ─────────────────────────────────
  const CANVAS  = 550;
  const PADDING = 100;
  const DRAW    = CANVAS - PADDING * 2;

  // ─── KOLORY DACHU — zachowane bez zmian ──────────────────────────────────
  const ROOF_FILL   = "#e8f4f3";
  const ROOF_STROKE = "#569793";
  const DIM_COLOR   = "#569793";
  const LABEL_COLOR = "#2C3E50";

  // ─── SKALOWANIE — bez zmian ───────────────────────────────────────────────
  let maxWidthMeters = width || 1;
  if (["trapezoid", "trapezoid_right"].includes(roofType)) {
    maxWidthMeters = Math.max(trapezoid_base_a || 0, trapezoid_base_b || 0);
  } else if (roofType === "triangle") {
    maxWidthMeters = triangle_base || width || 1;
  } else if (roofType === "rhombus") {
    maxWidthMeters = (width || 1) + Math.abs(rhombus_offset_x || 0);
  }

  const roofL  = length || 1;
  const scale  = DRAW / Math.max(maxWidthMeters, roofL, 1);

  const maxWidthPx = maxWidthMeters * scale;
  const roofWpx    = (width || 1) * scale;
  const roofLpx    = roofL * scale;
  const offsetPx   = (rhombus_offset_x || 0) * scale;

  // ─── WYMIARY SVG ──────────────────────────────────────────────────────────
  const COMPASS_MARGIN = 85;
  const svgW = maxWidthPx + PADDING * 2 + COMPASS_MARGIN;
  const svgH = roofLpx   + PADDING * 2;

  // ─── KSZTAŁTY ─────────────────────────────────────────────────────────────
  const baseApx     = (trapezoid_base_a || 0) * scale;
  const baseBpx     = (trapezoid_base_b || 0) * scale;
  const triBasePx   = (triangle_base || width || 1) * scale;
  const triHeightPx = (triangle_height || roofL) * scale;

  // ─── POZYCJE PANELI — bez zmian ───────────────────────────────────────────
  const panelSvgX = (panel) => {
    const base = PADDING + (offsetPx < 0 ? Math.abs(offsetPx) : 0);
    return base + panel.x * scale;
  };

  const panelSvgY = (panel) => {
    const roofHeightPx  = length * scale;
    const panelHeightPx = panel.height * scale;
    const panelYFromTop = roofHeightPx - panel.y * scale - panelHeightPx;
    return PADDING + panelYFromTop;
  };

  // ─── POZYCJA RÓŻY WIATRÓW — bez zmian ────────────────────────────────────
  const cx = maxWidthPx + PADDING + COMPASS_MARGIN - 10;
  const cy = PADDING + 28;
  const cr = 22;

  // ─── ID GRADIENTU PANELU (unikalny per instancja) ─────────────────────────
  const gradId      = "pvGrad";
  const patternId   = "roofTile";
  const shadowId    = "roofShadow";
  const panelShadId = "panelShad";

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        width="100%"
        style={{ display: "block", maxWidth: svgW, height: "auto" }}
        className="mx-auto"
      >
        {/* ════════════════════════════════════════════════════════════════
            DEFS — gradienty, pattern dachówki, filtry cienia
        ════════════════════════════════════════════════════════════════ */}
        <defs>

          {/* Gradient panelu PV — ciemny realistyczny moduł */}
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stopColor="#0A0F14"/>
            <stop offset="50%"  stopColor="#141920"/>
            <stop offset="100%" stopColor="#1A1F24"/>
          </linearGradient>

          {/* Subtelny pattern dachówki — poziome linie co 8px */}
          <pattern id={patternId} x="0" y="0" width="16" height="8" patternUnits="userSpaceOnUse">
            <rect width="16" height="8" fill={ROOF_FILL}/>
            <line x1="0" y1="8" x2="16" y2="8" stroke={ROOF_STROKE} strokeWidth="0.4" opacity="0.35"/>
            <line x1="0" y1="0" x2="0"  y2="8" stroke={ROOF_STROKE} strokeWidth="0.25" opacity="0.2"/>
          </pattern>

          {/* Cień dachu */}
          <filter id={shadowId} x="-5%" y="-5%" width="115%" height="115%">
            <feDropShadow dx="2" dy="3" stdDeviation="3" floodColor="#1B4F72" floodOpacity="0.18"/>
          </filter>

          {/* Cień panelu */}
          <filter id={panelShadId} x="-8%" y="-8%" width="120%" height="120%">
            <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodColor="#000000" floodOpacity="0.32"/>
          </filter>

          {/* Strzałki wymiarów */}
          <marker id="arrowEnd" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill={DIM_COLOR}/>
          </marker>
          <marker id="arrowStart" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse">
            <path d="M0,0 L0,6 L6,3 z" fill={DIM_COLOR}/>
          </marker>
        </defs>

        {/* ── TŁO OBSZARU ROBOCZEGO ─────────────────────────────────────── */}
        <rect x={0} y={0} width={svgW} height={svgH} fill="white"/>

        {/* ════════════════════════════════════════════════════════════════
            OBRYS DACHU — kształty z patterntem dachówki + cień
            Kolory ROOF_FILL i ROOF_STROKE zachowane bez zmian.
        ════════════════════════════════════════════════════════════════ */}

        {/* PROSTOKĄT (rectangular / flat / ground) */}
        {(roofType === "rectangular" || roofType === "flat" || roofType === "ground" || !roofType) && (
          <g filter={`url(#${shadowId})`}>
            <rect
              x={PADDING} y={PADDING}
              width={roofWpx} height={roofLpx}
              fill={`url(#${patternId})`}
              stroke={ROOF_STROKE}
              strokeWidth="2.5"
              rx="3"
            />
            {/* Linia kalenicy — środek poziomy (dach dwuspadowy) */}
            {roofType === "rectangular" && (
              <line
                x1={PADDING}           y1={PADDING + roofLpx / 2}
                x2={PADDING + roofWpx} y2={PADDING + roofLpx / 2}
                stroke={ROOF_STROKE} strokeWidth="1.8"
                strokeDasharray="6,4" opacity="0.7"
              />
            )}
          </g>
        )}

        {/* TRÓJKĄT */}
        {roofType === "triangle" && (
          <g filter={`url(#${shadowId})`}>
            <polygon
              points={`
                ${PADDING},${PADDING + triHeightPx}
                ${PADDING + triBasePx},${PADDING + triHeightPx}
                ${PADDING + triBasePx / 2},${PADDING}
              `}
              fill={`url(#${patternId})`}
              stroke={ROOF_STROKE}
              strokeWidth="2.5"
            />
          </g>
        )}

        {/* TRAPEZ */}
        {roofType === "trapezoid" && (
          <g filter={`url(#${shadowId})`}>
            <polygon
              points={`
                ${PADDING + (maxWidthPx - baseBpx) / 2},${PADDING}
                ${PADDING + (maxWidthPx + baseBpx) / 2},${PADDING}
                ${PADDING + (maxWidthPx + baseApx) / 2},${PADDING + roofLpx}
                ${PADDING + (maxWidthPx - baseApx) / 2},${PADDING + roofLpx}
              `}
              fill={`url(#${patternId})`}
              stroke={ROOF_STROKE}
              strokeWidth="2.5"
            />
          </g>
        )}

        {/* TRAPEZ PROSTOKĄTNY */}
        {roofType === "trapezoid_right" && (
          <g filter={`url(#${shadowId})`}>
            <polygon
              points={`
                ${PADDING},${PADDING}
                ${PADDING + baseBpx},${PADDING}
                ${PADDING + baseApx},${PADDING + roofLpx}
                ${PADDING},${PADDING + roofLpx}
              `}
              fill={`url(#${patternId})`}
              stroke={ROOF_STROKE}
              strokeWidth="2.5"
            />
          </g>
        )}

        {/* RÓWNOLEGŁOBOK */}
        {roofType === "rhombus" && (
          <g filter={`url(#${shadowId})`}>
            <polygon
              points={`
                ${PADDING + (offsetPx > 0 ? offsetPx : 0)},${PADDING}
                ${PADDING + (offsetPx > 0 ? offsetPx : 0) + roofWpx},${PADDING}
                ${PADDING + (offsetPx < 0 ? Math.abs(offsetPx) : 0) + roofWpx},${PADDING + roofLpx}
                ${PADDING + (offsetPx < 0 ? Math.abs(offsetPx) : 0)},${PADDING + roofLpx}
              `}
              fill={`url(#${patternId})`}
              stroke={ROOF_STROKE}
              strokeWidth="2.5"
            />
          </g>
        )}

        {/* ════════════════════════════════════════════════════════════════
            WYMIARY (bez zmian — logika i pozycja)
        ════════════════════════════════════════════════════════════════ */}

        {/* Wymiar poziomy — górna krawędź */}
        {!["trapezoid", "trapezoid_right", "rhombus"].includes(roofType) && (
          <text x={PADDING + maxWidthPx / 2} y={PADDING - 18}
                textAnchor="middle" fontSize="13" fill={DIM_COLOR} fontWeight="bold">
            {(roofType === "triangle" ? triangle_base : width)?.toFixed(2)}m
          </text>
        )}

        {/* Wymiar pionowy */}
        <text
          x={PADDING - 28} y={PADDING + roofLpx / 2}
          textAnchor="end" fontSize="13" fill={DIM_COLOR}
          fontWeight="bold" dominantBaseline="middle"
        >
          {roofL ? roofL.toFixed(2) : "—"}m
        </text>

        {/* Strzałka wymiaru pionowego */}
        <line
          x1={PADDING - 18} y1={PADDING + 6}
          x2={PADDING - 18} y2={PADDING + roofLpx - 6}
          stroke={DIM_COLOR} strokeWidth="1.5"
          markerStart="url(#arrowStart)"
          markerEnd="url(#arrowEnd)"
        />

        {/* ════════════════════════════════════════════════════════════════
            PANELE PV — realistyczne moduły
            Pozycje px/py/pW/pH z backendu — bez zmian.
            Zmiana wizualna: gradient + siatka ogniw + cień.
        ════════════════════════════════════════════════════════════════ */}
        {panels.map((panel, idx) => {
          const pW = (panel.width  || 0) * scale;
          const pH = (panel.height || 0) * scale;
          const px = panelSvgX(panel);
          const py = panelSvgY(panel);

          // Siatka ogniw: 3 kolumny × 6 wierszy (jak w Python SVG)
          const N_COL = 3;
          const N_ROW = 6;
          const cw = pW / N_COL;
          const ch = pH / N_ROW;

          return (
            <g key={idx} filter={`url(#${panelShadId})`}>
              {/* Tło panelu — ciemny gradient */}
              <rect
                x={px} y={py}
                width={pW} height={pH}
                fill={`url(#${gradId})`}
                stroke="#2A2F33"
                strokeWidth="1.2"
                rx="1"
              />

              {/* Siatka pionowych linii ogniw */}
              {Array.from({ length: N_COL - 1 }).map((_, ci) => (
                <line
                  key={`v${ci}`}
                  x1={px + (ci + 1) * cw} y1={py}
                  x2={px + (ci + 1) * cw} y2={py + pH}
                  stroke="rgba(255,255,255,0.18)" strokeWidth="0.5"
                />
              ))}

              {/* Siatka poziomych linii ogniw */}
              {Array.from({ length: N_ROW - 1 }).map((_, ri) => (
                <line
                  key={`h${ri}`}
                  x1={px}      y1={py + (ri + 1) * ch}
                  x2={px + pW} y2={py + (ri + 1) * ch}
                  stroke="rgba(255,255,255,0.12)" strokeWidth="0.4"
                />
              ))}

              {/* Delikatny highlight w lewym górnym rogu — efekt 3D */}
              <rect
                x={px} y={py}
                width={pW} height={pH * 0.25}
                fill="rgba(255,255,255,0.04)"
                rx="1"
              />

              {/* Numer panelu — max 50, biały tekst na ciemnym tle */}
              {idx < 50 && (
                <text
                  x={px + pW / 2}
                  y={py + pH / 2}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={Math.max(7, Math.min(11, pW * 0.22))}
                  fill="rgba(255,255,255,0.75)"
                  fontWeight="bold"
                >
                  {panel.label}
                </text>
              )}
            </g>
          );
        })}

        {/* ════════════════════════════════════════════════════════════════
            RÓŻA WIATRÓW — identyczna z RoofSchemaDisplay.jsx
        ════════════════════════════════════════════════════════════════ */}
        <CompassRose x={cx} y={cy} r={cr} azimuthDeg={azimuthDeg}/>

        {/* Skala — prawa dolna */}
        <text x={svgW - 8} y={svgH - 8}
              textAnchor="end" fontSize="10" fill="#9ca3af">
          1m = {scale.toFixed(1)}px
        </text>

      </svg>
    </div>
  );
};

export default RoofVisualizer;
