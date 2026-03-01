# backend/app/core/report_generator.py
"""
ReportGenerator v5.1 — Zsynchronizowany z nowym RoofVisualizer.jsx

ARCHITEKTURA:
  • Krok 1 — pełna struktura S0–S9 (base.html pozostaje bez zmian)
  • Krok 2 — stabilny generator: 4 metody wykresów + generate()
  • Krok 3 — wizualne odwzorowanie frontendu 1:1:
      - _chart_monthly_balance  → kolory Tailwind jak w EnergyFlowChart.jsx
      - _chart_cashflow_25      → AreaChart jak CashflowChart25 (React)
      - _chart_daily_flow       → brak legend per-wykres, jedna legenda na dole
      - _chart_roof_panels      → SVG programatyczny (jak RoofVisualizer.jsx v5.1):
                                   panel: gradient #0A1A2F→#15273D→#1F2F45 stroke #2A2F33
                                   dach: fill #d9d9d9 pattern dachówki stroke #7a7a7a
                                   siatka ogniw 3×6, highlight 25%, biały numer panelu
                                   róża wiatrów rotate=180-azimuth (logika frontendu)
  • Krok 4 — polish: DPI 200, tight bbox, spójne marginesy

PALETA (zsynchronizowana z frontendem):
  EnergyFlowChart.jsx COLORS:
    pv              → #D4AC0D   (złoty)
    gridImport      → #E57373   (pastelowy czerwony)
    consumption     → #2E86C1   (niebieski)
    batteryCharge   → #66BB6A   (zielony)
    batteryDischarge→ #A78BFA   (lawendowy fiolet)
    soc             → #1B4F72   (ciemny błękit)

  Miesięczny bilans (spec z promptu — Tailwind):
    autokonsumpcja  → #22c55e   green-500
    nadwyżka        → #facc15   yellow-400
    pobór z sieci   → #ef4444   red-500
    zapotrzebowanie → #3b82f6   blue-500

  CashflowChart25 (EnergyCharts.jsx):
    stroke PV       → #D4AC0D   fill → #FEF9E7
    stroke bat      → #8b5cf6   fill → #f5f3ff
    linia zerowa    → #94a3b8
    zwrot           → #1E8449

  RoofVisualizer.jsx (v5.1 — NOWA PALETA):
    panel gradient  → #0A1A2F → #15273D → #1F2F45 (ciemny granat diagonal)
    panel stroke    → #2A2F33
    dach fill       → #d9d9d9  (szara dachówka, pattern 16×8px)
    dach stroke     → #7a7a7a
    wymiary         → #6b6b6b
"""

import os
import base64
from io import BytesIO
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ── Monkey-patch WeasyPrint/pydyf (kompatybilność wersji) ────────────────────
try:
    import pydyf
    if not hasattr(pydyf.Stream, "transform"):
        def _transform(self, a, b, c, d, e, f):
            fn = getattr(self, "concat", None)
            if callable(fn):
                fn(a, b, c, d, e, f)
        pydyf.Stream.transform = _transform
    if not hasattr(pydyf.Stream, "text_matrix"):
        def _text_matrix(self, *v):
            fn = getattr(self, "set_text_matrix", None)
            if callable(fn):
                fn(*v)
        pydyf.Stream.text_matrix = _text_matrix
except ImportError:
    pass

from weasyprint import HTML
from app.schemas.report import ReportData

# ── matplotlib (graceful fallback) ───────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import matplotlib.patches as mpatches
    import numpy as np
    from matplotlib.lines import Line2D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[ReportGenerator] matplotlib niedostępny — wykresy zastąpione tabelami HTML")

