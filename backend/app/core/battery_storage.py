# backend/app/core/battery_storage.py
"""
Moduł rekomendacji magazynów energii dla instalacji PV.

CHANGELOG (v2.3 — PHYSICS FIXES):
- DoD nie jest już mnożone przez sprawność w obliczeniach uzysku (tylko opis/pojemność).
- Wprowadzono EFFECTIVE_CYCLES_PER_YEAR = 240 (sezonowość pracy magazynu w PL).
- Dodano model ładowania z podziałem sprawności na ładowanie/rozładowanie.
- Dodano ograniczenie mocy ładowania przez inwerter i baterię (power_kw).
- Poprawiono calculate_required_battery_capacity: operuje na usable_capacity_kwh (bez dzielenia przez DoD).
- Poprawiono dane LUNA2000 (LFP, DoD=1.0).
"""

from typing import Dict, List, Optional

# =============================================================================
# PARAMETRY GLOBALNE
# =============================================================================

# Realistyczna liczba efektywnych cykli pracy magazynu w Polsce (uwzględnia zimę)
EFFECTIVE_CYCLES_PER_YEAR = 240


# =============================================================================
# BAZA DANYCH MAGAZYNÓW ENERGII
# =============================================================================

BATTERIES_DATABASE = [
    # === MAŁE MAGAZYNY (5-8 kWh) ===
    {
        "brand": "BYD",
        "model": "Battery-Box Premium HVS 5.1",
        "capacity_kwh": 5.1,
        "usable_capacity_kwh": 4.6,
        "power_kw": 5.0,
        "efficiency": 0.96,   # roundtrip efficiency
        "price_pln": 14000,
        "cycles": 6000,
        "warranty_years": 10,
        "expandable": True,
        "chemistry": "LFP",
        "dod": 0.90,
    },
    {
        "brand": "Pylontech",
        "model": "US3000C (7.2 kWh)",
        "capacity_kwh": 7.2,
        "usable_capacity_kwh": 6.5,
        "power_kw": 3.7,
        "efficiency": 0.95,
        "price_pln": 16000,
        "cycles": 6000,
        "warranty_years": 10,
        "expandable": True,
        "chemistry": "LFP",
        "dod": 0.90,
    },

    # === ŚREDNIE MAGAZYNY (9-11 kWh) ===
    {
        "brand": "BYD",
        "model": "Battery-Box Premium HVS 10.2",
        "capacity_kwh": 10.2,
        "usable_capacity_kwh": 9.2,
        "power_kw": 8.3,
        "efficiency": 0.96,
        "price_pln": 24000,
        "cycles": 6000,
        "warranty_years": 10,
        "expandable": True,
        "chemistry": "LFP",
        "dod": 0.90,
    },
    {
        "brand": "Huawei",
        "model": "LUNA2000-10-S0",
        "capacity_kwh": 10.0,
        "usable_capacity_kwh": 9.0,
        "power_kw": 5.0,
        "efficiency": 0.90,
        "price_pln": 22000,
        "cycles": 10000,
        "warranty_years": 10,
        "expandable": True,
        "chemistry": "LFP",   # POPRAWKA: LFP, nie NMC
        "dod": 1.00,          # POPRAWKA: 100% DoD (programowy margines)
    },
    {
        "brand": "LG Chem",
        "model": "RESU10H",
        "capacity_kwh": 9.8,
        "usable_capacity_kwh": 8.8,
        "power_kw": 5.0,
        "efficiency": 0.95,
        "price_pln": 26000,
        "cycles": 6000,
        "warranty_years": 10,
        "expandable": False,
        "chemistry": "NMC",
        "dod": 0.80,
    },

    # === DUŻE MAGAZYNY (13-15 kWh) ===
    {
        "brand": "Tesla",
        "model": "Powerwall 3",
        "capacity_kwh": 13.5,
        "usable_capacity_kwh": 13.5,
        "power_kw": 11.5,
        "efficiency": 0.90,
        "price_pln": 35000,
        "cycles": 10000,
        "warranty_years": 10,
        "expandable": False,
        "chemistry": "NMC",
        "dod": 1.00,
    },
    {
        "brand": "BYD",
        "model": "Battery-Box Premium HVS 15.4",
        "capacity_kwh": 15.4,
        "usable_capacity_kwh": 13.9,
        "power_kw": 10.0,
        "efficiency": 0.96,
        "price_pln": 32000,
        "cycles": 6000,
        "warranty_years": 10,
        "expandable": True,
        "chemistry": "LFP",
        "dod": 0.90,
    },
    {
        "brand": "Sonnen",
        "model": "sonnenBatterie 10",
        "capacity_kwh": 11.0,
        "usable_capacity_kwh": 10.0,
        "power_kw": 3.3,
        "efficiency": 0.93,
        "price_pln": 38000,
        "cycles": 10000,
        "warranty_years": 10,
        "expandable": True,
        "chemistry": "LFP",
        "dod": 0.91,
    }
]


