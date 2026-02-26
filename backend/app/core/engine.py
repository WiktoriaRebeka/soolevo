# backend/app/core/engine.py
"""
Główny punkt wejścia dla obliczeń scenariuszy.
KOMPLETNY PLIK - gotowy do wklejenia.
"""

from typing import Dict, Any, List
from app.schemas.scenarios import ScenariosRequest, ScenariosResponse, ScenarioResponseItem, RoofFacet
from app.core.scenario_runner import ScenarioRunner
from app.core.facet_geometry import compute_facet_area_and_length
# Import rygorystycznych silników obliczeniowych
from app.core.consumption_engine import calculate_annual_demand
from app.core.estimate_annual_consumption import (
    estimate_annual_consumption,
    estimate_heating_load,
    estimate_ev_load,
    estimate_ac_load
)


def calculate_scenarios_engine(request: ScenariosRequest) -> ScenariosResponse:
    """Generuje 3 scenariusze (premium, standard, economy)."""
    consumption_data = _compute_annual_consumption(request)
    annual_consumption_kwh = consumption_data["annual_consumption_kwh"]
    tariff_type = consumption_data["tariff_type"]
    
    if not request.facets or len(request.facets) == 0:
        raise ValueError("Brak płatów dachu (facets) w requescie")
    
    # FIX: Konwertujemy pierwszy facet (który może być dict) na obiekt RoofFacet
    first_facet = RoofFacet(**request.facets[0].model_dump() if hasattr(request.facets[0], 'model_dump') else request.facets[0])
    
    context = _prepare_context_from_facet(
        facet=first_facet,
        annual_consumption_kwh=annual_consumption_kwh,
        province=request.province,
        tariff_type=tariff_type,
        operator=request.operator,
        household_size=request.household_size,
        people_home_weekday=getattr(request, "people_home_weekday", 1),
        request=request # PRZEKAZUJEMY CAŁY REQUEST
    )
    if not request.facets or len(request.facets) == 0:
        raise ValueError("Brak płatów dachu (facets) w requescie")
    
    # FIX: Konwertujemy pierwszy facet (który jest dict) na obiekt RoofFacet
    first_facet_raw = request.facets[0]
    # Obsługa obu przypadków: już obiekt lub słownik
    if isinstance(first_facet_raw, dict):
        first_facet = RoofFacet(**first_facet_raw)
    else:
        first_facet = first_facet_raw  # już jest RoofFacet
    
    context = _prepare_context_from_facet(
        facet=first_facet,
        annual_consumption_kwh=annual_consumption_kwh,
        province=request.province,
        tariff_type=tariff_type,
        operator=request.operator,
        household_size=request.household_size,
        people_home_weekday=getattr(request, "people_home_weekday", 1),
        request=request # PRZEKAZUJEMY CAŁY REQUEST
    )

    scenario_configs = [
        {
            "quality_tier": "premium",
            "markup_percentage": 35,
            "description": "Najwyższa jakość - panele premium, topowy falownik, pełna gwarancja",
        },
        {
            "quality_tier": "standard",
            "markup_percentage": 30,
            "description": "Optymalna równowaga - sprawdzone komponenty, dobra wydajność",
        },
        {
            "quality_tier": "economy",
            "markup_percentage": 25,
            "description": "Najtańsza opcja - komponenty budżetowe, podstawowa gwarancja",
        },
    ]
    
    scenarios_results: List[ScenarioResponseItem] = []
    
    for config in scenario_configs:
        runner = ScenarioRunner(scenario_config=config, context=context)
        result = runner.run()
        
        response_item = ScenarioResponseItem(
            scenario_name=result.scenario_name,
            tier=result.scenario_name,
            label=_get_scenario_label(result.scenario_name),
            description=config["description"],
            panels_count=result.panels_count,
            panel_model=result.panel_model,
            panel_brand=_extract_brand(result.panel_model),
            panel_power_wp=result.panel_power_wp,
            total_power_kwp=result.total_power_kwp,
            inverter_model=result.inverter_model,
            inverter_power_kw=result.inverter_power_kw,
            inverter_brand=_extract_brand(result.inverter_model),
            inverter_quantity=1,
            facet_layouts=result.facet_layouts,
            facet_area_m2=context.get("roof_area_m2"),
            facet_slope_length_m=context.get("roof_slope_length_m"),
            facet_offset_x=context.get("roof_offset_x"),
            annual_production_kwh=result.annual_production_kwh,
            annual_consumption_kwh=result.annual_consumption_kwh,
            annual_demand_kwh=result.annual_consumption_kwh,
            coverage_percent=_compute_coverage_percent(result.annual_production_kwh, result.annual_consumption_kwh),
            pv_cost_gross_pln=result.pv_cost_gross_pln,
            cost_total_gross_pln=result.pv_cost_gross_pln,
            pv_savings_pln=result.pv_savings_pln,
            pv_payback_years=result.pv_payback_years,
            payback_years=result.pv_payback_years,
            pv_payback_optimistic_years=result.pv_payback_optimistic_years,
            payback_optimistic_years=result.pv_payback_optimistic_years,
            pv_payback_pessimistic_years=result.pv_payback_pessimistic_years,
            payback_pessimistic_years=result.pv_payback_pessimistic_years,
            pv_total_savings_25y_pln=result.pv_total_savings_25y_pln,
            battery_recommended=result.battery_recommended,
            battery_capacity_kwh=result.battery_capacity_kwh,
            battery_power_kw=result.battery_power_kw,
            battery_model=result.battery_model,
            battery_cost_gross_pln=result.battery_cost_gross_pln,
            total_cost_with_battery_pln=result.total_cost_with_battery_pln,
            with_battery_total_cost_pln=result.total_cost_with_battery_pln,
            battery_savings_pln=result.battery_savings_pln,
            total_savings_with_battery_pln=result.total_savings_with_battery_pln,
            battery_payback_years=result.battery_payback_years,
            with_battery_payback_years=result.battery_payback_years,
            battery_payback_optimistic_years=result.battery_payback_optimistic_years,
            with_battery_payback_optimistic_years=result.battery_payback_optimistic_years,
            battery_payback_pessimistic_years=result.battery_payback_pessimistic_years,
            with_battery_payback_pessimistic_years=result.battery_payback_pessimistic_years,
            battery_total_savings_25y_pln=result.battery_total_savings_25y_pln,
            is_economically_justified=result.is_economically_justified,
            hourly_result_without_battery=result.hourly_result_without_battery,
            hourly_result_with_battery=result.hourly_result_with_battery,
            autoconsumption_rate=result.autoconsumption_rate,
            autoconsumption_kwh=_compute_autoconsumption_kwh(result),
            self_sufficiency_rate=result.self_sufficiency_rate,
            self_sufficiency_percent=result.self_sufficiency_rate * 100,
            autoconsumption_rate_with_battery=result.autoconsumption_rate_with_battery,
            self_sufficiency_rate_with_battery=result.self_sufficiency_rate_with_battery,
            self_sufficiency_percent_with_battery=result.self_sufficiency_rate_with_battery * 100,

            surplus_kwh=_compute_surplus_kwh(result),
            effective_surplus_rate=result.effective_surplus_rate,
            net_billing_annual_deposit_pln=result.net_billing_annual_deposit_pln,
            shading_loss_percent=result.shading_loss_percent,
            microinverters_recommended=False,
            microinverters_cost_pln=0.0,
        )
        
        scenarios_results.append(response_item)
    
    return ScenariosResponse(
        scenarios=scenarios_results,
        input_data={
            "bill": request.bill,
            "is_annual_bill": request.is_annual_bill,
            "province": request.province,
            "annual_consumption_kwh": annual_consumption_kwh,
            "roof_area_m2": context.get("roof_area_m2"),
            "roof_slope_length_m": context.get("roof_slope_length_m"),
            "roof_offset_x": context.get("roof_offset_x"),
        },
    )


