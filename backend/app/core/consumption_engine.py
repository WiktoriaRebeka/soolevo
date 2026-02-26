from typing import Dict, Optional, List
from app.schemas.scenarios import ScenariosRequest
from app.core.estimate_annual_consumption import (
    estimate_base_consumption,
    estimate_heating_load,
    estimate_ac_load,
    estimate_ev_load,
    estimate_induction_load,
    estimate_dhw_load
)

def decompose_consumption(total_annual_kwh: float, request: ScenariosRequest) -> dict:
    """
    MODEL BUCKETÓW v4.6: Rozbija całkowite zużycie na 3 strumienie sezonowe.
    """
    heating_kwh = 0.0
    cooling_kwh = 0.0
    
    # 1. Obsługa urządzeń, które JUŻ SĄ (siedzą w obecnym rachunku)
    if request.has_heat_pump:
        # Jeśli ma pompę, ok. 50% rachunku to grzanie (max 4500)
        heating_kwh = min(total_annual_kwh * 0.5, 4500.0)
    if request.has_ac:
        # Jeśli ma klimę, ok. 10% rachunku to chłodzenie
        cooling_kwh = min(total_annual_kwh * 0.1, 600.0)

    # 2. Obsługa urządzeń PLANOWANYCH (dodajemy je do profilu)
    if request.planned_heat_pump:
        heating_kwh += 4500.0
    if request.planned_ac:
        cooling_kwh += 500.0
        
    # 3. Reszta to baza (AGD/RTV/Gotowanie/EV)
    base_kwh = max(total_annual_kwh - heating_kwh - cooling_kwh, 0.0)
    
    return {
        "base_kwh": base_kwh,
        "heating_kwh": heating_kwh,
        "cooling_kwh": cooling_kwh
    }

def calculate_annual_demand(bill_pln: float, is_annual_bill: bool, operator: str, tariff: str, **kwargs) -> float:
    """Rygorystyczna dekompozycja rachunku PLN -> kWh."""
    from app.data.energy_rates import ENERGY_RATES
    try:
        rates = ENERGY_RATES[operator.lower()][tariff.lower().replace("-", "")]
    except KeyError:
        rates = ENERGY_RATES["pge"]["g11"]

    total_annual_bill = bill_pln if is_annual_bill else bill_pln * 12
    fixed_fees = (rates["network_fixed_monthly_pln"] + rates["subscription_options"].get("monthly", 8.0)) * 12
    money_for_var = total_annual_bill - fixed_fees
    if money_for_var <= 0: return 0.0

    if "energy_price_kwh" in rates:
        var_rate = (rates["energy_price_kwh"] + rates["distribution_variable_kwh"] +
                    rates["quality_fee_kwh"] + rates["oze_fee_kwh"] + rates["cogeneration_fee_kwh"])
    else:
        v_peak = rates["energy_price_kwh_peak"] + rates["distribution_variable_kwh_peak"]
        v_off = rates["energy_price_kwh_offpeak"] + rates["distribution_variable_kwh_offpeak"]
        var_rate = (0.6 * v_peak + 0.4 * v_off) + rates["quality_fee_kwh"]

    return round(money_for_var / var_rate, 0)

def estimate_annual_consumption_logic(area_m2: float, residents: int, **kwargs) -> float:
    """Szacuje zużycie dla nowych domów."""
    base = estimate_base_consumption(area_m2=area_m2, residents=residents)
    # Zakładamy pompę ciepła dla nowych domów w trybie estymacji
    heating = estimate_heating_load(area_m2=area_m2, has_heat_pump=True)
    return round(base + heating, 0)

class ConsumptionEngine:
    """Klasa kompatybilności wstecznej."""
    @staticmethod
    def calculate_annual_demand(*args, **kwargs): return calculate_annual_demand(*args, **kwargs)