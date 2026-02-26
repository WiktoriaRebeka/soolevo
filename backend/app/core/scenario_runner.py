# backend/app/core/scenario_runner.py
"""
ScenarioRunner - Orkiestruje obliczenia dla pojedynczego scenariusza.

v3.1 - WSZYSTKIE POPRAWKI:
✅ Godzinowe ceny RCEm
✅ Taryfy G12/G12w
✅ Rozdział energia/dystrybucja
✅ Limit zwrotu 20%
✅ Opportunity cost baterii
✅ Wymiana falownika w ROI
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from app.core.hourly_engine import HourlyEngine
from app.core.battery_engine import BatteryEngine
from app.core.financial_engine import FinancialEngine
from app.core.layout_engine import LayoutEngine
from app.core.production_engine import ProductionEngine
from app.data.energy_rates import (
    get_retail_tariff_pln_per_kwh,
    get_tariff_zones_g11,
    get_tariff_zones_g12,
    calculate_average_tariff,
)
from app.core.facet_geometry import compute_facet_area_and_length
from app.core.consumption_engine import decompose_consumption
@dataclass
class ScenarioResult:
    """Wynik obliczeń dla pojedynczego scenariusza."""
    scenario_name: str
    panels_count: int
    panel_model: str
    panel_power_wp: int 
    total_power_kwp: float
    inverter_model: str
    inverter_power_kw: float
    facet_layouts: List[Any] 
    annual_production_kwh: float
    annual_consumption_kwh: float
    pv_cost_gross_pln: float
    pv_savings_pln: float
    pv_payback_years: float
    pv_payback_optimistic_years: float
    pv_payback_pessimistic_years: float
    pv_total_savings_25y_pln: float
    battery_recommended: bool
    battery_capacity_kwh: float
    battery_power_kw: float
    battery_model: str
    battery_cost_gross_pln: float
    total_cost_with_battery_pln: float
    battery_savings_pln: float
    total_savings_with_battery_pln: float
    battery_payback_years: float
    battery_payback_optimistic_years: float
    battery_payback_pessimistic_years: float
    battery_total_savings_25y_pln: float
    autoconsumption_rate: float
    self_sufficiency_rate: float
    autoconsumption_rate_with_battery: float
    self_sufficiency_rate_with_battery: float
    self_sufficiency_percent_with_battery: float
    effective_surplus_rate: float
    net_billing_annual_deposit_pln: float
    is_economically_justified: bool = False
    shading_loss_percent: float = 0.0
    hourly_result_without_battery: Optional[Dict[str, Any]] = None
    hourly_result_with_battery: Optional[Dict[str, Any]] = None

class ScenarioRunner:
    """Orkiestruje obliczenia dla pojedynczego scenariusza (premium/standard/economy)."""

    def __init__(self, scenario_config: Dict[str, Any], context: Dict[str, Any]):
        self.scenario_config = scenario_config
        self.context = context
        
        self.layout_engine = LayoutEngine(scenario_config)
        self.production_engine = ProductionEngine()
        self.battery_engine = BatteryEngine(scenario_config)
        self.financial_engine = FinancialEngine(scenario_config)

 
    def run(self) -> ScenarioResult:
        """Uruchamia pełny pipeline obliczeń."""
        from app.schemas.scenarios import FacetLayout, PanelPosition
        # 1. Pobierz dane wejściowe z kontekstu (naprawia NameError)
        facet = self.context["facet_obj"]
        quality_tier = self.scenario_config.get("quality_tier", "standard")
        annual_consumption_kwh = self.context["annual_consumption_kwh"]
        location = self.context.get("location", "mazowieckie")
        operator = self.context.get("operator", "pge") # FIX: Pobranie operatora
        
        geom = compute_facet_area_and_length(facet)
        slope_h = geom["slope_length"]
        offset_x = geom["offset_x"]

        # Inicjalizacja zmiennych dla baterii (FIX: Zapobiega błędom, gdy bateria nie jest wybrana)
        battery_savings_pln = 0.0
        total_savings_with_battery_pln = 0.0
        is_economically_justified = False # <--- INICJALIZACJA
        battery_payback_years = 0.0
        battery_payback_optimistic = 0.0
        battery_payback_pessimistic = 0.0
        battery_total_savings_25y = 0.0
        battery_cost_gross_pln = 0.0
        total_cost_with_battery_pln = 0.0
        autoconsumption_rate_with_battery = 0.0
        self_sufficiency_rate_with_battery = 0.0
        hourly_result_with_batt = None


        # 2. Dobór sprzętu (Panele z pełnymi danymi inżynierskimi)
        from app.data.equipment_scenarios import get_scenario_by_tier
        
        scenario_preset = get_scenario_by_tier(quality_tier)
        panel_data = scenario_preset["panel"]
        panel_model = f"{panel_data['brand']} {panel_data['model']}"
        panel_power_kwp = panel_data["power_wp"] / 1000
        # 3. Oblicz limity dachu (naprawia TypeError)
        max_panels_info = self.layout_engine.compute_max_panels(
            facet, 
            panel_width_m=panel_data["width_m"], 
            panel_height_m=panel_data["height_m"]
        )
        max_panels = max_panels_info["placed_count"]

        # 4. Oblicz zapotrzebowanie (ile paneli chcemy)
        required_panels = self.production_engine.estimate_required_panels(
            future_demand=annual_consumption_kwh,
            target_ratio=1.1,
            power_kwp=panel_power_kwp,
            best_facet={"facet_obj": facet},
            province=location,
            config={"panel": panel_data}
        )

        # 5. Finalna liczba paneli (v4.4 - Rzetelność kosztowa)
        panels_count = min(max_panels, required_panels)
        # Logika dla GRUNTU: Zawsze parzysta liczba paneli (układ 2H)
        if facet.roof_type == "ground" and panels_count > 0:
            if panels_count % 2 != 0:
                # Jeśli nieparzysta, spróbuj dodać 1 panel
                if panels_count + 1 <= max_panels:
                    panels_count += 1
                else:
                    # Jeśli nie ma miejsca na +1, odejmij 1
                    panels_count -= 1
        # Jeśli dach jest za mały, zerujemy wszystko
        if panels_count < 0: panels_count = 0
        
        total_power_kwp = panels_count * panel_power_kwp


        # Jeśli nie ma paneli, cała inwestycja wynosi 0
        if panels_count <= 0:
            return self._generate_empty_scenario_result(quality_tier, annual_consumption_kwh)

        # 6. Dobór falownika
        # 6. Dobór falownika
        inverter_info = self.financial_engine.compute_inverter(total_power_kwp)

        # 7. Generowanie layoutu dla frontendu

        facet_layout_grid = self.layout_engine.generate_layout(
            facet,
            count=panels_count,
            panel_width_m=panel_data["width_m"],
            panel_height_m=panel_data["height_m"]
        )
        # Mapowanie na schemat Pydantic dla wizualizacji

        panel_positions = [
            PanelPosition(
                x=p["x"],
                y=p["y"],
                width=p["width"],
                height=p["height"],
                label=p.get("label")
            )
            for p in facet_layout_grid
        ]

        facet_layouts = [
            FacetLayout(
                facet_id=facet.id,
                panels_count=panels_count,
                azimuth_deg=facet.azimuth_deg,
                efficiency_factor=1.0,
                layout=panel_positions,
                rhombus_side_b=offset_x
            )
        ]
        # Przygotuj layout_result dla kompatybilności z resztą metody
        layout_result = {
            "panels_count": panels_count,
            "panel_model": panel_model,
            "total_power_kwp": total_power_kwp,
            "inverter_model": inverter_info["inverter_model"],
            "inverter_power_kw": inverter_info["inverter_power_kw"],
            "facet_layouts": facet_layouts
        }

        # 8. Symulacja produkcji z uwzględnieniem ZACIENIENIA
        from app.data.sunlight import get_monthly_sunlight
        from app.core.shading import calculate_shading_loss
        
        monthly_irradiance = get_monthly_sunlight(location)
        
        # Obliczamy stratę z zacienienia (np. 0.25 dla południa)
        shading_loss = calculate_shading_loss(
            facet.has_shading, 
            facet.shading_direction, 
            "south" # orientacja dachu
        )

        yield_result = self.production_engine.calculate_monthly_production(
            panel_power_kwp=panel_power_kwp,
            panel_area_m2=(panel_data["width_m"] * panel_data["height_m"]) * panels_count,
            panel_efficiency=panel_data["efficiency"],
            province=location,
            monthly_irradiance=monthly_irradiance,
            panel_config=panel_data,
            azimuth_deg=self.context["roof_azimuth"],
            tilt_deg=self.context["roof_tilt"]
        )
        
        # Nakładamy stratę zacienienia na roczną produkcję
        annual_production_kwh = yield_result["annual_kwh"] * (1 - shading_loss)
 # =====================================================================
        # KROK 3: PRZYGOTOWANIE PARAMETRÓW TARYFOWYCH (v3.2 - Real Data)
        # =====================================================================
        from app.data.energy_rates import ENERGY_RATES, decompose_electricity_tariff
        
        tariff_type = self.context.get("tariff_type", "G11").lower().replace("-", "")
        # Pobieramy realne stawki dla wybranego operatora
        rates = ENERGY_RATES.get(operator, ENERGY_RATES["pge"]).get(tariff_type, ENERGY_RATES["pge"]["g11"])
        
        # FIX: Definiujemy other_fees na początku, aby były dostępne dla każdej taryfy
        other_fees = rates.get("quality_fee_kwh", 0) + rates.get("oze_fee_kwh", 0) + rates.get("cogeneration_fee_kwh", 0)

        # Pobieramy dekompozycję (ile kosztuje 1 kWh ze wszystkimi opłatami)
        components = decompose_electricity_tariff(operator, tariff_type)
        avg_tariff = components["total_variable_pln_per_kwh"]

        # Przygotowanie stref dla HourlyEngine
        if "energy_price_kwh" in rates:
            # Taryfa jednostrefowa G11
            tariff_zones = get_tariff_zones_g11(avg_tariff)
        else:
            # Taryfa dwustrefowa G12 / G12w
            v_peak = rates["energy_price_kwh_peak"] + rates["distribution_variable_kwh_peak"] + other_fees
            v_off = rates["energy_price_kwh_offpeak"] + rates["distribution_variable_kwh_offpeak"] + other_fees
            tariff_zones = get_tariff_zones_g12(v_peak, v_off)

        # =====================================================================
        # KROK 4: DEKOMPOZYCJA I SYMULACJA GODZINOWA
        # =====================================================================
        from app.data.energy_prices_tge import get_rcem_hourly
        from app.core.consumption_engine import decompose_consumption
        
        rcem_hourly = get_rcem_hourly(year=2025)
        
        # Rozbijamy zużycie na kubły sezonowe (Base, Heating, Cooling)
        buckets = decompose_consumption(annual_consumption_kwh, self.context["request"])
        
        hourly_engine_no_batt = HourlyEngine(
            annual_production_kwh=annual_production_kwh,
            annual_consumption_kwh=annual_consumption_kwh,
            electricity_tariff_pln_per_kwh=avg_tariff,
            rcem_hourly=rcem_hourly,
            tariff_type=tariff_type,
            tariff_zones=tariff_zones,
            heating_kwh=buckets["heating_kwh"], # NOWY PARAMETR
            cooling_kwh=buckets["cooling_kwh"], # NOWY PARAMETR
            battery_config={
                "operator": operator,
                "household_size": self.context.get("household_size", 3),
                "people_home_weekday": self.context.get("people_home_weekday", 1),
            },
        )
        hourly_result_no_batt = hourly_engine_no_batt.run_hourly_simulation()
        
        # ŹRÓDŁO PRAWDY dla oszczędności PV-only
        pv_savings_pln = hourly_result_no_batt["annual_cashflow"]["net"]
        
        autoconsumption_rate = hourly_result_no_batt["rates"]["autoconsumption_rate"]
        self_sufficiency_rate = hourly_result_no_batt["rates"]["self_sufficiency_rate"]
        effective_surplus_rate = hourly_result_no_batt["net_billing"]["effective_rate_pln_per_kwh"]
        net_billing_annual_deposit = hourly_result_no_batt["net_billing"]["annual_deposit_pln"]

        # =====================================================================
        # KROK 5: FINANSE (CAPEX + ROI dla PV-only)
        # =====================================================================
        capex_pv = self.financial_engine.compute_capex(
            panels_count=panels_count,
            panel_model=panel_model,
            inverter_model=layout_result["inverter_model"],
            battery_capacity_kwh=None,
        )
        
        pv_cost_gross_pln = capex_pv["pv_cost_gross_pln"]
        
        roi_pv = self.financial_engine.compute_roi(
            investment_gross_pln=pv_cost_gross_pln,
            base_annual_savings_pln=pv_savings_pln,
            inverter_cost_pln=capex_pv.get("inverter_cost_pln", 0),
        )

# =====================================================================
        # KROK 6: BATERIA (czy rekomendowana?)
        # =====================================================================
        # Pobieramy nadwyżkę z symulacji bez baterii
        surplus_kwh = hourly_result_no_batt["energy_flow"]["surplus_kwh"]

        battery_recommendation = self.battery_engine.recommend_battery(
            annual_production_kwh=annual_production_kwh,
            annual_consumption_kwh=annual_consumption_kwh,
            annual_surplus_kwh=surplus_kwh, # ✅ Dodano brakujący argument
            autoconsumption_rate=autoconsumption_rate,
        )
        
        # ✅ Bezpieczne sprawdzenie czy bateria jest zarekomendowana
        battery_recommended = battery_recommendation is not None
        
        if battery_recommended:
            battery_capacity_kwh = battery_recommendation["capacity_kwh"]
            battery_power_kw = battery_recommendation["power_kw"]
            battery_model = battery_recommendation["model"]
            is_economically_justified = battery_recommendation.get("is_economically_justified", False)
        else:
            battery_capacity_kwh = 0.0
            battery_power_kw = 0.0
            battery_model = ""

        # =====================================================================
        # KROK 7: SYMULACJA Z BATERIĄ (jeśli rekomendowana)
        # =====================================================================
        if battery_recommended and battery_capacity_kwh > 0:
            # FIX: Wszystkie parametry kontekstu muszą być identyczne jak w symulacji
            # bez baterii — w przeciwnym razie HourlyEngine generuje inny profil
            # zużycia i oba wyniki są nieporównywalne.
            battery_config = {
                "capacity_kwh": battery_capacity_kwh,
                "power_kw": battery_power_kw,
                "efficiency": 0.95,
                "operator": operator,
                "household_size": self.context.get("household_size", 3),
                "people_home_weekday": self.context.get("people_home_weekday", 1),
            }
            
            hourly_engine_with_batt = HourlyEngine(
                annual_production_kwh=annual_production_kwh,
                annual_consumption_kwh=annual_consumption_kwh,
                electricity_tariff_pln_per_kwh=avg_tariff,
                rcem_hourly=rcem_hourly,
                tariff_type=tariff_type,
                tariff_zones=tariff_zones,
                heating_kwh=buckets["heating_kwh"], # MUSI BYĆ IDENTYCZNE JAK W NO_BATT
                cooling_kwh=buckets["cooling_kwh"], # MUSI BYĆ IDENTYCZNE JAK W NO_BATT
                battery_config=battery_config,
            )
            
            hourly_result_with_batt = hourly_engine_with_batt.run_hourly_simulation()
            
            # ŹRÓDŁO PRAWDY dla oszczędności z baterią
            total_savings_with_battery_pln = hourly_result_with_batt["annual_cashflow"]["net"]
            
            # Różnica = korzyść z baterii
            battery_savings_pln = total_savings_with_battery_pln - pv_savings_pln
            
            autoconsumption_rate_with_battery = hourly_result_with_batt["rates"]["autoconsumption_rate"]
            self_sufficiency_rate_with_battery = hourly_result_with_batt["rates"]["self_sufficiency_rate"]
            
            # CAPEX baterii
            capex_battery = self.financial_engine.compute_capex(
                panels_count=panels_count,
                panel_model=panel_model,
                inverter_model=layout_result["inverter_model"],
                battery_capacity_kwh=battery_capacity_kwh,
            )
            
            battery_cost_gross_pln = capex_battery["battery_cost_gross_pln"]
            total_cost_with_battery_pln = capex_battery["total_cost_gross_pln"]
            
            # ROI dla PV + bateria
            roi_battery = self.financial_engine.compute_roi(
                investment_gross_pln=total_cost_with_battery_pln,
                base_annual_savings_pln=total_savings_with_battery_pln,
                inverter_cost_pln=capex_pv.get("inverter_cost_pln", 0),
            )
            
            battery_payback_years = roi_battery["payback_years"]
            battery_payback_optimistic = roi_battery["payback_optimistic_years"]
            battery_payback_pessimistic = roi_battery["payback_pessimistic_years"]
            battery_total_savings_25y = roi_battery["total_savings_25y_pln"]

        # =====================================================================
        # KROK 8: ZWRÓĆ WYNIK (v3.2 - Fix variable names)
        # =====================================================================
        return ScenarioResult(
            scenario_name=quality_tier,
            panels_count=panels_count,
            panel_model=panel_model,
            total_power_kwp=total_power_kwp,
            panel_power_wp=int(panel_power_kwp * 1000),
            is_economically_justified=is_economically_justified,
            inverter_model=layout_result["inverter_model"],
            inverter_power_kw=layout_result["inverter_power_kw"],
            facet_layouts=facet_layouts,
            annual_production_kwh=annual_production_kwh,
            annual_consumption_kwh=annual_consumption_kwh,
            pv_cost_gross_pln=pv_cost_gross_pln,
            pv_savings_pln=pv_savings_pln,
            pv_payback_years=roi_pv["payback_years"],
            pv_payback_optimistic_years=roi_pv["payback_optimistic_years"],
            pv_payback_pessimistic_years=roi_pv["payback_pessimistic_years"],
            pv_total_savings_25y_pln=roi_pv["total_savings_25y_pln"],
            battery_recommended=battery_recommended,
            battery_capacity_kwh=battery_capacity_kwh,
            battery_power_kw=battery_power_kw,
            battery_model=battery_model,
            battery_cost_gross_pln=battery_cost_gross_pln,
            total_cost_with_battery_pln=total_cost_with_battery_pln,
            battery_savings_pln=battery_savings_pln,
            total_savings_with_battery_pln=total_savings_with_battery_pln,
            battery_payback_years=battery_payback_years,
            battery_payback_optimistic_years=battery_payback_optimistic,
            battery_payback_pessimistic_years=battery_payback_pessimistic,
            battery_total_savings_25y_pln=battery_total_savings_25y,
            autoconsumption_rate=autoconsumption_rate,
            self_sufficiency_rate=self_sufficiency_rate,
            autoconsumption_rate_with_battery=autoconsumption_rate_with_battery,
            self_sufficiency_rate_with_battery=self_sufficiency_rate_with_battery,
            self_sufficiency_percent_with_battery=self_sufficiency_rate_with_battery * 100,
            effective_surplus_rate=effective_surplus_rate,
            net_billing_annual_deposit_pln=net_billing_annual_deposit,
            shading_loss_percent=shading_loss * 100, 
            hourly_result_without_battery=hourly_result_no_batt,
            hourly_result_with_battery=hourly_result_with_batt,
        )

    def _generate_empty_scenario_result(self, tier: str, consumption: float) -> ScenarioResult:
        """Generuje bezpieczny, wyzerowany wynik, gdy instalacja nie jest możliwa."""
        return ScenarioResult(
            scenario_name=tier,
            panels_count=0,
            panel_model="Brak miejsca na dachu",
            panel_power_wp=0,
            total_power_kwp=0.0,
            inverter_model="N/A",
            inverter_power_kw=0.0,
            facet_layouts=[],
            annual_production_kwh=0.0,
            annual_consumption_kwh=consumption,
            pv_cost_gross_pln=0.0,
            pv_savings_pln=0.0,
            pv_payback_years=0.0,
            pv_payback_optimistic_years=0.0,
            pv_payback_pessimistic_years=0.0,
            pv_total_savings_25y_pln=0.0,
            battery_recommended=False,
            battery_capacity_kwh=0.0,
            battery_power_kw=0.0,
            battery_model="",
            battery_cost_gross_pln=0.0,
            total_cost_with_battery_pln=0.0,
            battery_savings_pln=0.0,
            total_savings_with_battery_pln=0.0,
            battery_payback_years=0.0,
            battery_payback_optimistic_years=0.0,
            battery_payback_pessimistic_years=0.0,
            battery_total_savings_25y_pln=0.0,
            autoconsumption_rate=0.0,
            self_sufficiency_rate=0.0,
            autoconsumption_rate_with_battery=0.0,
            self_sufficiency_rate_with_battery=0.0,
            self_sufficiency_percent_with_battery=0.0,
            effective_surplus_rate=0.0,
            net_billing_annual_deposit_pln=0.0,
            is_economically_justified=False
        )
