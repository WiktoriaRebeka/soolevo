# backend/app/core/report_generator.py
"""
ReportGenerator v4.1 — PDF identyczny wizualnie z frontendem React/Recharts.

ZMIANY v4.1 (względem v4.0):
✅ _chart_monthly_balance()  — kolory IDENTYCZNE z wykresem dobowym (specyfikacja):
                               auto=#22c55e, nadwyżka=#facc15, sieć=#ef4444, demand=#3b82f6
✅ _chart_daily_flow()       — usunięte legendy per-wykres, jedna wspólna legenda na dole
✅ _chart_roof_panels()      — SVG generowany programatycznie (jak RoofVisualizer.jsx):
                               panel #FFD700/#B8860B, dach #E8F4F3/#569793,
                               róża wiatrów z azymutem (rotate=180-azimuth), numery paneli
✅ _chart_cashflow_25()      — bez zmian (v4.0 prawidłowy)
"""

import os
import base64
from io import BytesIO
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ── Monkey-patch WeasyPrint / pydyf ──────────────────────────────────────────
try:
    import pydyf
    if not hasattr(pydyf.Stream, "transform"):
        def transform(self, a, b, c, d, e, f):
            concat = getattr(self, "concat", None)
            if callable(concat):
                concat(a, b, c, d, e, f)
        pydyf.Stream.transform = transform
    if not hasattr(pydyf.Stream, "text_matrix"):
        def text_matrix(self, *values):
            s = getattr(self, "set_text_matrix", None)
            if callable(s):
                s(*values)
        pydyf.Stream.text_matrix = text_matrix
except ImportError:
    pass

from weasyprint import HTML
from app.schemas.report import ReportData

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
    print("[ReportGenerator] matplotlib niedostępny")

if MATPLOTLIB_AVAILABLE:
    plt.rcParams.update({
        "font.family":        "DejaVu Sans",
        "font.size":          9,
        "axes.titlesize":     11,
        "axes.titleweight":   "bold",
        "axes.titlecolor":    "#1f2937",
        "axes.labelsize":     8.5,
        "axes.labelcolor":    "#6b7280",
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.linewidth":     0.8,
        "axes.edgecolor":     "#e5e7eb",
        "axes.facecolor":     "white",
        "figure.facecolor":   "white",
        "grid.color":         "#e5e7eb",
        "grid.linewidth":     0.7,
        "grid.linestyle":     (0, (3, 3)),
        "grid.alpha":         1.0,
        "xtick.color":        "#6b7280",
        "ytick.color":        "#6b7280",
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        "legend.fontsize":    8.5,
        "legend.framealpha":  0.95,
        "legend.edgecolor":   "#e5e7eb",
        "legend.borderpad":   0.6,
        "legend.handlelength": 1.4,
        "legend.handleheight": 0.9,
    })

# ── Paleta kolorów (EnergyFlowChart.jsx) ─────────────────────────────────────
C_PV          = "#D4AC0D"   # pv (dobowy)
C_GRID_IMP    = "#E57373"   # gridImport (dobowy)
C_CONSUMPTION = "#2E86C1"   # consumption (dobowy)
C_BAT_CHARGE  = "#66BB6A"   # batteryCharge (dobowy)
C_BAT_DISC    = "#A78BFA"   # batteryDischarge (dobowy)
C_SOC         = "#1B4F72"   # soc (dobowy)

# Kolory miesięcznego bilansu — spec z promptu (Tailwind):
C_AUTO        = "#22c55e"   # autokonsumpcja = green-500
C_SURPLUS     = "#facc15"   # nadwyżka       = yellow-400
C_GRID_BAL    = "#ef4444"   # pobór z sieci  = red-500
C_DEMAND      = "#3b82f6"   # zapotrzebowanie= blue-500

# CashflowChart25:
C_PV_STROKE   = "#D4AC0D"
C_PV_FILL     = "#FEF9E7"
C_BAT_STROKE  = "#8b5cf6"
C_BAT_FILL    = "#f5f3ff"
C_ZERO_LINE   = "#94a3b8"
C_PAYBACK     = "#1E8449"

