# backend/app/core/shading.py
"""
Moduł obliczający wpływ zacienienia na produkcję energii PV.

Funkcje:
- Obliczanie strat energetycznych od zacienienia
- Rekomendacja mikroinwerterów dla zacienionej instalacji
- Analiza kierunku zacienienia vs orientacja dachu
"""

from typing import Dict


def calculate_shading_loss(
    has_shading: bool,
    shading_direction: str,
    roof_direction: str,
) -> float:
    """
    Oblicza współczynnik strat z tytułu zacienienia.

    Args:
        has_shading: Czy dach jest zacieniony
        shading_direction: Kierunek, z którego pada cień (south, east, west, north, itp.)
        roof_direction: Orientacja dachu (south, south-east, itp.)

    Returns:
        float: Współczynnik strat (0.0 = brak strat, 0.30 = 30% strat, max 0.40)
    """
    if not has_shading:
        return 0.0

    if not shading_direction:
        return 0.0

    # Normalizacja: akceptujemy zarówno "south_east" jak i "south-east"
    shading_direction = shading_direction.lower().strip().replace("_", "-")
    roof_direction = roof_direction.lower().strip().replace("_", "-")

    # Bazowe straty w zależności od kierunku cienia
    base_loss = {
        "south": 0.25,       # Najgorzej — cień z południa blokuje słońce w szczycie
        "south-east": 0.20,
        "south-west": 0.20,
        "east": 0.15,        # Cień poranny — tracisz produkcję rano
        "west": 0.15,        # Cień popołudniowy — tracisz produkcję po południu
        "north-east": 0.08,
        "north-west": 0.08,
        "north": 0.05,       # Najmniejszy wpływ — słońce rzadko od północy
    }

    loss = base_loss.get(shading_direction, 0.10)  # Fallback: 10%

    # Jeśli cień pada z tego samego kierunku co orientacja dachu → podwójnie źle
    # (panele skierowane w stronę cienia = maksymalna strata)
    if shading_direction == roof_direction:
        loss *= 1.3  # +30% kary

    # Max 40% strat (powyżej = instalacja w ogóle nie ma sensu)
    return round(min(loss, 0.40), 4)


def calculate_partial_shading_factor(
    shading_direction: str,
    time_of_day: str
) -> float:
    """
    Oblicza, w jakich godzinach występuje zacienienie (dla przyszłych analiz hourly).
    
    Args:
        shading_direction: Kierunek źródła cienia
        time_of_day: Pora dnia ('morning', 'noon', 'afternoon', 'evening')
    
    Returns:
        float: Współczynnik zacienienia w danej porze (0.0-1.0)
    """
    # Przykładowa logika - można rozbudować
    shading_schedule = {
        "east": {
            "morning": 0.8,   # Silne zacienienie rano
            "noon": 0.3,
            "afternoon": 0.1,
            "evening": 0.0
        },
        "west": {
            "morning": 0.0,
            "noon": 0.3,
            "afternoon": 0.8,  # Silne zacienienie po południu
            "evening": 0.9
        },
        "south": {
            "morning": 0.5,
            "noon": 0.9,       # Najgorsze w południe
            "afternoon": 0.6,
            "evening": 0.3
        },
        "north": {
            "morning": 0.1,
            "noon": 0.1,
            "afternoon": 0.1,
            "evening": 0.1
        }
    }
    
    return shading_schedule.get(shading_direction, {}).get(time_of_day, 0.0)


