# backend/app/data/equipment_scenarios.py
"""
Definicja 3 gotowych scenariuszy sprzętowych dla kalkulatora PV.

CHANGELOG:
- Dodano parametry elektryczne paneli (Voc, Vmp, Isc, Imp, beta_voc, beta_vmp)
  → wymagane do walidacji bezpieczeństwa stringów (RISK-01 z audytu)
- Wartości z datasheetów producentów (STC: 25°C, 1000 W/m²)
"""

from typing import Dict, Any

# =============================================================================
# SCENARIUSZ 1: PREMIUM
# =============================================================================
PREMIUM_SCENARIO = {
    "tier": "premium",
    "label": "Premium - Maksymalna Wydajność",
    "description": "Najwyższa jakość i trwałość. Idealne dla długoterminowej inwestycji.",
    
    "panel": {
        "id": "longi-550-himo6",
        "brand": "LONGi",
        "model": "Hi-MO 6 Explorer",
        "power_wp": 550,
        "width_m": 1.134,
        "height_m": 1.722,
        "efficiency": 0.226,
        "price": 580.00,
        "warranty_years": 25,
        "degradation_rate": 0.0045,
        "temp_coefficient": -0.26,
        "noct_celsius": 45.0,
        "gamma_pmax_percent": -0.26,

        "voc_v": 49.65,              # Napięcie obwodu otwartego [V]
        "vmp_v": 41.65,              # Napięcie mocy maksymalnej [V]
        "isc_a": 13.95,              # Prąd zwarcia [A]
        "imp_a": 13.21,              # Prąd mocy maksymalnej [A]
        "beta_voc_percent": -0.26,   # Wsp. temp. Voc [%/°C]
        "beta_vmp_percent": -0.32,   # Wsp. temp. Vmp [%/°C]
    },
    
    "inverter": {
        "brand": "Huawei",
        "model": "SUN2000-10KTL-M1",
        "power_kw": 10.0,
        "efficiency": 0.985,
        "price": 4200.00,
        "mppt_count": 2
    },
    
    "installation": {
        "labor_per_panel_pln": 350.00,
        "additional_materials_pln": 3500.00,
        "markup_percent": 0.15
    },
    
    "financial": {
        "subsidy_percent": 0.00,
        "maintenance_annual_pln": 300.00,
        "insurance_annual_pln": 200.00
    }
}

# =============================================================================
# SCENARIUSZ 2: STANDARD
# =============================================================================
STANDARD_SCENARIO = {
    "tier": "standard",
    "label": "Standard - Najlepszy Stosunek Ceny do Jakości",
    "description": "Sprawdzone rozwiązanie z bardzo dobrymi parametrami.",
    
    "panel": {
        "id": "jinko-500-tiger-neo",
        "brand": "Jinko Solar",
        "model": "Tiger Neo N-Type 500W",
        "power_wp": 500,
        "width_m": 1.134,
        "height_m": 1.722,
        "efficiency": 0.216,
        "price": 480.00,
        "warranty_years": 25,
        "degradation_rate": 0.0050,
        "temp_coefficient": -0.29,

        "noct_celsius": 45.0,
        "gamma_pmax_percent": -0.30,

        "voc_v": 47.30,
        "vmp_v": 40.14,
        "isc_a": 13.55,
        "imp_a": 12.45,
        "beta_voc_percent": -0.29,
        "beta_vmp_percent": -0.35,
    },
    
    "inverter": {
        "brand": "Fronius",
        "model": "Primo GEN24 8.0",
        "power_kw": 8.0,
        "efficiency": 0.980,
        "price": 3400.00,
        "mppt_count": 2
    },
    
    "installation": {
        "labor_per_panel_pln": 300.00,
        "additional_materials_pln": 2800.00,
        "markup_percent": 0.12
    },
    
    "financial": {
        "subsidy_percent": 0.00,
        "maintenance_annual_pln": 250.00,
        "insurance_annual_pln": 150.00
    }
}

# =============================================================================
# SCENARIUSZ 3: ECONOMY
# =============================================================================
ECONOMY_SCENARIO = {
    "tier": "economy",
    "label": "Economy - Oszczędna Inwestycja",
    "description": "Budżetowe rozwiązanie z dobrymi parametrami. Szybszy zwrot inwestycji.",
    
    "panel": {
        "id": "trina-450-vertex",
        "brand": "Trina Solar",
        "model": "Vertex S 450W",
        "power_wp": 450,
        "width_m": 1.096,
        "height_m": 1.754,
        "efficiency": 0.208,
        "price": 380.00,
        "warranty_years": 25,
        "degradation_rate": 0.0055,
        "temp_coefficient": -0.30,
        "noct_celsius": 45.0,
        "gamma_pmax_percent": -0.34,

        "voc_v": 43.50,
        "vmp_v": 36.12,
        "isc_a": 13.25,
        "imp_a": 12.45,
        "beta_voc_percent": -0.30,
        "beta_vmp_percent": -0.36,
    },
    
    "inverter": {
        "brand": "SolaX",
        "model": "X1-BOOST-6.0-D",
        "power_kw": 6.0,
        "efficiency": 0.975,
        "price": 2600.00,
        "mppt_count": 2
    },
    
    "installation": {
        "labor_per_panel_pln": 250.00,
        "additional_materials_pln": 2200.00,
        "markup_percent": 0.10
    },
    
    "financial": {
        "subsidy_percent": 0.00,
        "maintenance_annual_pln": 200.00,
        "insurance_annual_pln": 100.00
    }
}

# =============================================================================
ALL_SCENARIOS = [PREMIUM_SCENARIO, STANDARD_SCENARIO, ECONOMY_SCENARIO]


def get_scenario_by_tier(tier: str) -> Dict[str, Any]:
    """Zwraca scenariusz na podstawie poziomu."""
    tier = tier.lower()
    for scenario in ALL_SCENARIOS:
        if scenario["tier"] == tier:
            return scenario
    raise ValueError(f"Unknown tier: {tier}. Available: premium, standard, economy")


# Kopia zapasowa calculate_total_investment — kanoniczna wersja w finance.py
def calculate_total_investment(panels_count: int, scenario: Dict[str, Any]) -> Dict[str, float]:
    # Wszystkie ceny BRUTTO
    panels_cost = panels_count * scenario["panel"]["price"]
    inverter_cost = scenario["inverter"]["price"]
    installation_cost = panels_count * scenario["installation"]["labor_per_panel_pln"]
    materials_cost = scenario["installation"]["additional_materials_pln"]

    subtotal = panels_cost + inverter_cost + installation_cost + materials_cost

    # Marża liczona od BRUTTO
    markup = subtotal * scenario["installation"]["markup_percent"]

    total = subtotal + markup

    return {
        "panels_cost": round(panels_cost, 2),
        "inverter_cost": round(inverter_cost, 2),
        "installation_cost": round(installation_cost, 2),
        "materials_cost": round(materials_cost, 2),
        "subtotal": round(subtotal, 2),
        "markup": round(markup, 2),
        "total": round(total, 2),   # JEDYNA właściwa wartość końcowa
    }
