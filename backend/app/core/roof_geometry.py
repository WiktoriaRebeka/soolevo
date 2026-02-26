# backend/app/core/roof_geometry.py - v2.1 (KOMPLETNA WERSJA)
"""
Moduł obsługi różnych typów dachów dla instalacji PV.

Wspierane typy:
1. Prostokątny (rectangular) - pitched/flat
2. Dwuspadowy (gable) - klasyczny dom
3. Czterospadowy (hip) - 4 połacie
4. Trójkątny (triangle) - poddasze
5. TRAPEZ (trapezoid) - naczółki, nietypowe połacie
6. ROMB (rhombus/diamond) - dachy diamentowe, nowoczesna architektura
7. Wielospadowy (complex) - nieregularny polygon
8. Naczółkowy (gambrel) - stodoła
9. Mansardowy (mansard) - francuski
10. Instalacja naziemna (ground)
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import math


@dataclass
class RoofDimensions:
    """Wymiary dachu - różne dla różnych typów"""
    roof_type: str
    
    # Wspólne dla większości
    width: float = 0.0
    length: float = 0.0
    angle: int = 30
    
    # Dla dwuspadowego/czterospadowego
    ridge_height: float = 0.0
    
    # Dla trójkątnego
    base: float = 0.0
    height: float = 0.0
    
    # NOWE: Dla trapezu
    trapezoid_base_a: float = 0.0  # Podstawa dolna
    trapezoid_base_b: float = 0.0  # Podstawa górna
    trapezoid_height: float = 0.0  # Wysokość
    
    # NOWE: Dla rombu
    rhombus_diagonal_1: float = 0.0
    rhombus_diagonal_2: float = 0.0
    rhombus_side_b: float = 0.0 # Nowe pole dla boku b
    
    # Dla wielospadowego
    polygon_coords: List[Tuple[float, float]] = None


# =============================================================================
# OBLICZANIE POWIERZCHNI DLA RÓŻNYCH TYPÓW
# =============================================================================

def calculate_roof_area(roof_dims: RoofDimensions) -> Dict:
    """
    Oblicza powierzchnię dachu w zależności od typu.
    
    Returns:
        {
            'total_area_m2': float,
            'usable_area_m2': float,
            'slope_count': int,
            'optimal_orientation': str,
            'formula_used': str,
            'note': str
        }
    """
    roof_type = roof_dims.roof_type.lower()
    
    if roof_type == "rectangular":
        return _calculate_rectangular_roof(roof_dims)
    
    elif roof_type == "gable":
        return _calculate_gable_roof(roof_dims)
    
    elif roof_type == "hip":
        return _calculate_hip_roof(roof_dims)
    
    elif roof_type == "triangle":
        return _calculate_triangle_roof(roof_dims)
    
    elif roof_type == "trapezoid":  # NOWE
        return _calculate_trapezoid_roof(roof_dims)
    
    elif roof_type == "rhombus":  # NOWE
        return _calculate_rhombus_roof(roof_dims)
    
    elif roof_type == "gambrel":
        return _calculate_gambrel_roof(roof_dims)
    
    elif roof_type == "mansard":
        return _calculate_mansard_roof(roof_dims)
    
    elif roof_type == "complex":
        return _calculate_complex_roof(roof_dims)
    
    elif roof_type == "ground":
        return _calculate_ground_installation(roof_dims)
    
    else:
        raise ValueError(f"Nieznany typ dachu: {roof_type}")


# =============================================================================
# IMPLEMENTACJE - PODSTAWOWE TYPY
# =============================================================================

def _calculate_rectangular_roof(dims: RoofDimensions) -> Dict:
    """Dach prostokątny (skośny lub płaski)."""
    if dims.angle > 0:
        slope_length = dims.length / math.cos(math.radians(dims.angle))
    else:
        slope_length = dims.length
    
    total_area = dims.width * slope_length
    usable_area = total_area * 0.85
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 1,
        'optimal_orientation': 'landscape',
        'formula_used': 'width × slope_length',
        'note': 'Dach prostokątny - najbardziej standardowy'
    }


def _calculate_gable_roof(dims: RoofDimensions) -> Dict:
    """Dach dwuspadowy (klasyczny dom)."""
    half_width = dims.width / 2
    slope_length = math.sqrt(half_width**2 + dims.ridge_height**2)
    
    single_slope_area = slope_length * dims.length
    total_area = single_slope_area * 2
    usable_area = single_slope_area * 0.85  # 1 połać
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 2,
        'optimal_orientation': 'portrait',
        'formula_used': '2 × (slope_length × length)',
        'note': 'Montaż na 1 połaci (południowej)'
    }


def _calculate_hip_roof(dims: RoofDimensions) -> Dict:
    """Dach czterospadowy (4 połacie)."""
    base_area = dims.width * dims.length
    hip_factor = 1.0 / math.cos(math.radians(dims.angle)) if dims.angle > 0 else 1.0
    
    total_area = base_area * hip_factor * 1.15
    usable_area = total_area * 0.70  # 2 optymalne połacie
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 4,
        'optimal_orientation': 'portrait',
        'formula_used': 'base_area × hip_factor × 1.15',
        'note': 'Montaż na 2 optymalnych połaciach (S, SW, SE)'
    }


def _calculate_triangle_roof(dims: RoofDimensions) -> Dict:
    """Dach trójkątny (poddasze, szopa)."""
    total_area = 0.5 * dims.base * dims.height
    usable_area = total_area * 0.80
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 1,
        'optimal_orientation': 'portrait',
        'formula_used': '0.5 × base × height',
        'note': 'Dach trójkątny - typowo poddasze lub szopa'
    }


# =============================================================================
# NOWE IMPLEMENTACJE - TRAPEZ I ROMB
# =============================================================================

def _calculate_trapezoid_roof(dims: RoofDimensions) -> Dict:
    """
    Dach trapezowy - NOWE!
    
    Występuje w:
    - Naczółkach dachów czterospadowych
    - Dachach mansardowych
    - Nietypowych połaciach po rozbudowie domu
    
    Potrzebne dane:
    - trapezoid_base_a: Podstawa dolna (dłuższa) w metrach
    - trapezoid_base_b: Podstawa górna (krótsza) w metrach
    - trapezoid_height: Wysokość trapezu w metrach
    
    Wzór: (a + b) / 2 × h
    """
    # Walidacja
    if dims.trapezoid_base_a <= 0 or dims.trapezoid_base_b <= 0 or dims.trapezoid_height <= 0:
        raise ValueError("Wszystkie wymiary trapezu muszą być większe od 0")
    
    # Sprawdź czy to faktycznie trapez (a != b)
    if abs(dims.trapezoid_base_a - dims.trapezoid_base_b) < 0.01:
        # To jest prostokąt, nie trapez!
        total_area = dims.trapezoid_base_a * dims.trapezoid_height
        note = "⚠️ Podane wymiary tworzą prostokąt (podstawy równe) - rozważ typ 'rectangular'"
    else:
        # Wzór na pole trapezu
        total_area = ((dims.trapezoid_base_a + dims.trapezoid_base_b) / 2) * dims.trapezoid_height
        note = f"Trapez: podstawa dolna {dims.trapezoid_base_a}m, górna {dims.trapezoid_base_b}m"
    
    # Margines bezpieczeństwa 15% (nietypowy kształt)
    usable_area = total_area * 0.85
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 1,
        'optimal_orientation': 'custom',  # Zależy od kształtu
        'formula_used': '((a + b) / 2) × h',
        'note': note
    }


def _calculate_rhombus_roof(dims: RoofDimensions) -> Dict:
    """
    Dach rombowy (diamentowy) - NOWE!
    
    Występuje w:
    - Nowoczesnej architekturze (dachy diamentowe)
    - Pawilonach, altanach
    - Dachach piramidowych (przekrój poziomy)
    
    Potrzebne dane:
    - rhombus_diagonal_1: Przekątna 1 (d1) w metrach
    - rhombus_diagonal_2: Przekątna 2 (d2) w metrach
    
    Wzór: (d1 × d2) / 2
    
    Uwaga: Romb to specjalny przypadek romboidu, gdzie wszystkie boki są równe.
    """
    # Walidacja
    if dims.rhombus_diagonal_1 <= 0 or dims.rhombus_diagonal_2 <= 0:
        raise ValueError("Obie przekątne rombu muszą być większe od 0")
    
    # Wzór na pole rombu
    total_area = (dims.rhombus_diagonal_1 * dims.rhombus_diagonal_2) / 2
    
    # Margines bezpieczeństwa 20% (nietypowy kształt, trudniejszy montaż)
    usable_area = total_area * 0.80
    
    # Oblicz długość boku (dla informacji)
    # bok = √((d1/2)² + (d2/2)²)
    side_length = math.sqrt(
        (dims.rhombus_diagonal_1 / 2)**2 + 
        (dims.rhombus_diagonal_2 / 2)**2
    )
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 1,
        'optimal_orientation': 'custom',
        'formula_used': '(d1 × d2) / 2',
        'note': f"Romb diamentowy - przekątne {dims.rhombus_diagonal_1}m × {dims.rhombus_diagonal_2}m, bok ~{side_length:.1f}m",
        'side_length_m': round(side_length, 2)  # Dodatkowa info
    }


# =============================================================================
# POZOSTAŁE TYPY
# =============================================================================

def _calculate_gambrel_roof(dims: RoofDimensions) -> Dict:
    """Dach naczółkowy / stodoła."""
    base_area = dims.width * dims.length
    gambrel_factor = 1.4
    
    total_area = base_area * gambrel_factor
    usable_area = total_area * 0.75
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 4,
        'optimal_orientation': 'landscape',
        'formula_used': 'base_area × 1.4',
        'note': 'Dach naczółkowy (stodoła) - 2 kąty na połaci'
    }


def _calculate_mansard_roof(dims: RoofDimensions) -> Dict:
    """Dach mansardowy (francuski)."""
    base_area = dims.width * dims.length
    mansard_factor = 1.6
    
    total_area = base_area * mansard_factor
    usable_area = total_area * 0.65
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 4,
        'optimal_orientation': 'portrait',
        'formula_used': 'base_area × 1.6',
        'note': 'Dach mansardowy - 4 połacie z dwoma kątami'
    }


def _calculate_complex_roof(dims: RoofDimensions) -> Dict:
    """Dach wielospadowy (polygon)."""
    if not dims.polygon_coords:
        raise ValueError("Brak współrzędnych dla dachu wielospadowego")
    
    coords = dims.polygon_coords
    n = len(coords)
    
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += coords[i][0] * coords[j][1]
        area -= coords[j][0] * coords[i][1]
    
    total_area = abs(area) / 2.0
    usable_area = total_area * 0.75
    
    return {
        'total_area_m2': round(total_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': len(coords),
        'optimal_orientation': 'custom',
        'formula_used': 'Shoelace formula (Gauss)',
        'note': 'Dach niestandardowy - wymaga wizji lokalnej'
    }


def _calculate_ground_installation(dims: RoofDimensions) -> Dict:
    """Instalacja naziemna."""
    ground_area = dims.width * dims.length
    usable_area = ground_area * 0.50  # 2x więcej miejsca (odstępy)
    
    return {
        'total_area_m2': round(ground_area, 2),
        'usable_area_m2': round(usable_area, 2),
        'slope_count': 1,
        'optimal_orientation': 'landscape',
        'formula_used': 'width × length × 0.5',
        'note': 'Instalacja naziemna - odstępy między rzędami'
    }


# =============================================================================
# HELPER: Formularz UI
# =============================================================================

def get_required_fields_for_roof_type(roof_type: str) -> Dict:
    """
    Zwraca listę pól formularza dla danego typu dachu.
    """
    roof_configs = {
        "rectangular": {
            "fields": ["width", "length", "angle"],
            "labels": {
                "width": "Szerokość dachu [m]",
                "length": "Długość budynku [m]",
                "angle": "Kąt nachylenia (°)"
            },
            "tooltips": {
                "angle": "Typowo 30-45° dla domów jednorodzinnych"
            }
        },
        
        "gable": {
            "fields": ["width", "length", "ridge_height"],
            "labels": {
                "width": "Szerokość budynku [m]",
                "length": "Długość budynku [m]",
                "ridge_height": "Wysokość kalenicy [m]"
            },
            "tooltips": {
                "ridge_height": "Wysokość kalenicy ponad okapem (typowo 2-4m)"
            }
        },
        
        "hip": {
            "fields": ["width", "length", "ridge_height", "angle"],
            "labels": {
                "width": "Szerokość budynku [m]",
                "length": "Długość budynku [m]",
                "ridge_height": "Wysokość kalenicy [m]",
                "angle": "Kąt nachylenia (°)"
            },
            "tooltips": {}
        },
        
        "triangle": {
            "fields": ["base", "height"],
            "labels": {
                "base": "Podstawa trójkąta [m]",
                "height": "Wysokość trójkąta [m]"
            },
            "tooltips": {
                "base": "Długość podstawy",
                "height": "Wysokość od podstawy do szczytu"
            }
        },
        
        # NOWE: TRAPEZ
        "trapezoid": {
            "fields": ["trapezoid_base_a", "trapezoid_base_b", "trapezoid_height"],
            "labels": {
                "trapezoid_base_a": "Podstawa dolna (dłuższa, m)",
                "trapezoid_base_b": "Podstawa górna (krótsza, m)",
                "trapezoid_height": "Wysokość trapezu [m]"
            },
            "tooltips": {
                "trapezoid_base_a": "Dłuższa podstawa (dolna krawędź)",
                "trapezoid_base_b": "Krótsza podstawa (górna krawędź)",
                "trapezoid_height": "Odległość między podstawami"
            },
            "diagram": "Trapez: ___\n        /   \\\n       /     \\\n      /_______\\"
        },
        
        # NOWE: ROMB
        "rhombus": {
            "fields": ["rhombus_diagonal_1", "rhombus_diagonal_2"],
            "labels": {
                "rhombus_diagonal_1": "Przekątna 1 [m]",
                "rhombus_diagonal_2": "Przekątna 2 [m]"
            },
            "tooltips": {
                "rhombus_diagonal_1": "Pierwsza przekątna rombu (pozioma lub pionowa)",
                "rhombus_diagonal_2": "Druga przekątna rombu (prostopadła do pierwszej)"
            },
            "diagram": "Romb:   /\\\n       /  \\\n       \\  /\n        \\/"
        },
        
        "ground": {
            "fields": ["width", "length"],
            "labels": {
                "width": "Szerokość terenu [m]",
                "length": "Długość terenu [m]"
            },
            "tooltips": {
                "width": "Dostępna powierzchnia gruntu"
            }
        }
    }
    
    return roof_configs.get(roof_type, roof_configs["rectangular"])

# backend/app/core/roof_geometry.py - v2.2 (FIX: Inteligentna Walidacja)
"""
Moduł obsługi różnych typów dachów dla instalacji PV.
Zaktualizowany o obsługę Równoległoboku (Rombu) i trybu Real Roof Length.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import math


