# backend/app/core/finance.py
"""
[CZĘŚCIOWO DEPRECATED]

Ten plik zawiera mieszankę:
- DEPRECATED: Stare funkcje ROI (używaj FinancialEngine.compute_roi())
- AKTYWNE: calculate_monthly_net_billing_value (używane w main.py)

Dla nowego kodu używaj:
- app.core.financial_engine.FinancialEngine - dla CAPEX i ROI
- app.core.hourly_engine.HourlyEngine - dla oszczędności
"""

import warnings
from typing import Dict, Any

from app.data.energy_prices_tge import (
    get_rcem_monthly,
    get_net_billing_rate_with_vat,
)


def calculate_monthly_net_billing_value(
    monthly_surplus_kwh: dict,
    rcem_monthly: dict = None,
    year: int = 2025,
) -> dict:
    """
    Oblicza wartość depozytu per miesiąc z miesięcznymi cenami RCEm.
    
    [AKTYWNA FUNKCJA - używana w main.py endpoint /calculate/net-billing]
    
    Args:
        monthly_surplus_kwh: {'jan': kWh, ..., 'dec': kWh}
        rcem_monthly: Słownik {1: PLN/kWh, ..., 12: PLN/kWh} lub {'jan': PLN/kWh, ...}
        year: Rok prognozy (jeśli rcem_monthly=None)
    
    Returns:
        dict: {
            'monthly_deposit_pln': {'jan': PLN, ...},
            'annual_deposit_pln': float,
            'effective_surplus_rate_pln_kwh': float,
            'rcem_monthly_used': dict,
        }
    """
    if rcem_monthly is None:
        # Pobierz z energy_prices_tge (format: {1: price, 2: price, ...})
        rcem_monthly_numeric = get_rcem_monthly(year)
        # Konwertuj na format {jan, feb, ...}
        month_names = ["jan", "feb", "mar", "apr", "may", "jun", 
                      "jul", "aug", "sep", "oct", "nov", "dec"]
        rcem_monthly = {
            month_names[i]: rcem_monthly_numeric[i+1] 
            for i in range(12)
        }
    
    monthly_deposit = {}
    total_surplus = 0.0
    total_deposit = 0.0
    
    for month in ["jan", "feb", "mar", "apr", "may", "jun", 
                  "jul", "aug", "sep", "oct", "nov", "dec"]:
        surplus = monthly_surplus_kwh.get(month, 0.0)
        rcem = rcem_monthly.get(month, 0.25)
        
        # Depozyt = RCEm × 1.23 (VAT)
        deposit_rate = get_net_billing_rate_with_vat(rcem)
        deposit = surplus * deposit_rate
        
        monthly_deposit[month] = round(deposit, 2)
        total_surplus += surplus
        total_deposit += deposit
    
    # Efektywna stawka (ważona)
    if total_surplus > 0:
        effective_rate = total_deposit / total_surplus
    else:
        effective_rate = 0.30  # Fallback
    
    return {
        "monthly_deposit_pln": monthly_deposit,
        "annual_deposit_pln": round(total_deposit, 2),
        "effective_surplus_rate_pln_kwh": round(effective_rate, 3),
        "rcem_monthly_used": rcem_monthly,
    }


# =============================================================================
# DEPRECATED FUNKCJE (zachowane dla backward compatibility)
# =============================================================================

def calculate_roi(*args, **kwargs) -> Dict[str, Any]:
    """
    [DEPRECATED]
    
    Użyj zamiast tego:
        from app.core.financial_engine import FinancialEngine
        engine = FinancialEngine(scenario_config)
        result = engine.compute_roi(...)
    """
    warnings.warn(
        "calculate_roi() jest deprecated. "
        "Użyj FinancialEngine.compute_roi() z app.core.financial_engine",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Stary kod - zachowany dla backward compatibility
    return {
        "payback_years": 15.0,
        "payback_optimistic_years": 12.0,
        "payback_pessimistic_years": 18.0,
        "total_savings_25y_pln": 100000,
        "warning": "DEPRECATED - użyj FinancialEngine.compute_roi()",
    }


def calculate_savings(*args, **kwargs) -> float:
    """
    [DEPRECATED]
    
    Użyj zamiast tego:
        from app.core.hourly_engine import HourlyEngine
        engine = HourlyEngine(...)
        result = engine.run_hourly_simulation()
        savings = result["annual_cashflow"]["net"]
    """
    warnings.warn(
        "calculate_savings() jest deprecated. "
        "Użyj HourlyEngine.run_hourly_simulation() z app.core.hourly_engine",
        DeprecationWarning,
        stacklevel=2
    )
    
    return 0.0


def calculate_net_billing(*args, **kwargs) -> Dict[str, Any]:
    """
    [DEPRECATED]
    
    Użyj zamiast tego:
        from app.core.hourly_engine import HourlyEngine
        # HourlyEngine automatycznie oblicza net-billing
    """
    warnings.warn(
        "calculate_net_billing() jest deprecated. "
        "Użyj HourlyEngine z app.core.hourly_engine",
        DeprecationWarning,
        stacklevel=2
    )
    
    return {
        "annual_deposit_pln": 0.0,
        "warning": "DEPRECATED - użyj HourlyEngine",
    }


__all__ = [
    "calculate_monthly_net_billing_value",  # AKTYWNA
    "calculate_roi",  # DEPRECATED
    "calculate_savings",  # DEPRECATED
    "calculate_net_billing",  # DEPRECATED
]