# =============================================================================
# FUNKCJE POMOCNICZE (SPRAWNOŚĆ, KOMPATYBILNOŚĆ, UZYSK)
# =============================================================================

def effective_battery_efficiency(battery: Dict) -> float:
    """
    Efektywna sprawność energetyczna magazynu (roundtrip efficiency).

    UWAGA (po audycie):
    - DoD NIE jest tu mnożone, bo zostało już uwzględnione w usable_capacity_kwh.
    - Ta funkcja zwraca wyłącznie sprawność energetyczną cyklu ładowanie–rozładowanie.
    """
    roundtrip_efficiency = battery.get("efficiency", 0.95)
    return round(roundtrip_efficiency, 4)


def check_battery_inverter_compatibility(
    battery: Dict,
    inverter_power_kw: float,
) -> Dict:
    """
    Sprawdza czy moc falownika ≥ moc baterii.

    Jeśli bateria ma wyższą moc niż falownik, nie może się w pełni
    ładować/rozładować z deklarowaną mocą.
    """
    battery_power_kw = battery.get("power_kw", 0.0)
    compatible = inverter_power_kw >= battery_power_kw

    warning = None
    if not compatible:
        warning = (
            f"Moc falownika ({inverter_power_kw:.1f} kW) < moc baterii "
            f"({battery_power_kw:.1f} kW). Bateria nie będzie pracować z pełną mocą. "
            f"Rozważ falownik hybrydowy ≥ {battery_power_kw:.1f} kW."
        )

    return {
        "compatible": compatible,
        "battery_power_kw": battery_power_kw,
        "inverter_power_kw": inverter_power_kw,
        "warning": warning,
    }


def calculate_additional_autoconsumption(
    surplus_daily_kwh: float,
    battery_usable_kwh: float,
    roundtrip_efficiency: float,
    inverter_power_kw: Optional[float] = None,
    battery_power_kw: Optional[float] = None,
    assumed_charging_hours: int = 4,
) -> float:
    """
    Oblicza dodatkową autokonsumpcję (kWh/dzień) z magazynu energii.

    Korekta fizyczna:
    - Rozdzielamy sprawność na ładowanie i rozładowanie: η_roundtrip = η_in * η_out
      Przybliżenie: η_in = η_out = sqrt(η_roundtrip).
    - Uwzględniamy ograniczenie mocy ładowania przez:
        - moc baterii (battery_power_kw),
        - moc falownika (inverter_power_kw),
      zakładając okno ładowania np. 4h dziennie.
    - Nie mnożymy przez DoD, bo usable_capacity_kwh już to uwzględnia.
    """
    if surplus_daily_kwh <= 0 or battery_usable_kwh <= 0:
        return 0.0

    # Sprawność jednostronna (ładowanie / rozładowanie)
    one_way_eff = roundtrip_efficiency ** 0.5

    # Maksymalna energia, którą możemy "wlać" do baterii przy danej sprawności ładowania
    # (po stronie AC/DC przed stratami ładowania)
    max_energy_by_capacity = battery_usable_kwh / one_way_eff

    # Ograniczenie mocy ładowania (kW) × czas ładowania (h)
    max_power_kw_candidates = []
    if inverter_power_kw and inverter_power_kw > 0:
        max_power_kw_candidates.append(inverter_power_kw)
    if battery_power_kw and battery_power_kw > 0:
        max_power_kw_candidates.append(battery_power_kw)

    if max_power_kw_candidates:
        max_charge_power_limited = min(max_power_kw_candidates) * assumed_charging_hours
    else:
        # Jeśli nie znamy mocy, nie ograniczamy od strony mocy (tylko pojemnością)
        max_charge_power_limited = max_energy_by_capacity

    # Ile energii możemy realnie "wcisnąć" do baterii danego dnia
    potential_charge = min(
        surplus_daily_kwh,
        max_energy_by_capacity,
        max_charge_power_limited,
    )

    # Ile z tego wyjmiemy po uwzględnieniu pełnej sprawności roundtrip
    energy_out = potential_charge * roundtrip_efficiency
    return energy_out