@dataclass
class RoofDimensions:
    """Wymiary dachu - używane w testach i logice wewnętrznej"""
    roof_type: str
    width: float = 0.0
    length: float = 0.0
    angle: int = 30
    ridge_height: float = 0.0
    base: float = 0.0
    height: float = 0.0
    trapezoid_base_a: float = 0.0
    trapezoid_base_b: float = 0.0
    trapezoid_height: float = 0.0
    rhombus_diagonal_1: float = 0.0
    rhombus_diagonal_2: float = 0.0
    rhombus_side_b: float = 0.0 # Nowe pole dla boku b
    polygon_coords: List[Tuple[float, float]] = None


# =============================================================================
# WALIDACJA (Kluczowa dla uniknięcia błędów 400/500)
# =============================================================================

def validate_roof_dimensions(request) -> bool:
    """
    Waliduje wymagane pola dla KAŻDEJ połaci dachu w request.facets.
    Dostosowana do trybów 'building_length' oraz 'real_roof_length'.
    """
    if not request.facets or len(request.facets) == 0:
        raise ValueError("Brak połaci dachu (facets). Podaj przynajmniej jedną.")

    for i, facet in enumerate(request.facets):
        t = facet.roof_type
        mode = getattr(facet, 'roof_mode', 'building_length')
        prefix = f"Połać #{i+1} (id={facet.id}, typ={t})"

        # 1. DACHY STANDARDOWE (Rectangular, Flat, Gable, Hip, Ground)
        if t in ["rectangular", "flat", "gable", "hip", "ground"]:
            if not facet.width:
                raise ValueError(f"{prefix}: wymagana szerokość (width)")
            
            if mode == "real_roof_length":
                if not facet.real_roof_length:
                    raise ValueError(f"{prefix}: wymagana realna długość skosu")
            else:
                if not facet.length:
                    raise ValueError(f"{prefix}: wymagana długość budynku (length)")
                if t in ["gable", "hip"] and not facet.ridge_height:
                    raise ValueError(f"{prefix}: wymagana wysokość kalenicy")

        # 2. TRÓJKĄT
        elif t == "triangle":
            if not facet.triangle_base:
                raise ValueError(f"{prefix}: wymagana podstawa trójkąta")
            
            if mode == "real_roof_length":
                if not facet.real_roof_length:
                    raise ValueError(f"{prefix}: wymagana wysokość skosu (real_roof_length)")
            else:
                if not facet.triangle_height:
                    raise ValueError(f"{prefix}: wymagana wysokość rzutu (triangle_height)")

        # 3. TRAPEZ
        elif t == "trapezoid":
            if not facet.trapezoid_base_a or not facet.trapezoid_base_b:
                raise ValueError(f"{prefix}: wymagane obie podstawy trapezu (a i b)")
            
            if mode == "real_roof_length":
                if not facet.real_roof_length:
                    raise ValueError(f"{prefix}: wymagana wysokość skosu (real_roof_length)")
            else:
                if not facet.trapezoid_height:
                    raise ValueError(f"{prefix}: wymagana wysokość rzutu (trapezoid_height)")

        # 4. ROMB (Równoległobok)
        elif t == "rhombus":
            # Podstawa (a) i Bok (b) są zawsze wymagane
            if not facet.rhombus_diagonal_1:
                raise ValueError(f"{prefix}: wymagana podstawa (a)")
            
            # Używamy getattr, bo rhombus_side_b to nowe pole
            if not getattr(facet, 'rhombus_side_b', None):
                raise ValueError(f"{prefix}: wymagany bok skośny (b)")
            
            # Wysokość (h) zależy od trybu
            if mode == "real_roof_length":
                if not facet.real_roof_length:
                    raise ValueError(f"{prefix}: wymagana wysokość skosu (real_roof_length)")
            else:
                if not facet.rhombus_diagonal_2:
                    raise ValueError(f"{prefix}: wymagana wysokość rzutu (rhombus_diagonal_2)")

        else:
            raise ValueError(f"{prefix}: Nieznany typ dachu: {t}")

    return True


