# backend/app/core/scenario_runner.py
"""
ScenarioRunner - Orkiestruje obliczenia dla pojedynczego scenariusza.

v4.0 — WSZYSTKIE POPRAWKI:
✅ Godzinowe ceny RCEm
✅ Taryfy G12/G12w
✅ Rozdział energia/dystrybucja
✅ Limit zwrotu 20%
✅ Opportunity cost baterii
✅ Wymiana falownika w ROI
✅ ScenarioResult jako Pydantic BaseModel (obsługuje model_dump())
✅ Realny godzinowy profil produkcji z danych irradiancji (nie sinus)
✅ Spójny profil produkcji dla symulacji z baterią i bez
"""

import math
from typing import Dict, Any, Optional, List

from pydantic import BaseModel
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


# =============================================================================
# POMOCNICZA FUNKCJA: Rozszerzenie miesięcznych danych produkcji do 8760h
# =============================================================================

def _expand_monthly_to_hourly_production(
    monthly_kwh_dict: dict,
    annual_total_kwh: float,
    days_per_month: list = None,
) -> List[float]:
    """
    Rozszerza miesięczne dane produkcji PV (kWh/miesiąc) do profilu godzinowego 8760h.

    Używa sezonowego modelu długości dnia słońca:
      - Styczeń: słońce ok. 7:00–15:00 (8h)
      - Czerwiec: słońce ok. 5:00–21:00 (16h)

    Normalizuje wynik do rocznej sumy z ProductionEngine (z korekcją temperatury i IAM).

    Args:
        monthly_kwh_dict: Słownik {nazwa_miesiąca: kWh} z ProductionEngine.
                          Obsługuje klucze polskie i angielskie.
        annual_total_kwh: Roczna suma produkcji z ProductionEngine (do normalizacji).
        days_per_month:   Opcjonalna lista liczby dni w każdym miesiącu
                          (domyślnie rok nieprzestępny).

    Returns:
        Lista 8760 wartości float [kWh/h].
    """
    DAYS = days_per_month or [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    NAMES_PL = [
        "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
        "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
    ]
    NAMES_EN = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    ]

    # Wyciągamy miesięczne wartości w kolejności kalendarzowej
    monthly_vals: List[float] = []
    for pl, en in zip(NAMES_PL, NAMES_EN):
        val = (
            monthly_kwh_dict.get(pl)
            or monthly_kwh_dict.get(en)
            or monthly_kwh_dict.get(pl.capitalize())
            or monthly_kwh_dict.get(en.capitalize())
            or 0.0
        )
        monthly_vals.append(float(val))

    profile: List[float] = []

    for m_idx, (days, monthly_kwh) in enumerate(zip(DAYS, monthly_vals)):
        daily_kwh = monthly_kwh / max(days, 1)

        # Sezonowa długość dnia słońca (przybliżona sinusoida)
        # m_idx=0 → styczeń (min ~8h), m_idx=5 → czerwiec (max ~16h)
        phase     = math.pi * m_idx / 11.0  # 0 → π w ciągu roku
        sun_start = max(5, int(8 - 2 * math.sin(phase)))
        sun_end   = min(21, int(16 + 2 * math.sin(phase)))
        span      = max(sun_end - sun_start, 1)
        mid       = (sun_start + sun_end) / 2.0

        for _day in range(days):
            for h in range(24):
                if sun_start <= h <= sun_end:
                    # Paraboliczny profil dzienny (0 na brzegach, 1 w południe)
                    hf = max(0.0, 1.0 - ((h - mid) / (span / 2.0)) ** 2)
                else:
                    hf = 0.0
                profile.append(daily_kwh * hf)

    # Normalizacja do rocznej sumy z ProductionEngine
    total = sum(profile)
    if total > 0.0 and annual_total_kwh > 0.0:
        scale   = annual_total_kwh / total
        profile = [v * scale for v in profile]

    # Gwarancja dokładnie 8760 wartości
    if len(profile) > 8760:
        profile = profile[:8760]
    elif len(profile) < 8760:
        profile += [0.0] * (8760 - len(profile))

    return profile


# =============================================================================
# DATACLASS WYNIKOWY — Pydantic BaseModel (obsługuje .model_dump())
# =============================================================================

class ScenarioResult(BaseModel):
    """Wynik obliczeń dla pojedynczego scenariusza PV."""

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

    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# GŁÓWNA KLASA
# =============================================================================

