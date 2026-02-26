// frontend/src/components/RoofVisualizer.jsx
// Krok 4: responsywny SVG (viewBox), spójne kolory, róża wiatrów, brak duplikatu legendy
//
// ZASADY — nie naruszamy:
// - Pozycje paneli (x, y, width, height) pobierane WYŁĄCZNIE z backendu
// - panel.width / panel.height (nie panelWidth/panelHeight)
// - Pozycje w metrach × scale → px
// - Backend: y=0 jest w LEWYM GÓRNYM rogu (zgodnie z PanelPosition)

import React from "react";

// ─── KOLORY DLA RÓŻY WIATRÓW (zgodne z RoofSchemaDisplay) ───
const C = { dim: '#1B4F72', muted: '#6b7280' };

// ─── KOMPONENT RÓŻY WIATRÓW (Ten sam co w RoofSchemaDisplay) ───
// Zmiana: przyjmuje x, y, r jako propsy, bo w Visualizerze pozycja jest dynamiczna
function CompassRose({ x, y, r = 22, azimuthDeg = 180 }) {
  const cx = x, cy = y;
  
  // Logika rotacji: 180 - azimuth (dla widoku "nieba")
  const rotate = 180 - azimuthDeg;

  const arm = r * 0.78;
  const hw  = r * 0.22;

  return (
    <g transform={`rotate(${rotate}, ${cx}, ${cy})`}>
      {/* Zewnętrzny krąg */}
      <circle cx={cx} cy={cy} r={r} fill="white" stroke={C.dim} strokeWidth="1.2" opacity="0.92"/>

      {/* ── Ramię S (dół) — wypełnione czerwonym ── */}
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

      {/* Opisy kierunków */}
      <text x={cx}   y={cy - r - 3} textAnchor="middle" fontSize={r*0.5} fontWeight="900" fill={C.dim}>N</text>
      <text x={cx}   y={cy + r + 9} textAnchor="middle" fontSize={r*0.5} fontWeight="900" fill="#E74C3C">S</text>
      <text x={cx + r + 4} y={cy + 2.5} textAnchor="start"   fontSize={r*0.45} fontWeight="700" fill={C.muted}>E</text>
      <text x={cx - r - 4} y={cy + 2.5} textAnchor="end"     fontSize={r*0.45} fontWeight="700" fill={C.muted}>W</text>
    </g>
  );
}

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
  azimuthDeg = 180, // Domyślnie Południe
}) => {
  // ─── STAŁE OBSZARU ROBOCZEGO ───────────────────────────────────────────────
  // Bez zmian — logika skalowania musi być identyczna z poprzednią wersją
  const CANVAS  = 550;
  const PADDING = 100;
  const DRAW    = CANVAS - PADDING * 2;

  // ─── KOLORY — zsynchronizowane z PDF C_PRIMARY / ScenarioCard ─────────────
  const ROOF_FILL   = "#e8f4f3";   // jak poprzednio
  const ROOF_STROKE = "#569793";   // jak poprzednio
  const PANEL_FILL  = "#FFD700";
  const PANEL_STR   = "#B8860B";
  const LABEL_COLOR = "#2C3E50";   // C_DARK_TEXT z index.css
  const DIM_COLOR   = "#569793";   // wymiary w kolorze dachu

  // ─── SKALOWANIE (bez zmian — logika backendu) ─────────────────────────────
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

  // ─── WYMIARY SVG ───────────────────────────────────────────────────────────
  // Dodajemy zapas na różę wiatrów (40px z prawej)
  const COMPASS_MARGIN = 85;
  const svgW = maxWidthPx + PADDING * 2 + COMPASS_MARGIN;
  const svgH = roofLpx   + PADDING * 2;

  // ─── KSZTAŁTY — wymiary w px ───────────────────────────────────────────────
  const baseApx    = (trapezoid_base_a || 0) * scale;
  const baseBpx    = (trapezoid_base_b || 0) * scale;
  const triBasePx  = (triangle_base || width || 1) * scale;
  const triHeightPx = (triangle_height || roofL) * scale;

  // ─── POZYCJE PANELI (bez zmian — dane z backendu) ─────────────────────────
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

  // ─── POZYCJA RÓŻY WIATRÓW ─────────────────────────────────────────────────
  // Prawy górny róg — poza obszarem dachu
  const cx = maxWidthPx + PADDING + COMPASS_MARGIN - 10;
  const cy = PADDING + 28;
  const cr = 22; // promień róży

  return (
    // ── WRAPPER: brak border — ScenarioCard opakowuje własnym boxem ──────────
    <div className="w-full">

      {/* ── SVG: viewBox + width="100%" = responsywność ─────────────────────
          Poprzednie: width={svgW} → overflowowało na mobile
          Teraz: viewBox zachowuje proporcje, width="100%" skaluje do kontenera */}
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        width="100%"
        height="auto"
        style={{ display: "block", maxWidth: svgW }}
        className="mx-auto"
      >
        {/* ── TŁO OBSZARU ROBOCZEGO ─────────────────────────────────────── */}
        <rect
          x={0} y={0}
          width={svgW} height={svgH}
          fill="white"
        />

        {/* ── OBRYS DACHU ───────────────────────────────────────────────── */}

        {roofType === "triangle" && (
          <polygon
            points={`
              ${PADDING},${PADDING + triHeightPx}
              ${PADDING + triBasePx},${PADDING + triHeightPx}
              ${PADDING + triBasePx / 2},${PADDING}
            `}
            fill={ROOF_FILL}
            stroke={ROOF_STROKE}
            strokeWidth="3"
          />
        )}

        {roofType === "trapezoid" && (
          <polygon
            points={`
              ${PADDING + (maxWidthPx - baseBpx) / 2},${PADDING}
              ${PADDING + (maxWidthPx + baseBpx) / 2},${PADDING}
              ${PADDING + (maxWidthPx + baseApx) / 2},${PADDING + roofLpx}
              ${PADDING + (maxWidthPx - baseApx) / 2},${PADDING + roofLpx}
            `}
            fill={ROOF_FILL}
            stroke={ROOF_STROKE}
            strokeWidth="3"
          />
        )}

        {roofType === "trapezoid_right" && (
          <polygon
            points={`
              ${PADDING},${PADDING}
              ${PADDING + baseBpx},${PADDING}
              ${PADDING + baseApx},${PADDING + roofLpx}
              ${PADDING},${PADDING + roofLpx}
            `}
            fill={ROOF_FILL}
            stroke={ROOF_STROKE}
            strokeWidth="3"
          />
        )}

        {roofType === "rhombus" && (
          <polygon
            points={`
              ${PADDING + (offsetPx > 0 ? offsetPx : 0)},${PADDING}
              ${PADDING + (offsetPx > 0 ? offsetPx : 0) + roofWpx},${PADDING}
              ${PADDING + (offsetPx < 0 ? Math.abs(offsetPx) : 0) + roofWpx},${PADDING + roofLpx}
              ${PADDING + (offsetPx < 0 ? Math.abs(offsetPx) : 0)},${PADDING + roofLpx}
            `}
            fill={ROOF_FILL}
            stroke={ROOF_STROKE}
            strokeWidth="2"
          />
        )}

        {(["rectangular", "flat", "gable", "hip", "ground"].includes(roofType) || !roofType) && (
          <rect
            x={PADDING}
            y={PADDING}
            width={roofWpx}
            height={roofLpx}
            fill={ROOF_FILL}
            stroke={ROOF_STROKE}
            strokeWidth="3"
          />
        )}

        {/* ── ETYKIETY WYMIARÓW ─────────────────────────────────────────── */}

        {/* Trapezy — dwie podstawy */}
        {["trapezoid", "trapezoid_right"].includes(roofType) && (
          <>
            <text x={PADDING + maxWidthPx / 2} y={PADDING - 18} textAnchor="middle" fontSize="13" fill={DIM_COLOR} fontWeight="bold">
              {trapezoid_base_b?.toFixed(2)}m (góra b)
            </text>
            <text x={PADDING + maxWidthPx / 2} y={PADDING + roofLpx + 28} textAnchor="middle" fontSize="13" fill={LABEL_COLOR} fontWeight="bold">
              {trapezoid_base_a?.toFixed(2)}m (dół a)
            </text>
          </>
        )}

        {/* Romb */}
        {roofType === "rhombus" && (
          <>
            <text x={PADDING + offsetPx + roofWpx / 2} y={PADDING - 18} textAnchor="middle" fontSize="13" fill={DIM_COLOR} fontWeight="bold">
              {width?.toFixed(2)}m (góra)
            </text>
            <text x={PADDING + roofWpx / 2} y={PADDING + roofLpx + 28} textAnchor="middle" fontSize="13" fill={LABEL_COLOR} fontWeight="bold">
              {width?.toFixed(2)}m (dół)
            </text>
          </>
        )}

        {/* Pozostałe — jedna szerokość */}
        {!["trapezoid", "trapezoid_right", "rhombus"].includes(roofType) && (
          <text x={PADDING + maxWidthPx / 2} y={PADDING - 18} textAnchor="middle" fontSize="13" fill={DIM_COLOR} fontWeight="bold">
            {(roofType === "triangle" ? triangle_base : width)?.toFixed(2)}m
          </text>
        )}

        {/* Wymiar pionowy */}
        <text
          x={PADDING - 28}
          y={PADDING + roofLpx / 2}
          textAnchor="end"
          fontSize="13"
          fill={DIM_COLOR}
          fontWeight="bold"
          dominantBaseline="middle"
        >
          {roofL ? roofL.toFixed(2) : "—"}m
        </text>

        {/* Strzałka przy wymiarze pionowym */}
        <line
          x1={PADDING - 18} y1={PADDING + 6}
          x2={PADDING - 18} y2={PADDING + roofLpx - 6}
          stroke={DIM_COLOR} strokeWidth="1.5"
          markerStart="url(#arrowStart)"
          markerEnd="url(#arrowEnd)"
        />

        {/* Definicja grotów strzałek */}
        <defs>
          <marker id="arrowEnd" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill={DIM_COLOR} />
          </marker>
          <marker id="arrowStart" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse">
            <path d="M0,0 L0,6 L6,3 z" fill={DIM_COLOR} />
          </marker>
        </defs>

        {/* ── PANELE (pozycje z backendu — bez zmian) ──────────────────── */}
        {panels.map((panel, idx) => {
          const pW = (panel.width  || 0) * scale;
          const pH = (panel.height || 0) * scale;
          const px = panelSvgX(panel);
          const py = panelSvgY(panel);

          return (
            <g key={idx}>
              <rect
                x={px} y={py}
                width={pW} height={pH}
                fill={PANEL_FILL}
                stroke={PANEL_STR}
                strokeWidth="1.5"
                opacity="0.9"
              />
              {/* Numery tylko dla max 50 paneli — bez zmian */}
              {idx < 50 && (
                <text
                  x={px + pW / 2}
                  y={py + pH / 2}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="10"
                  fill="#333"
                  fontWeight="bold"
                >
                  {panel.label}
                </text>
              )}
            </g>
          );
        })}

        {/* ── RÓŻA WIATRÓW (DYNAMICZNA) ────────────────────────────────── */}
        <CompassRose x={cx} y={cy} r={cr} azimuthDeg={azimuthDeg} />

        {/* Skala — prawa dolna */}
        <text
          x={svgW - 8}
          y={svgH - 8}
          textAnchor="end"
          fontSize="10"
          fill="#9ca3af"
        >
          1m = {scale.toFixed(1)}px
        </text>

      </svg>
    </div>
  );
};

export default RoofVisualizer;
