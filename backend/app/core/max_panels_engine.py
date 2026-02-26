# app/core/max_panels_engine.py
from typing import Dict, List
import math

from app.core.geometry import (
    calculate_equal_row_distribution,
    remove_orphan_modules,
    calculate_flat_roof_row_spacing,
)

from app.core.config import LayoutConfig

DEFAULT_MARGIN_SIDES = LayoutConfig.MARGIN_SIDES
DEFAULT_MARGIN_TOP = LayoutConfig.MARGIN_TOP
DEFAULT_MARGIN_BOTTOM = LayoutConfig.MARGIN_BOTTOM
DEFAULT_GAP = LayoutConfig.GAP

MIN_PANELS_PER_ROW = 2


def _safe_int_floor(value: float) -> int:
    # Dodajemy epsilon (0.0001), aby uniknąć błędów typu 2.99999999 -> 2 zamiast 3
    return int(math.floor(value + 0.0001)) if value > 0 else 0


def compute_max_panels_rectangular(
    roof_width: float,
    roof_length: float,
    panel_width: float,
    panel_height: float,
    margin_sides: float = DEFAULT_MARGIN_SIDES,
    margin_top: float = DEFAULT_MARGIN_TOP,
    margin_bottom: float = DEFAULT_MARGIN_BOTTOM,
    gap: float = DEFAULT_GAP,
) -> Dict:
    warnings = []

    usable_width = roof_width - 2 * margin_sides
    usable_length = roof_length - margin_top - margin_bottom

    if usable_width <= 0 or usable_length <= 0:
        return {"placed_count": 0, "row_distribution": [], "warnings": ["rectangular: unusable"]}

    max_per_row = _safe_int_floor((usable_width + gap) / (panel_width + gap))
    max_rows = _safe_int_floor((usable_length + gap) / (panel_height + gap))

    if max_per_row <= 0 or max_rows <= 0:
        return {"placed_count": 0, "row_distribution": [], "warnings": ["rectangular: too small"]}

    total_capacity = max_per_row * max_rows

    row_distribution = calculate_equal_row_distribution(total_capacity, max_per_row)
    row_distribution, removed = remove_orphan_modules(row_distribution, MIN_PANELS_PER_ROW)

    if removed > 0:
        warnings.append("removed_orphans")

    return {
        "placed_count": sum(row_distribution),
        "row_distribution": row_distribution,
        "warnings": warnings,
    }


def compute_max_panels_flat(
    roof_width: float,
    roof_length: float,
    panel_width: float,
    panel_length: float,
    tilt_angle_deg: float,
    min_sun_elevation_deg: float = 17.0,
    margin_sides: float = DEFAULT_MARGIN_SIDES,
    margin_top: float = DEFAULT_MARGIN_TOP,
    margin_bottom: float = DEFAULT_MARGIN_BOTTOM,
    gap: float = DEFAULT_GAP,
) -> Dict:
    """
    Oblicza pojemność dachu płaskiego/gruntu.
    Poprawka: Ostatni rząd nie potrzebuje odstępu na cień za sobą.
    """
    warnings = []

    usable_width = roof_width - 2 * margin_sides
    usable_length = roof_length - margin_top - margin_bottom

    if usable_width <= 0 or usable_length <= 0:
        return {"placed_count": 0, "row_distribution": [], "warnings": ["unusable_area"]}

    # 1. Odstęp między konstrukcjami (Anti-Shading)
    row_spacing = calculate_flat_roof_row_spacing(
        panel_length_m=panel_length,
        tilt_angle_deg=tilt_angle_deg,
        min_sun_elevation_deg=min_sun_elevation_deg,
    )

    # 2. Rzut poziomy samej konstrukcji (bez cienia)
    row_depth = panel_length * math.cos(math.radians(tilt_angle_deg))

    # 3. Obliczamy ile rzędów wejdzie (N rzędów potrzebuje N-1 odstępów)
    # Wzór: (L + spacing) / (depth + spacing)
    if (row_depth + row_spacing) > 0:
        max_rows = _safe_int_floor((usable_length + row_spacing) / (row_depth + row_spacing))
    else:
        max_rows = 0

    # Zabezpieczenie: jeśli teren jest mniejszy niż rzut nawet jednej konstrukcji
    if usable_length < row_depth:
        max_rows = 0

    max_per_row = _safe_int_floor((usable_width + gap) / (panel_width + gap))

    if max_rows <= 0 or max_per_row <= 0:
        return {"placed_count": 0, "row_distribution": [], "warnings": ["too_small"]}

    total_capacity = max_rows * max_per_row

    # Rozkład rzędów
    row_distribution = calculate_equal_row_distribution(total_capacity, max_per_row)
    
    return {
        "placed_count": sum(row_distribution),
        "row_distribution": row_distribution,
        "warnings": warnings,
    }
    