class ScenarioRunner:
    """Orkiestruje obliczenia dla pojedynczego scenariusza (premium/standard/economy)."""

    def __init__(self, scenario_config: Dict[str, Any], context: Dict[str, Any]):
        self.scenario_config   = scenario_config
        self.context           = context

        self.layout_engine     = LayoutEngine(scenario_config)
        self.production_engine = ProductionEngine()
        self.battery_engine    = BatteryEngine(scenario_config)
        self.financial_engine  = FinancialEngine(scenario_config)

    # ─────────────────────────────────────────────────────────────────────────
    def run(self) -> ScenarioResult:
        """Uruchamia pełny pipeline obliczeń."""
        from app.schemas.scenarios import FacetLayout, PanelPosition

        # =====================================================================
        # KROK 1: Dane wejściowe z kontekstu
        # =====================================================================
        facet                  = self.context["facet_obj"]
        quality_tier           = self.scenario_config.get("quality_tier", "standard")
        annual_consumption_kwh = self.context["annual_consumption_kwh"]
        location               = self.context.get("location", "mazowieckie")
        operator               = self.context.get("operator", "pge")

        geom     = compute_facet_area_and_length(facet)
        slope_h  = geom["slope_length"]
        offset_x = geom["offset_x"]

        # Inicjalizacja zmiennych baterii — domyślne zera, nadpisywane w KROK 7
        battery_savings_pln                = 0.0
        total_savings_with_battery_pln     = 0.0
        is_economically_justified          = False
        battery_payback_years              = 0.0
        battery_payback_optimistic         = 0.0
        battery_payback_pessimistic        = 0.0
        battery_total_savings_25y          = 0.0
        battery_cost_gross_pln             = 0.0
        total_cost_with_battery_pln        = 0.0
        autoconsumption_rate_with_battery  = 0.0
        self_sufficiency_rate_with_battery = 0.0
        hourly_result_with_batt            = None

        # =====================================================================
        # KROK 2: Dobór sprzętu
        # =====================================================================
        from app.data.equipment_scenarios import get_scenario_by_tier

        scenario_preset = get_scenario_by_tier(quality_tier)
        panel_data      = scenario_preset["panel"]
        panel_model     = f"{panel_data['brand']} {panel_data['model']}"
        panel_power_kwp = panel_data["power_wp"] / 1000.0

        # =====================================================================
        # KROK 3: Limity dachu i dobór liczby paneli
        # =====================================================================
        max_panels_info = self.layout_engine.compute_max_panels(
            facet,
            panel_width_m=panel_data["width_m"],
            panel_height_m=panel_data["height_m"],
        )
        max_panels = max_panels_info["placed_count"]

        required_panels = self.production_engine.estimate_required_panels(
            future_demand=annual_consumption_kwh,
            target_ratio=1.1,
            power_kwp=panel_power_kwp,
            best_facet={"facet_obj": facet},
            province=location,
            config={"panel": panel_data},
        )

        panels_count = min(max_panels, required_panels)

        # Logika dla gruntu: parzysta liczba paneli (układ 2H)
        if facet.roof_type == "ground" and panels_count > 0:
            if panels_count % 2 != 0:
                if panels_count + 1 <= max_panels:
                    panels_count += 1
                else:
                    panels_count -= 1

        if panels_count < 0:
            panels_count = 0

        total_power_kwp = panels_count * panel_power_kwp

        if panels_count <= 0:
            return self._generate_empty_scenario_result(quality_tier, annual_consumption_kwh)

        # Dobór falownika
        inverter_info = self.financial_engine.compute_inverter(total_power_kwp)

        # =====================================================================
        # KROK 3b: Layout paneli dla frontendu
        # =====================================================================
        facet_layout_grid = self.layout_engine.generate_layout(
            facet,
            count=panels_count,
            panel_width_m=panel_data["width_m"],
            panel_height_m=panel_data["height_m"],
        )

        panel_positions = [
            PanelPosition(
                x=p["x"],
                y=p["y"],
                width=p["width"],
                height=p["height"],
                label=p.get("label"),
            )
            for p in facet_layout_grid
        ]

        facet_layouts = [
            FacetLayout(
                facet_id=facet.id,
                panels_count=panels_count,
                panel_width_m=panel_data["width_m"],
                panel_height_m=panel_data["height_m"],
                azimuth_deg=facet.azimuth_deg,
                efficiency_factor=1.0,
                layout=panel_positions,
                rhombus_side_b=offset_x,
                row_distribution=max_panels_info.get("row_distribution", []),
            )
        ]

        layout_result = {
            "panels_count":      panels_count,
            "panel_model":       panel_model,
            "total_power_kwp":   total_power_kwp,
            "inverter_model":    inverter_info["inverter_model"],
            "inverter_power_kw": inverter_info["inverter_power_kw"],
            "facet_layouts":     facet_layouts,
        }

        # =====================================================================
        # KROK 3c: Produkcja miesięczna — dane rzeczywiste z irradiancji
        # =====================================================================
        from app.data.sunlight import get_monthly_sunlight
        from app.core.shading import calculate_shading_loss

        monthly_irradiance = get_monthly_sunlight(location)

        shading_loss = calculate_shading_loss(
            facet.has_shading,
            facet.shading_direction,
            "south",
        )

        yield_result = self.production_engine.calculate_monthly_production(
            panel_power_kwp=panel_power_kwp,
            panel_area_m2=(panel_data["width_m"] * panel_data["height_m"]) * panels_count,
            panel_efficiency=panel_data["efficiency"],
            province=location,
            monthly_irradiance=monthly_irradiance,
            panel_config=panel_data,
            azimuth_deg=self.context["roof_azimuth"],
            tilt_deg=self.context["roof_tilt"],
        )

        # Roczna produkcja z korektą zacienienia
        annual_production_kwh = yield_result["annual_kwh"] * (1.0 - shading_loss)

        # ── Realny godzinowy profil produkcji (FIX v4.0) ─────────────────────
        # Rozszerzamy miesięczne kWh do 8760h zamiast syntetycznego sinusa.
        # WAŻNE: OBYDWA silniki godzinowe (z baterią i bez) muszą dostać
        # IDENTYCZNY profil — inaczej symulacje są nieporównywalne.
        real_production_profile: Optional[List[float]] = None
        if yield_result.get("monthly_kwh") and annual_production_kwh > 0:
            real_production_profile = _expand_monthly_to_hourly_production(
                monthly_kwh_dict=yield_result["monthly_kwh"],
                annual_total_kwh=annual_production_kwh,
            )

        # =====================================================================
        # KROK 4: Parametry taryfowe
        # =====================================================================
        from app.data.energy_rates import ENERGY_RATES, decompose_electricity_tariff

        tariff_type = self.context.get("tariff_type", "G11").lower().replace("-", "")
        rates       = (
            ENERGY_RATES.get(operator, ENERGY_RATES["pge"])
            .get(tariff_type, ENERGY_RATES["pge"]["g11"])
        )

        other_fees = (
            rates.get("quality_fee_kwh", 0)
            + rates.get("oze_fee_kwh", 0)
            + rates.get("cogeneration_fee_kwh", 0)
        )

        components = decompose_electricity_tariff(operator, tariff_type)
        avg_tariff  = components["total_variable_pln_per_kwh"]

        if "energy_price_kwh" in rates:
            tariff_zones = get_tariff_zones_g11(avg_tariff)
        else:
            v_peak = (
                rates["energy_price_kwh_peak"]
                + rates["distribution_variable_kwh_peak"]
                + other_fees
            )
            v_off = (
                rates["energy_price_kwh_offpeak"]
                + rates["distribution_variable_kwh_offpeak"]
                + other_fees
            )
            tariff_zones = get_tariff_zones_g12(v_peak, v_off)

        # =====================================================================
        # KROK 4b: Symulacja godzinowa — BEZ BATERII
        # =====================================================================
        from app.data.energy_prices_tge import get_rcem_hourly

        rcem_hourly = get_rcem_hourly(year=2025)

        buckets = decompose_consumption(annual_consumption_kwh, self.context["request"])

        hourly_engine_no_batt = HourlyEngine(
            annual_production_kwh=annual_production_kwh,
            annual_consumption_kwh=annual_consumption_kwh,
            electricity_tariff_pln_per_kwh=avg_tariff,
            rcem_hourly=rcem_hourly,
            tariff_type=tariff_type,
            tariff_zones=tariff_zones,
            heating_kwh=buckets["heating_kwh"],
            cooling_kwh=buckets["cooling_kwh"],
            battery_config={
                "operator":            operator,
                "household_size":      self.context.get("household_size", 3),
                "people_home_weekday": self.context.get("people_home_weekday", 1),
            },
        )

        # Przekazujemy realny profil (None → engine generuje swój syntetyczny profil)
        hourly_result_no_batt = hourly_engine_no_batt.run_hourly_simulation(
            production_profile=real_production_profile,
        )

        # Źródło prawdy dla oszczędności PV-only
        pv_savings_pln         = hourly_result_no_batt["annual_cashflow"]["net"]
        autoconsumption_rate   = hourly_result_no_batt["rates"]["autoconsumption_rate"]
        self_sufficiency_rate  = hourly_result_no_batt["rates"]["self_sufficiency_rate"]
        effective_surplus_rate = hourly_result_no_batt["net_billing"]["effective_rate_pln_per_kwh"]
        net_billing_annual_deposit = hourly_result_no_batt["net_billing"]["annual_deposit_pln"]

        # =====================================================================
        # KROK 5: CAPEX + ROI dla PV-only
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
        # KROK 6: Rekomendacja baterii
        # =====================================================================
        surplus_kwh = hourly_result_no_batt["energy_flow"]["surplus_kwh"]

        battery_recommendation = self.battery_engine.recommend_battery(
            annual_production_kwh=annual_production_kwh,
            annual_consumption_kwh=annual_consumption_kwh,
            annual_surplus_kwh=surplus_kwh,
            autoconsumption_rate=autoconsumption_rate,
        )

        battery_recommended = battery_recommendation is not None

        if battery_recommended:
            battery_capacity_kwh      = battery_recommendation["capacity_kwh"]
            battery_power_kw          = battery_recommendation["power_kw"]
            battery_model             = battery_recommendation["model"]
            is_economically_justified = battery_recommendation.get(
                "is_economically_justified", False
            )
        else:
            battery_capacity_kwh = 0.0
            battery_power_kw     = 0.0
            battery_model        = ""

        # =====================================================================
        # KROK 7: Symulacja godzinowa — Z BATERIĄ (jeśli rekomendowana)
        # =====================================================================
        if battery_recommended and battery_capacity_kwh > 0:
            battery_cfg = {
                "capacity_kwh":        battery_capacity_kwh,
                "power_kw":            battery_power_kw,
                "efficiency":          0.95,
                "operator":            operator,
                "household_size":      self.context.get("household_size", 3),
                "people_home_weekday": self.context.get("people_home_weekday", 1),
            }

            hourly_engine_with_batt = HourlyEngine(
                annual_production_kwh=annual_production_kwh,
                annual_consumption_kwh=annual_consumption_kwh,
                electricity_tariff_pln_per_kwh=avg_tariff,
                rcem_hourly=rcem_hourly,
                tariff_type=tariff_type,
                tariff_zones=tariff_zones,
                # KRYTYCZNE: identyczne buckets jak dla no_batt!
                heating_kwh=buckets["heating_kwh"],
                cooling_kwh=buckets["cooling_kwh"],
                battery_config=battery_cfg,
            )

            # KRYTYCZNE: identyczny profil produkcji jak dla no_batt!
            hourly_result_with_batt = hourly_engine_with_batt.run_hourly_simulation(
                production_profile=real_production_profile,
            )

            total_savings_with_battery_pln     = hourly_result_with_batt["annual_cashflow"]["net"]
            battery_savings_pln                = total_savings_with_battery_pln - pv_savings_pln
            autoconsumption_rate_with_battery  = hourly_result_with_batt["rates"]["autoconsumption_rate"]
            self_sufficiency_rate_with_battery = hourly_result_with_batt["rates"]["self_sufficiency_rate"]

            capex_battery = self.financial_engine.compute_capex(
                panels_count=panels_count,
                panel_model=panel_model,
                inverter_model=layout_result["inverter_model"],
                battery_capacity_kwh=battery_capacity_kwh,
            )

            battery_cost_gross_pln      = capex_battery["battery_cost_gross_pln"]
            total_cost_with_battery_pln = capex_battery["total_cost_gross_pln"]

            roi_battery = self.financial_engine.compute_roi(
                investment_gross_pln=total_cost_with_battery_pln,
                base_annual_savings_pln=total_savings_with_battery_pln,
                inverter_cost_pln=capex_pv.get("inverter_cost_pln", 0),
            )

            battery_payback_years       = roi_battery["payback_years"]
            battery_payback_optimistic  = roi_battery["payback_optimistic_years"]
            battery_payback_pessimistic = roi_battery["payback_pessimistic_years"]
            battery_total_savings_25y   = roi_battery["total_savings_25y_pln"]

        # =====================================================================
        # KROK 8: Zwróć wynik
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

    # ─────────────────────────────────────────────────────────────────────────
    def _generate_empty_scenario_result(
        self, tier: str, consumption: float
    ) -> ScenarioResult:
        """Generuje bezpieczny, wyzerowany wynik gdy instalacja nie jest możliwa."""
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
            is_economically_justified=False,
        )