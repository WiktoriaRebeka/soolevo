# backend/app/core/net_billing_engine.py

from typing import Dict, Any
from app.core.finance import (
    calculate_monthly_net_billing_value,
    calculate_net_billing_value,
)
from app.core.net_billing import generate_price_scenarios


class NetBillingEngine:
    """
    Odpowiada za całą logikę net-billing:
    - miesięczne depozyty RCEm
    - efektywna stawka net-billing
    - uproszczone i zaawansowane modele nadwyżek
    """

    def __init__(self, rcem_monthly: Dict[str, float] = None, year: int = 2025):
        self.rcem_monthly = rcem_monthly
        self.year = year

    def compute_monthly_deposit(self, monthly_surplus_kwh: Dict[str, float]) -> Dict[str, Any]:
        return calculate_monthly_net_billing_value(
            monthly_surplus_kwh=monthly_surplus_kwh,
            rcem_monthly=self.rcem_monthly,
            year=self.year,
        )

    def compute_annual_deposit(self, surplus_kwh: float, fallback_rate: float = 0.30) -> float:
        return calculate_net_billing_value(
            energy_surplus_kwh=surplus_kwh,
            rcem_price_pln=fallback_rate,
        )

    def compute_effective_rate(self, monthly_surplus_kwh: Dict[str, float]) -> float:
        result = self.compute_monthly_deposit(monthly_surplus_kwh)
        return result["effective_surplus_rate_pln_kwh"]

    def get_hourly_prices(self):
        """
        Zwraca scenariusze cen godzinowych:
        - base
        - high
        - low
        - raw
        """
        return generate_price_scenarios(csv_path=None, fallback_years=1)