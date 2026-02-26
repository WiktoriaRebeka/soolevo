# backend/app/core/geometry.py

import math
from typing import List, Tuple, Dict
from app.core.facet_geometry import compute_facet_area_and_length
from app.core.config import LayoutConfig
# Domyślne marginesy i odstępy
DEFAULT_MARGIN_SIDES = 0.30
DEFAULT_MARGIN_BOTTOM = 0.30
DEFAULT_GAP = 0.02

def to_radians(degrees: float) -> float:
    """Konwertuje stopnie na radiany."""
    return math.radians(degrees)


def get_effective_roof_length(
    length: float, angle_degrees: float, is_actual_length: bool
) -> float:
    """Decyduje, czy użyć długości bezpośrednio, czy przeliczyć przez kąt."""
    if is_actual_length:
        return round(length, 2)
    return calculate_real_roof_length(length, angle_degrees)


def calculate_real_roof_length(building_length: float, angle_degrees: float) -> float:
    """
    Oblicza realną długość połaci dachu (skosu).
    Zgodnie z logiką rzutu: bierzemy połowę długości budynku (run) i liczymy przeciwprostokątną.
    """
    if angle_degrees is None or angle_degrees == 0:
        return building_length
    
    radians = to_radians(angle_degrees)
    cos_val = math.cos(radians)
    
    if cos_val <= 0:
        return building_length

    # KLUCZOWA POPRAWKA: Dzielimy długość budynku na pół przed nałożeniem cosinusa
    run = building_length / 2.0
    real_length = run / cos_val
    
    return round(real_length, 2)


def calculate_flat_roof_row_spacing(
    panel_length_m: float,
    tilt_angle_deg: float = 30.0,
    min_sun_elevation_deg: float = 17.0,    # Polska, grudzień (52°N)
) -> float:
    """
    Oblicza minimalny odstęp między rzędami paneli na dachu płaskim/gruncie,
    aby uniknąć zacienienia jednego rzędu przez drugi zimą.

    Args:
        panel_length_m: Długość panelu [m] (wymiar w kierunku nachylenia)
        tilt_angle_deg: Kąt nachylenia stelaża [°] (typowo 25-35°)
        min_sun_elevation_deg: Min. kąt elewacji słońca [°]
                               Polska zima (52°N): ~15-17° (21 grudnia, południe)

    Returns:
        float: Wymagany odstęp [m] od końca jednego rzędu do początku następnego

    Porównanie:
        JS:     sunAngle=45° → spacing=1.05m (za mało, zacienienie zimą!)
        Python: sunAngle=17° → spacing=3.44m (prawidłowe dla polskiej zimy)
    """
    panel_projected_height = panel_length_m * math.sin(math.radians(tilt_angle_deg))
    tan_sun = math.tan(math.radians(min_sun_elevation_deg))

    if tan_sun <= 0:
        return panel_length_m * 3  # Fallback: 3× długość panelu

    spacing = panel_projected_height / tan_sun
    return round(spacing, 2)


def calculate_flat_roof_effective_length(
    building_length: float,
    panel_length_m: float,
    tilt_angle_deg: float = 30.0,
    min_sun_elevation_deg: float = 17.0,
) -> float:
    """
    Oblicza efektywną długość dachu płaskiego po uwzględnieniu spacingu.

    Zwraca długość, w której można umieścić panele (building_length minus
    spacing potrzebny za każdym rzędem).

    Portowane z JS:
        effectiveBuildingLength = buildingLength - rowSpacing
    """
    spacing = calculate_flat_roof_row_spacing(
        panel_length_m=panel_length_m,
        tilt_angle_deg=tilt_angle_deg,
        min_sun_elevation_deg=min_sun_elevation_deg,
    )

    # Efektywna długość uwzględniająca spacing
    # Każdy rząd zajmuje: panel_length × cos(tilt) + spacing
    row_footprint = panel_length_m * math.cos(math.radians(tilt_angle_deg)) + spacing
    rows_fit = max(1, int(building_length / row_footprint))

    effective_length = rows_fit * panel_length_m * math.cos(math.radians(tilt_angle_deg))
    return round(effective_length, 2)


