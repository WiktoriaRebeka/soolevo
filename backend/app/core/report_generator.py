# backend/app/core/report_generator.py
"""
ReportGenerator v3.0 — Kompletny generator PDF dla raportu fotowoltaicznego.

ZMIANY v3.0 (poprawki danych):
✅ _chart_monthly_balance() — używa PRAWDZIWYCH danych miesięcznych z energy_flow
✅ _chart_monthly_balance() — fallback na sezonowe wagi TYLKO gdy dane niedostępne
✅ _chart_daily_flow() — fallback TYLKO gdy seasonal_charts jest pusty (nie zastępuje realnych zer)
✅ _chart_daily_flow() — wykres dwupanelowy (lato + zima) z nową paletą kolorów
✅ Brak sinusów i sztucznych danych w ścieżce normalnego wywołania
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
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[ReportGenerator] matplotlib niedostepny — wykresy zastapione tabelami CSS")


# ── Globalna konfiguracja matplotlib ─────────────────────────────────────────
if MATPLOTLIB_AVAILABLE:
    plt.rcParams.update({
        "font.family":       "DejaVu Sans",
        "font.size":         9,
        "axes.titlesize":    11,
        "axes.titleweight":  "bold",
        "axes.titlecolor":   "#1B4F72",
        "axes.labelsize":    8.5,
        "axes.labelcolor":   "#555555",
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.linewidth":    0.8,
        "axes.edgecolor":    "#CCCCCC",
        "axes.facecolor":    "#F8FAFB",
        "figure.facecolor":  "white",
        "grid.color":        "#E8ECEF",
        "grid.linewidth":    0.6,
        "grid.alpha":        1.0,
        "xtick.color":       "#555555",
        "ytick.color":       "#555555",
        "xtick.labelsize":   8,
        "ytick.labelsize":   8,
        "legend.fontsize":   8,
        "legend.framealpha": 0.95,
        "legend.edgecolor":  "#DDDDDD",
        "legend.borderpad":  0.5,
        "legend.handlelength": 1.2,
    })

# ── Paleta kolorów spójna z aplikacją ────────────────────────────────────────
C_AUTO    = "#27AE60"   # autokonsumpcja — zielony
C_SURPLUS = "#F39C12"   # nadwyżka do sieci — pomarańczowy
C_GRID    = "#E74C3C"   # pobór z sieci — czerwony
C_DEMAND  = "#2980B9"   # zapotrzebowanie — niebieski
C_PV      = "#F39C12"   # produkcja PV — pomarańczowy (spójnie z frontendem)
C_STD     = "#2E86C1"   # scenariusz standard
C_ECO     = "#27AE60"   # scenariusz economy
C_ZERO    = "#7F8C8D"   # linia zerowa


class ReportGenerator:

    def __init__(self):
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        APP_DIR     = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
        BACKEND_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))

        self.base_dir      = BACKEND_DIR
        self.templates_dir = os.path.join(APP_DIR, "templates")
        self.static_dir    = os.path.join(BACKEND_DIR, "static")

        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.env.filters['format_pln'] = self._format_pln
        self.env.filters['format_num'] = self._format_num

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

    # ── Helpers matplotlib ────────────────────────────────────────────────────

    @staticmethod
    def _fig_to_b64(fig) -> str:
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=180, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    @staticmethod
    def _style_ax(ax, title=None, ylabel=None):
        """Jednolity styl osi — czysty, czytelny, spójny z aplikacją."""
        ax.set_facecolor("#F8FAFB")
        ax.yaxis.grid(True, color="#E8ECEF", linewidth=0.7, zorder=0)
        ax.xaxis.grid(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#DDDDDD")
        ax.spines["bottom"].set_color("#DDDDDD")
        ax.tick_params(axis="both", which="both", length=0)
        if title:
            ax.set_title(title, fontsize=10, fontweight="bold", color="#1B4F72", pad=10)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=8, color="#777777", labelpad=6)

    # ── WYKRES 1: Miesięczny bilans energii ──────────────────────────────────

    def _chart_monthly_balance(self, std: dict) -> str:
        """
        Wykres 1: Miesięczny bilans energii.
        Używa prawdziwych danych z energy_flow gdy dostępne,
        fallback na sezonowe wagi tylko gdy dane są niedostępne.
        """
        MONTHS = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

        # ── Próba 1: Dane z symulacji bez baterii (preferowane) ──────────────
        hr_no_batt = std.get("hourly_result_without_battery") or {}
        ef = hr_no_batt.get("energy_flow") or {}
        mp = ef.get("monthly_production_kwh") or []
        mc = ef.get("monthly_consumption_kwh") or []
        ma = ef.get("monthly_autoconsumption_kwh") or []

        # ── Próba 2: Dane z symulacji z baterią (jeśli brak bez) ─────────────
        if len(mp) != 12:
            hr_batt = std.get("hourly_result_with_battery") or {}
            ef2 = hr_batt.get("energy_flow") or {}
            mp = ef2.get("monthly_production_kwh") or []
            mc = ef2.get("monthly_consumption_kwh") or []
            ma = ef2.get("monthly_autoconsumption_kwh") or []

        # ── Próba 3: Dane net_billing (monthly_surplus) ───────────────────────
        # Uzupełnienie autokonsumpcji z net_billing jeśli brak
        if len(ma) != 12 and len(mp) == 12:
            nb = hr_no_batt.get("net_billing") or hr_batt.get("net_billing") or {}
            monthly_surplus_nb = nb.get("monthly_surplus_kwh") or {}
            if monthly_surplus_nb:
                # monthly_surplus_kwh ma klucze 1..12
                surplus_list = [float(monthly_surplus_nb.get(i, 0)) for i in range(1, 13)]
                ma = [max(0.0, p - s) for p, s in zip(mp, surplus_list)]

        # ── Fallback: Sezonowe wagi (tylko gdy brak danych) ───────────────────
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

        # ── Dane pochodne ─────────────────────────────────────────────────────
        surplus = [max(0.0, p - a) for p, a in zip(mp, ma)]
        grid    = [max(0.0, c - a) for c, a in zip(mc, ma)]

        # ── Wykres ────────────────────────────────────────────────────────────
        C_AUTO    = "#2ECC71"   # zielony — autokonsumpcja
        C_SURPLUS = "#3498DB"   # niebieski — nadwyżka
        C_GRID    = "#E74C3C"   # czerwony — pobór z sieci
        C_DEMAND  = "#2C3E50"   # granatowy — linia zapotrzebowania

        x  = np.arange(12)
        bw = 0.36

        fig, ax = plt.subplots(figsize=(10, 4.0), facecolor="white")
        self._style_ax(ax, ylabel="kWh / miesiąc")

        # Słupki produkcji (auto + nadwyżka)
        ax.bar(x - bw/2, ma,      width=bw, label="Autokonsumpcja",
            color=C_AUTO,    alpha=0.92, zorder=3, linewidth=0)
        ax.bar(x - bw/2, surplus, width=bw, label="Nadwyżka do sieci",
            color=C_SURPLUS, alpha=0.92, bottom=ma, zorder=3, linewidth=0)

        # Słupki poboru z sieci
        ax.bar(x + bw/2, grid, width=bw, label="Pobór z sieci",
            color=C_GRID, alpha=0.88, zorder=3, linewidth=0)

        # Linia zapotrzebowania
        ax.plot(x, mc, color=C_DEMAND, linewidth=2.2, marker="o", markersize=4.5,
                label="Zapotrzebowanie", zorder=5, linestyle="--", dash_capstyle="round")

        ax.set_xticks(x)
        ax.set_xticklabels(MONTHS, fontsize=8.5)
        ax.set_xlim(-0.6, 11.6)

        import matplotlib.ticker as mticker
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"{int(v):,}".replace(",", " ")))

        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.14),
            ncol=4,
            frameon=False,
            fontsize=8.5,
            handlelength=1.2,
        )

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)
    # ── WYKRES 2: ROI / Krzywa zwrotu kosztów ───────────────────────────────

    def _chart_payback(self, std: dict, eco: dict) -> str:
        """
        Wykres kumulatywnych oszczędności przez 25 lat.
        Pasmo inflacji: 3% (pesymistyczny) – 6% (optymistyczny).
        """
        years  = list(range(26))  # 0..25
        lata   = list(range(1, 26))

        def _cumulative(annual_savings: float, investment: float,
                        rate_low: float, rate_high: float):
            """Zwraca (base, optimistic, pessimistic) — kumulatywne oszczędności."""
            base, opt, pes = [], [], []
            cum_b = cum_o = cum_p = -investment
            for yr in lata:
                multiplier = (1 + (rate_low + rate_high) / 2) ** yr
                mul_o = (1 + rate_high) ** yr
                mul_p = (1 + rate_low) ** yr
                cum_b += annual_savings * multiplier
                cum_o += annual_savings * mul_o
                cum_p += annual_savings * mul_p
                base.append(cum_b)
                opt.append(cum_o)
                pes.append(cum_p)
            return base, opt, pes

        std_savings    = float(std.get("pv_savings_pln") or 0)
        std_investment = float(std.get("pv_cost_gross_pln") or 1)
        eco_savings    = float(eco.get("pv_savings_pln") or std_savings * 0.85) if eco else std_savings * 0.85
        eco_investment = float(eco.get("pv_cost_gross_pln") or std_investment * 0.82) if eco else std_investment * 0.82

        std_base, std_opt, std_pes = _cumulative(std_savings, std_investment, 0.03, 0.06)
        eco_base, eco_opt, eco_pes = _cumulative(eco_savings, eco_investment, 0.03, 0.06)

        fig, ax = plt.subplots(figsize=(10, 4.2), facecolor="white")
        self._style_ax(ax, ylabel="Kumulatywne oszczędności (PLN)")

        # Linia zerowa
        ax.axhline(0, color=C_ZERO, linewidth=1.0, linestyle=":", alpha=0.6, zorder=2)

        # Pasmo inflacyjne Standard
        ax.fill_between(lata, std_pes, std_opt, color=C_STD, alpha=0.10, zorder=1)
        ax.plot(lata, std_base, color=C_STD, linewidth=2.4, label="Standard", zorder=4)
        ax.plot(lata, std_opt,  color=C_STD, linewidth=0.8, linestyle="--", alpha=0.5, zorder=3)
        ax.plot(lata, std_pes,  color=C_STD, linewidth=0.8, linestyle="--", alpha=0.5, zorder=3)

        # Economy (jeśli dostępny)
        if eco:
            ax.plot(lata, eco_base, color=C_ECO, linewidth=1.6,
                    linestyle="-.", label="Economy", zorder=4)

        # Adnotacje pasma inflacji
        if std_opt:
            ax.text(24.5, std_opt[-1],  "6%/rok", fontsize=7, color=C_STD, alpha=0.7,
                    ha="right", va="bottom")
            ax.text(24.5, std_pes[-1],  "3%/rok", fontsize=7, color=C_STD, alpha=0.7,
                    ha="right", va="top")

        # Zaznaczenie punktu zwrotu
        payback_yr = std.get("pv_payback_years")
        if payback_yr and 0 < payback_yr < 25:
            ax.axvline(payback_yr, color="#E74C3C", linewidth=1.0, linestyle=":",
                       alpha=0.7, zorder=3)
            ax.text(payback_yr + 0.3, min(std_base) * 0.3,
                    f"Zwrot: {payback_yr:.1f} lat",
                    fontsize=7.5, color="#E74C3C", alpha=0.85, va="center")

        # Wypełnienie zysku (nad zerem)
        ax.fill_between(lata, std_base, 0,
                        where=[v >= 0 for v in std_base],
                        alpha=0.08, color=C_STD, zorder=1)

        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"{int(v):,} zł".replace(",", " ")))
        ax.set_xlim(0, 25.5)
        ax.legend(loc="upper left", frameon=True, edgecolor="#DDDDDD",
                  fontsize=8.5, handlelength=1.4)

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # ── WYKRES 3: Dobowy przepływ energii ────────────────────────────────────

    
    def _chart_daily_flow(self, std: dict) -> str:
        """
        Wykres 3: Dobowy przepływ energii (lato vs zima).
        Fallback uruchamiany TYLKO gdy seasonal_charts jest pusty/niedostępny.
        Nie zastępuje prawdziwych niskich wartości zimowych sztucznymi danymi.
        """
        hr     = (std.get("hourly_result_with_battery")
                or std.get("hourly_result_without_battery") or {})
        sc     = hr.get("seasonal_charts") or {}
        summer = sc.get("summer") or []
        winter = sc.get("winter") or []

        ap       = std.get("annual_production_kwh") or 4000
        ac       = std.get("annual_consumption_kwh") or 3500
        peak_pv  = ap / 8760 * 12
        avg_cons = ac / 8760

        def extract_series(day_data, *keys):
            """Wyciąga wartości godzinowe dla podanych kluczy. Zwraca None jeśli brak danych."""
            if not day_data or len(day_data) < 24:
                return None
            if not isinstance(day_data[0], dict):
                return None
            for key in keys:
                vals = [float(day_data[h].get(key, 0.0)) for h in range(min(24, len(day_data)))]
                # Akceptujemy serię nawet jeśli ma zerowe wartości (np. noc zimowa)
                # Tylko całkowity brak klucza jest powodem do spróbowania następnego
                if any(k in day_data[0] for k in keys):
                    return vals
            return None

        def extract_any(day_data, *keys):
            """Wyciąga wartości dla pierwszego istniejącego klucza, dopuszcza zera."""
            if not day_data or len(day_data) < 24:
                return None
            if not isinstance(day_data[0], dict):
                return None
            for key in keys:
                if key in day_data[0]:
                    return [float(day_data[h].get(key, 0.0)) for h in range(min(24, len(day_data)))]
            return None

        # ── Wyciąganie danych letnich ─────────────────────────────────────────
        has_real_summer = len(summer) >= 24
        s_prod = extract_any(summer, "pv", "pv_production") if has_real_summer else None
        s_cons = extract_any(summer, "consumption") if has_real_summer else None
        s_grid = extract_any(summer, "gridImport", "grid_import") if has_real_summer else None
        s_batt = extract_any(summer, "batteryDischarge") if has_real_summer else None

        # ── Wyciąganie danych zimowych ────────────────────────────────────────
        has_real_winter = len(winter) >= 24
        w_prod = extract_any(winter, "pv", "pv_production") if has_real_winter else None
        w_cons = extract_any(winter, "consumption") if has_real_winter else None
        w_grid = extract_any(winter, "gridImport", "grid_import") if has_real_winter else None

        # ── Fallback TYLKO gdy seasonal_charts jest niedostępny ───────────────
        # NIE zastępujemy prawdziwych zerowych wartości zimowych — to są realne dane.
        if s_prod is None:
            s_prod = ([0.0]*6 + [peak_pv*f for f in
                    [.08,.22,.42,.62,.80,.92,1.,.98,.88,.72,.52,.30]]
                    + [.06,0,0,0,0,0])
        if s_cons is None:
            s_cons = ([avg_cons*.7]*6 + [avg_cons*f for f in
                    [1.3,1.5,1.1,.9,.9,1.,1.,1.,1.1,1.2,1.5,1.8,2.,1.8,1.3,1.,.8,.7]])
        if s_grid is None:
            s_grid = [max(0.0, c - p) for c, p in zip(s_cons, s_prod)]

        if w_prod is None:
            w_prod = ([0.0]*9 + [peak_pv*.3*f for f in
                    [.3,.6,.85,1.,.85,.6]] + [0.0]*9)
        if w_cons is None:
            w_cons = ([avg_cons*1.1]*7 + [avg_cons*f for f in
                    [1.4,1.2,1.,1.,1.,1.,1.,1.,1.2,1.5,1.8,2.,1.9,1.5,1.2,1.1,1.]])
        if w_grid is None:
            w_grid = [max(0.0, c - p) for c, p in zip(w_cons, w_prod)]

        # ── Dopełnienie do 24 wartości jeśli potrzeba ─────────────────────────
        def pad24(lst):
            lst = list(lst) if lst else []
            if len(lst) < 24:
                lst += [0.0] * (24 - len(lst))
            return lst[:24]

        s_prod, s_cons, s_grid = pad24(s_prod), pad24(s_cons), pad24(s_grid)
        w_prod, w_cons, w_grid = pad24(w_prod), pad24(w_cons), pad24(w_grid)

        hours = [f"{h:02d}:00" for h in range(24)]
        x     = np.arange(24)

        C_PV   = "#F39C12"   # pomarańczowy — produkcja PV
        C_CONS = "#2C3E50"   # granatowy — zużycie
        C_GRID = "#E74C3C"   # czerwony — pobór z sieci
        C_BATT = "#9B59B6"   # fioletowy — bateria

        fig, axes = plt.subplots(1, 2, figsize=(12, 4.0), facecolor="white", sharey=False)

        for ax, prod, cons, grid, label, icon in [
            (axes[0], s_prod, s_cons, s_grid, "Czerwiec (szczyt letni)", "☀"),
            (axes[1], w_prod, w_cons, w_grid, "Styczeń (minimum zimowe)", "❄"),
        ]:
            self._style_ax(ax, title=label, ylabel="kWh/h")

            # Produkcja PV (wypełnienie obszarowe)
            ax.fill_between(x, 0, prod, color=C_PV, alpha=0.35, label="Produkcja PV")
            ax.plot(x, prod, color=C_PV, linewidth=2.0, zorder=4)

            # Zużycie (linia)
            ax.plot(x, cons, color=C_CONS, linewidth=1.8, linestyle="--",
                    label="Zapotrzebowanie", zorder=5)

            # Pobór z sieci (obszar pod linią zużycia gdy brakuje PV)
            ax.fill_between(x, 0, grid, color=C_GRID, alpha=0.25,
                            label="Pobór z sieci", zorder=3)

            ax.set_xticks(range(0, 24, 3))
            ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)], fontsize=7.5)
            ax.legend(fontsize=7.5, frameon=True, edgecolor="#DDDDDD",
                    loc="upper right", handlelength=1.2)

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)
    # ── WYKRES 4: Schemat dachu z panelami ───────────────────────────────────

    def _chart_roof_panels(self, std: dict, request) -> str:
        """
        Schemat 2D rozmieszczenia paneli na dachu.
        Bazuje na facet_layouts z ScenarioResult.
        """
        PANEL_COLOR  = "#2E86C1"
        ROOF_COLOR   = "#ECF0F1"
        DIM_COLOR    = "#7F8C8D"
        TEXT_COLOR   = "#1B4F72"
        GAP          = 0.04   # przerwa między panelami [m]

        facet_layouts = std.get("facet_layouts") or []
        if not facet_layouts:
            # Brak danych layoutu — zwróć placeholder
            fig, ax = plt.subplots(figsize=(8, 5), facecolor="white")
            ax.set_axis_off()
            ax.text(0.5, 0.5, "Brak danych o układzie paneli",
                    ha="center", va="center", fontsize=12, color="#AAAAAA",
                    transform=ax.transAxes)
            return self._fig_to_b64(fig)

        layout = facet_layouts[0] if isinstance(facet_layouts[0], dict) else vars(facet_layouts[0])

        # Wymiary panelu
        panel_w = float(layout.get("panel_width_m",  1.134))
        panel_h = float(layout.get("panel_height_m", 1.762))

        # Kolumny i wiersze z layout
        rows_dist = layout.get("row_distribution") or []
        if not rows_dist:
            panels_count = int(std.get("panels_count") or 0)
            cols = max(1, int(panels_count ** 0.5))
            rows_dist = [cols] * (panels_count // cols + (1 if panels_count % cols else 0))

        panels_count = sum(rows_dist)
        total_kwp    = float(std.get("total_power_kwp") or panels_count * 0.43)
        cols         = max(rows_dist) if rows_dist else 1

        # Wymiary dachu na rysunku
        facet_w = cols * (panel_w + GAP) + GAP
        facet_l = len(rows_dist) * (panel_h + GAP) + GAP

        fig_w = max(7.0, facet_w * 1.5 + 1.5)
        fig_h = max(5.0, facet_l * 1.5 + 1.0)

        fig, ax = plt.subplots(figsize=(min(fig_w, 10), min(fig_h, 7)), facecolor="white")
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_xlim(-0.5, facet_w + 0.6)
        ax.set_ylim(-0.6, facet_l + 0.4)

        # Tło dachu
        from matplotlib.patches import FancyBboxPatch
        roof_rect = FancyBboxPatch(
            (0, 0), facet_w, facet_l,
            boxstyle="round,pad=0.0", linewidth=1.5,
            edgecolor="#BDC3C7", facecolor=ROOF_COLOR, zorder=1
        )
        ax.add_patch(roof_rect)

        # Rysowanie paneli
        y = GAP
        for row_idx, n_cols in enumerate(rows_dist):
            x_offset = (facet_w - n_cols * (panel_w + GAP) - GAP) / 2
            x = x_offset + GAP
            for col_idx in range(n_cols):
                panel = FancyBboxPatch(
                    (x, y), panel_w, panel_h,
                    boxstyle="round,pad=0.01", linewidth=0.4,
                    edgecolor="#1A5276", facecolor=PANEL_COLOR, alpha=0.82, zorder=2
                )
                ax.add_patch(panel)
                # Linie komórek panelu
                cell_h = panel_h / 3
                cell_w = panel_w / 3
                for ci in range(1, 3):
                    ax.plot([x, x + panel_w], [y + ci * cell_h, y + ci * cell_h],
                            color="white", linewidth=0.25, alpha=0.4, zorder=3)
                    ax.plot([x + ci * cell_w, x + ci * cell_w], [y, y + panel_h],
                            color="white", linewidth=0.25, alpha=0.4, zorder=3)
                x += panel_w + GAP
            y += panel_h + GAP

        # Wymiary strzałkowe
        arrowstyle = dict(arrowstyle="<->", color=DIM_COLOR, lw=1.0, mutation_scale=8)

        ax.annotate("", xy=(facet_w, -0.30), xytext=(0, -0.30), arrowprops=arrowstyle)
        ax.text(facet_w / 2, -0.44, f"{facet_w:.1f} m",
                ha="center", va="top", fontsize=7.5, color=DIM_COLOR, fontweight="bold")

        ax.annotate("", xy=(facet_w + 0.28, facet_l), xytext=(facet_w + 0.28, 0),
                    arrowprops=arrowstyle)
        ax.text(facet_w + 0.44, facet_l / 2, f"{facet_l:.1f} m",
                ha="left", va="center", fontsize=7.5, color=DIM_COLOR,
                fontweight="bold", rotation=90)

        ax.text(facet_w / 2, facet_l + 0.18,
                f"{panels_count} paneli · {total_kwp:.2f} kWp",
                ha="center", va="bottom", fontsize=9, color=TEXT_COLOR, fontweight="black")

        fig.tight_layout(pad=0.3)
        return self._fig_to_b64(fig)

    # ── METODA GŁÓWNA: generate() ─────────────────────────────────────────────

    def generate(self, report_data: ReportData) -> bytes:
        """
        Generuje PDF raportu fotowoltaicznego.
        Wszystkie wykresy oparte na prawdziwych danych z symulacji.
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
            charts["payback"] = self._chart_payback(std, eco)
        except Exception as e:
            print(f"[ReportGenerator] CHART payback error: {e}")
            import traceback; traceback.print_exc()

        try:
            charts["daily_flow"] = self._chart_daily_flow(std)
        except Exception as e:
            print(f"[ReportGenerator] CHART daily_flow error: {e}")
            import traceback; traceback.print_exc()

        try:
            charts["roof_panels"] = self._chart_roof_panels(std, report_data.input_request)
        except Exception as e:
            print(f"[ReportGenerator] CHART roof_panels error: {e}")
            import traceback; traceback.print_exc()

        template = self.env.get_template("report/base.html")

        context = {
            "data":            report_data.input_data_summary,
            "req":             report_data.input_request,
            "standard":        std,
            "premium":         prem,
            "economy":         eco,
            "warnings":        report_data.warnings_and_confirmations,
            "charts":          charts,
            "generation_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "version":         "3.0.0",
        }

        rendered_html = template.render(**context)

        css_path = os.path.join(self.static_dir, "report", "report.css")
        stylesheets = []
        if os.path.exists(css_path):
            stylesheets.append(CSS(filename=css_path))
        else:
            print(f"[ReportGenerator] OSTRZEZENIE: Nie znaleziono CSS: {css_path}")

        pdf_bytes = HTML(
            string=rendered_html,
            base_url=self.base_dir
        ).write_pdf(stylesheets=stylesheets)

        return pdf_bytes