# =============================================================================
# OBLICZANIE POWIERZCHNI (Dla testów jednostkowych)
# =============================================================================

def calculate_roof_area(roof_dims: RoofDimensions) -> Dict:
    """
    Oblicza powierzchnię dachu w zależności od typu.
    Uproszczona wersja używana głównie do weryfikacji danych wejściowych.
    """
    t = roof_dims.roof_type.lower()
    
    if t in ["rectangular", "flat", "ground"]:
        area = roof_dims.width * roof_dims.length
        return {'total_area_m2': round(area, 2), 'formula': 'w * l'}
    
    elif t == "triangle":
        area = 0.5 * roof_dims.base * roof_dims.height
        return {'total_area_m2': round(area, 2), 'formula': '0.5 * b * h'}
    
    elif t == "trapezoid":
        area = 0.5 * (roof_dims.trapezoid_base_a + roof_dims.trapezoid_base_b) * roof_dims.trapezoid_height
        return {'total_area_m2': round(area, 2), 'formula': '0.5 * (a+b) * h'}
    
    elif t == "rhombus":
        # Równoległobok: P = a * h
        area = roof_dims.rhombus_diagonal_1 * roof_dims.rhombus_diagonal_2
        return {'total_area_m2': round(area, 2), 'formula': 'a * h'}
    
    return {'total_area_m2': 0.0, 'formula': 'unknown'}

