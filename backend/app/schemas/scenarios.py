# backend/app/schemas/scenarios.py
"""
Pydantic schemas dla endpointu /calculate/scenarios.
KOMPLETNY PLIK - gotowy do wklejenia.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PanelPosition(BaseModel):
    """Pozycja pojedynczego panelu na dachu."""
    x: float
    y: float
    width: float
    height: float
    label: Optional[str] = None


class FacetLayout(BaseModel):
    """Layout paneli na pojedynczym płacie dachu."""
    facet_id: str
    panels_count: int
    azimuth_deg: float
    efficiency_factor: float
    layout: List[PanelPosition]
    rhombus_side_b: Optional[float] = 0.0


class RoofFacet(BaseModel):
    """Pojedynczy płat dachu."""
    id: str
    roof_type: str
    roof_mode: str = "building_length"
    width: Optional[float] = None
    length: Optional[float] = None
    real_roof_length: Optional[float] = None
    ridge_height: Optional[float] = None
    triangle_base: Optional[float] = None
    triangle_height: Optional[float] = None
    trapezoid_base_a: Optional[float] = None
    trapezoid_base_b: Optional[float] = None
    trapezoid_height: Optional[float] = None
    rhombus_diagonal_1: Optional[float] = None
    rhombus_diagonal_2: Optional[float] = None
    rhombus_side_b: Optional[float] = None
    azimuth_deg: float
    angle: float
    obstacles_count: int = 0
    has_shading: bool = False
    shading_direction: Optional[str] = None


class ScenariosRequest(BaseModel):
    """Request do endpointu /calculate/scenarios."""
    bill: float
    is_annual_bill: bool
    operator: str
    tariff: str
    province: str
    household_size: int
    people_home_weekday: int
    facets: List[RoofFacet]
    include_battery: bool = False
    estimated_consumption_mode: bool = False
    area_m2: Optional[float] = None
    building_standard: Optional[str] = "WT2021"
    uses_induction: bool = False
    has_heat_pump: bool = False
    has_ac: bool = False
    has_ev: bool = False
    planned_ev: bool = False
    planned_heat_pump: bool = False
    planned_ac: bool = False
    planned_other_kwh: Optional[float] = None
    energy_rates: Optional[Dict[str, float]] = None
    energy_price_kwh: Optional[float] = None
    inflation_rate: float = 0.04


class ScenarioResponseItem(BaseModel):
    """Pojedynczy scenariusz w odpowiedzi."""
    scenario_name: str = Field(..., description="Nazwa scenariusza")
    tier: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    panels_count: int = Field(..., description="Liczba paneli")
    panel_model: str = Field(..., description="Model panelu")
    panel_brand: Optional[str] = None
    panel_power_wp: Optional[int] = None
    total_power_kwp: float = Field(..., description="Moc systemu [kWp]")
    inverter_model: str = Field(..., description="Model falownika")
    inverter_power_kw: float = Field(..., description="Moc falownika [kW]")
    inverter_brand: Optional[str] = None
    inverter_quantity: Optional[int] = 1
    facet_layouts: Optional[List[FacetLayout]] = None
    annual_production_kwh: float = Field(..., description="Roczna produkcja [kWh]")
    annual_consumption_kwh: float = Field(..., description="Roczne zapotrzebowanie [kWh]")
    annual_demand_kwh: Optional[float] = None
    coverage_percent: Optional[float] = None
    pv_cost_gross_pln: float = Field(..., description="Koszt PV [PLN]")
    cost_total_gross_pln: Optional[float] = None
    pv_savings_pln: float = Field(..., description="Oszczędności roczne [PLN]")
    pv_payback_years: float = Field(..., description="Zwrot PV [lata]")
    payback_years: Optional[float] = None
    pv_payback_optimistic_years: float = Field(..., description="Zwrot optymistyczny [lata]")
    payback_optimistic_years: Optional[float] = None
    pv_payback_pessimistic_years: float = Field(..., description="Zwrot pesymistyczny [lata]")
    payback_pessimistic_years: Optional[float] = None
    pv_total_savings_25y_pln: float = Field(..., description="Suma oszczędności 25 lat [PLN]")
    battery_recommended: bool = Field(..., description="Czy bateria rekomendowana")
    battery_capacity_kwh: float = Field(default=0.0, description="Pojemność baterii [kWh]")
    battery_power_kw: float = Field(default=0.0, description="Moc baterii [kW]")
    battery_model: str = Field(default="", description="Model baterii")
    battery_cost_gross_pln: float = Field(default=0.0, description="Koszt baterii [PLN]")
    total_cost_with_battery_pln: float = Field(default=0.0, description="Koszt PV+bateria [PLN]")
    with_battery_total_cost_pln: Optional[float] = None
    battery_savings_pln: float = Field(default=0.0, description="Dodatkowe oszczędności z baterii [PLN]")
    total_savings_with_battery_pln: float = Field(default=0.0, description="Suma oszczędności PV+bateria [PLN]")
    battery_payback_years: float = Field(default=0.0, description="Zwrot PV+bateria [lata]")
    with_battery_payback_years: Optional[float] = None
    battery_payback_optimistic_years: float = Field(default=0.0, description="Zwrot bateria optymistyczny")
    with_battery_payback_optimistic_years: Optional[float] = None
    battery_payback_pessimistic_years: float = Field(default=0.0, description="Zwrot bateria pesymistyczny")
    with_battery_payback_pessimistic_years: Optional[float] = None
    battery_total_savings_25y_pln: float = Field(default=0.0, description="Suma 25y z baterią [PLN]")
    is_economically_justified: bool = Field(default=False, description="Czy bateria jest uzasadniona ekonomicznie")
    hourly_result_without_battery: Optional[Dict[str, Any]] = Field(None, description="Symulacja bez baterii")
    hourly_result_with_battery: Optional[Dict[str, Any]] = Field(None, description="Symulacja z baterią")
    autoconsumption_rate: float = Field(..., description="Autokonsumpcja (0-1)")
    autoconsumption_kwh: Optional[float] = None
    self_sufficiency_rate: float = Field(..., description="Samowystarczalność (0-1)")
    self_sufficiency_percent: Optional[float] = None
    autoconsumption_rate_with_battery: float = Field(default=0.0, description="Autokonsumpcja z baterią")
    self_sufficiency_rate_with_battery: float = Field(default=0.0, description="Samowystarczalność z baterią")
    self_sufficiency_percent_with_battery: Optional[float] = None
    surplus_kwh: Optional[float] = None
    effective_surplus_rate: float = Field(..., description="Stawka net-billing [PLN/kWh]")
    net_billing_annual_deposit_pln: float = Field(..., description="Depozyt net-billing [PLN]")
    shading_loss_percent: Optional[float] = 0.0
    microinverters_recommended: Optional[bool] = False
    microinverters_cost_pln: Optional[float] = 0.0
    facet_area_m2: float | None = None
    facet_slope_length_m: float | None = None
    facet_offset_x: float | None = None


class ScenariosResponse(BaseModel):
    """Odpowiedź z 3 scenariuszami."""
    scenarios: List[ScenarioResponseItem] = Field(..., description="Lista scenariuszy")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Dane wejściowe")