def _compute_annual_consumption(request: ScenariosRequest) -> Dict[str, Any]:
    """
    Oblicza roczne zużycie energii. 
    Eliminuje błąd dzielenia przez 0.80 i wprowadza rzetelną dekompozycję rachunku.
    """
    # 1. Wyznaczenie bazy (z rachunku lub estymacji metrażowej)
    if request.estimated_consumption_mode and request.area_m2:
        # Tryb: Nowy dom (brak rachunków)
        base_consumption = estimate_annual_consumption(
            area_m2=request.area_m2,
            residents=request.household_size,
            standard=request.building_standard or "WT2021",
            uses_induction=request.uses_induction,
        )
    else:
        # Tryb: Istniejący dom (liczymy z rachunku PLN -> kWh)
        # Rygorystyczna dekompozycja uwzględniająca opłaty stałe i mocowe
        base_consumption = calculate_annual_demand(
            bill_pln=request.bill,
            is_annual_bill=request.is_annual_bill,
            operator=request.operator,
            tariff=request.tariff
        )
    
    # 2. Dodanie planowanych obciążeń (Add-ons)
    # Używamy funkcji estymujących zamiast sztywnych stałych
    additional_consumption = 0.0
    if request.planned_ev:
        additional_consumption += estimate_ev_load(ev_km_per_year=15000)
    if request.planned_heat_pump:
        # Jeśli użytkownik ma rachunek, ale planuje pompę, szacujemy jej pobór dla metrażu
        area = request.area_m2 or 150 
        additional_consumption += estimate_heating_load(area_m2=area, has_heat_pump=True)
    if request.planned_ac:
        additional_consumption += estimate_ac_load(has_ac=True)
    if request.planned_other_kwh:
        additional_consumption += request.planned_other_kwh
    
    total_annual_kwh = base_consumption + additional_consumption
    
    # 3. Normalizacja typu taryfy
    tariff_type = request.tariff.upper().replace("-", "")
    if tariff_type not in ["G11", "G12", "G12W"]:
        tariff_type = "G11"
    
    return {
        "annual_consumption_kwh": round(total_annual_kwh, 0),
        "tariff_type": tariff_type,
    }