# =============================================================================
# ISTNIEJĄCE: Klasy geometryczne i grid paneli (bez zmian)
# =============================================================================

class Point:
    """Reprezentuje punkt na płaszczyźnie dachu (X, Y)."""
    def __init__(self, x: float, y: float):
        self.x = round(x, 3)
        self.y = round(y, 3)

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"


class Rectangle:
    def __init__(self, x: float, y: float, width: float, height: float, label: str = "object"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.label = label

    def __repr__(self):
        return f"Rectangle(label={self.label}, x={self.x}, y={self.y}, w={self.width}, h={self.height})"

    def get_area(self) -> float:
        return round(self.width * self.height, 2)

    def collides_with(self, other: "Rectangle") -> bool:
        return not (
            self.x + self.width <= other.x
            or self.x >= other.x + other.width
            or self.y + self.height <= other.y
            or self.y >= other.y + other.height
        )

    def is_entirely_inside_polygon(self, polygon: list) -> bool:
        corners = [
            (self.x, self.y),
            (self.x + self.width, self.y),
            (self.x, self.y + self.height),
            (self.x + self.width, self.y + self.height),
        ]
        for cx, cy in corners:
            if not is_point_in_polygon(cx, cy, polygon):
                return False
        return True


def generate_rectangular_grid_with_obstacles(
    roof_width: float,
    roof_length: float,
    panel_width: float,
    panel_height: float,
    obstacles_count: int = 0,
    roof_type: str = "rectangular",
    gap: float = 0.10,
    margin: float = 0.15,
):
    """Generuje siatkę paneli PV na prostokątnym dachu."""
    usable_width = roof_width - 2 * margin
    usable_length = roof_length - 2 * margin

    if usable_width <= 0 or usable_length <= 0:
        return []

    cols = int((usable_width + gap) // (panel_width + gap))
    rows = int((usable_length + gap) // (panel_height + gap))

    grid = []
    label_counter = 1

    for r in range(rows):
        for c in range(cols):
            x = margin + c * (panel_width + gap)
            y = margin + r * (panel_height + gap)
            rect = Rectangle(x=x, y=y, width=panel_width, height=panel_height, label=f"P{label_counter}")
            grid.append(rect)
            label_counter += 1

    if obstacles_count > 0:
        grid = grid[:-obstacles_count] if obstacles_count < len(grid) else []

    return grid


def calculate_rectangle_area(width: float, length: float) -> float:
    """Oblicza pole powierzchni prostokąta."""
    if width <= 0 or length <= 0:
        raise ValueError("Wymiary dachu muszą być większe od zera!")
    return round(width * length, 2)


def calculate_triangle_area(base: float, height: float) -> float:
    """Oblicza pole powierzchni trójkąta."""
    if base <= 0 or height <= 0:
        raise ValueError("Wymiary trójkąta muszą być większe od zera!")
    return round(0.5 * base * height, 2)


def calculate_trapezoid_area(base_a: float, base_b: float, height: float) -> float:
    """Oblicza pole powierzchni trapezu."""
    if base_a <= 0 or base_b <= 0 or height <= 0:
        raise ValueError("Wymiary trapezu muszą być większe od zera!")
    return round(0.5 * (base_a + base_b) * height, 2)


def is_point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """Sprawdza, czy punkt (x, y) jest wewnątrz wielokąta (Ray Casting)."""
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def calculate_equal_row_distribution(
    total_panels: int,
    max_panels_per_row: int,
) -> List[int]:
    """
    Oblicza równy rozkład paneli na rzędy.
    
    Algorithm:
        1. Oblicz liczbę rzędów: rows = ceil(total / max_per_row)
        2. Base panels: base = total // rows
        3. Extra panels: extra = total % rows
        4. Pierwsze 'extra' rzędów dostaje +1 panel
    
    Args:
        total_panels: Całkowita liczba paneli
        max_panels_per_row: Max paneli w jednym rzędzie
    
    Returns:
        Lista liczby paneli w każdym rzędzie [rząd1, rząd2, ...]
    
    Example:
        >>> calculate_equal_row_distribution(16, 13)
        [8, 8]  # Nie [13, 3]!
        
        >>> calculate_equal_row_distribution(17, 13)
        [9, 8]
        
        >>> calculate_equal_row_distribution(20, 10)
        [10, 10]
    """
    if total_panels <= 0 or max_panels_per_row <= 0:
        return []
    
    # Minimalna liczba rzędów
    num_rows = math.ceil(total_panels / max_panels_per_row)
    
    # Równy podział
    base_panels = total_panels // num_rows
    extra_panels = total_panels % num_rows
    
    # Buduj rozkład
    row_distribution = []
    for i in range(num_rows):
        if i < extra_panels:
            row_distribution.append(base_panels + 1)
        else:
            row_distribution.append(base_panels)
    
    return row_distribution


def remove_orphan_modules(
    row_distribution: List[int],
    min_panels_per_row: int = 2,
) -> Tuple[List[int], int]:
    """
    Usuwa rzędy z zbyt małą liczbą paneli (orphan modules).
    
    Uzasadnienie fizyczne:
        - 1 panel w rzędzie = 1 panel w stringu
        - Za niskie napięcie dla MPPT inwertera
        - Lepiej usunąć niż mieć niefunkcjonalny string
    
    Args:
        row_distribution: Lista paneli per rząd
        min_panels_per_row: Minimalna liczba (domyślnie 2)
    
    Returns:
        (nowa_lista, liczba_usuniętych_paneli)
    
    Example:
        >>> remove_orphan_modules([8, 8, 1], 2)
        ([8, 8], 1)
    """
    filtered = [r for r in row_distribution if r >= min_panels_per_row]
    removed_count = sum(row_distribution) - sum(filtered)
    return filtered, removed_count


def generate_rectangular_grid_equal_rows(
    roof_length_m: float,
    roof_width_m: float,
    panel_length_m: float,
    panel_width_m: float,
    orientation: str = "portrait",
    margin_sides_m: float = 0.30,
    margin_top_m: float = 0.50,     # Kalenica
    margin_bottom_m: float = 0.30,  # Okap
    row_spacing_m: float = 0.05,
    min_panels_per_row: int = 2,
) -> dict:
    """
    Generuje układ prostokątny z równym rozkładem paneli na rzędy.
    
    ZMIANA v3.0: Równe rzędy zamiast maksymalizacji pierwszego.
    
    Returns:
        dict: {
            'panels': [{'x': m, 'y': m}, ...],
            'row_distribution': [8, 8],
            'placed_count': 16,
            'warnings': [str],
        }
    """
    warnings = []
    
    # Wymiary panelu
    if orientation == "portrait":
        panel_l = panel_length_m
        panel_w = panel_width_m
    else:  # landscape
        panel_l = panel_width_m
        panel_w = panel_length_m
    
    # Usable area
    usable_length = roof_length_m - margin_top_m - margin_bottom_m
    usable_width = roof_width_m - 2 * margin_sides_m
    
    if usable_length <= 0 or usable_width <= 0:
        warnings.append("⚠️ Marginesy większe niż dach!")
        return {
            "panels": [],
            "row_distribution": [],
            "placed_count": 0,
            "warnings": warnings,
        }
    
    # Max paneli w rzędzie (wzdłuż szerokości)
    max_panels_width = int(usable_width / panel_w)
    
    # Max liczba rzędów (wzdłuż długości)
    max_rows = int(usable_length / (panel_l + row_spacing_m))
    
    # Całkowita pojemność
    total_capacity = max_panels_width * max_rows
    
    # 📌 RÓWNY ROZKŁAD
    row_distribution = calculate_equal_row_distribution(
        total_panels=total_capacity,
        max_panels_per_row=max_panels_width,
    )
    
    # 📌 USUŃ ORPHAN MODULES
    row_distribution, removed = remove_orphan_modules(
        row_distribution, 
        min_panels_per_row
    )
    
    if removed > 0:
        warnings.append(
            f"⚠️ Usunięto {removed} panel(e/i) (rzędy z <{min_panels_per_row} panelami)"
        )
    
    # Generuj współrzędne
    panels = []
    y_offset = margin_bottom_m
    
    for row_idx, panels_in_row in enumerate(row_distribution):
        # Centrowanie w rzędzie
        row_width_used = panels_in_row * panel_w
        x_start = margin_sides_m + (usable_width - row_width_used) / 2
        
        for col_idx in range(panels_in_row):
            x = x_start + col_idx * panel_w
            y = y_offset
            
            panels.append({
                "x": round(x, 2),
                "y": round(y, 2),
                "row": row_idx + 1,
                "col": col_idx + 1,
            })
        
        y_offset += panel_l + row_spacing_m
    
    return {
        "panels": panels,
        "row_distribution": row_distribution,
        "placed_count": len(panels),
        "warnings": warnings,
    }


def generate_layout_rectangular(facet, panel_width, panel_height, count):
    layout = []
    geom = compute_facet_area_and_length(facet)
    width = facet.width or 0
    length = geom["slope_length"]

    if width <= 0 or length <= 0:
        return layout

    # UŻYWAMY GLOBALNEJ KONFIGURACJI ZAMIAST HARDKODOWANYCH WARTOŚCI
    margin_sides = LayoutConfig.MARGIN_SIDES
    margin_bottom = LayoutConfig.MARGIN_BOTTOM
    gap = LayoutConfig.GAP

    usable_width = width - 2 * margin_sides
    
    # Obliczamy liczbę kolumn DOKŁADNIE tak samo jak w max_panels_engine
    cols = math.floor((usable_width + gap) / (panel_width + gap))
    
    if cols <= 0:
        return layout

    placed = 0
    # Iterujemy po rzędach i kolumnach
    rows = math.ceil(count / cols)

    for r in range(rows):
        # Sprawdzamy ile paneli faktycznie zostanie w tym rzędzie (ostatni może być niepełny)
        panels_in_this_row = min(cols, count - placed)
        
        # Szerokość zajęta przez panele w tym konkretnym rzędzie (do centrowania)
        row_width_used = panels_in_this_row * panel_width + (panels_in_this_row - 1) * gap
        x_start = margin_sides + (usable_width - row_width_used) / 2

        for c in range(panels_in_this_row):
            x = x_start + c * (panel_width + gap)
            y = margin_bottom + r * (panel_height + gap)

            # ZABEZPIECZENIE: Nie dodawaj panela, jeśli wystaje poza wysokość dachu
            if y + panel_height > length + 0.01: # 1cm tolerancji
                continue

            layout.append({
                "x": round(x, 3),
                "y": round(y, 3),
                "width": panel_width,
                "height": panel_height,
                "label": f"P{placed+1}",
            })
            placed += 1

    return layout

def generate_layout_triangle(facet, panel_width, panel_height, count):
    """Layout trójkąta z poprawnym centrowaniem rzędów względem osi dachu."""
    geom = compute_facet_area_and_length(facet)
    base = facet.triangle_base or 0
    height = geom["slope_length"]

    margin_sides = LayoutConfig.MARGIN_SIDES
    margin_bottom = LayoutConfig.MARGIN_BOTTOM
    gap = LayoutConfig.GAP

    base_work = base - 2 * margin_sides
    height_work = height - margin_bottom

    if base_work <= 0 or height_work <= 0: return []

    layout = []
    y_start = 0.0
    placed = 0

    # Obliczamy rozkład rzędów, aby uniknąć samotnych paneli
    # (Uproszczone: trójkąt i tak wymusza zwężanie, więc bierzemy max dostępne)
    while placed < count:
        row_top = y_start + panel_height
        if row_top > height_work: break

        t = row_top / height_work
        available_width = base_work * (1 - t)
        max_in_row = int((available_width + gap) // (panel_width + gap))

        if max_in_row < 2: break

        panels_in_row = min(max_in_row, count - placed)
        row_width_used = panels_in_row * panel_width + (panels_in_row - 1) * gap
        
        # KLUCZ: Centrowanie paska w trójkącie + centrowanie paneli w pasku
        slice_offset_x = (base - available_width) / 2
        x_start_in_slice = (available_width - row_width_used) / 2
        x_base = slice_offset_x + x_start_in_slice

        for i in range(panels_in_row):
            layout.append({
                "x": round(x_base + i * (panel_width + gap), 3),
                "y": round(y_start + margin_bottom, 3),
                "width": panel_width,
                "height": panel_height,
                "label": f"P{placed + 1}",
            })
            placed += 1
        y_start += panel_height + gap
    return layout
def generate_layout_trapezoid(facet, panel_width, panel_height, count):
    """Trapez Równoramienny: Centrowanie paneli względem osi."""
    geom = compute_facet_area_and_length(facet)
    a, b, h = (facet.trapezoid_base_a or 0), (facet.trapezoid_base_b or 0), geom["slope_length"]
    gap, m_sides, m_bottom = LayoutConfig.GAP, LayoutConfig.MARGIN_SIDES, LayoutConfig.MARGIN_BOTTOM
    placed, y, layout = 0, 0.0, []

    while placed < count and y + panel_height <= h - m_bottom:
        check_y = (y + panel_height) if b < a else y
        t = check_y / h if h > 0 else 0
        available_width = a + (b - a) * t
        max_cols = math.floor((available_width - 2*m_sides + gap) / (panel_width + gap))
        panels_in_row = min(max_cols, count - placed)
        if panels_in_row <= 0: break
        
        row_width_used = panels_in_row * panel_width + (panels_in_row - 1) * gap
        # CENTROWANIE: (Szerokość dachu w tym miejscu - szerokość rzędu) / 2 + przesunięcie paska
        slice_offset_x = (max(a, b) - available_width) / 2
        x_start_in_slice = (available_width - row_width_used) / 2
        x_base = slice_offset_x + x_start_in_slice

        for c in range(panels_in_row):
            layout.append({"x": round(x_base + c * (panel_width + gap), 3), "y": round(y + m_bottom, 3), "width": panel_width, "height": panel_height, "label": f"P{placed+1}"})
            placed += 1
        y += panel_height + gap
    return layout

def generate_layout_trapezoid_right(facet, panel_width, panel_height, count):
    """Trapez Prostokątny: Wyrównanie do pionowej krawędzi (lewej)."""
    geom = compute_facet_area_and_length(facet)
    a, b, h = (facet.trapezoid_base_a or 0), (facet.trapezoid_base_b or 0), geom["slope_length"]
    gap, m_sides, m_bottom = LayoutConfig.GAP, LayoutConfig.MARGIN_SIDES, LayoutConfig.MARGIN_BOTTOM
    placed, y, layout = 0, 0.0, []

    while placed < count and y + panel_height <= h - m_bottom:
        check_y = (y + panel_height) if b < a else y
        t = check_y / h if h > 0 else 0
        available_width = a + (b - a) * t
        # Liczymy ile wejdzie od pionowej ściany do skosu
        max_cols = math.floor((available_width - 2*m_sides + gap) / (panel_width + gap))
        panels_in_row = min(max_cols, count - placed)
        if panels_in_row <= 0: break
        
        # WYRÓWNANIE DO LEWEJ: startujemy od marginesu, bo lewa ściana jest pionowa (x=0)
        x_base = m_sides 

        for c in range(panels_in_row):
            layout.append({"x": round(x_base + c * (panel_width + gap), 3), "y": round(y + m_bottom, 3), "width": panel_width, "height": panel_height, "label": f"P{placed+1}"})
            placed += 1
        y += panel_height + gap
    return layout

def generate_layout_rhombus(facet, panel_width, panel_height, count):
    """Layout równoległoboku z precyzyjnym centrowaniem wewnątrz skośnych boków."""
    layout = []
    geom = compute_facet_area_and_length(facet)
    a, h, offset = (facet.rhombus_diagonal_1 or 0), geom["slope_length"], (geom["offset_x"] or 0.0)
    gap, m_sides, m_bottom = LayoutConfig.GAP, LayoutConfig.MARGIN_SIDES, LayoutConfig.MARGIN_BOTTOM
    
    # Szerokość, którą tracimy przez pochylenie boku na wysokości jednego panela
    width_loss = abs(offset) * (panel_height / h) if h > 0 else 0
    usable_width = a - (2 * m_sides) - width_loss
    
    max_in_row = int((usable_width + gap) // (panel_width + gap))
    if max_in_row <= 0: return []

    placed, y = 0, m_bottom
    while placed < count and (y + panel_height) <= (h - m_bottom):
        # Obliczamy przesunięcie lewej krawędzi dachu na tej wysokości
        # Jeśli dach pochyla się w prawo (offset > 0), najbardziej wysunięty w lewo 
        # punkt rzędu to jego górny lewy róg.
        row_roof_left_edge = (y / h) * offset
        if offset > 0:
            row_roof_left_edge = ((y + panel_height) / h) * offset

        panels_in_row = min(max_in_row, count - placed)
        row_width_used = panels_in_row * panel_width + (panels_in_row - 1) * gap
        
        # Startujemy od krawędzi dachu + margines + centrowanie wewnątrz wolnego miejsca
        x_base = row_roof_left_edge + m_sides + (usable_width - row_width_used) / 2

        for i in range(panels_in_row):
            layout.append({
                "x": round(x_base + i * (panel_width + gap), 3),
                "y": round(y, 3),
                "width": panel_width,
                "height": panel_height,
                "label": f"P{placed + 1}"
            })
            placed += 1
        y += panel_height + gap
    return layout



def generate_layout_flat(facet, panel_width, panel_height, count):
    """
    Dedykowany generator dla dachu płaskiego/gruntu.
    Uwzględnia odstępy Anti-Shading między rzędami.
    """
    layout = []
    width = facet.width or 0
    length = facet.length or 0
    # Kąt nachylenia stelaża (ekierki) - domyślnie 15 stopni dla płaskich
    tilt = facet.angle if (facet.angle and facet.angle > 0) else 15.0

    margin_sides = LayoutConfig.MARGIN_SIDES
    margin_bottom = LayoutConfig.MARGIN_BOTTOM
    gap = LayoutConfig.GAP

    # 1. Obliczamy odstęp między rzędami (Anti-Shading)
    spacing = calculate_flat_roof_row_spacing(
        panel_length_m=panel_height,
        tilt_angle_deg=tilt,
        min_sun_elevation_deg=17.0
    )

    # 2. Rzut poziomy panela (ile miejsca zajmuje pochylony panel na dachu)
    row_footprint_y = panel_height * math.cos(math.radians(tilt))
    
    usable_width = width - 2 * margin_sides
    cols = math.floor((usable_width + gap) / (panel_width + gap))
    
    if cols <= 0: return []

    placed = 0
    current_y = margin_bottom

    while placed < count:
        # Sprawdzamy czy kolejny rząd zmieści się na dachu
        if current_y + row_footprint_y > length:
            break

        panels_in_this_row = min(cols, count - placed)
        row_width_used = panels_in_this_row * panel_width + (panels_in_this_row - 1) * gap
        x_start = margin_sides + (usable_width - row_width_used) / 2

        for c in range(panels_in_this_row):
            layout.append({
                "x": round(x_start + c * (panel_width + gap), 3),
                "y": round(current_y, 3),
                "width": panel_width,
                "height": round(row_footprint_y, 3), # Rysujemy rzut (krótszy panel)
                "label": f"P{placed+1}",
            })
            placed += 1
        
        # KLUCZ: Przesuwamy Y o rzut panela + wymagany odstęp Anti-Shading
        current_y += row_footprint_y + spacing

    return layout

def generate_layout_ground(facet, panel_width, panel_height, count):
    """
    Dedykowany generator dla gruntu - układ 2-rzędowy (2H).
    Panele w parze są 'scalone' (brak przerwy między dolnym a górnym).
    """
    layout = []
    width = facet.width or 0
    length = facet.length or 0
    tilt = 35.0 

    margin_sides = LayoutConfig.MARGIN_SIDES
    margin_bottom = LayoutConfig.MARGIN_BOTTOM
    gap = LayoutConfig.GAP

    # Odstęp między stołami (Anti-Shading)
    spacing = calculate_flat_roof_row_spacing(
        panel_length_m=panel_height * 2,
        tilt_angle_deg=tilt,
        min_sun_elevation_deg=17.0
    )

    # Rzut poziomy JEDNEGO panela (połowa głębokości stołu)
    panel_footprint_y = panel_height * math.cos(math.radians(tilt))
    
    usable_width = width - 2 * margin_sides
    cols = math.floor((usable_width + gap) / (panel_width + gap))
    
    if cols <= 0: return []

    placed = 0
    current_y = margin_bottom

    while placed < count:
        # Ile par (stołów) zostało do postawienia?
        remaining_pairs = math.ceil((count - placed) / 2)
        pairs_in_row = min(cols, remaining_pairs)
        
        if pairs_in_row <= 0: break
        
        # Sprawdzamy czy stół (2 panele) zmieści się na długość
        if current_y + (2 * panel_footprint_y) > length + 0.05: # 5cm tolerancji
            break

        row_width_used = pairs_in_row * panel_width + (pairs_in_row - 1) * gap
        x_start = margin_sides + (usable_width - row_width_used) / 2

        for c in range(pairs_in_row):
            # Panel DOLNY (P1, P3, P5...)
            layout.append({
                "x": round(x_start + c * (panel_width + gap), 3),
                "y": round(current_y, 3),
                "width": panel_width,
                "height": round(panel_footprint_y, 3),
                "label": f"P{placed+1}",
            })
            
            # Panel GÓRNY (P2, P4, P6...) - Scalony z dolnym
            if placed + 1 < count:
                layout.append({
                    "x": round(x_start + c * (panel_width + gap), 3),
                    "y": round(current_y + panel_footprint_y, 3),
                    "width": panel_width,
                    "height": round(panel_footprint_y, 3),
                    "label": f"P{placed+2}",
                })
            
            placed += 2
        
        # Skok do następnego rzędu stołów (Głębokość stołu + Odstęp na cień)
        current_y += (2 * panel_footprint_y) + spacing

    return layout

def generate_layout_for_facet(facet, panel_width, panel_height, count):
    """Główny dyspozytor layoutu - kieruje do odpowiedniej funkcji."""
    t = facet.roof_type
       
    if t == "ground":
        return generate_layout_ground(facet, panel_width, panel_height, count)
    
    if t == "flat":
        return generate_layout_flat(facet, panel_width, panel_height, count)
        
    if t in ["rectangular", "gable", "hip"]:
        return generate_layout_rectangular(facet, panel_width, panel_height, count)
        
    if t == "triangle":
        return generate_layout_triangle(facet, panel_width, panel_height, count)
        
    if t == "trapezoid":
        return generate_layout_trapezoid(facet, panel_width, panel_height, count)

    if t == "trapezoid_right":
        return generate_layout_trapezoid_right(facet, panel_width, panel_height, count)
        
    if t == "rhombus":
        return generate_layout_rhombus(facet, panel_width, panel_height, count)
        
    return []