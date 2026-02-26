# backend/app/schemas/report.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .scenarios import ScenariosRequest # Importujemy istniejący ScenariosRequest

class ReportRequest(BaseModel):
    """Request dla endpointu raportu, bazujący na ScenariosRequest + opcje raportu."""
    # W zasadzie kopiujemy ScenariosRequest, ale dodajemy pole raportu
    bill: float
    is_annual_bill: bool
    operator: str
    tariff: str
    province: str
    household_size: int
    people_home_weekday: int
    facets: List[Any] # Używamy Any, bo nie chcemy importować RoofFacet tutaj
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
    
    # Nowe pole dla raportu
    scenario_to_highlight: str = Field("standard", description="Scenariusz do wyróżnienia w raporcie")


class Warning(BaseModel):
    """Pojedyncze ostrzeżenie/potwierdzenie dla raportu."""
    type: str = Field(..., description="Typ ostrzeżenia: 'red', 'yellow', 'green'")
    code: str = Field(..., description="Kod ostrzeżenia: np. 'W1', 'U2'")
    title: str
    message: str

class ReportData(BaseModel):
    """Kompletny zestaw danych do wygenerowania raportu PDF."""
    input_request: ScenariosRequest # Używamy oryginalnego requestu
    highlighted_scenario_name: str = Field("standard", description="Nazwa scenariusza do wyróżnienia w raporcie")
    all_scenarios_results: Dict[str, Any] # Będzie zawierać wyniki dla 'premium', 'standard', 'economy'
    warnings_and_confirmations: List[Warning]
    # Dodatkowe dane, które mogą być potrzebne do wykresów/podsumowania
    input_data_summary: Dict[str, Any]