# =============================================================================
# FUNKCJE OBLICZENIOWE
# =============================================================================

def calculate_required_battery_capacity(
    annual_consumption_kwh: float,
    autoconsumption_rate: float,
    target_autonomy_hours: int = 12,
    household_size: int = 4,
    consumption_profile: Optional[dict] = None,
) -> float:
    """
    Oblicza wymaganą pojemność magazynu energii (w kWh UŻYTECZNYCH).

    Korekta po audycie:
    - Nie dzielimy przez DoD, bo baza używa usable_capacity_kwh.
    - DoD jest własnością produktu, nie parametrem projektowym tutaj.
    """
    daily_consumption = annual_consumption_kwh / 365

    # Jeśli mamy profil zużycia, używamy evening + night jako "bez słońca"
    if consumption_profile:
        evening_frac = consumption_profile.get("evening", 0.25)
        night_frac = consumption_profile.get("night", 0.20)
        no_sun_fraction = evening_frac + night_frac
        consumption_without_sun = daily_consumption * no_sun_fraction
    else:
        # Uproszczony model: 14h bez słońca
        hours_without_sun = 14
        hourly_consumption = daily_consumption / 24
        consumption_without_sun = hourly_consumption * hours_without_sun

    # Korekta na wielkość gospodarstwa
    household_multiplier = 1.0 + (household_size - 4) * 0.1
    consumption_without_sun *= household_multiplier

    # Margines bezpieczeństwa (rezerwa)
    safety_margin = 1.20

    required_usable_capacity = consumption_without_sun * safety_margin
    return round(required_usable_capacity, 1)