# =============================================================================
# PRZYKŁADY UŻYCIA
# =============================================================================
if __name__ == "__main__":
    print("="*60)
    print("TESTY - WSZYSTKIE TYPY DACHÓW")
    print("="*60)
    print()
    
    # Test 1: Prostokątny
    print("=== Test 1: Dach prostokątny ===")
    rect = RoofDimensions(roof_type="rectangular", width=10.0, length=12.0, angle=35)
    r1 = calculate_roof_area(rect)
    print(f"Powierzchnia: {r1['total_area_m2']} m²")
    print(f"Użyteczna: {r1['usable_area_m2']} m²")
    print(f"Wzór: {r1['formula_used']}")
    print()
    
    # Test 2: Dwuspadowy
    print("=== Test 2: Dach dwuspadowy ===")
    gable = RoofDimensions(roof_type="gable", width=10.0, length=15.0, ridge_height=3.0)
    r2 = calculate_roof_area(gable)
    print(f"Całkowita: {r2['total_area_m2']} m² (2 połacie)")
    print(f"Użyteczna: {r2['usable_area_m2']} m² (1 połać)")
    print(f"Note: {r2['note']}")
    print()
    
    # Test 3: Trójkątny
    print("=== Test 3: Dach trójkątny ===")
    triangle = RoofDimensions(roof_type="triangle", base=8.0, height=6.0)
    r3 = calculate_roof_area(triangle)
    print(f"Powierzchnia: {r3['total_area_m2']} m²")
    print(f"Wzór: {r3['formula_used']}")
    print()
    
    # Test 4: TRAPEZ - NOWY!
    print("=== Test 4: Dach trapezowy (NOWY!) ===")
    trapezoid = RoofDimensions(
        roof_type="trapezoid",
        trapezoid_base_a=12.0,  # Dolna podstawa
        trapezoid_base_b=8.0,   # Górna podstawa
        trapezoid_height=10.0   # Wysokość
    )
    r4 = calculate_roof_area(trapezoid)
    print(f"Powierzchnia: {r4['total_area_m2']} m²")
    print(f"Użyteczna: {r4['usable_area_m2']} m²")
    print(f"Wzór: {r4['formula_used']}")
    print(f"Note: {r4['note']}")
    print()
    
    # Test 5: ROMB - NOWY!
    print("=== Test 5: Dach rombowy (NOWY!) ===")
    rhombus = RoofDimensions(
        roof_type="rhombus",
        rhombus_diagonal_1=10.0,  # Przekątna 1
        rhombus_diagonal_2=8.0    # Przekątna 2
    )
    r5 = calculate_roof_area(rhombus)
    print(f"Powierzchnia: {r5['total_area_m2']} m²")
    print(f"Użyteczna: {r5['usable_area_m2']} m²")
    print(f"Wzór: {r5['formula_used']}")
    print(f"Note: {r5['note']}")
    print(f"Długość boku: {r5.get('side_length_m', 'N/A')} m")
    print()
    
    # Test 6: Naziemny
    print("=== Test 6: Instalacja naziemna ===")
    ground = RoofDimensions(roof_type="ground", width=20.0, length=30.0)
    r6 = calculate_roof_area(ground)
    print(f"Teren: {r6['total_area_m2']} m²")
    print(f"Użyteczna: {r6['usable_area_m2']} m² (z odstępami)")
    print(f"Note: {r6['note']}")
    print()
    
    print("="*60)
    print("PORÓWNANIE POWIERZCHNI")
    print("="*60)
    print(f"Prostokątny:   {r1['usable_area_m2']} m²")
    print(f"Dwuspadowy:    {r2['usable_area_m2']} m²")
    print(f"Trójkątny:     {r3['usable_area_m2']} m²")
    print(f"TRAPEZ:        {r4['usable_area_m2']} m² ← NOWY")
    print(f"ROMB:          {r5['usable_area_m2']} m² ← NOWY")
    print(f"Naziemny:      {r6['usable_area_m2']} m²")
