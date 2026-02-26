# backend/app/core/consumption.py

from typing import Dict
from app.data.usage_profiles import PERSON_TYPES, HOUSEHOLD_SIZE_MULTIPLIER

def calculate_autoconsumption_rate(
    consumption_profile: Dict[str, float],
    pv_production_profile: Dict[str, float] = None
) -> float:
    
    # Domyślny profil produkcji PV (uproszczony)
    if pv_production_profile is None:
        pv_production_profile = {
            'morning': 0.25,  # 6-10: Wschód słońca, niska produkcja
            'day': 0.60,      # 10-16: PEAK produkcji
            'evening': 0.15,  # 16-22: Zachód słońca
            'night': 0.00     # 22-6: Brak produkcji
        }
    
    # Oblicz overlap (nachodzenie produkcji i zużycia)
    # Im większy overlap w "day", tym wyższa autokonsumpcja
    autoconsumption_raw = sum(
        consumption_profile[period] * pv_production_profile[period]
        for period in consumption_profile
    )
    
    # Skalowanie: zakładamy że 100% overlap = 70% autokonsumpcji
    # (nawet idealne dopasowanie nie daje 100% bo są straty, baterii nie ma)
    max_autoconsumption = 0.70
    min_autoconsumption = 0.20  # Minimalna autokonsumpcja (lodówka, standby)
    
    # Normalizacja: overlap 0.6 (dzień) → max, overlap 0.1 → min
    # Formuła liniowa
    autoconsumption_rate = min_autoconsumption + (
        (autoconsumption_raw - 0.1) / (0.6 - 0.1)
    ) * (max_autoconsumption - min_autoconsumption)
    
    # Clamp do zakresu [min, max]
    autoconsumption_rate = max(min_autoconsumption, min(max_autoconsumption, autoconsumption_rate))
    
    return round(autoconsumption_rate, 4)


def calculate_energy_distribution(
    annual_production_kwh: float,
    annual_demand_kwh: float,
    autoconsumption_rate: float,
) -> dict:
    """DEPRECATED: Użyj calculate_monthly_autoconsumption() zamiast tego."""
    autoconsumption_kwh = annual_production_kwh * autoconsumption_rate
    surplus_kwh = annual_production_kwh - autoconsumption_kwh
    grid_import_kwh = max(0, annual_demand_kwh - autoconsumption_kwh)
    self_suff = (autoconsumption_kwh / annual_demand_kwh * 100) if annual_demand_kwh > 0 else 0

    return {
        "autoconsumption_kwh": round(autoconsumption_kwh, 2),
        "surplus_kwh": round(surplus_kwh, 2),
        "grid_import_kwh": round(grid_import_kwh, 2),
        "self_sufficiency_percent": round(self_suff, 1),
    }