def compute_max_panels_triangle(
    base: float,
    height: float,
    panel_width: float,
    panel_height: float,
    margin_sides: float = DEFAULT_MARGIN_SIDES,
    margin_bottom: float = DEFAULT_MARGIN_BOTTOM,
    gap: float = DEFAULT_GAP,
) -> Dict:
    """
    Finalna wersja obliczeń trójkąta:
    - szerokość liczona na górnej krawędzi panelu
    - W(y) = base_work * (1 - y / height_work)
    - minimum 2 panele w rzędzie
    - iteracja rzędów od dołu do góry
    """

    warnings = []

    # 1. Obszar roboczy trójkąta (padding z każdej strony)
    base_work = base - 2 * margin_sides
    height_work = height - 2 * margin_bottom

    if base_work <= 0 or height_work <= 0:
        return {"placed_count": 0, "row_distribution": [], "warnings": ["triangle: unusable"]}

    row_distribution = []
    y_start = 0.0  # zaczynamy od dołu obszaru roboczego

    # 2. Iteracja rzędów
    while True:
        row_top = y_start + panel_height

        # panel nie mieści się w pionie
        if row_top > height_work:
            break

        # 3. Szerokość trójkąta w najwęższym miejscu rzędu (górna krawędź panelu)
        t = row_top / height_work
        available_width = base_work * (1 - t)

        # 4. Liczba paneli w rzędzie
        max_in_row = int((available_width + gap) // (panel_width + gap))

        if max_in_row < 2:
            break  # nie ma sensu dalej, bo wyżej będzie tylko wężej

        row_distribution.append(max_in_row)

        # 5. Kolejny rząd
        y_start += panel_height + gap

    if not row_distribution:
        return {"placed_count": 0, "row_distribution": [], "warnings": ["triangle: too small"]}

    return {
        "placed_count": sum(row_distribution),
        "row_distribution": row_distribution,
        "warnings": warnings,
    }


def compute_max_panels_trapezoid(base_a, base_b, height, panel_width, panel_height):
    """Trapez Równoramienny: Symetryczne zwężanie z obu stron."""
    warnings, row_distribution = [], []
    y = LayoutConfig.MARGIN_BOTTOM
    while y + panel_height <= height:
        check_y = (y + panel_height) if base_b < base_a else y
        t = check_y / height if height > 0 else 0
        current_width = base_a + (base_b - base_a) * t
        # Odejmujemy marginesy z DWÓCH stron (symetria)
        usable_width = current_width - (2 * LayoutConfig.MARGIN_SIDES)
        max_in_row = _safe_int_floor((usable_width + LayoutConfig.GAP) / (panel_width + LayoutConfig.GAP))
        if max_in_row > 0: row_distribution.append(max_in_row)
        y += panel_height + LayoutConfig.GAP
    return {"placed_count": sum(row_distribution), "row_distribution": row_distribution, "warnings": warnings}

def compute_max_panels_trapezoid_right(base_a, base_b, height, panel_width, panel_height):
    """Trapez Prostokątny: Jedna strona pionowa, jeden skos."""
    warnings, row_distribution = [], []
    y = LayoutConfig.MARGIN_BOTTOM
    while y + panel_height <= height:
        check_y = (y + panel_height) if base_b < base_a else y
        t = check_y / height if height > 0 else 0
        current_width = base_a + (base_b - base_a) * t
        # KLUCZ: Marginesy są z obu stron, ale skos zabiera szerokość tylko z JEDNEJ strony
        # Szerokość robocza = szerokość całkowita - margines lewy - margines prawy
        usable_width = current_width - (2 * LayoutConfig.MARGIN_SIDES)
        max_in_row = _safe_int_floor((usable_width + LayoutConfig.GAP) / (panel_width + LayoutConfig.GAP))
        if max_in_row > 0: row_distribution.append(max_in_row)
        y += panel_height + LayoutConfig.GAP
    return {"placed_count": sum(row_distribution), "row_distribution": row_distribution, "warnings": warnings}

def compute_max_panels_rhombus(
    base_a: float,
    slope_h: float,
    offset_x: float,
    panel_width: float,
    panel_height: float,
    margin_sides: float = 0.30,
    margin_bottom: float = 0.30,
    gap: float = 0.05,
) -> Dict:
    warnings = []
    row_distribution = []
    
    usable_h = slope_h - (2 * margin_bottom)
    usable_a = base_a - (2 * margin_sides)
    
    if usable_h < panel_height or usable_a < panel_width:
        return {"placed_count": 0, "row_distribution": [], "warnings": ["Dach zbyt mały"]}

    # Obliczamy stratę szerokości na jeden rząd paneli wynikającą z kąta alpha
    # Strata = panel_height / tan(alpha). Ponieważ tan(alpha) = h / offset_x:
    # Strata = panel_height * (offset_x / slope_h)
    width_loss_per_row = offset_x * (panel_height / slope_h) if slope_h > 0 else 0
    
    # W równoległoboku, aby prostokątny panel zmieścił się w "pochylonym" rzędzie,
    # efektywna szerokość rzędu dla paneli to: podstawa - strata_na_skos
    effective_row_width = usable_a - width_loss_per_row

    max_in_row = int((effective_row_width + gap) // (panel_width + gap))
    num_rows = int((usable_h + gap) // (panel_height + gap))
    
    if max_in_row >= 1 and num_rows >= 1:
        row_distribution = [max_in_row] * num_rows

    return {
        "placed_count": sum(row_distribution),
        "row_distribution": row_distribution,
        "warnings": warnings,
    }
    
def compute_max_panels_rhombus_eq(
    base_a: float,
    slope_h: float,
    offset_x: float,
    panel_width: float,
    panel_height: float,
    margin_sides: float = 0.30,
    margin_bottom: float = 0.30,
    gap: float = 0.05,
) -> Dict:
    """Alias dla spójności z dyspozytorem."""
    return compute_max_panels_rhombus(
        base_a, slope_h, offset_x, panel_width, panel_height, margin_sides, margin_bottom, gap
    )


def compute_max_panels_for_facet(facet, panel_width_m: float, panel_height_m: float) -> Dict:
    from app.core.facet_geometry import compute_facet_area_and_length
    geom = compute_facet_area_and_length(facet)
    t = facet.roof_type

    
    # 1. DACH SKOŚNY (v4.2 - Fix: Użycie skosu zamiast rzutu budynku)
    if t in ["rectangular", "gable", "hip"]:
        return compute_max_panels_rectangular(
            roof_width=facet.width,
            roof_length=geom["slope_length"], # <--- KLUCZOWA POPRAWKA
            panel_width=panel_width_m,
            panel_height=panel_height_m
        )

    # 2. DACH PŁASKI (Stelaże 1-rzędowe, wymagane odstępy)
    if t == "flat":
        # Zabezpieczenie przed None (Source of Truth Fix)
        r_width = facet.width or 0
        r_length = facet.length or getattr(facet, 'real_roof_length', 0) or 0
        
        return compute_max_panels_flat(
            roof_width=r_width,
            roof_length=r_length,
            panel_width=panel_width_m,
            panel_length=panel_height_m,
            tilt_angle_deg=15.0 # Standardowy kąt ekierki na dachu płaskim
        )

    # 3. GRUNT (Stelaże 2-rzędowe w pionie, inne odstępy)
    if t == "ground":
        r_width = facet.width or 0
        r_length = facet.length or getattr(facet, 'real_roof_length', 0) or 0
        
        # Obliczamy liczbę "stołów" (każdy stół ma 2 panele w pionie)
        result = compute_max_panels_flat(
            roof_width=r_width,
            roof_length=r_length,
            panel_width=panel_width_m,
            panel_length=panel_height_m * 2, # Stelaż na 2 panele
            tilt_angle_deg=35.0
        )
        
        # Ponieważ compute_max_panels_flat liczy "obiekty", a nasz obiekt to stelaż 2-panelowy,
        # musimy pomnożyć wynik przez 2, aby otrzymać łączną liczbę paneli.
        result["placed_count"] = result["placed_count"] * 2
        # Aktualizujemy rozkład rzędów (każdy rząd ma teraz 2x więcej paneli)
        result["row_distribution"] = [count * 2 for count in result["row_distribution"]]
        
        return result
    # 4. DACH TRÓJKĄTNY (Przywrócona logika)
    if t == "triangle":
        return compute_max_panels_triangle(
            base=facet.triangle_base,
            height=geom["slope_length"], # Wysokość skosu trójkąta
            panel_width=panel_width_m,
            panel_height=panel_height_m
        )

    # 4. TRAPEZY (ROZDZIELONE)
    if t == "trapezoid":
        return compute_max_panels_trapezoid(facet.trapezoid_base_a, facet.trapezoid_base_b, geom["slope_length"], panel_width_m, panel_height_m)
    
    if t == "trapezoid_right":
        return compute_max_panels_trapezoid_right(facet.trapezoid_base_a, facet.trapezoid_base_b, geom["slope_length"], panel_width_m, panel_height_m)


    if t == "rhombus":
        geom = compute_facet_area_and_length(facet)
        return compute_max_panels_rhombus(
            base_a=facet.rhombus_diagonal_1,
            slope_h=geom["slope_length"],
            offset_x=geom["offset_x"] or 0.0,
            panel_width=panel_width_m,
            panel_height=panel_height_m
        )

    if t == "rhombus_eq":
        geom = compute_facet_area_and_length(facet)
        return compute_max_panels_rhombus_eq(
            base_a=facet.rhombus_diagonal_1,
            slope_h=geom["slope_length"],
            offset_x=geom["offset_x"] or 0.0,
            panel_width=panel_width_m,
            panel_height=panel_height_m
        )

    return compute_max_panels_rectangular(
        facet.width, facet.length, panel_width_m, panel_height_m
    )