def recommend_battery(
    annual_consumption_kwh: float | None = None,
    annual_production_kwh: float | None = None,
    autoconsumption_rate: float | None = None,
    surplus_kwh: float | None = None,
    energy_price_kwh: float = 1.00,
    household_size: int = 4,
    prefer_brand: Optional[str] = None,
    consumption_profile: Optional[dict] = None,
    production_profile: Optional[dict] = None,
    inverter_power_kw: Optional[float] = None,
    net_billing_factor: float = 0.30,
    **kwargs
) -> Dict:
    """
    Rekomenduje magazyn energii.

    Po poprawkach fizycznych:
    - Uzysk z baterii liczony z roundtrip_efficiency (bez DoD).
    - Używamy EFFECTIVE_CYCLES_PER_YEAR zamiast 365.
    - Uwzględniamy ograniczenie mocy ładowania przez inwerter i baterię.
    """

    # 1. MAPOWANIE NAZW (legacy support)
    if annual_consumption_kwh is None:
        annual_consumption_kwh = (
            kwargs.get('annual_demand_kwh')
            or (consumption_profile.get('annual_demand_kwh') if consumption_profile else None)
            or (consumption_profile.get('annual_consumption_kwh') if consumption_profile else None)
        )
    if annual_production_kwh is None:
        annual_production_kwh = (
            kwargs.get('annual_production')
            or (production_profile.get('annual_production_kwh') if production_profile else None)
        )
    if autoconsumption_rate is None and consumption_profile:
        autoconsumption_rate = (
            consumption_profile.get('autoconsumption_rate')
            or consumption_profile.get('self_consumption_rate')
        )
    if surplus_kwh is None and consumption_profile:
        surplus_kwh = (
            consumption_profile.get('surplus_kwh')
            or consumption_profile.get('annual_surplus_kwh')
        )

    # 2. WALIDACJA
    missing = []
    if annual_consumption_kwh is None: missing.append("annual_consumption_kwh")
    if annual_production_kwh is None: missing.append("annual_production_kwh")
    if autoconsumption_rate is None: missing.append("autoconsumption_rate")
    if surplus_kwh is None: missing.append("surplus_kwh")
    if missing:
        raise ValueError(f"Brakujące dane wejściowe dla modułu baterii: {', '.join(missing)}")

    # 3. WYMAGANA POJEMNOŚĆ (usable kWh)
    required_kwh = calculate_required_battery_capacity(
        annual_consumption_kwh=annual_consumption_kwh,
        autoconsumption_rate=autoconsumption_rate,
        target_autonomy_hours=12,
        household_size=household_size,
        consumption_profile=consumption_profile,
    )

    # 4. DOBÓR BATERII
    suitable_batteries = [
        bat for bat in BATTERIES_DATABASE
        if bat['usable_capacity_kwh'] >= required_kwh
    ]
    if not suitable_batteries:
        suitable_batteries = [max(BATTERIES_DATABASE, key=lambda x: x['usable_capacity_kwh'])]
    suitable_batteries.sort(key=lambda x: x['price_pln'])

    if prefer_brand:
        preferred = [b for b in suitable_batteries if b['brand'].lower() == prefer_brand.lower()]
        if preferred:
            suitable_batteries = preferred

    selected = suitable_batteries[0]

    # Sprawność energetyczna (roundtrip)
    eff_efficiency = effective_battery_efficiency(selected)

    # 5. ANALIZA UZYSKU (z efektywną sprawnością i sezonowością)
    daily_surplus = surplus_kwh / 365.0  # średnia dobowa nadwyżka
    battery_capacity_usable = selected['usable_capacity_kwh']

    energy_out_daily = calculate_additional_autoconsumption(
        surplus_daily_kwh=daily_surplus,
        battery_usable_kwh=battery_capacity_usable,
        roundtrip_efficiency=eff_efficiency,
        inverter_power_kw=inverter_power_kw,
        battery_power_kw=selected.get("power_kw"),
        assumed_charging_hours=4,
    )

    # Zamiast 365 cykli → realistyczne EFFECTIVE_CYCLES_PER_YEAR
    additional_autoconsumption = energy_out_daily * EFFECTIVE_CYCLES_PER_YEAR

    # Autokonsumpcja przed i po baterii
    base_autoconsumption_kwh = annual_production_kwh * autoconsumption_rate
    new_autoconsumption_kwh = base_autoconsumption_kwh + additional_autoconsumption

    if annual_production_kwh <= 0:
        new_autoconsumption_rate = autoconsumption_rate
    else:
        new_autoconsumption_rate = min(0.95, new_autoconsumption_kwh / annual_production_kwh)

    # 6. OSZCZĘDNOŚCI (net-billing)
    savings_multiplier = 1.0 - net_billing_factor
    additional_savings_yearly = additional_autoconsumption * energy_price_kwh * savings_multiplier
    battery_cost = selected['price_pln']
    battery_maintenance_yearly = 100
    net_savings_yearly = additional_savings_yearly - battery_maintenance_yearly

    payback_years = battery_cost / net_savings_yearly if net_savings_yearly > 0 else 999

    # 7. DECYZJA O REKOMENDACJI
    recommended = (
        payback_years < 15
        and surplus_kwh > 2000
        and (new_autoconsumption_rate - autoconsumption_rate) > 0.10
    )

    # Kompatybilność bateria ↔ falownik
    inverter_compat = None
    if inverter_power_kw is not None and inverter_power_kw > 0:
        inverter_compat = check_battery_inverter_compatibility(
            battery=selected,
            inverter_power_kw=inverter_power_kw,
        )

    # 8. RATIONALE
    if recommended:
        rationale = (
            f"Magazyn {selected['brand']} {selected['model']} ({selected['capacity_kwh']} kWh) "
            f"zwiększy autokonsumpcję z {autoconsumption_rate*100:.0f}% do "
            f"{new_autoconsumption_rate*100:.0f}%. "
            f"Zwrot inwestycji: {payback_years:.1f} lat. "
            f"Sprawność energetyczna cyklu: {eff_efficiency*100:.1f}%."
        )
    else:
        if surplus_kwh < 2000:
            rationale = f"Mała nadwyżka ({surplus_kwh:.0f} kWh/rok) - magazyn niewykorzystany."
        elif payback_years >= 15:
            rationale = f"Długi okres zwrotu ({payback_years:.1f} lat) - nieopłacalne."
        else:
            rationale = "Obecna autokonsumpcja jest wystarczająco wysoka."

    if inverter_compat and not inverter_compat["compatible"]:
        rationale += f" ⚠️ {inverter_compat['warning']}"

    return {
        'recommended': recommended,
        # ZAWSZE zwracamy wybrany model baterii – nawet jeśli nie jest opłacalna
        'battery': selected,
        'required_capacity_kwh': round(required_kwh, 1),
        'new_autoconsumption_rate': round(new_autoconsumption_rate, 3),
        'additional_savings_yearly_pln': round(net_savings_yearly, 2),
        'payback_years': round(payback_years, 1) if payback_years < 999 else None,
        # ZAWSZE pełny koszt baterii (do audytu i scenariusza PV+magazyn)
        'total_cost_pln': battery_cost,
        'rationale': rationale,
        'effective_efficiency': round(eff_efficiency, 4),
        'inverter_compatibility': inverter_compat,
    }