def _prepare_context_from_facet(
    facet: RoofFacet,
    annual_consumption_kwh: float,
    province: str,
    tariff_type: str,
    operator: str,
    household_size: int,
    people_home_weekday: int,
    request: ScenariosRequest, # DODAJEMY CAŁY REQUEST
) -> Dict[str, Any]:
    """Przygotowuje kontekst dla ScenarioRunner z uwzględnieniem operatora i profilu zużycia."""
    geom = compute_facet_area_and_length(facet)

    return {
        "annual_consumption_kwh": annual_consumption_kwh,
        "location": province,
        "operator": operator,
        "tariff_type": tariff_type,
        "roof_area_m2": geom["area"],
        "roof_slope_length_m": geom["slope_length"],
        "roof_offset_x": geom["offset_x"],
        "roof_tilt": facet.angle,
        "roof_azimuth": facet.azimuth_deg,
        "roof_type": facet.roof_type,
        "facet_obj": facet,
        "household_size": household_size,
        "people_home_weekday": people_home_weekday,
        "request": request, # PRZEKAZUJEMY DALEJ
    }
    
def _get_scenario_label(scenario_name: str) -> str:
    """Zwraca label dla scenariusza."""
    labels = {"premium": "Premium", "standard": "Standard", "economy": "Economy"}
    return labels.get(scenario_name, scenario_name.capitalize())


def _extract_brand(model_name: str) -> str:
    """Wyciąga markę z nazwy modelu."""
    if not model_name:
        return ""
    parts = model_name.split()
    return parts[0] if parts else ""


def _extract_power_wp(model_name: str) -> int:
    """Wyciąga moc w Wp z nazwy modelu."""
    import re
    if not model_name:
        return 0
    match = re.search(r'(\d+)[A-Za-z]?$', model_name)
    if match:
        return int(match.group(1))
    return 0


def _compute_coverage_percent(production: float, consumption: float) -> float:
    """Oblicza % pokrycia zapotrzebowania."""
    if consumption == 0:
        return 0.0
    return min(100.0, (production / consumption) * 100)


def _compute_autoconsumption_kwh(result) -> float:
    """Wyciąga autoconsumption w kWh."""
    if result.hourly_result_without_battery:
        return result.hourly_result_without_battery["energy_flow"]["autoconsumption_kwh"]
    return result.annual_production_kwh * result.autoconsumption_rate


def _compute_surplus_kwh(result) -> float:
    """Wyciąga nadwyżkę w kWh."""
    if result.hourly_result_without_battery:
        return result.hourly_result_without_battery["energy_flow"]["surplus_kwh"]
    return result.annual_production_kwh * (1 - result.autoconsumption_rate)
