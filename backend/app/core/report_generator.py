# backend/app/core/report_generator.py
"""
ReportGenerator v4.0 — PDF identyczny wizualnie z frontendem React/Recharts.

ZMIANY v4.0:
✅ Kolory 100% zsynchronizowane z EnergyFlowChart.jsx i EnergyCharts.jsx (CashflowChart25)
✅ _chart_monthly_balance()  — stacked bars jak Recharts, paleta frontendu
✅ _chart_cashflow_25()      — AreaChart z fill jak CashflowChart25, adnotacje identyczne
✅ _chart_daily_flow()       — ComposedChart: bars + linia SOC, paleta frontendu
✅ _chart_roof_panels()      — białe tło, bez zmian logiki
✅ Zero starych kolorów, zero fallbacków sinusoidalnych w ścieżce normalnej
✅ plt.rcParams: białe tło, siatka #e5e7eb, font DejaVu Sans (≈Inter)
"""

import os
import base64
from io import BytesIO
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ── Monkey-patch WeasyPrint / pydyf (kompatybilność wersji) ──────────────────
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
            set_text_matrix = getattr(self, "set_text_matrix", None)
            if callable(set_text_matrix):
                set_text_matrix(*values)
                return
            set_matrix = getattr(self, "set_matrix", None)
            Matrix = getattr(pydyf, "Matrix", None)
            if callable(set_matrix) and Matrix is not None:
                try:
                    set_matrix(Matrix(*values))
                except Exception:
                    pass
        pydyf.Stream.text_matrix = text_matrix
except ImportError:
    pass

from weasyprint import HTML, CSS
from app.schemas.report import ReportData

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import matplotlib.patches as mpatches
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[ReportGenerator] matplotlib niedostępny — wykresy zastąpione tabelami CSS")


# ── Globalna konfiguracja matplotlib — identyczna z wyglądem frontendu ────────
if MATPLOTLIB_AVAILABLE:
    plt.rcParams.update({
        "font.family":        "DejaVu Sans",
        "font.size":          9,
        "axes.titlesize":     11,
        "axes.titleweight":   "bold",
        "axes.titlecolor":    "#1f2937",      # text-gray-800 jak frontend
        "axes.labelsize":     8.5,
        "axes.labelcolor":    "#6b7280",      # text-gray-500
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.linewidth":     0.8,
        "axes.edgecolor":     "#e5e7eb",      # gray-200 jak CartesianGrid
        "axes.facecolor":     "white",        # białe tło jak Recharts
        "figure.facecolor":   "white",
        "grid.color":         "#e5e7eb",      # gray-200
        "grid.linewidth":     0.7,
        "grid.linestyle":     (0, (3, 3)),    # dasharray 3 3
        "grid.alpha":         1.0,
        "xtick.color":        "#6b7280",
        "ytick.color":        "#6b7280",
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        "legend.fontsize":    8.5,
        "legend.framealpha":  0.95,
        "legend.edgecolor":   "#e5e7eb",
        "legend.borderpad":   0.6,
        "legend.handlelength": 1.2,
        "legend.handleheight": 0.9,
    })


# ── Paleta kolorów — 1:1 z EnergyFlowChart.jsx i CashflowChart25 ─────────────

# EnergyFlowChart.jsx COLORS object:
C_PV         = "#D4AC0D"   # pv — złoty (identyczny z CashflowChart25 stroke)
C_GRID_IMP   = "#E57373"   # gridImport — pastelowy czerwony
C_CONSUMPTION= "#2E86C1"   # consumption — niebieski
C_BAT_CHARGE = "#66BB6A"   # batteryCharge — świeża zieleń
C_BAT_DISC   = "#A78BFA"   # batteryDischarge — lawendowy fiolet
C_SOC        = "#1B4F72"   # soc — ciemny błękit

# CashflowChart25 w EnergyCharts.jsx:
C_PV_STROKE  = "#D4AC0D"   # stroke PV curve
C_PV_FILL    = "#FEF9E7"   # fill PV area
C_BAT_STROKE = "#8b5cf6"   # stroke PV+battery curve
C_BAT_FILL   = "#f5f3ff"   # fill PV+battery area
C_ZERO_LINE  = "#94a3b8"   # zero reference line
C_PAYBACK    = "#1E8449"   # annotation "Zwrot w ~X. roku"