def recommend_microinverters(
    has_shading: bool,
    shading_loss: float,
    panels_count: int,
    roof_type: str
) -> Dict:
    """
    Rekomenduje mikroinwertery dla instalacji z zacienieniem.
    
    Args:
        has_shading: Czy jest zacienienie
        shading_loss: Obliczony współczynnik strat (z calculate_shading_loss)
        panels_count: Liczba paneli
        roof_type: Typ dachu ('pitched', 'flat', 'ground')
    
    Returns:
        Dict:
        {
            'recommended': bool,
            'reason': str,
            'brand': str,
            'model': str,
            'cost_per_panel_pln': float,
            'total_cost_pln': float,
            'efficiency_gain_percent': float
        }
    
    Logic:
        Mikroinwertery są rekomendowane gdy:
        - Jest zacienienie > 10% strat
        - Instalacja ma > 8 paneli (opłacalność)
        - Dach skośny lub grunt (nie płaski - tam string inverter OK)
    """
    # Brak zacienienia = brak potrzeby mikroinwerterów
    if not has_shading or shading_loss < 0.10:
        return {
            'recommended': False,
            'reason': 'Brak istotnego zacienienia - standardowy falownik wystarczy',
            'brand': None,
            'model': None,
            'cost_per_panel_pln': 0,
            'total_cost_pln': 0,
            'efficiency_gain_percent': 0
        }
    
    # Mała instalacja (< 8 paneli) - mikroinwertery nieopłacalne
    if panels_count < 8:
        return {
            'recommended': False,
            'reason': f'Instalacja zbyt mała ({panels_count} paneli) - mikroinwertery nieopłacalne',
            'brand': None,
            'model': None,
            'cost_per_panel_pln': 0,
            'total_cost_pln': 0,
            'efficiency_gain_percent': 0
        }
    
    # Dach płaski - mikroinwertery mniej potrzebne (równomierne nasłonecznienie)
    if roof_type == "flat" and shading_loss < 0.15:
        return {
            'recommended': False,
            'reason': 'Dach płaski z niewielkim zacienieniem - standardowy falownik wystarcza',
            'brand': None,
            'model': None,
            'cost_per_panel_pln': 0,
            'total_cost_pln': 0,
            'efficiency_gain_percent': 0
        }
    
    # === REKOMENDACJA MIKROINWERTERÓW ===
    # Najpopularniejsze modele mikroinwerterów
    microinverter_cost_per_panel = 450  # PLN netto za mikroinwerter (Enphase IQ8+)
    total_cost = panels_count * microinverter_cost_per_panel
    
    # Zysk z mikroinwerterów: odzyskują ~50-70% strat od zacienienia
    efficiency_gain = shading_loss * 0.60  # Odzyskujemy 60% strat
    
    return {
        'recommended': True,
        'reason': f'Zacienienie powoduje {shading_loss*100:.0f}% strat. Mikroinwertery odzyskają ~{efficiency_gain*100:.0f}% tej energii.',
        'brand': 'Enphase',
        'model': 'IQ8+ Microinverter',
        'cost_per_panel_pln': microinverter_cost_per_panel,
        'total_cost_pln': total_cost,
        'efficiency_gain_percent': round(efficiency_gain * 100, 1)
    }


def calculate_optimal_tilt_with_shading(
    latitude: float,
    shading_direction: str,
    current_tilt: int
) -> Dict:
    """
    Sugeruje optymalny kąt nachylenia paneli przy zacienieniu.
    
    Args:
        latitude: Szerokość geograficzna (dla Polski: 49-54°)
        shading_direction: Kierunek zacienienia
        current_tilt: Obecny kąt nachylenia dachu
    
    Returns:
        Dict:
        {
            'optimal_tilt': int,
            'adjustment_reason': str,
            'expected_improvement': float
        }
    """
    # Standardowy optymalny kąt dla Polski: ~35-38°
    standard_optimal = int(latitude * 0.76)  # Przybliżona formuła
    
    # Przy zacienieniu od południa: zwiększ kąt (panele wyżej nad przeszkodą)
    if shading_direction == "south":
        optimal_tilt = min(current_tilt + 5, 45)  # Max 45°
        return {
            'optimal_tilt': optimal_tilt,
            'adjustment_reason': 'Zwiększenie kąta o 5° może zminimalizować wpływ cienia od południa',
            'expected_improvement': 0.05  # 5% poprawy
        }
    
    # Przy zacienieniu od wschodu/zachodu: lekka korekta
    elif shading_direction in ["east", "west"]:
        optimal_tilt = standard_optimal
        return {
            'optimal_tilt': optimal_tilt,
            'adjustment_reason': 'Standardowy kąt jest optymalny',
            'expected_improvement': 0.0
        }
    
    # Domyślnie
    return {
        'optimal_tilt': standard_optimal,
        'adjustment_reason': 'Brak konieczności zmiany kąta',
        'expected_improvement': 0.0
    }


# =============================================================================
# PRZYKŁADOWE UŻYCIE (DO TESTÓW)
# =============================================================================
if __name__ == "__main__":
    print("=== Test 1: Zacienienie od południa ===")
    loss1 = calculate_shading_loss(
        has_shading=True,
        shading_direction="south",
        roof_direction="south"
    )
    print(f"Straty: {loss1 * 100:.0f}%")
    
    micro1 = recommend_microinverters(
        has_shading=True,
        shading_loss=loss1,
        panels_count=20,
        roof_type="pitched"
    )
    print(f"Mikroinwertery: {micro1}")
    print()
    
    print("=== Test 2: Zacienienie od wschodu ===")
    loss2 = calculate_shading_loss(
        has_shading=True,
        shading_direction="east",
        roof_direction="south"
    )
    print(f"Straty: {loss2 * 100:.0f}%")
    
    micro2 = recommend_microinverters(
        has_shading=True,
        shading_loss=loss2,
        panels_count=15,
        roof_type="pitched"
    )
    print(f"Mikroinwertery: {micro2}")
    print()
    
    print("=== Test 3: Brak zacienienia ===")
    loss3 = calculate_shading_loss(
        has_shading=False,
        shading_direction="",
        roof_direction="south"
    )
    print(f"Straty: {loss3 * 100:.0f}%")
    
    micro3 = recommend_microinverters(
        has_shading=False,
        shading_loss=loss3,
        panels_count=20,
        roof_type="pitched"
    )
    print(f"Mikroinwertery: {micro3}")