# ── Globalne rcParams — białe tło, siatka jak Recharts ───────────────────────
if MATPLOTLIB_AVAILABLE:
    plt.rcParams.update({
        # Font
        "font.family":        "DejaVu Sans",
        "font.size":          9,
        # Osie
        "axes.titlesize":     11,
        "axes.titleweight":   "bold",
        "axes.titlecolor":    "#1f2937",
        "axes.labelsize":     8.5,
        "axes.labelcolor":    "#6b7280",
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.linewidth":     0.8,
        "axes.edgecolor":     "#e5e7eb",
        # Tło — BIAŁE jak Recharts
        "axes.facecolor":     "white",
        "figure.facecolor":   "white",
        # Siatka — #e5e7eb dasharray 3 3 jak CartesianGrid
        "grid.color":         "#e5e7eb",
        "grid.linewidth":     0.7,
        "grid.linestyle":     (0, (3, 3)),
        "grid.alpha":         1.0,
        # Ticki
        "xtick.color":        "#6b7280",
        "ytick.color":        "#6b7280",
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        # Legenda
        "legend.fontsize":    8.5,
        "legend.framealpha":  0.95,
        "legend.edgecolor":   "#e5e7eb",
        "legend.borderpad":   0.6,
        "legend.handlelength": 1.4,
        "legend.handleheight": 0.9,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# PALETA KOLORÓW — jedyne źródło prawdy
# ═══════════════════════════════════════════════════════════════════════════════

# Wykres dobowy (EnergyFlowChart.jsx)
C_PV          = "#D4AC0D"   # złoty
C_GRID_IMP    = "#E57373"   # pastelowy czerwony
C_CONSUMPTION = "#2E86C1"   # niebieski
C_BAT_CHARGE  = "#66BB6A"   # zielony
C_BAT_DISC    = "#A78BFA"   # lawendowy fiolet
C_SOC         = "#1B4F72"   # ciemny błękit (linia przerywana)

# Miesięczny bilans — kolory IDENTYCZNE z wykresem dobowym (Tailwind)
C_AUTO        = "#22c55e"   # autokonsumpcja = green-500
C_SURPLUS     = "#facc15"   # nadwyżka do sieci = yellow-400
C_GRID_BAL    = "#ef4444"   # pobór z sieci = red-500
C_DEMAND      = "#3b82f6"   # zapotrzebowanie = blue-500

# Cashflow 25 lat (CashflowChart25 w EnergyCharts.jsx)
C_PV_STROKE   = "#D4AC0D"
C_PV_FILL     = "#FEF9E7"
C_BAT_STROKE  = "#8b5cf6"
C_BAT_FILL    = "#f5f3ff"
C_ZERO_LINE   = "#94a3b8"
C_PAYBACK_CLR = "#1E8449"

# Ogólne
C_TEXT        = "#1f2937"
C_GRID_LINE   = "#e5e7eb"
C_TICK        = "#6b7280"


# ═══════════════════════════════════════════════════════════════════════════════
# ReportGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class ReportGenerator:

    def __init__(self):
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        APP_DIR     = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
        BACKEND_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))

        self.base_dir      = BACKEND_DIR
        self.templates_dir = os.path.join(APP_DIR, "templates")
        self.static_dir    = os.path.join(APP_DIR, "static")

        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.env.filters["format_pln"] = self._format_pln
        self.env.filters["format_num"]  = self._format_num

    # ── Formattery ────────────────────────────────────────────────────────────

    @staticmethod
    def _format_pln(value):
        if value is None:
            return "—"
        try:
            return f"{int(value):,} zł".replace(",", "\u00a0")
        except (ValueError, TypeError):
            return "—"

    @staticmethod
    def _format_num(value, decimals=0):
        if value is None:
            return "—"
        try:
            if decimals == 0:
                return f"{int(value):,}".replace(",", "\u00a0")
            return f"{float(value):,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")
        except (ValueError, TypeError):
            return "—"

    # ── Helper: figura → base64 PNG ──────────────────────────────────────────

    @staticmethod
    def _fig_to_b64(fig) -> str:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=200,
                    bbox_inches="tight", pad_inches=0.15,
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    # ── Helper: styl osi — identyczny z Recharts CartesianGrid ───────────────

    @staticmethod
    def _style_ax(ax, title=None, xlabel=None, ylabel=None):
        """
        Białe tło, pozioma siatka #e5e7eb dasharray 3 3,
        brak górnego i prawego spine — identycznie jak Recharts.
        """
        ax.set_facecolor("white")
        ax.yaxis.grid(True, color=C_GRID_LINE, linewidth=0.7,
                      linestyle=(0, (3, 3)), zorder=0)
        ax.xaxis.grid(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(C_GRID_LINE)
        ax.spines["bottom"].set_color(C_GRID_LINE)
        ax.tick_params(axis="both", which="both", length=0)
        if title:
            ax.set_title(title, fontsize=10, fontweight="bold",
                         color=C_TEXT, pad=10)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=8.5, color=C_TICK, labelpad=6)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=8.5, color=C_TICK, labelpad=6)

    # =========================================================================
    # WYKRES 1 — Miesięczny bilans energii
    # Stacked bar (auto + nadwyżka) + bar (pobór sieci) + linia zapotrzebowania
    # Kolory IDENTYCZNE z wykresem dobowym — specyfikacja z promptu
    # =========================================================================

    def _chart_monthly_balance(self, std: dict) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        MONTHS_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                     "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

        # ── 1. Próba: hourly_result_without_battery ────────────────────────────
        hr_no = std.get("hourly_result_without_battery") or {}
        ef    = hr_no.get("energy_flow") or {}
        mp    = ef.get("monthly_production_kwh") or []
        mc    = ef.get("monthly_consumption_kwh") or []
        ma    = ef.get("monthly_autoconsumption_kwh") or []

        # ── 2. Próba: hourly_result_with_battery ──────────────────────────────
        if len(mp) != 12:
            hr_b = std.get("hourly_result_with_battery") or {}
            ef2  = hr_b.get("energy_flow") or {}
            mp   = ef2.get("monthly_production_kwh") or []
            mc   = ef2.get("monthly_consumption_kwh") or []
            ma   = ef2.get("monthly_autoconsumption_kwh") or []

        # ── 3. Uzupełnienie autokonsumpcji z net_billing ──────────────────────
        if len(ma) != 12 and len(mp) == 12:
            nb = (hr_no.get("net_billing") or
                  (std.get("hourly_result_with_battery") or {}).get("net_billing") or {})
            ms = nb.get("monthly_surplus_kwh") or {}
            if ms:
                sl = [float(ms.get(i, 0)) for i in range(1, 13)]
                ma = [max(0.0, p - s) for p, s in zip(mp, sl)]

        # ── 4. Fallback sezonowy (tylko gdy brak danych) ──────────────────────
        ap = std.get("annual_production_kwh") or 0
        ac = std.get("annual_consumption_kwh") or 0

        if len(mp) != 12:
            W = [.04, .05, .08, .10, .12, .13, .13, .12, .09, .07, .04, .03]
            mp = [ap * w for w in W]
        if len(mc) != 12:
            W = [.10, .09, .09, .08, .08, .07, .07, .07, .08, .09, .09, .09]
            mc = [ac * w for w in W]
        if len(ma) != 12:
            ar = std.get("autoconsumption_rate") or 0.4
            ma = [min(p * ar, c) for p, c in zip(mp, mc)]

        surplus = [max(0.0, p - a) for p, a in zip(mp, ma)]
        grid    = [max(0.0, c - a) for c, a in zip(mc, ma)]

        x  = np.arange(12)
        bw = 0.38

        fig, ax = plt.subplots(figsize=(11, 4.4), facecolor="white")
        self._style_ax(ax, ylabel="kWh / miesiąc")

        # Stacked: autokonsumpcja (#22c55e) + nadwyżka (#facc15)
        b1 = ax.bar(x - bw / 2, ma, width=bw,
                    label="Autokonsumpcja", color=C_AUTO,
                    zorder=3, linewidth=0, alpha=0.92)
        b2 = ax.bar(x - bw / 2, surplus, width=bw,
                    label="Nadwyżka do sieci", color=C_SURPLUS,
                    zorder=3, linewidth=0, alpha=0.92, bottom=ma)

        # Pobór z sieci (#ef4444)
        b3 = ax.bar(x + bw / 2, grid, width=bw,
                    label="Pobór z sieci", color=C_GRID_BAL,
                    zorder=3, linewidth=0, alpha=0.88)

        # Linia zapotrzebowania (#3b82f6) z markerami jak Recharts dot
        l1, = ax.plot(x, mc, color=C_DEMAND, linewidth=2.0,
                      marker="o", markersize=4.0,
                      markerfacecolor="white", markeredgewidth=1.5,
                      markeredgecolor=C_DEMAND,
                      label="Zapotrzebowanie", zorder=5,
                      solid_capstyle="round")

        ax.set_xticks(x)
        ax.set_xticklabels(MONTHS_PL, fontsize=8.5, color=C_TICK)
        ax.set_xlim(-0.65, 11.65)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"{int(v):,}".replace(",", "\u00a0")))

        # Legenda na dole — jak Recharts
        ax.legend(handles=[b1, b2, b3, l1],
                  loc="upper center", bbox_to_anchor=(0.5, -0.13),
                  ncol=4, frameon=False, fontsize=8.5,
                  handlelength=1.4, handleheight=0.9)

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 2 — Prognoza zysku netto (25 lat)
    # Identyczny z CashflowChart25 w EnergyCharts.jsx (Recharts AreaChart)
    # =========================================================================

    def _chart_cashflow_25(self, std: dict) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        pv_cost    = std.get("pv_cost_gross_pln") or 0
        bat_cost   = (std.get("with_battery_total_cost_pln") or
                      std.get("total_cost_with_battery_pln") or 0)
        pv_annual  = std.get("pv_savings_pln") or 0
        bat_annual = std.get("total_savings_with_battery_pln") or 0
        has_bat    = bat_annual > 0 and bat_cost > 0

        # Obliczenia identyczne z CashflowChart25 (React)
        lata    = list(range(1, 26))
        pv_cum  = []
        bat_cum = []
        pv_net  = -pv_cost
        bat_net = -bat_cost if has_bat else None

        for y in lata:
            f = 1.04 ** (y - 1)
            pv_net += pv_annual * f
            pv_cum.append(round(pv_net))
            if has_bat and bat_net is not None:
                bat_net += bat_annual * f
                bat_cum.append(round(bat_net))

        payback_yr = next((y for y, v in zip(lata, pv_cum) if v >= 0), None)

        fig, ax = plt.subplots(figsize=(11, 4.0), facecolor="white")
        self._style_ax(ax, xlabel="Rok", ylabel="Zysk netto")

        x = np.array(lata)

        # Obszar PV — fill identyczny z Recharts Area
        ax.fill_between(x, pv_cum, 0,
                        where=[v >= 0 for v in pv_cum],
                        color=C_PV_FILL, alpha=1.0, zorder=1)
        ax.fill_between(x, pv_cum, 0,
                        where=[v < 0 for v in pv_cum],
                        color=C_PV_FILL, alpha=0.5, zorder=1)
        ax.plot(x, pv_cum, color=C_PV_STROKE, linewidth=2.5,
                zorder=4, solid_capstyle="round", label="Tylko PV")

        # Obszar PV + Magazyn
        if has_bat and bat_cum:
            ax.fill_between(x, bat_cum, 0,
                            where=[v >= 0 for v in bat_cum],
                            color=C_BAT_FILL, alpha=1.0, zorder=1)
            ax.fill_between(x, bat_cum, 0,
                            where=[v < 0 for v in bat_cum],
                            color=C_BAT_FILL, alpha=0.4, zorder=1)
            ax.plot(x, bat_cum, color=C_BAT_STROKE, linewidth=2.5,
                    zorder=4, solid_capstyle="round", label="PV + Magazyn")

        # Linia zerowa — #94a3b8 dasharray 4 2
        ax.axhline(0, color=C_ZERO_LINE, linewidth=1.5,
                   linestyle=(0, (4, 2)), zorder=3)
        ax.text(1.0, 0, "próg zwrotu",
                fontsize=7.5, color=C_ZERO_LINE, va="bottom", ha="left")

        # Adnotacja roku zwrotu — #1E8449 bold
        if payback_yr:
            ax.axvline(payback_yr, color=C_PAYBACK_CLR, linewidth=1.2,
                       linestyle=":", alpha=0.85, zorder=3)
            y_pos = max(pv_cum) * 0.08 if pv_cum else 0
            ax.text(payback_yr + 0.3, y_pos,
                    f"Zwrot w ~{payback_yr}.\u00a0roku",
                    fontsize=8.5, color=C_PAYBACK_CLR,
                    fontweight="bold", va="bottom")

        # Oś X: 1, 4, 8, 12, 16, 20, 24, 25
        x_ticks = [1] + list(range(4, 26, 4)) + [25]
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([str(t) for t in x_ticks],
                           fontsize=8, color=C_TICK)
        ax.set_xlim(0.5, 25.5)

        # Oś Y: tysiące (10k, 20k, …)
        def _k(v, _):
            if v == 0:
                return "0"
            return f"{int(v / 1000)}k" if abs(v) >= 1000 else f"{int(v)}"

        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_k))
        ax.legend(loc="upper left", frameon=True,
                  edgecolor=C_GRID_LINE, fontsize=8.5)

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 3 — Dobowy przepływ energii (lato + zima)
    # ComposedChart: bars + linia SOC
    # KLUCZOWA ZMIANA v5.0: BRAK legend na wykresach — jedna wspólna na dole
    # =========================================================================

    def _chart_daily_flow(self, std: dict) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        hr = (std.get("hourly_result_with_battery") or
              std.get("hourly_result_without_battery") or {})
        sc     = hr.get("seasonal_charts") or {}
        summer = sc.get("summer") or []
        winter = sc.get("winter") or []

        ap       = std.get("annual_production_kwh") or 4000
        ac       = std.get("annual_consumption_kwh") or 3500
        peak_pv  = ap / 8760 * 12
        avg_cons = ac / 8760

        def extract(day_data, *keys):
            if not day_data or len(day_data) < 24:
                return None
            if not isinstance(day_data[0], dict):
                return None
            for key in keys:
                if key in day_data[0]:
                    return [float(day_data[h].get(key, 0.0))
                            for h in range(min(24, len(day_data)))]
            return None

        def pad24(lst):
            lst = list(lst) if lst else []
            return (lst + [0.0] * 24)[:24]

        has_s  = len(summer) >= 24
        s_pv   = extract(summer, "pv", "pv_production")      if has_s else None
        s_cons = extract(summer, "consumption")               if has_s else None
        s_grid = extract(summer, "gridImport", "grid_import") if has_s else None
        s_bchg = extract(summer, "batteryCharge")             if has_s else None
        s_bdis = extract(summer, "batteryDischarge")          if has_s else None
        s_soc  = extract(summer, "soc")                       if has_s else None

        has_w  = len(winter) >= 24
        w_pv   = extract(winter, "pv", "pv_production")      if has_w else None
        w_cons = extract(winter, "consumption")               if has_w else None
        w_grid = extract(winter, "gridImport", "grid_import") if has_w else None
        w_bchg = extract(winter, "batteryCharge")             if has_w else None
        w_bdis = extract(winter, "batteryDischarge")          if has_w else None
        w_soc  = extract(winter, "soc")                       if has_w else None

        # Fallback TYLKO gdy seasonal_charts kompletnie niedostępny
        if s_pv is None:
            s_pv = pad24([0.0]*6 + [peak_pv*f for f in
                         [.08,.22,.42,.62,.80,.92,1.,.98,.88,.72,.52,.30,.06]] + [0.0]*5)
        if s_cons is None:
            s_cons = pad24([avg_cons*.7]*6 + [avg_cons*f for f in
                           [1.3,1.5,1.1,.9,.9,1.,1.,1.,1.1,1.2,1.5,1.8,2.,1.8,1.3,1.,.8,.7]])
        if s_grid is None:
            s_grid = [max(0.0, c - p) for c, p in zip(s_cons, s_pv)]
        if w_pv is None:
            w_pv = pad24([0.0]*9 + [peak_pv*.3*f for f in
                         [.3,.6,.85,1.,.85,.6]] + [0.0]*9)
        if w_cons is None:
            w_cons = pad24([avg_cons*1.1]*7 + [avg_cons*f for f in
                           [1.4,1.2,1.,1.,1.,1.,1.,1.,1.2,1.5,1.8,2.,1.9,1.5,1.2,1.1,1.]])
        if w_grid is None:
            w_grid = [max(0.0, c - p) for c, p in zip(w_cons, w_pv)]

        has_battery = any([
            s_bchg and any(v > 0 for v in s_bchg),
            s_bdis and any(v > 0 for v in s_bdis),
            w_bchg and any(v > 0 for v in w_bchg),
        ])

        # Figura z miejscem na jedną legendę u dołu
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.8 if has_battery else 4.4),
                                 facecolor="white", sharey=False)

        x  = np.arange(24)
        bw = 0.20 if has_battery else 0.30

        panels = [
            (axes[0], s_pv, s_cons, s_grid, s_bchg, s_bdis, s_soc,
             "☀  Szczyt letni (Czerwiec)"),
            (axes[1], w_pv, w_cons, w_grid, w_bchg, w_bdis, w_soc,
             "❄  Minimum zimowe (Styczeń)"),
        ]

        for ax, pv, cons, grid, bchg, bdis, soc, title in panels:
            self._style_ax(ax, title=title, ylabel="kW")

            offsets = [-2, -1, 0, 1, 2] if has_battery else [-1, 0, 1]

            ax.bar(x + offsets[0] * bw, pv,   width=bw, color=C_PV,
                   zorder=3, linewidth=0, alpha=0.92)
            ax.bar(x + offsets[1] * bw, grid, width=bw, color=C_GRID_IMP,
                   zorder=3, linewidth=0, alpha=0.88)
            ax.bar(x + offsets[2] * bw, cons, width=bw, color=C_CONSUMPTION,
                   zorder=3, linewidth=0, alpha=0.80)

            if has_battery:
                ax.bar(x + offsets[3] * bw,
                       pad24(bchg) if bchg else [0.0]*24,
                       width=bw, color=C_BAT_CHARGE,
                       zorder=3, linewidth=0, alpha=0.92)
                ax.bar(x + offsets[4] * bw,
                       pad24(bdis) if bdis else [0.0]*24,
                       width=bw, color=C_BAT_DISC,
                       zorder=3, linewidth=0, alpha=0.92)

            # Oś X: co 3 godziny jak w EnergyFlowChart.jsx interval=2
            ax.set_xticks(range(0, 24, 3))
            ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)],
                               fontsize=7.5, color=C_TICK)
            ax.set_xlim(-0.8, 23.8)

            # SOC na prawej osi — linia przerywana #1B4F72
            if has_battery and soc and any(v > 0 for v in soc):
                ax_r = ax.twinx()
                ax_r.plot(x, soc, color=C_SOC, linewidth=1.8,
                          linestyle=(0, (4, 2)), zorder=5)
                ax_r.set_ylim(0, 130)
                ax_r.set_yticks([0, 25, 50, 75, 100])
                ax_r.set_yticklabels(["0%", "25%", "50%", "75%", "100%"],
                                     fontsize=7, color=C_SOC)
                ax_r.spines["top"].set_visible(False)
                ax_r.spines["right"].set_color(C_GRID_LINE)
                ax_r.tick_params(axis="y", which="both", length=0)

            # ← CELOWO BRAK ax.legend() — legenda jest wspólna pod figurą

        # ── JEDNA WSPÓLNA LEGENDA na dole (jak frontend — legenda pod wykresem) ──
        handles = [
            mpatches.Patch(facecolor=C_PV,          alpha=0.92, label="Produkcja PV"),
            mpatches.Patch(facecolor=C_GRID_IMP,    alpha=0.88, label="Pobór z sieci"),
            mpatches.Patch(facecolor=C_CONSUMPTION, alpha=0.80, label="Zużycie domu"),
        ]
        if has_battery:
            handles += [
                mpatches.Patch(facecolor=C_BAT_CHARGE, alpha=0.92, label="Ładowanie bat."),
                mpatches.Patch(facecolor=C_BAT_DISC,   alpha=0.92, label="Rozładowanie bat."),
                Line2D([0], [0], color=C_SOC, linewidth=1.8,
                       linestyle=(0, (4, 2)), label="SOC (%)"),
            ]

        fig.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.0),
            ncol=len(handles),
            frameon=False,
            fontsize=8.5,
            handlelength=1.4,
            handleheight=0.85,
            columnspacing=1.2,
        )

        fig.tight_layout(pad=1.2, w_pad=2.0)
        fig.subplots_adjust(bottom=0.18 if has_battery else 0.16)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 4 — Schemat dachu z panelami (SVG programatyczny)
    # Zsynchronizowany z RoofVisualizer.jsx v5.1:
    #   panel:  gradient #0A1A2F→#15273D→#1F2F45  stroke=#2A2F33  (ciemny granat)
    #   dach:   fill=#d9d9d9 pattern dachówki (16×8px) stroke=#7a7a7a
    #   siatka ogniw: 3kol×6wier, białe linie rgba(255,255,255,0.18/0.12)
    #   highlight: rgba(255,255,255,0.04) na górnych 25% panelu
    #   numer panelu: rgba(255,255,255,0.75) — biały na ciemnym tle
    #   Y-flip: py = roofH - panel.y*scale - panel.h*scale (jak panelSvgY())
    #   róża:   rotate = 180 - azimuth_deg (jak CompassRose.jsx)
    # =========================================================================

    def _chart_roof_panels(self, std: dict, request) -> str:
        # ── Kolory zsynchronizowane z RoofVisualizer.jsx v5.1 ─────────────────
        # Panel: ciemny gradient granatowy (jak linearGradient pvGrad w JSX)
        PANEL_GRAD_START = "#0A1A2F"  # stop 0%
        PANEL_GRAD_MID   = "#15273D"  # stop 50%
        PANEL_GRAD_END   = "#1F2F45"  # stop 100%
        PANEL_STR        = "#2A2F33"  # ramka panelu
        # Dach: szara dachówka (jak ROOF_FILL / ROOF_STROKE w JSX)
        ROOF_FILL        = "#d9d9d9"
        ROOF_STROKE      = "#7a7a7a"
        # Pozostałe
        DIM_COLOR        = "#6b6b6b"  # linie wymiarów (jak DIM_COLOR w JSX)
        MUTED            = "#6b7280"
        RED_S            = "#E74C3C"  # ramię S = czerwone (kierunek połaci)
        FONT             = "DejaVu Sans, Arial, sans-serif"
        C_TEXT_SVG       = "#2C3E50"  # LABEL_COLOR jak w JSX

        # ── Pobierz layout ──────────────────────────────────────────────────────
        facet_layouts = std.get("facet_layouts") or []
        if not facet_layouts:
            return self._roof_placeholder_svg()

        fl = facet_layouts[0]
        if not isinstance(fl, dict):
            try:
                fl = fl.dict() if hasattr(fl, "dict") else vars(fl)
            except Exception:
                return self._roof_placeholder_svg()

        panel_positions = fl.get("layout") or fl.get("panel_positions") or []
        if not panel_positions:
            return self._roof_placeholder_svg()

        facet_w  = float(fl.get("width_m")    or fl.get("facet_w") or 10.0)
        facet_l  = float(fl.get("length_m")   or fl.get("facet_l") or 5.0)
        azimuth  = float(fl.get("azimuth_deg") or 180.0)

        panels_count = int(std.get("panels_count") or len(panel_positions))
        total_kwp    = float(std.get("total_power_kwp") or
                             std.get("peak_power_kwp") or 0.0)

        # ── Skala / layout SVG ──────────────────────────────────────────────────
        SCALE    = 60.0   # px / metr
        PAD      = 52     # padding wewnątrz SVG na wymiary
        COMP_R   = 24     # promień róży wiatrów
        COMP_MX  = 48     # margines do środka róży od prawej krawędzi dachu

        roof_w_px = facet_w * SCALE
        roof_h_px = facet_l * SCALE

        svg_w = int(roof_w_px + PAD * 2 + COMP_MX + COMP_R * 2 + 14)
        svg_h = int(roof_h_px + PAD * 2 + 50)   # +50 na legendę na dole

        # Pozycja dachu w SVG
        rx0 = PAD
        ry0 = PAD

        # Środek róży
        cx_c = rx0 + roof_w_px + COMP_MX + COMP_R
        cy_c = ry0 + COMP_R + 8

        # ── Budowanie SVG ───────────────────────────────────────────────────────
        out = []
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {svg_w} {svg_h}" '
            f'width="{svg_w}" height="{svg_h}">'
        )

        # ── DEFS: markery strzałek + gradient panelu + pattern dachu + cienie ──
        out.append(f'''<defs>
  <!-- Markery strzałek wymiarów -->
  <marker id="ae" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
    <path d="M0,0 L0,6 L6,3 z" fill="{DIM_COLOR}"/>
  </marker>
  <marker id="as" markerWidth="6" markerHeight="6" refX="3" refY="3"
          orient="auto-start-reverse">
    <path d="M0,0 L0,6 L6,3 z" fill="{DIM_COLOR}"/>
  </marker>

  <!-- Gradient panelu PV — ciemny granat diagonal (identyczny z pvGrad w RoofVisualizer.jsx) -->
  <linearGradient id="pvGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%"   stop-color="{PANEL_GRAD_START}"/>
    <stop offset="50%"  stop-color="{PANEL_GRAD_MID}"/>
    <stop offset="100%" stop-color="{PANEL_GRAD_END}"/>
  </linearGradient>

  <!-- Pattern dachówki — subtelne poziome linie co 8px (jak patternId w JSX) -->
  <pattern id="roofTile" x="0" y="0" width="16" height="8" patternUnits="userSpaceOnUse">
    <rect width="16" height="8" fill="{ROOF_FILL}"/>
    <line x1="0" y1="8" x2="16" y2="8" stroke="{ROOF_STROKE}" stroke-width="0.4" opacity="0.35"/>
    <line x1="0" y1="0" x2="0"  y2="8" stroke="{ROOF_STROKE}" stroke-width="0.25" opacity="0.2"/>
  </pattern>

  <!-- Cień panelu — efekt głębi (jak panelShad filter w RoofVisualizer.jsx) -->
  <filter id="panelShad" x="-8%" y="-8%" width="120%" height="120%">
    <feDropShadow dx="1" dy="1.5" stdDeviation="1.2" flood-color="rgba(0,0,0,0.45)"/>
  </filter>

  <!-- Cień dachu -->
  <filter id="roofShad" x="-5%" y="-5%" width="115%" height="115%">
    <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.12)"/>
  </filter>
</defs>''')

        # Białe tło
        out.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')

        # Powierzchnia dachu — szara dachówka z patterntem (jak w RoofVisualizer.jsx)
        out.append(
            f'<rect x="{rx0}" y="{ry0}" '
            f'width="{roof_w_px:.1f}" height="{roof_h_px:.1f}" '
            f'fill="url(#roofTile)" stroke="{ROOF_STROKE}" '
            f'stroke-width="2.5" rx="3" filter="url(#roofShad)"/>'
        )

        # ── Panele — ciemny gradient + siatka ogniw + cień ────────────────────
        # Wizualnie identyczne z RoofVisualizer.jsx v5.1 (pvGrad + panelShad)
        for idx, pos in enumerate(panel_positions):
            if isinstance(pos, dict):
                px_m  = float(pos.get("x", 0))
                py_m  = float(pos.get("y", 0))
                pw_m  = float(pos.get("width", 1.134))
                ph_m  = float(pos.get("height", 1.762))
                label = pos.get("label") or str(idx + 1)
            else:
                px_m  = float(getattr(pos, "x", 0))
                py_m  = float(getattr(pos, "y", 0))
                pw_m  = float(getattr(pos, "width", 1.134))
                ph_m  = float(getattr(pos, "height", 1.762))
                label = getattr(pos, "label", None) or str(idx + 1)

            pw = pw_m * SCALE
            ph = ph_m * SCALE
            px = rx0 + px_m * SCALE
            # Y-FLIP identyczny z panelSvgY() w RoofVisualizer.jsx:
            # panelYFromTop = roofHeightPx - panel.y*scale - panel.height*scale
            py = ry0 + (facet_l * SCALE - py_m * SCALE - ph)

            # ── Panel: gradient granatowy + cień (jak <g filter="url(#panelShad)"> w JSX)
            out.append(f'<g filter="url(#panelShad)">')

            # Tło panelu — gradient diagonal (pvGrad)
            out.append(
                f'<rect x="{px:.1f}" y="{py:.1f}" '
                f'width="{pw:.1f}" height="{ph:.1f}" '
                f'fill="url(#pvGrad)" stroke="{PANEL_STR}" '
                f'stroke-width="1.2" rx="1"/>'
            )

            # Siatka ogniw: 3 kolumny × 6 wierszy
            # Pionowe linie — opacity 0.18 (jak w JSX)
            N_COL, N_ROW = 3, 6
            cw = pw / N_COL
            ch = ph / N_ROW
            for ci in range(1, N_COL):
                lx = px + ci * cw
                out.append(
                    f'<line x1="{lx:.1f}" y1="{py:.1f}" '
                    f'x2="{lx:.1f}" y2="{py + ph:.1f}" '
                    f'stroke="rgba(255,255,255,0.18)" stroke-width="0.5"/>'
                )
            # Poziome linie — opacity 0.12 (jak w JSX)
            for ri in range(1, N_ROW):
                ly = py + ri * ch
                out.append(
                    f'<line x1="{px:.1f}" y1="{ly:.1f}" '
                    f'x2="{px + pw:.1f}" y2="{ly:.1f}" '
                    f'stroke="rgba(255,255,255,0.12)" stroke-width="0.4"/>'
                )

            # Highlight w lewym górnym rogu — efekt 3D (jak w JSX)
            out.append(
                f'<rect x="{px:.1f}" y="{py:.1f}" '
                f'width="{pw:.1f}" height="{ph * 0.25:.1f}" '
                f'fill="rgba(255,255,255,0.04)" rx="1"/>'
            )

            # Numer panelu — BIAŁY tekst (maks 60 jak w JSX)
            if idx < 60:
                tx = px + pw / 2
                ty = py + ph / 2
                fs = max(7, min(11, int(pw * 0.22)))
                out.append(
                    f'<text x="{tx:.1f}" y="{ty:.1f}" '
                    f'text-anchor="middle" dominant-baseline="middle" '
                    f'font-size="{fs}" font-weight="bold" '
                    f'fill="rgba(255,255,255,0.75)" '
                    f'font-family="{FONT}">{label}</text>'
                )

            out.append('</g>')  # koniec grupy panelu

        # ── Wymiar poziomy (szerokość dachu) ────────────────────────────────────
        dim_y = ry0 + roof_h_px + 22
        mx    = rx0 + roof_w_px / 2
        out.append(
            f'<line x1="{rx0:.1f}" y1="{dim_y}" '
            f'x2="{rx0 + roof_w_px:.1f}" y2="{dim_y}" '
            f'stroke="{DIM_COLOR}" stroke-width="1.2" '
            f'marker-start="url(#as)" marker-end="url(#ae)"/>'
        )
        out.append(
            f'<text x="{mx:.1f}" y="{dim_y + 14}" '
            f'text-anchor="middle" font-size="11.5" '
            f'font-weight="bold" fill="{DIM_COLOR}" '
            f'font-family="{FONT}">{facet_w:.1f}\u00a0m</text>'
        )

        # ── Wymiar pionowy (długość dachu) ──────────────────────────────────────
        dvx = rx0 - 24
        mvy = ry0 + roof_h_px / 2
        out.append(
            f'<line x1="{dvx}" y1="{ry0:.1f}" '
            f'x2="{dvx}" y2="{ry0 + roof_h_px:.1f}" '
            f'stroke="{DIM_COLOR}" stroke-width="1.2" '
            f'marker-start="url(#as)" marker-end="url(#ae)"/>'
        )
        out.append(
            f'<text x="{dvx - 6}" y="{mvy:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="11.5" font-weight="bold" fill="{DIM_COLOR}" '
            f'font-family="{FONT}" '
            f'transform="rotate(-90,{dvx - 6},{mvy:.1f})">'
            f'{facet_l:.1f}\u00a0m</text>'
        )

        # ── Napis: liczba paneli i kWp ──────────────────────────────────────────
        header_y = max(ry0 - 12, 12)
        out.append(
            f'<text x="{rx0 + roof_w_px / 2:.1f}" y="{header_y}" '
            f'text-anchor="middle" font-size="12" '
            f'font-weight="900" fill="{C_TEXT_SVG}" '
            f'font-family="{FONT}">'
            f'{panels_count}\u00a0paneli\u00a0·\u00a0{total_kwp:.2f}\u00a0kWp</text>'
        )

        # ── Legenda kolorów (dach + panele) — zsynchronizowana z JSX ──────────
        # Pozycja: pod wymiarem poziomym
        leg_y  = svg_h - 14
        leg_x0 = rx0

        # Kwadrat dachu (szary — jak w legendzie JSX)
        out.append(
            f'<rect x="{leg_x0}" y="{leg_y - 9}" width="14" height="10" '
            f'fill="{ROOF_FILL}" stroke="{ROOF_STROKE}" '
            f'stroke-width="1.5" rx="2"/>'
        )
        out.append(
            f'<text x="{leg_x0 + 18}" y="{leg_y}" '
            f'font-size="9.5" fill="{MUTED}" font-family="{FONT}">'
            f'Powierzchnia dachu</text>'
        )

        # Kwadrat panelu (środkowy kolor gradientu dla czytelności na małym rect)
        leg_x1 = leg_x0 + 140
        out.append(
            f'<rect x="{leg_x1}" y="{leg_y - 9}" width="14" height="10" '
            f'fill="{PANEL_GRAD_MID}" stroke="{PANEL_STR}" '
            f'stroke-width="1.5" rx="2"/>'
        )
        out.append(
            f'<text x="{leg_x1 + 18}" y="{leg_y}" '
            f'font-size="9.5" fill="{MUTED}" font-family="{FONT}">'
            f'Panele fotowoltaiczne</text>'
        )

        # ── Róża wiatrów (CompassRose z RoofVisualizer.jsx) ─────────────────────
        out.extend(
            self._svg_compass_rose(cx_c, cy_c, COMP_R, azimuth,
                                   DIM_COLOR, RED_S, MUTED, FONT)
        )

        out.append("</svg>")
        svg_str = "\n".join(out)
        return base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")

    # ── Róża wiatrów — logika identyczna z CompassRose.jsx ────────────────────

    @staticmethod
    def _svg_compass_rose(cx, cy, r, azimuth_deg,
                          dim_color, red_color, muted, font) -> list:
        """
        Wektorowa róża wiatrów.
        rotate = 180 - azimuth_deg — IDENTYCZNIE jak w RoofVisualizer.jsx.
        Ramię S (dół) = czerwone = kierunek połaci.
        """
        rotate = 180.0 - azimuth_deg
        arm = r * 0.78
        hw  = r * 0.22

        lines = [f'<g transform="rotate({rotate:.1f},{cx:.1f},{cy:.1f})">']

        # Krąg zewnętrzny
        lines.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" '
            f'fill="white" stroke="{dim_color}" stroke-width="1.2" opacity="0.92"/>'
        )

        # Ramię S — czerwone (kierunek połaci)
        lines.append(
            f'<polygon points="{cx:.1f},{cy + arm:.1f} '
            f'{cx - hw:.1f},{cy + 2:.1f} {cx + hw:.1f},{cy + 2:.1f}" '
            f'fill="{red_color}" opacity="0.9"/>'
        )
        # Ramię N — ciemny
        lines.append(
            f'<polygon points="{cx:.1f},{cy - arm:.1f} '
            f'{cx - hw:.1f},{cy - 2:.1f} {cx + hw:.1f},{cy - 2:.1f}" '
            f'fill="{dim_color}" opacity="0.75"/>'
        )
        # Ramię E — muted
        lines.append(
            f'<polygon points="{cx + arm:.1f},{cy:.1f} '
            f'{cx + 2:.1f},{cy - hw:.1f} {cx + 2:.1f},{cy + hw:.1f}" '
            f'fill="{muted}" opacity="0.5"/>'
        )
        # Ramię W — muted
        lines.append(
            f'<polygon points="{cx - arm:.1f},{cy:.1f} '
            f'{cx - 2:.1f},{cy - hw:.1f} {cx - 2:.1f},{cy + hw:.1f}" '
            f'fill="{muted}" opacity="0.5"/>'
        )
        # Środkowy punkt
        lines.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" '
            f'fill="white" stroke="{dim_color}" stroke-width="1.2"/>'
        )

        # Etykiety — obracają się RAZEM (identycznie jak w frontendzie)
        lines.append(
            f'<text x="{cx:.1f}" y="{cy - r - 3:.1f}" '
            f'text-anchor="middle" font-size="7.5" font-weight="900" '
            f'fill="{dim_color}" font-family="{font}">N</text>'
        )
        lines.append(
            f'<text x="{cx:.1f}" y="{cy + r + 10:.1f}" '
            f'text-anchor="middle" font-size="7.5" font-weight="900" '
            f'fill="{red_color}" font-family="{font}">S</text>'
        )
        lines.append(
            f'<text x="{cx + r + 5:.1f}" y="{cy + 2.5:.1f}" '
            f'text-anchor="start" font-size="6.5" font-weight="700" '
            f'fill="{muted}" font-family="{font}">E</text>'
        )
        lines.append(
            f'<text x="{cx - r - 5:.1f}" y="{cy + 2.5:.1f}" '
            f'text-anchor="end" font-size="6.5" font-weight="700" '
            f'fill="{muted}" font-family="{font}">W</text>'
        )
        lines.append("</g>")
        return lines

    @staticmethod
    def _roof_placeholder_svg() -> str:
        """Placeholder gdy brak danych layoutu."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="180">'
            '<rect width="420" height="180" fill="#f9fafb"/>'
            '<text x="210" y="90" text-anchor="middle" dominant-baseline="middle" '
            'font-size="13" fill="#9ca3af" '
            'font-family="DejaVu Sans, Arial, sans-serif">'
            'Brak danych o układzie paneli</text>'
            '</svg>'
        )
        return base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    # =========================================================================
    # METODA GŁÓWNA: generate()
    # =========================================================================

    def generate(self, report_data: ReportData) -> bytes:
        """
        Generuje PDF raportu fotowoltaicznego.
        Wszystkie wykresy odwzorowują frontend 1:1.
        Raport obejmuje sekcje S0–S9.
        """
        import traceback

        std  = report_data.all_scenarios_results.get("standard") or {}
        eco  = report_data.all_scenarios_results.get("economy")  or {}
        prem = report_data.all_scenarios_results.get("premium")  or {}

        charts = {}

        for name, method, args in [
            ("monthly_balance", self._chart_monthly_balance, (std,)),
            ("payback",         self._chart_cashflow_25,     (std,)),
            ("daily_flow",      self._chart_daily_flow,      (std,)),
            ("roof_panels",     self._chart_roof_panels,     (std, report_data.input_request)),
        ]:
            try:
                charts[name] = method(*args)
            except Exception as e:
                print(f"[ReportGenerator] CHART {name} error: {e}")
                traceback.print_exc()
                charts[name] = ""

        template = self.env.get_template("report/base.html")

        css_path    = os.path.join(self.static_dir, "report", "report.css")
        css_content = ""
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
        else:
            print(f"[ReportGenerator] OSTRZEŻENIE: CSS nie znaleziony: {css_path}")

        context = {
            "data":            report_data.input_data_summary,
            "req":             report_data.input_request,
            "standard":        std,
            "premium":         prem,
            "economy":         eco,
            "warnings":        report_data.warnings_and_confirmations,
            "charts":          charts,
            "generation_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "version":         "5.1.0",
            "css_content":     css_content,
        }

        rendered_html = template.render(**context)

        return HTML(
            string=rendered_html,
            base_url=self.base_dir,
        ).write_pdf()