C_TEXT        = "#1f2937"
C_GRID_LINE   = "#e5e7eb"
C_TICK        = "#6b7280"


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

    @staticmethod
    def _format_pln(value):
        if value is None: return "—"
        try: return f"{int(value):,} zł".replace(",", " ")
        except: return "—"

    @staticmethod
    def _format_num(value, decimals=0):
        if value is None: return "—"
        try:
            if decimals == 0: return f"{int(value):,}".replace(",", " ")
            return f"{float(value):,.{decimals}f}".replace(",", " ").replace(".", ",")
        except: return "—"

    @staticmethod
    def _fig_to_b64(fig) -> str:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=180, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    @staticmethod
    def _style_ax(ax, title=None, xlabel=None, ylabel=None):
        ax.set_facecolor("white")
        ax.yaxis.grid(True, color=C_GRID_LINE, linewidth=0.7,
                      linestyle=(0, (3, 3)), zorder=0)
        ax.xaxis.grid(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(C_GRID_LINE)
        ax.spines["bottom"].set_color(C_GRID_LINE)
        ax.tick_params(axis="both", which="both", length=0)
        if title:   ax.set_title(title, fontsize=10, fontweight="bold", color=C_TEXT, pad=10)
        if xlabel:  ax.set_xlabel(xlabel, fontsize=8.5, color=C_TICK, labelpad=6)
        if ylabel:  ax.set_ylabel(ylabel, fontsize=8.5, color=C_TICK, labelpad=6)

    # =========================================================================
    # WYKRES 1: Miesięczny bilans energii
    # ✅ v4.1: kolory identyczne z wykresem dobowym
    # =========================================================================

    def _chart_monthly_balance(self, std: dict) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        MONTHS_PL = ["Sty","Lut","Mar","Kwi","Maj","Cze",
                     "Lip","Sie","Wrz","Paź","Lis","Gru"]

        hr_no = std.get("hourly_result_without_battery") or {}
        ef    = hr_no.get("energy_flow") or {}
        mp    = ef.get("monthly_production_kwh") or []
        mc    = ef.get("monthly_consumption_kwh") or []
        ma    = ef.get("monthly_autoconsumption_kwh") or []

        if len(mp) != 12:
            hr_b = std.get("hourly_result_with_battery") or {}
            ef2  = hr_b.get("energy_flow") or {}
            mp   = ef2.get("monthly_production_kwh") or []
            mc   = ef2.get("monthly_consumption_kwh") or []
            ma   = ef2.get("monthly_autoconsumption_kwh") or []

        if len(ma) != 12 and len(mp) == 12:
            nb = (hr_no.get("net_billing")
                  or (std.get("hourly_result_with_battery") or {}).get("net_billing") or {})
            ms = nb.get("monthly_surplus_kwh") or {}
            if ms:
                surplus_list = [float(ms.get(i, 0)) for i in range(1, 13)]
                ma = [max(0.0, p - s) for p, s in zip(mp, surplus_list)]

        ap = std.get("annual_production_kwh") or 0
        ac = std.get("annual_consumption_kwh") or 0
        if len(mp) != 12:
            W = [.04,.05,.08,.10,.12,.13,.13,.12,.09,.07,.04,.03]
            mp = [ap * w for w in W]
        if len(mc) != 12:
            W = [.10,.09,.09,.08,.08,.07,.07,.07,.08,.09,.09,.09]
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

        # Stacked bary produkcji (autokonsumpcja + nadwyżka)
        b1 = ax.bar(x - bw/2, ma, width=bw,
                    label="Autokonsumpcja", color=C_AUTO,
                    zorder=3, linewidth=0, alpha=0.92)
        b2 = ax.bar(x - bw/2, surplus, width=bw,
                    label="Nadwyżka do sieci", color=C_SURPLUS,
                    zorder=3, linewidth=0, alpha=0.92, bottom=ma)

        # Słupek poboru z sieci
        b3 = ax.bar(x + bw/2, grid, width=bw,
                    label="Pobór z sieci", color=C_GRID_BAL,
                    zorder=3, linewidth=0, alpha=0.88)

        # Linia zapotrzebowania
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
            lambda v, _: f"{int(v):,}".replace(",", " ")))

        ax.legend(handles=[b1, b2, b3, l1],
                  loc="upper center", bbox_to_anchor=(0.5, -0.13),
                  ncol=4, frameon=False, fontsize=8.5,
                  handlelength=1.4, handleheight=0.9)

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 2: Prognoza zysku netto (25 lat) — CashflowChart25
    # =========================================================================

    def _chart_cashflow_25(self, std: dict) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        pv_cost    = std.get("pv_cost_gross_pln") or 0
        bat_cost   = std.get("with_battery_total_cost_pln") or std.get("total_cost_with_battery_pln") or 0
        pv_annual  = std.get("pv_savings_pln") or 0
        bat_annual = std.get("total_savings_with_battery_pln") or 0
        has_bat    = bat_annual > 0 and bat_cost > 0

        lata    = list(range(1, 26))
        pv_cum  = []
        bat_cum = []
        pv_net  = -pv_cost
        bat_net = (-bat_cost) if has_bat else None

        for y in lata:
            f = 1.04 ** (y - 1)
            pv_net += pv_annual * f
            pv_cum.append(round(pv_net))
            if has_bat and bat_net is not None:
                bat_net += bat_annual * f
                bat_cum.append(round(bat_net))

        payback_yr = next((y for y, v in zip(lata, pv_cum) if v >= 0), None)

        fig, ax = plt.subplots(figsize=(11, 4.0), facecolor="white")
        self._style_ax(ax, xlabel="Rok", ylabel="Zysk netto (PLN)")
        x = np.array(lata)

        ax.fill_between(x, pv_cum, 0, where=[v >= 0 for v in pv_cum],
                        color=C_PV_FILL, alpha=1.0, zorder=1)
        ax.fill_between(x, pv_cum, 0, where=[v < 0 for v in pv_cum],
                        color="#FEF9E7", alpha=0.5, zorder=1)
        ax.plot(x, pv_cum, color=C_PV_STROKE, linewidth=2.5,
                zorder=4, solid_capstyle="round", label="Tylko PV")

        if has_bat and bat_cum:
            ax.fill_between(x, bat_cum, 0, where=[v >= 0 for v in bat_cum],
                            color=C_BAT_FILL, alpha=1.0, zorder=1)
            ax.fill_between(x, bat_cum, 0, where=[v < 0 for v in bat_cum],
                            color=C_BAT_FILL, alpha=0.4, zorder=1)
            ax.plot(x, bat_cum, color=C_BAT_STROKE, linewidth=2.5,
                    zorder=4, solid_capstyle="round", label="PV + Magazyn")

        ax.axhline(0, color=C_ZERO_LINE, linewidth=1.5,
                   linestyle=(0, (4, 2)), zorder=3)
        ax.text(1.0, 0, "próg zwrotu", fontsize=7.5, color=C_ZERO_LINE,
                va="bottom", ha="left")

        if payback_yr:
            ax.axvline(payback_yr, color=C_PAYBACK, linewidth=1.2,
                       linestyle=":", alpha=0.85, zorder=3)
            ax.text(payback_yr + 0.3, max(pv_cum) * 0.08,
                    f"Zwrot w ~{payback_yr}. roku",
                    fontsize=8.5, color=C_PAYBACK, fontweight="bold", va="bottom")

        x_ticks = [1] + list(range(4, 26, 4)) + [25]
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([str(t) for t in x_ticks], fontsize=8, color=C_TICK)
        ax.set_xlim(0.5, 25.5)

        def _k(v, _):
            if v == 0: return "0"
            return f"{int(v/1000)}k" if abs(v) >= 1000 else f"{int(v)}"
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_k))
        ax.legend(loc="upper left", frameon=True, edgecolor=C_GRID_LINE, fontsize=8.5)
        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 3: Dobowy przepływ energii
    # ✅ v4.1: BRAK legend na wykresach — jedna wspólna legenda na dole
    # =========================================================================

    def _chart_daily_flow(self, std: dict) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        hr = (std.get("hourly_result_with_battery")
              or std.get("hourly_result_without_battery") or {})
        sc     = hr.get("seasonal_charts") or {}
        summer = sc.get("summer") or []
        winter = sc.get("winter") or []

        ap       = std.get("annual_production_kwh") or 4000
        ac       = std.get("annual_consumption_kwh") or 3500
        peak_pv  = ap / 8760 * 12
        avg_cons = ac / 8760

        def extract(day_data, *keys):
            if not day_data or len(day_data) < 24: return None
            if not isinstance(day_data[0], dict): return None
            for key in keys:
                if key in day_data[0]:
                    return [float(day_data[h].get(key, 0.0))
                            for h in range(min(24, len(day_data)))]
            return None

        def pad24(lst):
            lst = list(lst) if lst else []
            return (lst + [0.0]*24)[:24]

        has_s  = len(summer) >= 24
        s_pv   = extract(summer, "pv", "pv_production") if has_s else None
        s_cons = extract(summer, "consumption")          if has_s else None
        s_grid = extract(summer, "gridImport", "grid_import") if has_s else None
        s_bchg = extract(summer, "batteryCharge")        if has_s else None
        s_bdis = extract(summer, "batteryDischarge")     if has_s else None
        s_soc  = extract(summer, "soc")                  if has_s else None

        has_w  = len(winter) >= 24
        w_pv   = extract(winter, "pv", "pv_production") if has_w else None
        w_cons = extract(winter, "consumption")          if has_w else None
        w_grid = extract(winter, "gridImport", "grid_import") if has_w else None
        w_bchg = extract(winter, "batteryCharge")        if has_w else None
        w_bdis = extract(winter, "batteryDischarge")     if has_w else None
        w_soc  = extract(winter, "soc")                  if has_w else None

        if s_pv is None:
            s_pv = pad24([0.0]*6 + [peak_pv*f for f in
                         [.08,.22,.42,.62,.80,.92,1.,.98,.88,.72,.52,.30,.06]] + [0.0]*5)
        if s_cons is None:
            s_cons = pad24([avg_cons*.7]*6 + [avg_cons*f for f in
                           [1.3,1.5,1.1,.9,.9,1.,1.,1.,1.1,1.2,1.5,1.8,2.,1.8,1.3,1.,.8,.7]])
        if s_grid is None: s_grid = [max(0.0, c - p) for c, p in zip(s_cons, s_pv)]
        if w_pv is None:
            w_pv = pad24([0.0]*9 + [peak_pv*.3*f for f in [.3,.6,.85,1.,.85,.6]] + [0.0]*9)
        if w_cons is None:
            w_cons = pad24([avg_cons*1.1]*7 + [avg_cons*f for f in
                           [1.4,1.2,1.,1.,1.,1.,1.,1.,1.2,1.5,1.8,2.,1.9,1.5,1.2,1.1,1.]])
        if w_grid is None: w_grid = [max(0.0, c - p) for c, p in zip(w_cons, w_pv)]

        has_battery = (
            (s_bchg and any(v > 0 for v in s_bchg)) or
            (s_bdis and any(v > 0 for v in s_bdis)) or
            (w_bchg and any(v > 0 for v in w_bchg))
        )

        # Figura z przestrzenią na legendę (bottom=0.18)
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

            ax.bar(x + offsets[0]*bw, pv,   width=bw, color=C_PV,
                   zorder=3, linewidth=0, alpha=0.92)
            ax.bar(x + offsets[1]*bw, grid, width=bw, color=C_GRID_IMP,
                   zorder=3, linewidth=0, alpha=0.88)
            ax.bar(x + offsets[2]*bw, cons, width=bw, color=C_CONSUMPTION,
                   zorder=3, linewidth=0, alpha=0.80)

            if has_battery:
                ax.bar(x + offsets[3]*bw,
                       pad24(bchg) if bchg else [0.0]*24,
                       width=bw, color=C_BAT_CHARGE,
                       zorder=3, linewidth=0, alpha=0.92)
                ax.bar(x + offsets[4]*bw,
                       pad24(bdis) if bdis else [0.0]*24,
                       width=bw, color=C_BAT_DISC,
                       zorder=3, linewidth=0, alpha=0.92)

            ax.set_xticks(range(0, 24, 3))
            ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)],
                               fontsize=7.5, color=C_TICK)
            ax.set_xlim(-0.8, 23.8)

            # Linia SOC na prawej osi (bez legendy — pojawi się w fig.legend)
            if has_battery and soc and any(v > 0 for v in soc):
                ax_r = ax.twinx()
                ax_r.plot(x, soc, color=C_SOC, linewidth=1.8,
                          linestyle=(0, (4, 2)), zorder=5)
                ax_r.set_ylim(0, 130)
                ax_r.set_yticks([0, 25, 50, 75, 100])
                ax_r.set_yticklabels(["0%","25%","50%","75%","100%"],
                                     fontsize=7, color=C_SOC)
                ax_r.spines["top"].set_visible(False)
                ax_r.spines["right"].set_color(C_GRID_LINE)
                ax_r.tick_params(axis="y", which="both", length=0)
            # ← BRAK ax.legend() — celowo!

        # ── JEDNA WSPÓLNA LEGENDA na dole figury ──────────────────────────────
        handles = [
            mpatches.Patch(facecolor=C_PV,         alpha=0.92, label="Produkcja PV"),
            mpatches.Patch(facecolor=C_GRID_IMP,   alpha=0.88, label="Pobór z sieci"),
            mpatches.Patch(facecolor=C_CONSUMPTION,alpha=0.80, label="Zużycie domu"),
        ]
        if has_battery:
            handles += [
                mpatches.Patch(facecolor=C_BAT_CHARGE, alpha=0.92, label="Ładowanie bat."),
                mpatches.Patch(facecolor=C_BAT_DISC,   alpha=0.92, label="Rozładowanie bat."),
                Line2D([0],[0], color=C_SOC, linewidth=1.8,
                       linestyle=(0,(4,2)), label="SOC (%)"),
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
    # WYKRES 4: Schemat dachu z panelami — SVG identyczny z RoofVisualizer.jsx
    # ✅ v4.1: SVG generowany programatycznie
    #    panel #FFD700/#B8860B, dach #E8F4F3/#569793
    #    róża wiatrów: rotate = 180 - azimuth_deg
    #    numery paneli, wymiary strzałkowe
    # =========================================================================

    def _chart_roof_panels(self, std: dict, request) -> str:
        # Kolory — identyczne z RoofVisualizer.jsx + ScenarioCard.jsx
        PANEL_FILL  = "#FFD700"
        PANEL_STR   = "#B8860B"
        ROOF_FILL   = "#E8F4F3"
        ROOF_STROKE = "#569793"
        DIM_COLOR   = "#1B4F72"
        MUTED       = "#6b7280"
        C_RED       = "#E74C3C"
        FONT        = "DejaVu Sans, Arial, sans-serif"

        facet_layouts = std.get("facet_layouts") or []
        if not facet_layouts:
            return self._roof_placeholder_svg()

        fl = facet_layouts[0]
        if not isinstance(fl, dict):
            try:
                fl = fl.dict() if hasattr(fl, "dict") else vars(fl)
            except Exception:
                return self._roof_placeholder_svg()

        # Pozycje paneli
        panel_positions = fl.get("layout") or fl.get("panel_positions") or []
        if not panel_positions:
            return self._roof_placeholder_svg()

        facet_w = float(fl.get("width_m")  or fl.get("facet_w") or 10.0)
        facet_l = float(fl.get("length_m") or fl.get("facet_l") or 5.0)
        azimuth = float(fl.get("azimuth_deg") or 180.0)

        panels_count = int(std.get("panels_count") or len(panel_positions))
        total_kwp    = float(std.get("total_power_kwp") or std.get("peak_power_kwp") or 0.0)

        # Skala i padding
        SCALE   = 60.0   # px / metr
        PAD     = 50     # padding na wymiary
        COMP_R  = 24     # promień róży wiatrów
        COMP_MX = 46     # margines od prawej krawędzi dachu do środka róży

        roof_w  = facet_w * SCALE
        roof_h  = facet_l * SCALE
        svg_w   = int(roof_w + PAD * 2 + COMP_MX + COMP_R * 2 + 12)
        svg_h   = int(roof_h + PAD * 2 + 36)

        # Pozycja dachu w SVG
        rx0 = PAD
        ry0 = PAD

        # Środek róży wiatrów
        cx_c = rx0 + roof_w + COMP_MX + COMP_R
        cy_c = ry0 + COMP_R + 8

        out = []
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {svg_w} {svg_h}" '
            f'width="{svg_w}" height="{svg_h}">'
        )

        # Definicje markerów strzałek
        out.append(f'''<defs>
  <marker id="ae" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
    <path d="M0,0 L0,6 L6,3 z" fill="{DIM_COLOR}"/>
  </marker>
  <marker id="as" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse">
    <path d="M0,0 L0,6 L6,3 z" fill="{DIM_COLOR}"/>
  </marker>
</defs>''')

        # Białe tło
        out.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')

        # Obrys dachu
        out.append(
            f'<rect x="{rx0}" y="{ry0}" '
            f'width="{roof_w:.1f}" height="{roof_h:.1f}" '
            f'fill="{ROOF_FILL}" stroke="{ROOF_STROKE}" '
            f'stroke-width="2" rx="3"/>'
        )

        # Panele
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

            px = rx0 + px_m * SCALE
            # Frontend panelSvgY: Y jest odwrócone (y=0 backend = dół dachu w SVG)
            # panelYFromTop = roofHeightPx - panel.y * scale - panelHeightPx
            py = ry0 + (facet_l * SCALE - py_m * SCALE - ph_m * SCALE)
            pw = pw_m * SCALE
            ph = ph_m * SCALE

            # Prostokąt panelu
            out.append(
                f'<rect x="{px:.1f}" y="{py:.1f}" '
                f'width="{pw:.1f}" height="{ph:.1f}" '
                f'fill="{PANEL_FILL}" stroke="{PANEL_STR}" '
                f'stroke-width="1.2" opacity="0.92" rx="1"/>'
            )

            # Siatka komórek (3 kolumny × 6 wierszy jak w prawdziwym panelu)
            N_COL = 3; N_ROW = 6
            cw = pw / N_COL; ch = ph / N_ROW
            for ci in range(1, N_COL):
                lx = px + ci * cw
                out.append(
                    f'<line x1="{lx:.1f}" y1="{py:.1f}" '
                    f'x2="{lx:.1f}" y2="{py+ph:.1f}" '
                    f'stroke="white" stroke-width="0.4" opacity="0.5"/>'
                )
            for ri in range(1, N_ROW):
                ly = py + ri * ch
                out.append(
                    f'<line x1="{px:.1f}" y1="{ly:.1f}" '
                    f'x2="{px+pw:.1f}" y2="{ly:.1f}" '
                    f'stroke="white" stroke-width="0.4" opacity="0.5"/>'
                )

            # Numer panelu (maks 60 szt. jak w frontendzie)
            if idx < 60:
                tx = px + pw / 2
                ty = py + ph / 2
                fs = max(7, min(11, int(pw * 0.22)))
                out.append(
                    f'<text x="{tx:.1f}" y="{ty:.1f}" '
                    f'text-anchor="middle" dominant-baseline="middle" '
                    f'font-size="{fs}" font-weight="bold" fill="#333" '
                    f'font-family="{FONT}">{label}</text>'
                )

        # Wymiar poziomy (szerokość dachu)
        dim_y  = ry0 + roof_h + 20
        mx     = rx0 + roof_w / 2
        out.append(
            f'<line x1="{rx0:.1f}" y1="{dim_y}" '
            f'x2="{rx0+roof_w:.1f}" y2="{dim_y}" '
            f'stroke="{DIM_COLOR}" stroke-width="1.2" '
            f'marker-start="url(#as)" marker-end="url(#ae)"/>'
        )
        out.append(
            f'<text x="{mx:.1f}" y="{dim_y+13}" '
            f'text-anchor="middle" font-size="11" '
            f'font-weight="bold" fill="{DIM_COLOR}" '
            f'font-family="{FONT}">{facet_w:.1f} m</text>'
        )

        # Wymiar pionowy (długość dachu)
        dvx = rx0 - 22
        mvy = ry0 + roof_h / 2
        out.append(
            f'<line x1="{dvx}" y1="{ry0:.1f}" '
            f'x2="{dvx}" y2="{ry0+roof_h:.1f}" '
            f'stroke="{DIM_COLOR}" stroke-width="1.2" '
            f'marker-start="url(#as)" marker-end="url(#ae)"/>'
        )
        out.append(
            f'<text x="{dvx-5}" y="{mvy:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="11" font-weight="bold" fill="{DIM_COLOR}" '
            f'font-family="{FONT}" '
            f'transform="rotate(-90,{dvx-5},{mvy:.1f})">'
            f'{facet_l:.1f} m</text>'
        )

        # Napis z liczbą paneli i mocą
        header_y = ry0 - 12
        out.append(
            f'<text x="{rx0 + roof_w/2:.1f}" y="{header_y}" '
            f'text-anchor="middle" font-size="12" '
            f'font-weight="900" fill="{C_TEXT}" '
            f'font-family="{FONT}">'
            f'{panels_count} paneli · {total_kwp:.2f} kWp</text>'
        )

        # Róża wiatrów — identyczna z CompassRose z RoofVisualizer.jsx
        out.extend(self._svg_compass_rose(
            cx=cx_c, cy=cy_c, r=COMP_R,
            azimuth_deg=azimuth,
            dim_color=DIM_COLOR, red_color=C_RED, muted=MUTED, font=FONT
        ))

        out.append("</svg>")

        svg_str = "\n".join(out)
        return base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _svg_compass_rose(cx, cy, r, azimuth_deg,
                          dim_color, red_color, muted, font) -> list:
        """
        Róża wiatrów identyczna z CompassRose z RoofVisualizer.jsx.
        rotate = 180 - azimuth_deg (logika z frontendu).
        Ramię S (dół) = czerwone = kierunek połaci.
        """
        rotate = 180 - azimuth_deg
        arm = r * 0.78
        hw  = r * 0.22

        lines = [f'<g transform="rotate({rotate:.1f},{cx:.1f},{cy:.1f})">']

        # Krąg
        lines.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" '
            f'fill="white" stroke="{dim_color}" stroke-width="1.2" opacity="0.92"/>')

        # Ramię S — czerwone (kierunek połaci)
        lines.append(
            f'<polygon points="{cx:.1f},{cy+arm:.1f} '
            f'{cx-hw:.1f},{cy+2:.1f} {cx+hw:.1f},{cy+2:.1f}" '
            f'fill="{red_color}" opacity="0.9"/>')

        # Ramię N — ciemny
        lines.append(
            f'<polygon points="{cx:.1f},{cy-arm:.1f} '
            f'{cx-hw:.1f},{cy-2:.1f} {cx+hw:.1f},{cy-2:.1f}" '
            f'fill="{dim_color}" opacity="0.75"/>')

        # Ramię E — muted
        lines.append(
            f'<polygon points="{cx+arm:.1f},{cy:.1f} '
            f'{cx+2:.1f},{cy-hw:.1f} {cx+2:.1f},{cy+hw:.1f}" '
            f'fill="{muted}" opacity="0.5"/>')

        # Ramię W — muted
        lines.append(
            f'<polygon points="{cx-arm:.1f},{cy:.1f} '
            f'{cx-2:.1f},{cy-hw:.1f} {cx-2:.1f},{cy+hw:.1f}" '
            f'fill="{muted}" opacity="0.5"/>')

        # Środkowy punkt
        lines.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" '
            f'fill="white" stroke="{dim_color}" stroke-width="1.2"/>')

        # Etykiety kierunków (obracają się RAZEM z różą — jak w frontendzie)
        lines.append(
            f'<text x="{cx:.1f}" y="{cy-r-3:.1f}" '
            f'text-anchor="middle" font-size="7.5" font-weight="900" '
            f'fill="{dim_color}" font-family="{font}">N</text>')
        lines.append(
            f'<text x="{cx:.1f}" y="{cy+r+10:.1f}" '
            f'text-anchor="middle" font-size="7.5" font-weight="900" '
            f'fill="{red_color}" font-family="{font}">S</text>')
        lines.append(
            f'<text x="{cx+r+5:.1f}" y="{cy+2.5:.1f}" '
            f'text-anchor="start" font-size="6.5" font-weight="700" '
            f'fill="{muted}" font-family="{font}">E</text>')
        lines.append(
            f'<text x="{cx-r-5:.1f}" y="{cy+2.5:.1f}" '
            f'text-anchor="end" font-size="6.5" font-weight="700" '
            f'fill="{muted}" font-family="{font}">W</text>')

        lines.append("</g>")
        return lines

    @staticmethod
    def _roof_placeholder_svg() -> str:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="180">'
            '<rect width="400" height="180" fill="white"/>'
            '<text x="200" y="90" text-anchor="middle" dominant-baseline="middle" '
            'font-size="13" fill="#9ca3af" font-family="Arial, sans-serif">'
            'Brak danych o układzie paneli</text>'
            '</svg>'
        )
        return base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    # =========================================================================
    # METODA GŁÓWNA: generate()
    # =========================================================================

    def generate(self, report_data: ReportData) -> bytes:
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
                import traceback; traceback.print_exc()

        template = self.env.get_template("report/base.html")

        css_path    = os.path.join(self.static_dir, "report", "report.css")
        css_content = ""
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
        else:
            print(f"[ReportGenerator] CSS nie znaleziony: {css_path}")

        context = {
            "data":            report_data.input_data_summary,
            "req":             report_data.input_request,
            "standard":        std,
            "premium":         prem,
            "economy":         eco,
            "warnings":        report_data.warnings_and_confirmations,
            "charts":          charts,
            "generation_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "version":         "4.1.0",
            "css_content":     css_content,
        }

        rendered_html = template.render(**context)
        return HTML(string=rendered_html, base_url=self.base_dir).write_pdf()