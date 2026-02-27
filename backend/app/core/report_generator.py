# backend/app/core/report_generator.py
# ─────────────────────────────────────────────────────────────
#  Generator raportów PDF — WeasyPrint + Jinja2
#
#  POPRAWKA KRYTYCZNA:
#  1. self.static_dir = APP_DIR/static (nie BACKEND_DIR/static)
#  2. CSS wstrzykiwany inline jako <style> (nie <link> href) —
#     WeasyPrint na Windows nie potrafi rozwiązać ścieżek względnych
#     gdy base_url jest ścieżką Windows z backslashami.
# ─────────────────────────────────────────────────────────────

import os
import base64
from io import BytesIO
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
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
C_AUTO    = "#27AE60"
C_SURPLUS = "#F39C12"
C_GRID    = "#E74C3C"
C_DEMAND  = "#2980B9"
C_STD     = "#2E86C1"
C_ECO     = "#27AE60"
C_ZERO    = "#7F8C8D"


class ReportGenerator:
    def __init__(self):
        # ── Ścieżki ──────────────────────────────────────────────────────────
        # Struktura katalogów w OBU projektach:
        #   backend/
        #     app/
        #       core/
        #         report_generator.py   ← CURRENT_DIR
        #       templates/              ← APP_DIR/templates
        #       static/                 ← APP_DIR/static   ← POPRAWKA (było BACKEND_DIR/static)
        #     (brak backend/static/ w soolevo!)
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        APP_DIR     = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
        BACKEND_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))

        self.base_dir      = BACKEND_DIR
        self.templates_dir = os.path.join(APP_DIR, "templates")
        # POPRAWKA: static jest w APP_DIR (backend/app/static/), nie w BACKEND_DIR
        self.static_dir    = os.path.join(APP_DIR, "static")

        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.env.filters['format_pln'] = self._format_pln
        self.env.filters['format_num'] = self._format_num

    # ── formattery ────────────────────────────────────────────────────────────

    def _format_pln(self, value):
        if value is None:
            return "—"
        try:
            return f"{int(value):,} zl".replace(",", " ")
        except (ValueError, TypeError):
            return "—"

    def _format_num(self, value, decimals=0):
        if value is None:
            return "—"
        try:
            if decimals == 0:
                return f"{int(value):,}".replace(",", " ")
            else:
                return f"{float(value):,.{decimals}f}".replace(",", " ").replace(".", ",")
        except (ValueError, TypeError):
            return "—"

    # ── helpers matplotlib ────────────────────────────────────────────────────

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
        ax.grid(axis="y", color="#E8ECEF", linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["bottom", "left"]:
            ax.spines[spine].set_color("#CCCCCC")
            ax.spines[spine].set_linewidth(0.8)
        if title:
            ax.set_title(title, fontsize=11, fontweight="bold",
                         color="#1B4F72", pad=10, loc="left")
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=8.5, color="#555555")

    # ── wykresy ───────────────────────────────────────────────────────────────

    def _chart_monthly_balance(self, std) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""
        months = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                  "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]
        monthly = getattr(std, "monthly_production_kwh", None) or {}
        monthly_consumption = getattr(std, "monthly_consumption_kwh", None) or {}

        prod_vals    = [monthly.get(str(m), monthly.get(m, 0)) for m in range(1, 13)]
        cons_vals    = [monthly_consumption.get(str(m), monthly_consumption.get(m, 0)) for m in range(1, 13)]

        auto_rate  = getattr(std, "autoconsumption_rate", 0.35)
        auto_vals  = [p * auto_rate for p in prod_vals]
        surplus    = [p - a for p, a in zip(prod_vals, auto_vals)]
        grid_draw  = [max(0, c - a) for c, a in zip(cons_vals, auto_vals)]

        x = range(12)
        fig, ax = plt.subplots(figsize=(9.5, 3.2))
        self._style_ax(ax, ylabel="kWh / miesiąc")

        bar_w = 0.55
        ax.bar(x, auto_vals,  bar_w, label="Autokonsumpcja",   color=C_AUTO,    zorder=3)
        ax.bar(x, surplus,    bar_w, label="Nadwyżka do sieci", color=C_SURPLUS, zorder=3,
               bottom=auto_vals)
        ax.bar(x, grid_draw,  bar_w, label="Pobór z sieci",     color=C_GRID,    zorder=3,
               bottom=auto_vals, alpha=0.0)

        offset = [a + s for a, s in zip(auto_vals, surplus)]
        ax.bar(x, grid_draw, bar_w, color=C_GRID, zorder=3, bottom=offset, alpha=0.6)

        demand_line = [a + g for a, g in zip(auto_vals, grid_draw)]
        ax.plot(x, demand_line, color=C_DEMAND, linewidth=1.8,
                marker="o", markersize=4, zorder=5, label="Zapotrzebowanie")

        ax.set_xticks(list(x))
        ax.set_xticklabels(months, fontsize=8)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18),
                  ncol=4, framealpha=0.95, edgecolor="#DDDDDD",
                  fontsize=8, handlelength=1.2)
        fig.tight_layout()
        return self._fig_to_b64(fig)

    def _chart_payback(self, std, eco) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""
        cost_std = getattr(std, "pv_cost_gross_pln", 19000) or 19000
        cost_eco = getattr(eco, "pv_cost_gross_pln", 14000) or 14000
        sav_std  = getattr(std, "pv_savings_pln",   2500)  or 2500
        sav_eco  = getattr(eco, "pv_savings_pln",   2200)  or 2200
        inflation = 0.04

        years = list(range(26))
        def cum(cost, sav):
            vals = [-cost]
            for i in range(1, 26):
                vals.append(vals[-1] + sav * ((1 + inflation) ** i))
            return vals

        vals_std = cum(cost_std, sav_std)
        vals_eco = cum(cost_eco, sav_eco)

        payback_yr = None
        for i in range(1, 26):
            if vals_std[i] >= 0 and vals_std[i - 1] < 0:
                payback_yr = i
                break

        fig, ax = plt.subplots(figsize=(9.5, 3.2))
        self._style_ax(ax, ylabel="Skumulowane oszczędności [zł]")

        ax.plot(years, [v / 1000 for v in vals_std], color=C_STD,
                linewidth=2, label="Standard", zorder=4)
        ax.plot(years, [v / 1000 for v in vals_eco], color=C_ECO,
                linewidth=1.5, linestyle="--", label="Economy", zorder=4)
        ax.axhline(0, color=C_ZERO, linewidth=0.8, linestyle=":")

        lo_std = [v * 0.85 / 1000 for v in vals_std]
        hi_std = [v * 1.15 / 1000 for v in vals_std]
        ax.fill_between(years, lo_std, hi_std, alpha=0.12, color=C_STD)

        if payback_yr:
            ax.axvline(payback_yr, color="#E74C3C", linewidth=1.0, linestyle="--", zorder=3)
            ax.annotate(f"Zwrot\n≈ {payback_yr} lat",
                        xy=(payback_yr, 0),
                        xytext=(payback_yr + 0.4, max(vals_std) * 0.15 / 1000),
                        fontsize=8, color="#C0392B", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#E74C3C", lw=0.8))

        max_v = max(vals_std[-1], vals_eco[-1]) / 1000
        ax.annotate(f"6%/rok", xy=(25, max_v * 1.05), fontsize=7, color="#888")
        ax.annotate(f"3%/rok", xy=(25, max_v * 0.72), fontsize=7, color="#888")

        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f"{int(x)} tys. zł"))
        ax.set_xlabel("Rok", fontsize=8.5, color="#555555")
        ax.legend(loc="upper left", fontsize=8, framealpha=0.95)
        fig.tight_layout()
        return self._fig_to_b64(fig)

    def _chart_daily_flow(self, std) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""
        hours = list(range(24))
        prod_peak   = getattr(std, "total_power_kwp", 6.0) or 6.0

        def summer_profile(h):
            if 5 <= h <= 20:
                import math
                return max(0, prod_peak * 0.9 * math.sin(math.pi * (h - 5) / 15) ** 1.4)
            return 0.0

        def winter_profile(h):
            if 8 <= h <= 15:
                import math
                return max(0, prod_peak * 0.22 * math.sin(math.pi * (h - 8) / 7) ** 1.2)
            return 0.0

        def cons_profile(h):
            base = 0.15
            morning = 0.35 if 6 <= h <= 9 else 0.0
            evening = 0.55 if 18 <= h <= 22 else 0.0
            return base + morning + evening

        cons = [cons_profile(h) for h in hours]
        s_prod = [summer_profile(h) for h in hours]
        w_prod = [winter_profile(h) for h in hours]

        auto_s  = [min(p, c) for p, c in zip(s_prod, cons)]
        surp_s  = [max(0, p - c) for p, c in zip(s_prod, cons)]
        grid_s  = [max(0, c - p) for c, p in zip(cons, s_prod)]

        auto_w  = [min(p, c) for p, c in zip(w_prod, cons)]
        surp_w  = [max(0, p - c) for p, c in zip(w_prod, cons)]
        grid_w  = [max(0, c - p) for c, p in zip(cons, w_prod)]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.0))

        for ax, auto, surp, grid, title in [
            (ax1, auto_s, surp_s, grid_s, "Lato (czerwiec)"),
            (ax2, auto_w, surp_w, grid_w, "Zima (styczeń)"),
        ]:
            self._style_ax(ax, ylabel="kW")
            ax.set_title(title, fontsize=10, fontweight="bold",
                         color="#1B4F72", pad=6, loc="center")
            ax.bar(hours, auto,  0.7, color=C_AUTO,    label="Autokonsumpcja PV", zorder=3)
            ax.bar(hours, surp,  0.7, color=C_SURPLUS, label="Nadwyżka do sieci",
                   bottom=auto, zorder=3)
            ax.bar(hours, grid,  0.7, color=C_GRID,    label="Pobór z sieci",
                   alpha=0.5, zorder=2)
            ax.plot(hours, cons, color=C_DEMAND, linewidth=1.5,
                    marker=".", markersize=3, zorder=5, label="Zużycie domu")
            ax.set_xticks([0, 4, 8, 12, 16, 20, 23])
            ax.set_xticklabels(["00:00", "04:00", "08:00", "12:00",
                                 "16:00", "20:00", "23:00"], fontsize=7)
            ax.set_xlabel("Godzina", fontsize=8)

        handles, labels = ax1.get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center",
                   ncol=4, fontsize=7.5, framealpha=0.95,
                   bbox_to_anchor=(0.5, -0.08))
        fig.tight_layout(rect=[0, 0.05, 1, 1])
        return self._fig_to_b64(fig)

    def _chart_roof_panels(self, std, req) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""
        try:
            panels = getattr(std, "panels_count", 12) or 12
            power  = getattr(std, "total_power_kwp", 6.0) or 6.0

            facets = getattr(req, "facets", [])
            facet  = facets[0] if facets else {}
            if hasattr(facet, "width_m"):
                W = getattr(facet, "width_m", 10.0) or 10.0
                H = getattr(facet, "height_m", 5.8) or 5.8
            elif isinstance(facet, dict):
                W = float(facet.get("width_m") or facet.get("building_width_m") or 10.0)
                H = float(facet.get("height_m") or facet.get("building_length_m") or 5.8)
            else:
                W, H = 10.0, 5.8

            panel_w, panel_h = 1.13, 2.28
            cols = max(1, int(W / (panel_w + 0.05)))
            rows = max(1, int(H / (panel_h + 0.05)))

            fig, ax = plt.subplots(figsize=(5.5, 3.2))
            ax.set_facecolor("#E8F4EA")
            ax.set_xlim(-0.3, W + 0.3)
            ax.set_ylim(-0.3, H + 0.3)
            ax.set_aspect("equal")
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.set_xticks([])
            ax.set_yticks([])

            import matplotlib.patches as mpatches
            roof = mpatches.FancyBboxPatch((0, 0), W, H,
                                           boxstyle="round,pad=0.1",
                                           linewidth=1.5,
                                           edgecolor="#8B9467",
                                           facecolor="#D4E6D4",
                                           zorder=1)
            ax.add_patch(roof)

            placed = 0
            gap = 0.08
            for r in range(rows):
                for c in range(cols):
                    if placed >= panels:
                        break
                    x0 = c * (panel_w + gap) + gap
                    y0 = r * (panel_h + gap) + gap
                    if x0 + panel_w > W - gap or y0 + panel_h > H - gap:
                        continue
                    panel = mpatches.FancyBboxPatch(
                        (x0, y0), panel_w, panel_h,
                        boxstyle="round,pad=0.04",
                        linewidth=0.5,
                        edgecolor="#1A4A6B",
                        facecolor="#F5C842",
                        zorder=2,
                    )
                    ax.add_patch(panel)
                    placed += 1
                if placed >= panels:
                    break

            ax.annotate(f"{panels} paneli · {power:.2f} kWp",
                        xy=(W / 2, H + 0.15), ha="center", va="bottom",
                        fontsize=8, fontweight="bold", color="#1B4F72")
            ax.annotate(f"{W:.1f} m", xy=(W / 2, -0.2),
                        ha="center", va="top", fontsize=7.5, color="#555")
            ax.annotate(f"{H:.1f} m", xy=(W + 0.1, H / 2),
                        ha="left", va="center", fontsize=7.5,
                        color="#555", rotation=-90)

            from matplotlib.patches import Patch
            legend = [
                Patch(facecolor="#D4E6D4", edgecolor="#8B9467", label="Powierzchnia dachu"),
                Patch(facecolor="#F5C842", edgecolor="#1A4A6B", label="Panele fotowoltaiczne"),
            ]
            ax.legend(handles=legend, loc="lower right", fontsize=7,
                      framealpha=0.9, edgecolor="#CCCCCC",
                      bbox_to_anchor=(1.0, -0.25))
            ax.annotate("Rzut z góry. Finalne rozmieszczenie ustali instalator.",
                        xy=(0, -0.2), fontsize=6.5, color="#888", va="top")
            fig.tight_layout()
            return self._fig_to_b64(fig)
        except Exception as e:
            print(f"[ReportGenerator] CHART roof_panels error (detail): {e}")
            return ""

    # ── generowanie PDF ───────────────────────────────────────────────────────

    def generate(self, report_data: ReportData) -> bytes:
        """Generuje PDF i zwraca bytes."""

        # ── Wyodrębnij scenariusze ────────────────────────────────────────────
        results = report_data.all_scenarios_results
        from app.schemas.scenarios import ScenarioResult

        def _to_obj(name):
            raw = results.get(name) or results.get(name.upper())
            if raw is None:
                return None
            if isinstance(raw, dict):
                try:
                    return ScenarioResult(**raw)
                except Exception:
                    return type("Obj", (), raw)()
            return raw

        std  = _to_obj("standard")
        prem = _to_obj("premium")
        eco  = _to_obj("economy")

        if std is None:
            raise ValueError("Brak danych dla scenariusza 'standard' w ReportData")

        # ── Generuj wykresy ──────────────────────────────────────────────────
        charts = {}
        try:
            charts["monthly_balance"] = self._chart_monthly_balance(std)
        except Exception as e:
            print(f"[ReportGenerator] CHART monthly_balance error: {e}")
        try:
            charts["payback"] = self._chart_payback(std, eco)
        except Exception as e:
            print(f"[ReportGenerator] CHART payback error: {e}")
        try:
            charts["daily_flow"] = self._chart_daily_flow(std)
        except Exception as e:
            print(f"[ReportGenerator] CHART daily_flow error: {e}")
        try:
            charts["roof_panels"] = self._chart_roof_panels(std, report_data.input_request)
        except Exception as e:
            print(f"[ReportGenerator] CHART roof_panels error: {e}")

        # ── Wczytaj CSS do stringa — JEDYNA NIEZAWODNA METODA DLA WEASYPRINT ──
        # WeasyPrint nie może rozwiązać ścieżek względnych z <link href="...">,
        # szczególnie na Windows (backslashe w base_url). CSS musi być inline.
        css_path = os.path.join(self.static_dir, "report", "report.css")
        css_content = ""
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
            print(f"[ReportGenerator] CSS załadowany: {css_path} ({len(css_content)} znaków)")
        else:
            print(f"[ReportGenerator] OSTRZEZENIE: Nie znaleziono CSS: {css_path}")
            print(f"[ReportGenerator] static_dir = {self.static_dir}")

        # ── Renderuj HTML ────────────────────────────────────────────────────
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
            "version":         "2.2.0",
            "css_content":     css_content,   # ← przekazany do base.html jako <style>
        }

        rendered_html = template.render(**context)

        # ── Generuj PDF ──────────────────────────────────────────────────────
        # Nie używamy stylesheets= — CSS jest już w <style> w rendered_html
        pdf_bytes = HTML(
            string=rendered_html,
            base_url=self.base_dir,
        ).write_pdf()

        return pdf_bytes
