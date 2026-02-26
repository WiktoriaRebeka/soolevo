# backend/app/core/estimate_annual_consumption.py


from typing import Optional
from typing import Optional


def estimate_annual_consumption(
    area_m2: float,
    residents: int,
    standard: str = "WT2021",
    uses_induction: bool = False,
) -> float:
    """
    Główna funkcja szacująca całkowite zużycie dla nowego domu (Master Function).
    Sumuje bazę, ogrzewanie (zakładając pompę ciepła) oraz indukcję.
    
    UWAGA: Dodatki takie jak EV czy AC są dodawane w engine.py na podstawie 
    wyboru użytkownika, aby uniknąć podwójnego liczenia.
    """
    # 1. Baza (AGD/RTV/Oświetlenie)
    base = estimate_base_consumption(area_m2, residents)
    
    # 2. Ogrzewanie (Dla nowych domów w trybie estymacji zakładamy pompę ciepła)
    heating = estimate_heating_load(area_m2, standard, has_heat_pump=True)
    
    # 3. Ciepła woda (Również zakładamy pompę ciepła/zasobnik elektryczny)
    dhw = estimate_dhw_load(residents, has_heat_pump=True)
    
    # 4. Gotowanie
    induction = estimate_induction_load(uses_induction)
    
    return round(base + heating + dhw + induction, 0)


def estimate_base_consumption(area_m2: float, residents: int) -> float:
    """
    Oblicza bazowe zużycie energii (AGD/RTV/Oświetlenie).

    Model:
        E_base = C_fixed + (N * E_person) + (A * E_area)

    Gdzie:
        C_fixed  = 1000 kWh  – stałe obciążenie (lodówka, router, standby, brama, oświetlenie zewn.)
        E_person = 500 kWh   – pranie, zmywanie, gotowanie, elektronika
        E_area   = 4 kWh/m2  – oświetlenie wewnętrzne, sprzątanie

    Przykład:
        Dom 140 m2, 4 osoby:
        1000 + (4 * 500) + (140 * 4) = 3560 kWh/rok
    """
    FIXED_LOAD = 1000.0      # kWh
    PER_PERSON_LOAD = 500.0  # kWh/osoba
    PER_M2_LOAD = 4.0        # kWh/m2

    base_consumption = FIXED_LOAD + (residents * PER_PERSON_LOAD) + (area_m2 * PER_M2_LOAD)
    return round(base_consumption, 0)


def estimate_heating_load(
    area_m2: float,
    standard: str = "WT2021",
    has_heat_pump: bool = True,
) -> float:
    """
    Szacuje zużycie energii elektrycznej na ogrzewanie pomieszczeń.

    Model:
        EU_co (kWh/m2/rok) zależne od standardu:
            - passive          ~ 15
            - WT2021 (nowy)    ~ 50
            - older_insulated  ~ 90

        Jeśli pompa ciepła:
            E_heating = Area * EU_co / SCOP
            SCOP_heating ≈ 3.5

        Jeśli brak pompy ciepła:
            - zakładamy ogrzewanie gaz/drewno,
            - prąd tylko na pompy obiegowe: stałe ~200 kWh/rok.
    """
    standards_map = {
        "passive": 15.0,
        "WT2021": 50.0,
        "older_insulated": 90.0,
    }
    eu_co = standards_map.get(standard, 50.0)

    if has_heat_pump:
        scop_heating = 3.5
        heating = (area_m2 * eu_co) / scop_heating
    else:
        heating = 200.0  # kWh/rok – pompy obiegowe, sterowanie

    return round(heating, 0)


def estimate_dhw_load(residents: int, has_heat_pump: bool = True) -> float:
    """
    Szacuje zużycie energii elektrycznej na ciepłą wodę użytkową (DHW).

    Założenia:
        - 1 osoba zużywa ok. 1000–1200 kWh energii cieplnej na wodę rocznie.
        - Dla pompy ciepła (COP ≈ 2.5):
            E_dhw ≈ N * (1100 / 2.5) ≈ N * 450 kWh

        Jeśli brak pompy ciepła:
            - zakładamy, że woda grzana jest gazem/drewnem,
            - prąd na wodę ≈ 0 kWh (pomijamy).
    """
    if has_heat_pump:
        per_person_elec_kwh = 450.0
        dhw = residents * per_person_elec_kwh
    else:
        dhw = 0.0

    return round(dhw, 0)


def estimate_ac_load(has_ac: bool) -> float:
    """
    Szacuje zużycie klimatyzacji.

    Założenie:
        - 1–2 jednostki split w polskim klimacie: ~400–500 kWh/rok.
    """
    return 400.0 if has_ac else 0.0


def estimate_ev_load(ev_km_per_year: int) -> float:
    """
    Szacuje zużycie energii na ładowanie samochodu elektrycznego.

    Model:
        20 kWh / 100 km → 0.2 kWh/km

        E_ev = (km / 100) * 20
    """
    if ev_km_per_year <= 0:
        return 0.0
    return round((ev_km_per_year / 100.0) * 20.0, 0)


def estimate_induction_load(uses_induction: bool) -> float:
    """
    Szacuje dodatkowe zużycie energii na gotowanie na płycie indukcyjnej.

    Założenie:
        +300 kWh/rok przy gotowaniu na prądzie zamiast gazu.
    """
    return 300.0 if uses_induction else 0.0


