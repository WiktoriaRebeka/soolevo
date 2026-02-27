import os
import base64
from io import BytesIO
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import pydyf  # <--- 1. Dodajemy import

# ── FIX: Monkey Patch dla kompatybilności WeasyPrint z różnymi wersjami pydyf ──
# Jeśli `pydyf.Stream` nie ma metody `transform`, dodajemy ją jako
# bezpieczną nakładkę:
# - gdy jest `concat` (nowsze pydyf) → delegujemy do `concat`
# - w pozostałych przypadkach robimy no-op, żeby uniknąć błędów typu AttributeError/TypeError
if not hasattr(pydyf.Stream, "transform"):
    def transform(self, a, b, c, d, e, f):
        concat = getattr(self, "concat", None)
        if callable(concat):
            concat(a, b, c, d, e, f)
        else:
            # Brak znanej metody transformacji — pomijamy, żeby nie wywalać PDF
            return

    pydyf.Stream.transform = transform

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
        "font.family":       "DejaVu Sans",   # obsługuje polskie znaki
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
C_DEMAND  = "#2980B9"   # zapotrzebowanie / linia — niebieski
C_STD     = "#2E86C1"   # Standard — niebieski
C_ECO     = "#27AE60"   # Economy — zielony
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
        ax.yaxis.grid(True, color="#E8ECEF", linewidth=0.7, zorder=0)
        ax.xaxis.grid(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#DDDDDD")
        ax.spines["bottom"].set_color("#DDDDDD")
        ax.tick_params(axis="both", which="both", length=0)
        if title:
            ax.set_title(title, fontsize=10, fontweight="bold",
                         color="#1B4F72", pad=10)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=8, color="#777777", labelpad=6)

    # ── WYKRES 1: Miesięczny bilans energii ──────────────────────────────────

    def _chart_monthly_balance(self, std: dict) -> str:
        MONTHS = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                  "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

        hr = (std.get("hourly_result_without_battery") or {})
        ef = hr.get("energy_flow") or {}
        mp = ef.get("monthly_production_kwh") or []
        mc = ef.get("monthly_consumption_kwh") or []
        ma = ef.get("monthly_autoconsumption_kwh") or []

        if len(mp) != 12:
            W  = [.04, .05, .08, .10, .12, .13, .13, .12, .09, .07, .04, .03]
            ap = std.get("annual_production_kwh") or 0
            mp = [ap * w for w in W]
        if len(mc) != 12:
            W  = [.10, .09, .09, .08, .08, .07, .07, .07, .08, .09, .09, .09]
            ac = std.get("annual_consumption_kwh") or 0
            mc = [ac * w for w in W]
        if len(ma) != 12:
            r  = std.get("autoconsumption_rate") or 0.4
            ma = [min(p * r, c) for p, c in zip(mp, mc)]

        surplus = [max(0, p - a) for p, a in zip(mp, ma)]
        grid    = [max(0, c - a) for c, a in zip(mc, ma)]
        x  = np.arange(12)
        bw = 0.36

        fig, ax = plt.subplots(figsize=(10, 4.0), facecolor="white")
        self._style_ax(ax, ylabel="kWh / miesiąc")

        # Słupki — lewa strona: produkcja (auto + nadwyżka)
        b1 = ax.bar(x - bw/2, ma,      width=bw, label="Autokonsumpcja",
                    color=C_AUTO,    alpha=0.92, zorder=3, linewidth=0)
        ax.bar(     x - bw/2, surplus, width=bw, label="Nadwyżka do sieci",
                    color=C_SURPLUS, alpha=0.92, bottom=ma, zorder=3, linewidth=0)

        # Słupki — prawa strona: pobór z sieci
        ax.bar(x + bw/2, grid, width=bw, label="Pobór z sieci",
               color=C_GRID, alpha=0.88, zorder=3, linewidth=0)

        # Linia zapotrzebowania
        ax.plot(x, mc, color=C_DEMAND, linewidth=2.2, marker="o", markersize=4.5,
                label="Zapotrzebowanie", zorder=5, linestyle="--", dash_capstyle="round")

        ax.set_xticks(x)
        ax.set_xticklabels(MONTHS, fontsize=8.5)
        ax.set_xlim(-0.6, 11.6)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"{int(v):,}".replace(",", " ")))

        # Legenda pozioma na dole wykresu
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16),
                  ncol=4, frameon=True, edgecolor="#DDDDDD",
                  fontsize=8, handlelength=1.4, handletextpad=0.5,
                  columnspacing=1.2)

        fig.subplots_adjust(bottom=0.2)
        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # ── WYKRES 2: Zwrot inwestycji w czasie ──────────────────────────────────

    def _chart_payback(self, std: dict, eco: dict) -> str:
        inf  = 0.04
        lata = list(range(0, 26))

        def cum(savings, cost, inf_rate=0.04):
            r = [-cost]
            for rok in range(1, 26):
                r.append(r[-1] + savings * ((1 + inf_rate) ** (rok - 1)))
            return r

        std_sav  = std.get("pv_savings_pln") or 0
        std_cost = std.get("pv_cost_gross_pln") or 0
        eco_sav  = (eco or {}).get("pv_savings_pln") or 0
        eco_cost = (eco or {}).get("pv_cost_gross_pln") or 0

        std_base = cum(std_sav, std_cost, 0.04)
        std_opt  = cum(std_sav, std_cost, 0.06)
        std_pes  = cum(std_sav, std_cost, 0.03)
        eco_base = cum(eco_sav, eco_cost, 0.04) if eco else None

        std_pb = next((i for i, v in enumerate(std_base) if v >= 0), None)

        fig, ax = plt.subplots(figsize=(10, 4.0), facecolor="white")
        self._style_ax(ax, ylabel="Skumulowane oszczędności [zł]")

        # Pasmo optymistyczny–pesymistyczny
        ax.fill_between(lata, std_opt, std_pes,
                        alpha=0.12, color=C_STD, zorder=1, label="_nolegend_")

        # Linie scenariuszy
        ax.plot(lata, std_opt, color=C_STD, linewidth=1.0,
                linestyle=":", alpha=0.6, zorder=2)
        ax.plot(lata, std_pes, color=C_STD, linewidth=1.0,
                linestyle=":", alpha=0.6, zorder=2)
        ax.plot(lata, std_base, color=C_STD, linewidth=2.8,
                label="Standard", zorder=4)
        if eco_base:
            ax.plot(lata, eco_base, color=C_ECO, linewidth=2.2,
                    linestyle="--", label="Economy", zorder=3)

        # Linia zerowa
        ax.axhline(0, color=C_ZERO, linewidth=1.0, linestyle=":", zorder=2)

        # Adnotacja zwrotu
        if std_pb:
            ax.axvline(std_pb, color=C_STD, linewidth=1.2,
                       linestyle="--", alpha=0.5, zorder=2)
            y_ann = max(std_base) * 0.18
            ax.annotate(
                f"Zwrot\n≈ {std_pb} lat",
                xy=(std_pb, 0),
                xytext=(std_pb + 1.0, y_ann if y_ann > 0 else max(std_base) * 0.1),
                fontsize=8, color=C_STD, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_STD, lw=1.0),
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor=C_STD, alpha=0.9)
            )

        ax.set_xlabel("Rok", fontsize=8.5, color="#555555")
        ax.set_xlim(0, 25)
        ax.set_xticks(range(0, 26, 5))
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{int(v/1000)} tys. zł"))

        # Szare wypełnienie obszaru zysku (powyżej zera)
        ax.fill_between(lata, std_base, 0,
                        where=[v >= 0 for v in std_base],
                        alpha=0.08, color=C_STD, zorder=1)

        ax.legend(loc="upper left", frameon=True, edgecolor="#DDDDDD",
                  fontsize=8.5, handlelength=1.4)

        # Adnotacja pasma inflacji
        ax.text(24.5, std_opt[-1], "6%/rok", fontsize=7, color=C_STD,
                alpha=0.7, ha="right", va="bottom")
        ax.text(24.5, std_pes[-1], "3%/rok", fontsize=7, color=C_STD,
                alpha=0.7, ha="right", va="top")

        fig.tight_layout(pad=1.2)
        return self._fig_to_b64(fig)

    # ── WYKRES 3: Dobowy przepływ energii ────────────────────────────────────

    def _chart_daily_flow(self, std: dict) -> str:
        hr     = (std.get("hourly_result_with_battery")
                  or std.get("hourly_result_without_battery") or {})
        sc     = hr.get("seasonal_charts") or {}
        summer = sc.get("summer") or sc.get("lato") or []
        winter = sc.get("winter") or sc.get("zima") or []

        def extract(day_data, *keys):
            if not day_data or not isinstance(day_data[0], dict):
                return None
            for key in keys:
                vals = [float(day_data[h].get(key, 0)) if h < len(day_data) else 0.0
                        for h in range(24)]
                if any(v > 0 for v in vals):
                    return vals
            return [0.0] * 24

        ap       = std.get("annual_production_kwh") or 4000
        ac       = std.get("annual_consumption_kwh") or 3500
        peak_pv  = ap / 8760 * 12
        avg_cons = ac / 8760

        s_prod = extract(summer, "pv", "pv_production")
        s_cons = extract(summer, "consumption")
        s_grid = extract(summer, "gridImport", "grid_import")
        w_prod = extract(winter, "pv", "pv_production")
        w_cons = extract(winter, "consumption")
        w_grid = extract(winter, "gridImport", "grid_import")

        if not s_prod or not any(v > 0 for v in s_prod):
            s_prod = ([0.0]*6 + [peak_pv*f for f in
                      [.08,.22,.42,.62,.80,.92,1.,.98,.88,.72,.52,.30]]
                      + [.06,0,0,0,0,0])
        if not s_cons or not any(v > 0 for v in s_cons):
            s_cons = ([avg_cons*.7]*6 + [avg_cons*f for f in
                      [1.3,1.5,1.1,.9,.9,1.,1.,1.,1.1,1.2,1.5,1.8,2.,1.8,1.3,1.,.8,.7]])
        if not w_prod or not any(v > 0 for v in w_prod):
            w_prod = ([0.0]*9 + [peak_pv*.3*f for f in
                      [.3,.6,.85,1.,.85,.6]] + [0.0]*9)
        if not w_cons or not any(v > 0 for v in w_cons):
            w_cons = ([avg_cons*1.1]*7 + [avg_cons*f for f in
                      [1.4,1.2,1.,1.,1.,1.,1.,1.,1.2,1.5,1.8,2.,1.9,1.5,1.2,1.1,1.]])
        if not s_grid:
            s_grid = [max(0., c - p) for c, p in zip(s_cons, s_prod)]
        if not w_grid:
            w_grid = [max(0., c - p) for c, p in zip(w_cons, w_prod)]

        s_prod = s_prod[:24]; s_cons = s_cons[:24]; s_grid = s_grid[:24]
        w_prod = w_prod[:24]; w_cons = w_cons[:24]; w_grid = w_grid[:24]
        s_auto = [min(p, c) for p, c in zip(s_prod, s_cons)]
        s_surp = [max(0., p - a) for p, a in zip(s_prod, s_auto)]
        w_auto = [min(p, c) for p, c in zip(w_prod, w_cons)]
        w_surp = [max(0., p - a) for p, a in zip(w_prod, w_auto)]
        godziny = list(range(24))
        xticks  = [0, 4, 8, 12, 16, 20, 23]
        xlabels = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:00"]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.6),
                                        facecolor="white", sharey=False)
        fig.subplots_adjust(wspace=0.30)

        for ax, auto, surp, grid, cons, title in [
            (ax1, s_auto, s_surp, s_grid, s_cons, "Lato (czerwiec)"),
            (ax2, w_auto, w_surp, w_grid, w_cons, "Zima (styczeń)"),
        ]:
            self._style_ax(ax, title=title, ylabel="kW")
            ax.bar(godziny, auto, width=.8, color=C_AUTO,    alpha=0.92, zorder=3, linewidth=0)
            ax.bar(godziny, surp, width=.8, color=C_SURPLUS, alpha=0.92,
                   bottom=auto, zorder=3, linewidth=0)
            ax.bar(godziny, grid, width=.8, color=C_GRID,    alpha=0.80, zorder=3, linewidth=0)
            ax.plot(godziny, cons, color=C_DEMAND, linewidth=2.0, zorder=5,
                    marker=".", markersize=3.5, markevery=2)
            ax.set_xlabel("Godzina", fontsize=8)
            ax.set_xlim(-0.5, 23.5)
            ax.set_xticks(xticks)
            ax.set_xticklabels(xlabels, fontsize=7.5, rotation=0, ha="center")
            ax.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda v, _: f"{v:.1f}"))

        # BEZ legendy matplotlib — legenda jest w HTML template (s3_charts.html)
        fig.tight_layout(pad=0.8)
        return self._fig_to_b64(fig)

    # ── WYKRES 4: Wizualizacja rozmieszczenia paneli na dachu ────────────────

    def _chart_roof_panels(self, std: dict, req: dict) -> str:
        """
        Rysuje rzut dachu z góry z rozmieszczonymi panelami.
        Dane paneli: std['facet_layouts'][0]['layout'] — pozycje z backendu (x, y, w, h w metrach).
        Kształt dachu: req (input_request) → roof_type + wymiary.
        """
        import matplotlib.patches as mpatches
        import matplotlib.patheffects as pe

        # ── Pobierz dane paneli z backendu ───────────────────────────────────
        facet_layouts = std.get("facet_layouts") or []
        all_panels = []
        for fl in facet_layouts:
            layout = fl.get("layout") if isinstance(fl, dict) else []
            if layout:
                all_panels.extend(layout if isinstance(layout[0], dict)
                                  else [p.__dict__ for p in layout])

        panels_count = std.get("panels_count") or len(all_panels)
        panel_power  = std.get("panel_power_wp") or 550
        total_kwp    = std.get("total_power_kwp") or 0

        # ── Dane geometryczne dachu z request ────────────────────────────────
        facets = []
        if hasattr(req, 'facets'):
            facets = req.facets
        elif isinstance(req, dict):
            facets = req.get('facets') or []

        facet = facets[0] if facets else {}
        if hasattr(facet, '__dict__'):
            facet = facet.__dict__
        elif not isinstance(facet, dict):
            facet = {}

        roof_type = facet.get('roof_type') or 'rectangular'
        slope_len = std.get("facet_slope_length_m") or std.get("facet_area_m2", 10) ** 0.5

        # Wymiary zależne od kształtu
        if roof_type == 'triangle':
            facet_w = facet.get('triangle_base') or facet.get('width') or 10.0
            facet_l = slope_len
            tri_h   = facet.get('triangle_height') or facet_l
            shape_type = 'triangle'
        elif roof_type in ('trapezoid', 'trapezoid_right'):
            facet_w = facet.get('trapezoid_base_a') or 10.0
            base_b  = facet.get('trapezoid_base_b') or facet_w * 0.6
            facet_l = slope_len
            shape_type = 'trapezoid'
        elif roof_type == 'rhombus':
            facet_w = facet.get('rhombus_diagonal_1') or 10.0
            facet_l = slope_len
            offset  = facet.get('rhombus_side_b') or 0
            shape_type = 'rhombus'
        else:
            facet_w = facet.get('width') or 10.0
            facet_l = slope_len
            shape_type = 'rectangular'

        if facet_w < 0.1:  facet_w = 10.0
        if facet_l < 0.1:  facet_l = 8.0

        # ── Skalowanie: kompaktowy wykres, max 6.5" szerokości, max 3.5" wysokości
        # Żeby zmieścić się razem z "Parametry systemu" na jednej stronie PDF
        TARGET_W = 5.5   # cali — szerokość wykresu dachu
        TARGET_H = 3.2   # cali — wysokość (ograniczona!)
        scale = min(TARGET_W / max(facet_w, 0.1), TARGET_H / max(facet_l, 0.1))
        # Dodatkowe ograniczenie: max 40 px/m żeby panele były widoczne
        scale = min(scale, 40 / 72.0)  # 72 dpi → px/inch
        # Przelicz na jednostki wykresu (1 jednostka = 1 m)
        scale = min((TARGET_W - 1.5) / max(facet_w, 0.1),
                    (TARGET_H - 0.8) / max(facet_l, 0.1))

        fw = facet_w * scale
        fl = facet_l * scale
        PAD = 0.7  # marginesy w jednostkach wykresu

        fig_w = fw + PAD * 2 + 0.5
        fig_h = fl + PAD * 2 + 0.6
        # Twardy limit rozmiaru figury
        fig_w = min(fig_w, 6.0)
        fig_h = min(fig_h, 3.8)

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="white")
        ax.set_facecolor("white")
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_xlim(-PAD, fw + PAD + 0.4)
        ax.set_ylim(-PAD - 0.4, fl + PAD + 0.25)

        # ── Obrys dachu ───────────────────────────────────────────────────────
        ROOF_FILL   = "#E8F4F3"
        ROOF_STROKE = "#569793"
        PANEL_FILL  = "#FFD700"
        PANEL_EDGE  = "#B8860B"
        DIM_COLOR   = "#569793"
        TEXT_COLOR  = "#1B4F72"

        if shape_type == 'triangle':
            tri_h_px = (tri_h if tri_h else facet_l) * scale
            bw_px    = facet_w * scale
            roof_pts = [(0, 0), (bw_px, 0), (bw_px / 2, tri_h_px)]
        elif shape_type == 'trapezoid':
            base_b_px = (base_b or facet_w * 0.6) * scale
            off = (fw - base_b_px) / 2
            roof_pts = [(0, 0), (fw, 0), (fw - off, fl), (off, fl)]
        elif shape_type == 'rhombus':
            off_px = (offset or facet_w * 0.3) * scale
            roof_pts = [(0, 0), (fw, 0), (fw + off_px, fl), (off_px, fl)]
        else:
            roof_pts = [(0, 0), (fw, 0), (fw, fl), (0, fl)]

        roof_patch = plt.Polygon(
            roof_pts, closed=True,
            facecolor=ROOF_FILL, edgecolor=ROOF_STROKE, linewidth=2.5, zorder=1
        )
        ax.add_patch(roof_patch)

        # ── Panele ────────────────────────────────────────────────────────────
        if all_panels:
            # Użyj prawdziwych pozycji z backendu
            # Backend: y=0 na dole (jak matematyczny układ)
            for p in all_panels:
                px = float(p.get('x', 0)) * scale
                # Konwersja: backend ma y od dołu, matplotlib też od dołu → OK
                py = float(p.get('y', 0)) * scale
                pw = float(p.get('width', 1.0)) * scale
                ph = float(p.get('height', 0.5)) * scale
                rect = mpatches.Rectangle(
                    (px, py), pw, ph,
                    facecolor=PANEL_FILL, edgecolor=PANEL_EDGE,
                    linewidth=0.6, zorder=3
                )
                ax.add_patch(rect)
        else:
            # Fallback: narysuj siatkę paneli w kształcie dachu
            pw = 1.13 * scale
            ph = 0.57 * scale
            gap = 0.04 * scale
            y = 0.3 * scale
            while y + ph <= fl - 0.2 * scale:
                x = 0.3 * scale
                while x + pw <= fw - 0.2 * scale:
                    rect = mpatches.Rectangle(
                        (x, y), pw, ph,
                        facecolor=PANEL_FILL, edgecolor=PANEL_EDGE,
                        linewidth=0.6, zorder=3
                    )
                    ax.add_patch(rect)
                    x += pw + gap
                y += ph + gap

        # ── Wymiary ───────────────────────────────────────────────────────────
        arrowstyle = dict(arrowstyle="<->", color=DIM_COLOR, lw=1.0,
                          mutation_scale=8)

        # Szerokość (dół)
        ax.annotate("", xy=(fw, -0.3), xytext=(0, -0.3), arrowprops=arrowstyle)
        ax.text(fw / 2, -0.42, f"{facet_w:.1f} m",
                ha='center', va='top', fontsize=7.5, color=DIM_COLOR, fontweight='bold')

        # Długość (prawa strona)
        ax.annotate("", xy=(fw + 0.28, fl), xytext=(fw + 0.28, 0), arrowprops=arrowstyle)
        ax.text(fw + 0.42, fl / 2, f"{facet_l:.1f} m",
                ha='left', va='center', fontsize=7.5, color=DIM_COLOR,
                fontweight='bold', rotation=90)

        # ── Tytuł nad dachem ──────────────────────────────────────────────────
        ax.text(fw / 2, fl + 0.16,
                f"{panels_count} paneli · {total_kwp:.2f} kWp",
                ha='center', va='bottom', fontsize=9,
                color=TEXT_COLOR, fontweight='black')

        # BEZ legendy matplotlib — legenda jest w HTML template (s2_main_scenario.html)
        fig.tight_layout(pad=0.3)
        return self._fig_to_b64(fig)

    # ── główna metoda ─────────────────────────────────────────────────────────

    def generate(self, report_data: ReportData) -> bytes:
        std  = report_data.all_scenarios_results.get("standard") or {}
        eco  = report_data.all_scenarios_results.get("economy")  or {}
        prem = report_data.all_scenarios_results.get("premium")  or {}

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

        template = self.env.get_template('report/base.html')

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
        }

        rendered_html = template.render(**context)

        css_path = os.path.join(self.static_dir, 'report', 'report.css')
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