# backend/app/core/report_generator.py
# ─────────────────────────────────────────────────────────────
#  Generator raportów PDF — WeasyPrint + Jinja2 + prawdziwe dane z silników
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
    print("[ReportGenerator] matplotlib niedostępny — wykresy zastąpione tabelami CSS")


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
        CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
        APP_DIR     = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
        BACKEND_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))

        self.base_dir      = BACKEND_DIR
        self.templates_dir = os.path.join(APP_DIR, "templates")
        self.static_dir    = os.path.join(APP_DIR, "static")

        self.env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.env.filters['format_pln'] = self._format_pln
        self.env.filters['format_num'] = self._format_num

    # ── formattery ────────────────────────────────────────────────────────────

    def _format_pln(self, value):
        if value is None:
            return "—"
        try:
            return f"{int(value):,} zł".replace(",", " ")
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
        fig.savefig(
            buf,
            format="png",
            dpi=180,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    @staticmethod
    def _style_ax(ax, title=None, ylabel=None):
        ax.set_facecolor("#F8FAFB")
        ax.grid(axis="y", color="#E8ECEF", linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["bottom", "left"]:
            ax.spines[spine].set_color("#CCCCCC")
            ax.spines[spine].set_linewidth(0.8)
        if title:
            ax.set_title(
                title,
                fontsize=11,
                fontweight="bold",
                color="#1B4F72",
                pad=10,
                loc="left",
            )
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=8.5, color="#555555")

    # ── wykres: miesięczny bilans energii (prawdziwe dane) ───────────────────

    def _chart_monthly_balance(self, std) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        months_labels = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                         "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

        # Próba pobrania prawdziwych danych
        monthly_prod = getattr(std, "monthly_production_kwh", None) or {}
        monthly_cons = getattr(std, "monthly_consumption_kwh", None) or {}

        # Jeśli nie ma pól w ScenarioResult, spróbuj wyciągnąć z hourly_result
        hourly = getattr(std, "hourly_result_without_battery", None) or {}
        if not monthly_cons:
            monthly_cons = hourly.get("monthly_consumption_kwh", {}) or {}

        # Jeśli nadal pusto – fallback: rozbij roczne na 12 równych części
        annual_prod = getattr(std, "annual_production_kwh", 0.0) or 0.0
        annual_cons = getattr(std, "annual_consumption_kwh", 0.0) or 0.0

        if not monthly_prod:
            monthly_prod = {m: annual_prod / 12.0 for m in range(1, 13)}
        if not monthly_cons:
            monthly_cons = {m: annual_cons / 12.0 for m in range(1, 13)}

        prod_vals = [
            float(monthly_prod.get(str(m), monthly_prod.get(m, 0.0))) for m in range(1, 13)
        ]
        cons_vals = [
            float(monthly_cons.get(str(m), monthly_cons.get(m, 0.0))) for m in range(1, 13)
        ]

        # Autokonsumpcja = min(produkcja, zużycie)
        auto_vals = [min(p, c) for p, c in zip(prod_vals, cons_vals)]
        surplus   = [max(0.0, p - a) for p, a in zip(prod_vals, auto_vals)]
        grid_draw = [max(0.0, c - a) for c, a in zip(cons_vals, auto_vals)]

        x = np.arange(12)
        fig, ax = plt.subplots(figsize=(9.5, 3.2))
        self._style_ax(ax, ylabel="kWh / miesiąc")

        bar_w = 0.55
        ax.bar(x, auto_vals,  bar_w, label="Autokonsumpcja",    color=C_AUTO,    zorder=3)
        ax.bar(x, surplus,    bar_w, label="Nadwyżka do sieci", color=C_SURPLUS, zorder=3,
               bottom=auto_vals)
        offset = [a + s for a, s in zip(auto_vals, surplus)]
        ax.bar(x, grid_draw,  bar_w, label="Pobór z sieci",      color=C_GRID,
               bottom=offset, alpha=0.6, zorder=3)

        demand_line = cons_vals
        ax.plot(x, demand_line, color=C_DEMAND, linewidth=1.8,
                marker="o", markersize=4, zorder=5, label="Zapotrzebowanie")

        ax.set_xticks(list(x))
        ax.set_xticklabels(months_labels, fontsize=8)
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=4,
            framealpha=0.95,
            edgecolor="#DDDDDD",
            fontsize=8,
            handlelength=1.2,
        )
        fig.tight_layout()
        return self._fig_to_b64(fig)

    # ── wykres: zwrot inwestycji (ROI) ───────────────────────────────────────

    def _chart_payback(self, std, eco) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        cost_std = getattr(std, "pv_cost_gross_pln", 19000) or 19000
        cost_eco = getattr(eco, "pv_cost_gross_pln", 14000) or 14000 if eco else cost_std
        sav_std  = getattr(std, "pv_savings_pln",   2500)  or 2500
        sav_eco  = getattr(eco, "pv_savings_pln",   2200)  or sav_std if eco else sav_std
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
            ax.annotate(
                f"Zwrot\n≈ {payback_yr} lat",
                xy=(payback_yr, 0),
                xytext=(payback_yr + 0.4, max(vals_std) * 0.15 / 1000),
                fontsize=8,
                color="#C0392B",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#E74C3C", lw=0.8),
            )

        max_v = max(vals_std[-1], vals_eco[-1]) / 1000
        ax.annotate(f"6%/rok", xy=(25, max_v * 1.05), fontsize=7, color="#888")
        ax.annotate(f"3%/rok", xy=(25, max_v * 0.72), fontsize=7, color="#888")

        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"{int(x)} tys. zł")
        )
        ax.set_xlabel("Rok", fontsize=8.5, color="#555555")
        ax.legend(loc="upper left", fontsize=8, framealpha=0.95)
        fig.tight_layout()
        return self._fig_to_b64(fig)

    # ── wykres: dobowy przepływ energii (lato vs zima, prawdziwe dane) ──────

    def _chart_daily_flow(self, std) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""

        hourly = getattr(std, "hourly_result_without_battery", None) or {}
        seasonal = hourly.get("seasonal_charts", {}) or {}

        summer = seasonal.get("summer") or []
        winter = seasonal.get("winter") or []

        # Jeśli nie ma danych sezonowych – fallback: brak wykresu
        if not summer and not winter:
            return ""

        def extract_series(day_data):
            hours = []
            auto = []
            surplus = []
            grid = []
            cons = []
            for row in day_data:
                h = row.get("hour") or row.get("hour_index") or len(hours)
                hours.append(h)
                auto.append(float(row.get("autoconsumption_kw", 0.0)))
                surplus.append(float(row.get("surplus_kw", 0.0)))
                grid.append(float(row.get("grid_import_kw", 0.0)))
                cons.append(float(row.get("home_consumption_kw", 0.0)))
            return hours, auto, surplus, grid, cons

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.0))

        # Lato
        if summer:
            h_s, auto_s, surp_s, grid_s, cons_s = extract_series(summer)
            self._style_ax(ax1, ylabel="kW")
            ax1.set_title("Lato (czerwiec)", fontsize=10, fontweight="bold",
                          color="#1B4F72", pad=6, loc="center")
            ax1.bar(h_s, auto_s,  0.7, color=C_AUTO,    label="Autokonsumpcja PV", zorder=3)
            ax1.bar(h_s, surp_s,  0.7, color=C_SURPLUS, label="Nadwyżka do sieci",
                    bottom=auto_s, zorder=3)
            ax1.bar(h_s, grid_s,  0.7, color=C_GRID,    label="Pobór z sieci",
                    alpha=0.5, zorder=2)
            ax1.plot(h_s, cons_s, color=C_DEMAND, linewidth=1.5,
                     marker=".", markersize=3, zorder=5, label="Zużycie domu")
            ax1.set_xticks([0, 4, 8, 12, 16, 20, 23])
            ax1.set_xticklabels(["00:00", "04:00", "08:00", "12:00",
                                 "16:00", "20:00", "23:00"], fontsize=7)
            ax1.set_xlabel("Godzina", fontsize=8)
        else:
            ax1.axis("off")
            ax1.text(
                0.5,
                0.5,
                "Brak danych letnich",
                ha="center",
                va="center",
                fontsize=8,
                color="#888",
            )

        # Zima
        if winter:
            h_w, auto_w, surp_w, grid_w, cons_w = extract_series(winter)
            self._style_ax(ax2, ylabel="kW")
            ax2.set_title("Zima (styczeń)", fontsize=10, fontweight="bold",
                          color="#1B4F72", pad=6, loc="center")
            ax2.bar(h_w, auto_w,  0.7, color=C_AUTO,    label="Autokonsumpcja PV", zorder=3)
            ax2.bar(h_w, surp_w,  0.7, color=C_SURPLUS, label="Nadwyżka do sieci",
                    bottom=auto_w, zorder=3)
            ax2.bar(h_w, grid_w,  0.7, color=C_GRID,    label="Pobór z sieci",
                    alpha=0.5, zorder=2)
            ax2.plot(h_w, cons_w, color=C_DEMAND, linewidth=1.5,
                     marker=".", markersize=3, zorder=5, label="Zużycie domu")
            ax2.set_xticks([0, 4, 8, 12, 16, 20, 23])
            ax2.set_xticklabels(["00:00", "04:00", "08:00", "12:00",
                                 "16:00", "20:00", "23:00"], fontsize=7)
            ax2.set_xlabel("Godzina", fontsize=8)
        else:
            ax2.axis("off")
            ax2.text(
                0.5,
                0.5,
                "Brak danych zimowych",
                ha="center",
                va="center",
                fontsize=8,
                color="#888",
            )

        # Legenda wspólna
        handles, labels = ax1.get_legend_handles_labels()
        if not handles:
            handles, labels = ax2.get_legend_handles_labels()
        if handles:
            fig.legend(
                handles,
                labels,
                loc="lower center",
                ncol=4,
                fontsize=7.5,
                framealpha=0.95,
                bbox_to_anchor=(0.5, -0.08),
            )

        fig.tight_layout(rect=[0, 0.05, 1, 1])
        return self._fig_to_b64(fig)

    # ── wykres: panele na dachu (zostawiony, tylko lekko uporządkowany) ─────

    def _chart_roof_panels(self, std, req) -> str:
        if not MATPLOTLIB_AVAILABLE:
            return ""
        try:
            panels = getattr(std, "panels_count", 12) or 12
            power  = getattr(std, "total_power_kwp", 6.0) or 6.0

            facets = getattr(req, "facets", []) or []
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
            roof = mpatches.FancyBboxPatch(
                (0, 0),
                W,
                H,
                boxstyle="round,pad=0.1",
                linewidth=1.5,
                edgecolor="#8B9467",
                facecolor="#D4E6D4",
                zorder=1,
            )
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
                        (x0, y0),
                        panel_w,
                        panel_h,
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

            ax.annotate(
                f"{panels} paneli · {power:.2f} kWp",
                xy=(W / 2, H + 0.15),
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                color="#1B4F72",
            )
            ax.annotate(
                f"{W:.1f} m",
                xy=(W / 2, -0.2),
                ha="center",
                va="top",
                fontsize=7.5,
                color="#555",
            )
            ax.annotate(
                f"{H:.1f} m",
                xy=(W + 0.1, H / 2),
                ha="left",
                va="center",
                fontsize=7.5,
                color="#555",
                rotation=-90,
            )

            from matplotlib.patches import Patch
            legend = [
                Patch(facecolor="#D4E6D4", edgecolor="#8B9467", label="Powierzchnia dachu"),
                Patch(facecolor="#F5C842", edgecolor="#1A4A6B", label="Panele fotowoltaiczne"),
            ]
            ax.legend(
                handles=legend,
                loc="lower right",
                fontsize=7,
                framealpha=0.9,
                edgecolor="#CCCCCC",
                bbox_to_anchor=(1.0, -0.25),
            )
            ax.annotate(
                "Rzut z góry. Finalne rozmieszczenie ustali instalator.",
                xy=(0, -0.2),
                fontsize=6.5,
                color="#888",
                va="top",
            )
            fig.tight_layout()
            return self._fig_to_b64(fig)
        except Exception as e:
            print(f"[ReportGenerator] CHART roof_panels error (detail): {e}")
            return ""

    # ── generowanie PDF ───────────────────────────────────────────────────────

    def generate(self, report_data: ReportData) -> bytes:
        """Generuje PDF i zwraca bytes."""

        results = report_data.all_scenarios_results

        def _to_obj(name):
            raw = results.get(name) or results.get(name.upper())
            if raw is None:
                return None
            if isinstance(raw, dict):
                return type("Obj", (), raw)()
            return raw

        std  = _to_obj("standard")
        prem = _to_obj("premium")
        eco  = _to_obj("economy")

        if std is None:
            raise ValueError("Brak danych dla scenariusza 'standard' w ReportData")

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

        css_path = os.path.join(self.static_dir, "report", "report.css")
        css_content = ""
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
            print(f"[ReportGenerator] CSS załadowany: {css_path} ({len(css_content)} znaków)")
        else:
            print(f"[ReportGenerator] OSTRZEŻENIE: Nie znaleziono CSS: {css_path}")
            print(f"[ReportGenerator] static_dir = {self.static_dir}")

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
            "version":         "2.3.0",
            "css_content":     css_content,
        }

        rendered_html = template.render(**context)

        pdf_bytes = HTML(
            string=rendered_html,
            base_url=self.base_dir,
        ).write_pdf()

        return pdf_bytes