def calculate_battery_roi_with_tou_tariff(
    battery: Dict,
    annual_consumption_kwh: float,
    peak_price_kwh: float = 1.20,
    offpeak_price_kwh: float = 0.60,
    peak_hours_per_day: int = 8
) -> Dict:
    """Oblicza ROI magazynu przy taryfie TOU (Time of Use) - G12/G12W."""
    daily_consumption = annual_consumption_kwh / 365
    peak_consumption_daily = daily_consumption * (peak_hours_per_day / 24)
    shifted_energy_daily = min(peak_consumption_daily, battery['usable_capacity_kwh'])
    shifted_energy_yearly = shifted_energy_daily * EFFECTIVE_CYCLES_PER_YEAR
    savings_per_kwh = peak_price_kwh - offpeak_price_kwh
    total_savings_yearly = shifted_energy_yearly * savings_per_kwh
    payback_years = battery['price_pln'] / total_savings_yearly if total_savings_yearly > 0 else 999

    return {
        'tou_arbitrage_savings_yearly': round(total_savings_yearly, 2),
        'tou_payback_years': round(payback_years, 1) if payback_years < 999 else None,
        'shifted_energy_kwh_yearly': round(shifted_energy_yearly, 2)
    }


# =============================================================================
# TESTY
# =============================================================================
if __name__ == "__main__":
    print("=== Test 1: Mała instalacja, duża nadwyżka (net_billing=0.30) ===")
    rec1 = recommend_battery(
        annual_demand_kwh=5000,
        annual_production_kwh=8000,
        autoconsumption_rate=0.35,
        surplus_kwh=5200,
        energy_price_kwh=1.00,
        household_size=4,
        net_billing_factor=0.30,
        inverter_power_kw=5.0,
    )
    print(f"Rekomendowany: {rec1['recommended']}")
    print(f"Efektywna sprawność: {rec1['effective_efficiency']*100:.1f}%")
    if rec1['battery']:
        print(f"Magazyn: {rec1['battery']['brand']} {rec1['battery']['model']}")
        print(f"Nowa autokonsumpcja: {rec1['new_autoconsumption_rate']*100:.0f}%")
        print(f"Zwrot po: {rec1['payback_years']} lat")
    if rec1['inverter_compatibility']:
        print(f"Kompatybilność: {rec1['inverter_compatibility']['compatible']}")
    print(f"Rationale: {rec1['rationale']}")