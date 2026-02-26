# backend/app/data/energy_rates.py
"""
Moduł zawierający stawki taryfowe dla różnych operatorów.

ZAWIERA:
- Oryginalny słownik ENERGY_RATES (backward compatibility)
- Nowe funkcje dla taryf G12/G12w i dekompozycji
- Wszystkie stare funkcje dla backward compatibility
"""

from typing import Dict, Optional


# =============================================================================
# ORYGINALNY SŁOWNIK ENERGY_RATES (dla backward compatibility)
# =============================================================================

ENERGY_RATES = {
    "pge": {
        "g11": {
            "energy_price_kwh": 0.6189,
            "distribution_variable_kwh": 0.4267,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 12.28,
            "subscription_options": {
                "monthly": 8.31,
                "bimonthly": 2.77,
                "semiannual": 0.92
            },
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 28.56},
                {"max_kwh": 1200, "annual_pln": 68.52},
                {"max_kwh": 2800, "annual_pln": 114.24},
                {"max_kwh": float('inf'), "annual_pln": 163.56}
            ]
        }
    },
    
    "tauron": {
        "g11": {
            "energy_price_kwh": 0.6113,
            "distribution_variable_kwh": 0.3690,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 13.36,
            "subscription_options": {
                "monthly": 5.60,
                "bimonthly": 2.80,
                "annual": 0.47
            },
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12": {
            "energy_price_kwh_peak": 0.8241,
            "energy_price_kwh_offpeak": 0.6273,
            "distribution_variable_kwh_peak": 0.4305,
            "distribution_variable_kwh_offpeak": 0.0861,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 13.36,
            "subscription_options": {"monthly": 5.60},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12w": {
            "energy_price_kwh_peak": 0.9471,
            "energy_price_kwh_offpeak": 0.6273,
            "distribution_variable_kwh_peak": 0.5043,
            "distribution_variable_kwh_offpeak": 0.0738,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 13.36,
            "subscription_options": {"monthly": 5.60},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        }
    },
    
    "enea": {
        "g11": {
            "energy_price_kwh": 0.6187,
            "distribution_variable_kwh": 0.3613,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 12.80,
            "subscription_options": {
                "monthly": 4.72,
                "bimonthly": 2.36
            },
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12": {
            "energy_price_kwh_peak": 0.8856,
            "energy_price_kwh_offpeak": 0.5166,
            "distribution_variable_kwh_peak": 0.4182,
            "distribution_variable_kwh_offpeak": 0.1353,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 17.90,
            "subscription_options": {"monthly": 4.72},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12w": {
            "energy_price_kwh_peak": 0.9963,
            "energy_price_kwh_offpeak": 0.5289,
            "distribution_variable_kwh_peak": 0.4059,
            "distribution_variable_kwh_offpeak": 0.1230,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 32.30,
            "subscription_options": {"monthly": 4.72},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        }
    },
    
    "energa": {
        "g11": {
            "energy_price_kwh": 0.6200,
            "distribution_variable_kwh": 0.5289,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 14.50,
            "subscription_options": {
                "monthly": 5.71,
                "bimonthly": 2.86
            },
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12": {
            "energy_price_kwh_peak": 0.8856,
            "energy_price_kwh_offpeak": 0.5781,
            "distribution_variable_kwh_peak": 0.6519,
            "distribution_variable_kwh_offpeak": 0.1845,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 24.80,
            "subscription_options": {"monthly": 5.71},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12w": {
            "energy_price_kwh_peak": 0.9225,
            "energy_price_kwh_offpeak": 0.6027,
            "distribution_variable_kwh_peak": 0.6765,
            "distribution_variable_kwh_offpeak": 0.1968,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 24.80,
            "subscription_options": {"monthly": 5.71},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        }
    },
    
    "eon": {
        "g11": {
            "energy_price_kwh": 0.6210,
            "distribution_variable_kwh": 0.3545,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 22.80,
            "subscription_options": {
                "monthly": 3.50,
                "commercial_fee": 16.27
            },
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12": {
            "energy_price_kwh_peak": 0.7425,
            "energy_price_kwh_offpeak": 0.6120,
            "distribution_variable_kwh_peak": 0.3850,
            "distribution_variable_kwh_offpeak": 0.1156,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 22.80,
            "subscription_options": {"monthly": 3.50, "commercial_fee": 16.27},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        },
        "g12w": {
            "energy_price_kwh_peak": 0.7995,
            "energy_price_kwh_offpeak": 0.6765,
            "distribution_variable_kwh_peak": 0.3888,
            "distribution_variable_kwh_offpeak": 0.1632,
            "quality_fee_kwh": 0.0407,
            "oze_fee_kwh": 0.0090,
            "cogeneration_fee_kwh": 0.0037,
            "network_fixed_monthly_pln": 22.80,
            "subscription_options": {"monthly": 3.50, "commercial_fee": 16.27},
            "capacity_fee_tiers": [
                {"max_kwh": 500, "annual_pln": 51.48},
                {"max_kwh": 1200, "annual_pln": 123.72},
                {"max_kwh": 2800, "annual_pln": 206.16},
                {"max_kwh": float('inf'), "annual_pln": 288.60}
            ]
        }
    }
}


# =============================================================================
# STARE FUNKCJE (backward compatibility)
# =============================================================================

def get_rate_data(operator: str = "pge", tariff: str = "g11") -> Dict:
    """
    Pobiera dane stawek dla danego operatora i taryfy.
    Domyślnie PGE G11.
    
    [ORYGINALNA FUNKCJA - backward compatibility]
    """
    op_data = ENERGY_RATES.get(operator.lower(), ENERGY_RATES["pge"])
    return op_data.get(tariff.lower(), op_data["g11"])