# Miesięczny bilans — z wymagań (spec w prompt):
C_AUTO       = "#22c55e"   # autokonsumpcja — zielony (Tailwind green-500)
C_SURPLUS    = "#facc15"   # nadwyżka do sieci — żółty (Tailwind yellow-400)
C_GRID_BAL   = "#ef4444"   # pobór z sieci — czerwony (Tailwind red-500)
C_DEMAND     = "#3b82f6"   # zapotrzebowanie (linia) — niebieski (Tailwind blue-500)

# Tekst i siatka
C_TEXT       = "#1f2937"   # gray-800
C_GRID_LINE  = "#e5e7eb"   # gray-200
C_TICK       = "#6b7280"   # gray-500


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
            return f"{int(value):,} zł".replace(",", " ")
        except (ValueError, TypeError):
            return "—"

    @staticmethod
    def _format_num(value, decimals=0):
        if value is None:
            return "—"
        try:
            if decimals == 0:
                return f"{int(value):,}".replace(",", " ")
            return f"{float(value):,.{decimals}f}".replace(",", " ").replace(".", ",")
        except (ValueError, TypeError):
            return "—"

    # ── Helper: fig → base64 PNG ──────────────────────────────────────────────

    @staticmethod
    def _fig_to_b64(fig) -> str:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=180, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    # ── Helper: styl osi identyczny z Recharts ────────────────────────────────

    @staticmethod
    def _style_ax(ax, title: str = None, xlabel: str = None, ylabel: str = None):
        """
        Styl osi 1:1 z Recharts:
        - białe tło
        - pozioma siatka #e5e7eb, dasharray 3 3
        - brak górnego i prawego spine
        - brak ticków
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
    # WYKRES 1: Miesięczny bilans energii
    # Odpowiednik: Recharts BarChart (stacked) + Line w frontendzie
    # =========================================================================

    def _chart_monthly_balance(self, std: dict) -> str:
        """
        Stacked bar chart: autokonsumpcja + nadwyżka | pobór z sieci
        Linia: zapotrzebowanie
        Kolory identyczne z frontendem (spec w prompt).
        """
        if not MATPLOTLIB_AVAILABLE:
            return ""

        MONTHS_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                     "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

        # ── Pobranie danych (priorytet: hourly_result_without_battery) ────────
        hr_no_batt = std.get("hourly_result_without_battery") or {}
        ef = hr_no_batt.get("energy_flow") or {}
        mp = ef.get("monthly_production_kwh") or []
        mc = ef.get("monthly_consumption_kwh") or []
        ma = ef.get("monthly_autoconsumption_kwh") or []

        if len(mp) != 12:
            hr_batt = std.get("hourly_result_with_battery") or {}
            ef2 = hr_batt.get("energy_flow") or {}
            mp = ef2.get("monthly_production_kwh") or []
            mc = ef2.get("monthly_consumption_kwh") or []
            ma = ef2.get("monthly_autoconsumption_kwh") or []

        # Uzupełnienie autokonsumpcji z net_billing jeśli brak
        if len(ma) != 12 and len(mp) == 12:
            nb = (hr_no_batt.get("net_billing")
                  or (std.get("hourly_result_with_battery") or {}).get("net_billing") or {})
            ms = nb.get("monthly_surplus_kwh") or {}
            if ms:
                surplus_list = [float(ms.get(i, 0)) for i in range(1, 13)]
                ma = [max(0.0, p - s) for p, s in zip(mp, surplus_list)]

        # Fallback na wagi sezonowe gdy brak danych
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

        fig, ax = plt.subplots(figsize=(11, 4.2), facecolor="white")
        self._style_ax(ax, ylabel="kWh / miesiąc")

        # ── Stacked bary produkcji: autokonsumpcja + nadwyżka (jak Recharts) ──
        ax.bar(x - bw / 2, ma,      width=bw,
               label="Autokonsumpcja",   color=C_AUTO,    zorder=3,
               linewidth=0, alpha=0.92)
        ax.bar(x - bw / 2, surplus, width=bw,
               label="Nadwyżka do sieci", color=C_SURPLUS, zorder=3,
               linewidth=0, alpha=0.92, bottom=ma)

        # ── Słupek poboru z sieci ─────────────────────────────────────────────
        ax.bar(x + bw / 2, grid, width=bw,
               label="Pobór z sieci", color=C_GRID_BAL, zorder=3,
               linewidth=0, alpha=0.88)

        # ── Linia zapotrzebowania (identyczna z Recharts Line) ────────────────
        ax.plot(x, mc, color=C_DEMAND, linewidth=2.0,
                marker="o", markersize=4.0, markerfacecolor="white",
                markeredgewidth=1.5, markeredgecolor=C_DEMAND,
                label="Zapotrzebowanie", zorder=5, solid_capstyle="round")

        ax.set_xticks(x)
        ax.set_xticklabels(MONTHS_PL, fontsize=8.5, color=C_TICK)
        ax.set_xlim(-0.65, 11.65)

        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"{int(v):,}".replace(",", " ")))

        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.13),
            ncol=4,
            frameon=False,
            fontsize=8.5,
            handlelength=1.2,
            handleheight=0.9,
        )

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 2: Prognoza zysku netto (25 lat)
    # Odpowiednik: CashflowChart25 w EnergyCharts.jsx (Recharts AreaChart)
    # =========================================================================

    def _chart_cashflow_25(self, std: dict) -> str:
        """
        Krzywe kumulatywnych zysków przez 25 lat z inflacją +4%/rok.
        Logika obliczeń identyczna z CashflowChart25 w React.
        Styl: AreaChart z fill — identyczny z Recharts.
        """
        if not MATPLOTLIB_AVAILABLE:
            return ""

        pv_cost   = std.get("pv_cost_gross_pln") or 0
        bat_cost  = (std.get("with_battery_total_cost_pln")
                     or std.get("total_cost_with_battery_pln") or 0)
        pv_annual = std.get("pv_savings_pln") or 0
        bat_annual= std.get("total_savings_with_battery_pln") or 0
        has_bat   = bat_annual > 0 and bat_cost > 0

        # ── Obliczenia jak w CashflowChart25 (React) ─────────────────────────
        lata     = list(range(1, 26))
        pv_cum   = []
        bat_cum  = []
        pv_net   = -pv_cost
        bat_net  = (-bat_cost) if has_bat else None

        for y in lata:
            factor  = (1.04 ** (y - 1))
            pv_net += pv_annual * factor
            pv_cum.append(round(pv_net))
            if has_bat and bat_net is not None:
                bat_net += bat_annual * factor
                bat_cum.append(round(bat_net))

        # Rok zwrotu — pierwsza wartość ≥ 0 (identycznie jak React .find())
        payback_yr = next((y for y, v in zip(lata, pv_cum) if v >= 0), None)

        fig, ax = plt.subplots(figsize=(11, 4.0), facecolor="white")
        self._style_ax(ax, xlabel="Rok", ylabel="Zysk netto (PLN)")

        x = np.array(lata)

        # ── Obszar PV (fill identyczny z Recharts Area) ───────────────────────
        ax.fill_between(x, pv_cum, 0,
                        where=[v >= 0 for v in pv_cum],
                        color=C_PV_FILL, alpha=1.0, zorder=1)
        ax.fill_between(x, pv_cum, 0,
                        where=[v < 0 for v in pv_cum],
                        color="#FEF9E7", alpha=0.5, zorder=1)
        ax.plot(x, pv_cum,
                color=C_PV_STROKE, linewidth=2.5, zorder=4,
                solid_capstyle="round", label="Tylko PV")

        # ── Obszar PV + Magazyn ───────────────────────────────────────────────
        if has_bat and bat_cum:
            ax.fill_between(x, bat_cum, 0,
                            where=[v >= 0 for v in bat_cum],
                            color=C_BAT_FILL, alpha=1.0, zorder=1)
            ax.fill_between(x, bat_cum, 0,
                            where=[v < 0 for v in bat_cum],
                            color=C_BAT_FILL, alpha=0.4, zorder=1)
            ax.plot(x, bat_cum,
                    color=C_BAT_STROKE, linewidth=2.5, zorder=4,
                    solid_capstyle="round", label="PV + Magazyn")

        # ── Linia zerowa (próg zwrotu) — identyczna z Recharts ReferenceLine ──
        ax.axhline(0,
                   color=C_ZERO_LINE, linewidth=1.5,
                   linestyle=(0, (4, 2)), zorder=3)
        ax.text(1.0, 0, "próg zwrotu",
                fontsize=7.5, color=C_ZERO_LINE,
                va="bottom", ha="left")

        # ── Adnotacja roku zwrotu — identyczna z badge w React ────────────────
        if payback_yr:
            ax.axvline(payback_yr,
                       color=C_PAYBACK, linewidth=1.2,
                       linestyle=":", alpha=0.85, zorder=3)
            ax.text(payback_yr + 0.3,
                    max(pv_cum) * 0.08,
                    f"Zwrot w ~{payback_yr}. roku",
                    fontsize=8.5, color=C_PAYBACK,
                    fontweight="bold", va="bottom")

        # ── Oś X — lata 1–25, tick co 4 lata (identycznie jak Recharts) ──────
        x_ticks = [1] + list(range(4, 26, 4)) + [25]
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([str(t) for t in x_ticks], fontsize=8, color=C_TICK)
        ax.set_xlim(0.5, 25.5)

        # ── Oś Y — formatowanie w tysiącach (10k, 20k …) ─────────────────────
        def _fmt_k(v, _):
            if v == 0:
                return "0"
            if abs(v) >= 1000:
                return f"{int(v / 1000)}k"
            return f"{int(v)}"

        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_k))

        ax.legend(
            loc="upper left",
            frameon=True,
            edgecolor=C_GRID_LINE,
            fontsize=8.5,
            handlelength=1.4,
        )

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 3: Dobowy przepływ energii (lato + zima)
    # Odpowiednik: EnergyFlowChart.jsx (Recharts ComposedChart: Bar + Line)
    # =========================================================================

    def _chart_daily_flow(self, std: dict) -> str:
        """
        ComposedChart: słupki (PV, ładowanie, rozładowanie baterii,
        pobór z sieci, zużycie domu) + linia SOC.
        Układ dwupanelowy: lato | zima.
        Kolory 100% identyczne z EnergyFlowChart.jsx COLORS.
        """
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

        # ── Ekstrakcja serii godzinowych ──────────────────────────────────────
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

        # Letnie serie
        has_s = len(summer) >= 24
        s_pv   = extract(summer, "pv", "pv_production") if has_s else None
        s_cons = extract(summer, "consumption")          if has_s else None
        s_grid = extract(summer, "gridImport", "grid_import") if has_s else None
        s_bchg = extract(summer, "batteryCharge")        if has_s else None
        s_bdis = extract(summer, "batteryDischarge")     if has_s else None
        s_soc  = extract(summer, "soc")                  if has_s else None

        # Zimowe serie
        has_w = len(winter) >= 24
        w_pv   = extract(winter, "pv", "pv_production") if has_w else None
        w_cons = extract(winter, "consumption")          if has_w else None
        w_grid = extract(winter, "gridImport", "grid_import") if has_w else None
        w_bchg = extract(winter, "batteryCharge")        if has_w else None
        w_bdis = extract(winter, "batteryDischarge")     if has_w else None
        w_soc  = extract(winter, "soc")                  if has_w else None

        # Fallback TYLKO gdy seasonal_charts jest kompletnie niedostępny
        if s_pv is None:
            s_pv = pad24([0.0]*6 + [peak_pv*f for f in
                         [.08,.22,.42,.62,.80,.92,1.,.98,.88,.72,.52,.30,.06]]
                         + [0.0]*5)
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

        # Sprawdź czy w ogóle jest bateria
        has_battery = (
            (s_bchg and any(v > 0 for v in s_bchg)) or
            (s_bdis and any(v > 0 for v in s_bdis)) or
            (w_bchg and any(v > 0 for v in w_bchg))
        )

        # ── Figura dwupanelowa ────────────────────────────────────────────────
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), facecolor="white",
                                 sharey=False)

        x     = np.arange(24)
        hours = [f"{h:02d}:00" for h in range(24)]

        panels = [
            (axes[0], s_pv, s_cons, s_grid, s_bchg, s_bdis, s_soc,
             "☀  Szczyt letni (Czerwiec)"),
            (axes[1], w_pv, w_cons, w_grid, w_bchg, w_bdis, w_soc,
             "❄  Minimum zimowe (Styczeń)"),
        ]

        for (ax, pv, cons, grid, bchg, bdis, soc, title) in panels:
            self._style_ax(ax, title=title, ylabel="kW")

            # Odpowiada Recharts Bar (stackId="supply"):
            #   PV i pobór z sieci są osobnymi grupami (nie stack) w frontendzie
            #   Zużycie domu osobny słupek — opacity 0.8
            bw = 0.22

            # Bar: Produkcja PV
            ax.bar(x - bw * 1.5, pv, width=bw,
                   color=C_PV, label="Produkcja PV",
                   zorder=3, linewidth=0, alpha=0.92)

            # Bar: Pobór z sieci
            ax.bar(x - bw * 0.5, grid, width=bw,
                   color=C_GRID_IMP, label="Pobór z sieci",
                   zorder=3, linewidth=0, alpha=0.88)

            # Bar: Zużycie domu
            ax.bar(x + bw * 0.5, cons, width=bw,
                   color=C_CONSUMPTION, label="Zużycie domu",
                   zorder=3, linewidth=0, alpha=0.80)

            if has_battery:
                # Bar: Ładowanie baterii
                ax.bar(x + bw * 1.5,
                       pad24(bchg) if bchg else [0.0]*24,
                       width=bw,
                       color=C_BAT_CHARGE, label="Ładowanie bat.",
                       zorder=3, linewidth=0, alpha=0.92)
                ax.bar(x + bw * 2.5,
                       pad24(bdis) if bdis else [0.0]*24,
                       width=bw,
                       color=C_BAT_DISC, label="Rozładowanie bat.",
                       zorder=3, linewidth=0, alpha=0.92)

            # Oś X: godziny 00:00, 03:00, … (co 3)
            ax.set_xticks(range(0, 24, 3))
            ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)],
                               fontsize=7.5, color=C_TICK)
            ax.set_xlim(-0.8, 23.8)

            # Linia SOC (prawa oś) — dashed, strokeWidth 1.8
            # Odpowiada: Line yAxisId="right" strokeDasharray="4 2" strokeWidth={2.5}
            if has_battery and soc and any(v > 0 for v in soc):
                ax_r = ax.twinx()
                ax_r.plot(x, soc,
                          color=C_SOC, linewidth=1.8,
                          linestyle=(0, (4, 2)),
                          label="Stan baterii (%)",
                          zorder=5)
                ax_r.set_ylim(0, 130)
                ax_r.set_yticks([0, 25, 50, 75, 100])
                ax_r.set_yticklabels(["0%", "25%", "50%", "75%", "100%"],
                                     fontsize=7, color=C_SOC)
                ax_r.spines["top"].set_visible(False)
                ax_r.spines["right"].set_color(C_GRID_LINE)
                ax_r.tick_params(axis="y", which="both", length=0)

            ax.legend(
                fontsize=7.5,
                frameon=True,
                edgecolor=C_GRID_LINE,
                loc="upper right",
                handlelength=1.2,
            )

        fig.tight_layout(pad=1.2, w_pad=2.0)
        return self._fig_to_b64(fig)

    # =========================================================================
    # WYKRES 4: Schemat dachu z panelami
    # Niezmieniony layoutem — białe tło, brak starych kolorów
    # =========================================================================

    def _chart_roof_panels(self, std: dict, request) -> str:
        """
        Schemat 2D rozmieszczenia paneli na dachu.
        Bazuje na facet_layouts z ScenarioResult.
        Tło dachu: #ECF0F1 (jak frontend). Panel: ciemnogranatowy #1B2A3B.
        """
        if not MATPLOTLIB_AVAILABLE:
            return ""

        facet_layouts = std.get("facet_layouts") or []
        if not facet_layouts:
            return ""

        panels_count = std.get("panels_count") or 0
        total_kwp    = std.get("peak_power_kwp") or 0.0

        # ── Wybieramy pierwszą połać (największą lub pierwszą w liście) ───────
        facet = facet_layouts[0]
        if len(facet_layouts) > 1:
            facet = max(facet_layouts,
                        key=lambda f: f.get("area_m2", 0) or 0)

        panel_positions = facet.get("panel_positions") or []
        if not panel_positions:
            return ""

        facet_w = facet.get("width_m")  or facet.get("facet_w") or 10.0
        facet_l = facet.get("length_m") or facet.get("facet_l") or 5.0

        panel_w = facet.get("panel_w") or 1.134
        panel_h = facet.get("panel_h") or 1.762
        GAP     = 0.05

        ROOF_COLOR  = "#ECF0F1"
        PANEL_COLOR = "#1B2A3B"
        GRID_COLOR  = "#4A90D9"
        DIM_COLOR   = "#5D6D7E"
        TEXT_COLOR  = C_TEXT

        CELLS_H = 6
        CELLS_V = 10

        cell_w = panel_w / CELLS_H
        cell_h = panel_h / CELLS_V

        margin = 0.5
        fig_w = facet_w + 2 * margin + 0.8
        fig_h = facet_l + 2 * margin + 0.6
        fig, ax = plt.subplots(figsize=(min(fig_w, 12), min(fig_h, 7)),
                               facecolor="white")
        ax.set_facecolor("white")

        # Tło dachu
        roof_rect = plt.Rectangle(
            (0, 0), facet_w, facet_l,
            linewidth=1.0, edgecolor="#BDC3C7",
            facecolor=ROOF_COLOR, zorder=1)
        ax.add_patch(roof_rect)

        # Rysowanie paneli
        for pos in panel_positions:
            x = pos.get("x", 0)
            y = pos.get("y", 0)

            panel_rect = plt.Rectangle(
                (x, y), panel_w, panel_h,
                linewidth=0.3, edgecolor="#0A1628",
                facecolor=PANEL_COLOR, zorder=2)
            ax.add_patch(panel_rect)

            # Siatka komórek (busbary)
            for ri in range(1, CELLS_H):
                ax.plot([x + ri * cell_w, x + ri * cell_w],
                        [y, y + panel_h],
                        color="white", linewidth=0.25, alpha=0.4, zorder=3)
            for ci in range(1, CELLS_V):
                ax.plot([x, x + panel_w],
                        [y + ci * cell_h, y + ci * cell_h],
                        color="white", linewidth=0.25, alpha=0.4, zorder=3)

        # Wymiary strzałkowe
        arrowstyle = dict(arrowstyle="<->", color=DIM_COLOR,
                          lw=1.0, mutation_scale=8)

        ax.annotate("", xy=(facet_w, -0.30), xytext=(0, -0.30),
                    arrowprops=arrowstyle)
        ax.text(facet_w / 2, -0.44, f"{facet_w:.1f} m",
                ha="center", va="top", fontsize=7.5,
                color=DIM_COLOR, fontweight="bold")

        ax.annotate("", xy=(facet_w + 0.28, facet_l),
                    xytext=(facet_w + 0.28, 0),
                    arrowprops=arrowstyle)
        ax.text(facet_w + 0.44, facet_l / 2, f"{facet_l:.1f} m",
                ha="left", va="center", fontsize=7.5,
                color=DIM_COLOR, fontweight="bold", rotation=90)

        ax.text(facet_w / 2, facet_l + 0.18,
                f"{panels_count} paneli · {total_kwp:.2f} kWp",
                ha="center", va="bottom", fontsize=9,
                color=TEXT_COLOR, fontweight="black")

        ax.set_xlim(-margin, facet_w + margin + 0.6)
        ax.set_ylim(-margin - 0.2, facet_l + margin + 0.3)
        ax.set_aspect("equal")
        ax.axis("off")

        fig.tight_layout(pad=0.3)
        return self._fig_to_b64(fig)

    # =========================================================================
    # METODA GŁÓWNA: generate()
    # =========================================================================

    def generate(self, report_data: ReportData) -> bytes:
        """
        Generuje PDF raportu fotowoltaicznego.
        Wszystkie wykresy odwzorowują frontend 1:1 wizualnie.
        """
        std  = report_data.all_scenarios_results.get("standard") or {}
        eco  = report_data.all_scenarios_results.get("economy")  or {}
        prem = report_data.all_scenarios_results.get("premium")  or {}

        charts = {}

        try:
            charts["monthly_balance"] = self._chart_monthly_balance(std)
        except Exception as e:
            print(f"[ReportGenerator] CHART monthly_balance error: {e}")
            import traceback; traceback.print_exc()

        try:
            # Nowy wykres cashflow_25 zastępuje stary "payback"
            charts["payback"] = self._chart_cashflow_25(std)
        except Exception as e:
            print(f"[ReportGenerator] CHART cashflow_25 error: {e}")
            import traceback; traceback.print_exc()

        try:
            charts["daily_flow"] = self._chart_daily_flow(std)
        except Exception as e:
            print(f"[ReportGenerator] CHART daily_flow error: {e}")
            import traceback; traceback.print_exc()

        try:
            charts["roof_panels"] = self._chart_roof_panels(
                std, report_data.input_request)
        except Exception as e:
            print(f"[ReportGenerator] CHART roof_panels error: {e}")
            import traceback; traceback.print_exc()

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
            "version":         "4.0.0",
            "css_content":     css_content,
        }

        rendered_html = template.render(**context)

        pdf_bytes = HTML(
            string=rendered_html,
            base_url=self.base_dir,
        ).write_pdf()
        return pdf_bytes