def calculate_monthly_autoconsumption(
    monthly_production: dict,
    annual_demand_kwh: float,
    consumption_profile: dict,
) -> dict:
    """
    Zaktualizowana wersja zgodna z Audytem Inżynierskim v3.0.
    Wprowadza współczynnik jednoczesności, aby uniknąć zawyżania autokonsumpcji.
    """
    monthly_demand = annual_demand_kwh / 12.0

    # Profil PV produkcji w ciągu dnia (bardziej realistyczny)
    # Suma musi wynosić 1.0. Noc = 0, bo słońce nie świeci.
    pv_day_profile = {
        "morning": 0.15, 
        "day": 0.70,      # Peak produkcji
        "evening": 0.15, 
        "night": 0.00
    }

    TECHNICAL_EFFICIENCY = 0.95

    monthly_auto = {}
    monthly_surplus = {}
    monthly_import = {}
    monthly_rate = {}

    for m, prod_kwh in monthly_production.items():
        overlap_kwh = 0.0
        for period in ["morning", "day", "evening", "night"]:
            pv_in_period = prod_kwh * pv_day_profile[period]
            demand_in_period = monthly_demand * consumption_profile[period]
            
            # Nakładamy karę za brak jednoczesności poboru i produkcji
            overlap_kwh += min(pv_in_period, demand_in_period) * TECHNICAL_EFFICIENCY

        # Autokonsumpcja nie może być większa niż produkcja ani niż zużycie
        auto_kwh = min(overlap_kwh, prod_kwh, monthly_demand)
        
        # Dodajemy "podstawę" (baseload) - lodówka/standby zawsze coś złapią (ok. 10% produkcji)
        # ale tylko jeśli produkcja w ogóle istnieje
        if prod_kwh > 0:
            baseload_auto = min(prod_kwh * 0.10, monthly_demand * 0.10)
            auto_kwh = max(auto_kwh, baseload_auto)

        surplus_kwh = max(0.0, prod_kwh - auto_kwh)
        import_kwh = max(0.0, monthly_demand - auto_kwh)

        monthly_auto[m] = round(auto_kwh, 2)
        monthly_surplus[m] = round(surplus_kwh, 2)
        monthly_import[m] = round(import_kwh, 2)
        monthly_rate[m] = round(auto_kwh / prod_kwh, 4) if prod_kwh > 0 else 0.0

    annual_auto = sum(monthly_auto.values())
    annual_surplus = sum(monthly_surplus.values())
    annual_import = sum(monthly_import.values())
    annual_prod = sum(monthly_production.values())

    return {
        "monthly_autoconsumption_kwh": monthly_auto,
        "monthly_surplus_kwh": monthly_surplus,
        "monthly_grid_import_kwh": monthly_import,
        "monthly_autoconsumption_rate": monthly_rate,
        "annual_autoconsumption_rate": round(annual_auto / annual_prod, 4) if annual_prod > 0 else 0,
        "annual_autoconsumption_kwh": round(annual_auto, 2),
        "annual_surplus_kwh": round(annual_surplus, 2),
        "annual_grid_import_kwh": round(annual_import, 2),
    }
# =============================================================================
# PRZYKŁAD UŻYCIA
# =============================================================================
if __name__ == "__main__":
    # Test 1: Rodzina 4os, wszyscy pracują
    print("=== Test 1: Rodzina 4os, wszyscy w pracy/szkole ===")
    profile1 = calculate_household_consumption_profile(
        household_size=4,
        people_home_weekday=0
    )
    print(f"Profil zużycia: {profile1}")
    
    autocons1 = calculate_autoconsumption_rate(profile1)
    print(f"Autokonsumpcja: {autocons1 * 100:.1f}%")
    
    dist1 = calculate_energy_distribution(
        annual_production_kwh=8000,
        annual_demand_kwh=7000,
        autoconsumption_rate=autocons1
    )
    print(f"Rozkład energii: {dist1}")
    print()
    
    # Test 2: Rodzina 4os, 2 osoby w domu (home office)
    print("=== Test 2: Rodzina 4os, 2 osoby w domu ===")
    profile2 = calculate_household_consumption_profile(
        household_size=4,
        people_home_weekday=2
    )
    print(f"Profil zużycia: {profile2}")
    
    autocons2 = calculate_autoconsumption_rate(profile2)
    print(f"Autokonsumpcja: {autocons2 * 100:.1f}%")
    
    dist2 = calculate_energy_distribution(
        annual_production_kwh=8000,
        annual_demand_kwh=7000,
        autoconsumption_rate=autocons2
    )
    print(f"Rozkład energii: {dist2}")
    print()
    
    # Test 3: Rodzina 4os, wszyscy w domu
    print("=== Test 3: Rodzina 4os, wszyscy w domu ===")
    profile3 = calculate_household_consumption_profile(
        household_size=4,
        people_home_weekday=4
    )
    print(f"Profil zużycia: {profile3}")
    
    autocons3 = calculate_autoconsumption_rate(profile3)
    print(f"Autokonsumpcja: {autocons3 * 100:.1f}%")
    
    dist3 = calculate_energy_distribution(
        annual_production_kwh=8000,
        annual_demand_kwh=7000,
        autoconsumption_rate=autocons3
    )
    print(f"Rozkład energii: {dist3}")