# =============================================================================
# NOWE FUNKCJE (v3.1)
# =============================================================================

def get_retail_tariff_pln_per_kwh(year: int = 2025, tariff_type: str = "G11") -> float:
    """
    Zwraca średnią cenę detaliczną energii.
    
    Args:
        year: Rok
        tariff_type: Rodzaj taryfy ("G11", "G12", "G12w")
    
    Returns:
        Cena PLN/kWh (brutto z VAT 23%)
    """
    base_prices = {
        "G11": 0.80,
        "G12": 0.78,
        "G12w": 0.76,
    }
    
    base_price = base_prices.get(tariff_type, 0.80)
    
    if year > 2025:
        inflation_rate = 0.04
        years_diff = year - 2025
        return base_price * ((1 + inflation_rate) ** years_diff)
    
    return base_price


def decompose_electricity_tariff(operator: str, tariff: str) -> Dict[str, float]:
    """
    DYNAMICZNA DEKOMPOZYCJA (v3.2): Pobiera realne składniki z bazy ENERGY_RATES.
    Usuwa błąd stałych procentów (0.56 / 0.31).
    Niezbędne do rzetelnego wyliczenia wartości depozytu w Net-billingu.
    """
    # Pobieramy dane dla konkretnego operatora i taryfy
    rates = get_rate_data(operator, tariff)
    
    # 1. Składnik energii czynnej (tylko to może być pokryte z depozytu prosumenckiego)
    if "energy_price_kwh" in rates:
        # Taryfa jednostrefowa (G11)
        energy_part = rates["energy_price_kwh"]
        dist_part = rates["distribution_variable_kwh"]
    else:
        # Taryfa dwustrefowa (G12/G12w) - średnia ważona statystyczna (60/40)
        energy_part = 0.6 * rates["energy_price_kwh_peak"] + 0.4 * rates["energy_price_kwh_offpeak"]
        dist_part = 0.6 * rates["distribution_variable_kwh_peak"] + 0.4 * rates["distribution_variable_kwh_offpeak"]
        
    # 2. Pozostałe opłaty zmienne (jakość, OZE, kogeneracja)
    # Te opłaty oraz dystrybucję prosument ZAWSZE płaci gotówką (nie z depozytu)
    other_fees = rates["quality_fee_kwh"] + rates["oze_fee_kwh"] + rates["cogeneration_fee_kwh"]
    
    total_variable = energy_part + dist_part + other_fees
    
    return {
        "energy_pln_per_kwh": round(energy_part, 4),
        "distribution_pln_per_kwh": round(dist_part + other_fees, 4), # FIX: Nazwa klucza zgodna z HourlyEngine
        "total_variable_pln_per_kwh": round(total_variable, 4),
        "total_pln_per_kwh": round(total_variable, 4)
    }

    
def get_tariff_zones_g11(base_tariff_pln_per_kwh: float) -> Dict[int, float]:
    """Zwraca stawki dla taryfy G11 (jednakowa całą dobę)."""
    return {hour: base_tariff_pln_per_kwh for hour in range(24)}


def get_tariff_zones_g12(
    peak_tariff_pln_per_kwh: float,
    offpeak_tariff_pln_per_kwh: float,
) -> Dict[int, float]:
    """
    Zwraca stawki dla taryfy G12 (dwustrefowa).
    
    Strefy G12:
    - Tania: 22:00-06:00 + 13:00-15:00
    - Droga: Pozostałe godziny
    """
    zones = {}
    
    for hour in range(24):
        if (22 <= hour or hour < 6) or (13 <= hour < 15):
            zones[hour] = offpeak_tariff_pln_per_kwh
        else:
            zones[hour] = peak_tariff_pln_per_kwh
    
    return zones


def get_tariff_zones_g12w(
    peak_tariff_pln_per_kwh: float,
    offpeak_tariff_pln_per_kwh: float,
) -> Dict[int, Dict[int, float]]:
    """
    Zwraca stawki dla taryfy G12w (dwustrefowa weekendowa).
    
    Strefy G12w:
    - Tania: 22:00-06:00 (codziennie) + CAŁE weekendy
    - Droga: Pozostałe godziny w dni robocze
    """
    zones = {}
    
    for day_of_week in range(7):
        zones[day_of_week] = {}
        
        is_weekend = day_of_week in [5, 6]
        
        for hour in range(24):
            if is_weekend:
                zones[day_of_week][hour] = offpeak_tariff_pln_per_kwh
            else:
                if 22 <= hour or hour < 6:
                    zones[day_of_week][hour] = offpeak_tariff_pln_per_kwh
                else:
                    zones[day_of_week][hour] = peak_tariff_pln_per_kwh
    
    return zones


def calculate_average_tariff(
    tariff_type: str,
    peak_tariff: float,
    offpeak_tariff: Optional[float] = None,
) -> float:
    """Oblicza średnią ważoną stawkę dla taryfy dwustrefowej."""
    if tariff_type == "G11":
        return peak_tariff
    
    elif tariff_type == "G12":
        offpeak_ratio = 0.40
        return peak_tariff * (1 - offpeak_ratio) + offpeak_tariff * offpeak_ratio
    
    elif tariff_type == "G12w":
        offpeak_ratio = 0.50
        return peak_tariff * (1 - offpeak_ratio) + offpeak_tariff * offpeak_ratio
    
    return peak_tariff


def get_net_billing_coefficient() -> float:
    """
    [DEPRECATED] Zwraca prosty współczynnik net-billing.
    Używaj zamiast tego energy_prices_tge.get_rcem_hourly()
    """
    import warnings
    warnings.warn(
        "get_net_billing_coefficient() jest deprecated. "
        "Użyj energy_prices_tge.get_rcem_hourly()",
        DeprecationWarning,
        stacklevel=2
    )
    return 0.30
