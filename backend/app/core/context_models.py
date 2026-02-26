# app/core/context_models.py

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class FacetContext:
    """
    Reprezentuje jedną połać po scoringu i obliczeniach geometrycznych.
    """
    facet_obj: Any
    efficiency: float
    max_panels: int
    row_distribution: List[int]
    warnings: List[str]
    grid: Any
    offset_x: float = 0.0
    slope_h: float = 0.0


@dataclass
class ScenarioContext:
    """
    Zawiera wszystkie dane wejściowe potrzebne do obliczeń scenariuszy.
    """
    request: Any
    future_demand: float
    consumption_profile: Dict[str, float]
    energy_rates: Dict[str, float]
    target_coverage_ratio: float
    facets: List[Any]

    @staticmethod
    def from_request(request, future_demand, consumption_profile, energy_rates):
        """
        Tworzy kontekst scenariusza na podstawie danych wejściowych.
        """
        target_ratio = 1.10 if (request.planned_ev or request.planned_heat_pump) else 1.00

        return ScenarioContext(
            request=request,
            future_demand=future_demand,
            consumption_profile=consumption_profile,
            energy_rates=energy_rates,
            target_coverage_ratio=target_ratio,
            facets=request.facets,
        )

@dataclass
class ScenarioResult:
    yield_data: Dict[str, Any]
    energy_dist: Dict[str, Any]
    savings: Dict[str, Any]
    roi_pv: Dict[str, Any]
    inverter: Dict[str, Any]
    investment: Dict[str, Any]
    facet_layout: Any
    offset_x: float
    effective_surplus_rate: float
    battery_recommendation: Any = None
    battery_savings: Dict[str, float] = None
    hourly_result: Dict[str, Any] = None 
    