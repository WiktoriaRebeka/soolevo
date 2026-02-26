# backend/app/core/financial_engine.py
"""
FinancialEngine - ŹRÓDŁO PRAWDY dla CAPEX i ROI.

POPRAWKI po audycie inżyniera:
✅ Dodano wymianę falownika w roku 13 (koszt ~60% ceny początkowej)
✅ Dodano opcjonalne dyskontowanie NPV (stopa 5%)
✅ Dodano koszty serwisowe (OPEX)
"""

from typing import Dict, Any, Optional
from app.data.equipment import EQUIPMENT_COSTS


class FinancialEngine:
    """
    Odpowiada WYŁĄCZNIE za finanse inwestycji:
    1. CAPEX (koszt paneli, falownika, montażu, baterii)
    2. ROI (zwrot inwestycji na podstawie savings z HourlyEngine)
    
    POPRAWKA: Uwzględnia wymianę falownika + koszty serwisowe.
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        self.scenario_config = scenario_config
        self.quality_tier = scenario_config.get("quality_tier", "standard")
        self.markup_percentage = scenario_config.get("markup_percentage", 30)

    def compute_capex(
        self,
        panels_count: int,
        panel_model: str,
        inverter_model: str,
        battery_capacity_kwh: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Oblicza CAPEX (koszt brutto) dla instalacji PV + opcjonalnie bateria.
        
        POPRAWKA v3.1 (Problem #7): Marża liczona od NETTO, nie BRUTTO.
        """
        panels_data = EQUIPMENT_COSTS["panels"].get(panel_model, {})
        panel_unit_price_brutto = panels_data.get("unit_price_pln", 0)
        
        # Problem #7: Marża powinna być liczona od NETTO
        panel_unit_price_netto = panel_unit_price_brutto / 1.23  # Usuń VAT
        panel_unit_price_with_markup_netto = panel_unit_price_netto * (1 + self.markup_percentage / 100)
        panel_unit_price_final = panel_unit_price_with_markup_netto * 1.23  # Dodaj VAT
        
        panels_cost = panels_count * panel_unit_price_final

        inverter_data = EQUIPMENT_COSTS["inverters"].get(inverter_model, {})
        inverter_cost_brutto = inverter_data.get("price_pln", 0)
        
        # Podobnie dla falownika
        inverter_cost_netto = inverter_cost_brutto / 1.23
        inverter_cost_with_markup_netto = inverter_cost_netto * (1 + self.markup_percentage / 100)
        inverter_cost = inverter_cost_with_markup_netto * 1.23

        installation_cost = self._compute_installation_cost(panels_count)

        pv_cost_gross_pln = panels_cost + inverter_cost + installation_cost

        battery_cost_gross_pln = 0.0
        if battery_capacity_kwh and battery_capacity_kwh > 0:
            battery_cost_gross_pln = self._compute_battery_cost(battery_capacity_kwh)

        total_cost_gross_pln = pv_cost_gross_pln + battery_cost_gross_pln

        return {
            "pv_cost_gross_pln": pv_cost_gross_pln,
            "battery_cost_gross_pln": battery_cost_gross_pln,
            "total_cost_gross_pln": total_cost_gross_pln,
            "inverter_cost_pln": inverter_cost,
        }

    def _compute_installation_cost(self, panels_count: int) -> float:
        """Oblicza koszt montażu (struktury, kable, praca)."""
        base_costs = {"premium": 6000, "standard": 5000, "economy": 4000}
        rate_per_panel = {"premium": 350, "standard": 300, "economy": 250}
        base = base_costs.get(self.quality_tier, 5000)
        rate = rate_per_panel.get(self.quality_tier, 300)
        return base + (panels_count * rate)

    def _compute_battery_cost(self, capacity_kwh: float) -> float:
        """Oblicza koszt baterii na podstawie pojemności."""
        cost_per_kwh = {"premium": 3800, "standard": 3500, "economy": 3200}
        rate = cost_per_kwh.get(self.quality_tier, 3500)
        return capacity_kwh * rate

    def compute_roi(
        self,
        investment_gross_pln: float,
        base_annual_savings_pln: float,
        inverter_cost_pln: float = 0,
        panel_degradation_rate: float = 0.005,
        energy_inflation_rate: float = 0.04,
        cost_inflation_rate: float = 0.03,
        analysis_horizon_years: int = 25,
        include_npv: bool = False,
        discount_rate: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Oblicza ROI (zwrot inwestycji) na podstawie savings z HourlyEngine.
        
        POPRAWKA: Uwzględnia wymianę falownika + koszty serwisowe + opcjonalnie NPV.
        
        Args:
            investment_gross_pln: Koszt inwestycji początkowej
            base_annual_savings_pln: Roczne oszczędności z symulacji (rok 1)
            inverter_cost_pln: Koszt falownika (dla wymiany w roku 13)
            panel_degradation_rate: Degradacja paneli (0.5%/rok)
            energy_inflation_rate: Inflacja cen energii (4%/rok)
            cost_inflation_rate: Inflacja kosztów OPEX (3%/rok)
            analysis_horizon_years: Horyzont analizy (25 lat)
            include_npv: Czy uwzględnić dyskontowanie NPV
            discount_rate: Stopa dyskontowa (5%/rok)
        """
        payback_baseline = self._compute_payback(
            investment=investment_gross_pln,
            annual_savings_y1=base_annual_savings_pln,
            inverter_cost=inverter_cost_pln,
            degradation=panel_degradation_rate,
            energy_inflation=energy_inflation_rate,
            cost_inflation=cost_inflation_rate,
            horizon=analysis_horizon_years,
            discount_rate=discount_rate if include_npv else 0.0,
        )

        payback_optimistic = self._compute_payback(
            investment=investment_gross_pln,
            annual_savings_y1=base_annual_savings_pln,
            inverter_cost=inverter_cost_pln,
            degradation=0.004,
            energy_inflation=0.06,
            cost_inflation=0.02,
            horizon=analysis_horizon_years,
            discount_rate=discount_rate if include_npv else 0.0,
        )

        payback_pessimistic = self._compute_payback(
            investment=investment_gross_pln,
            annual_savings_y1=base_annual_savings_pln,
            inverter_cost=inverter_cost_pln,
            degradation=0.007,
            energy_inflation=0.02,
            cost_inflation=0.04,
            horizon=analysis_horizon_years,
            discount_rate=discount_rate if include_npv else 0.0,
        )

        total_savings_25y = self._compute_total_savings_npv(
            annual_savings_y1=base_annual_savings_pln,
            inverter_cost=inverter_cost_pln,
            degradation=panel_degradation_rate,
            energy_inflation=energy_inflation_rate,
            cost_inflation=cost_inflation_rate,
            horizon=analysis_horizon_years,
            discount_rate=discount_rate if include_npv else 0.0,
        )

        return {
            "payback_years": round(payback_baseline["years"], 1),
            "payback_optimistic_years": round(payback_optimistic["years"], 1),
            "payback_pessimistic_years": round(payback_pessimistic["years"], 1),
            "total_savings_25y_pln": round(total_savings_25y, 0),
            "includes_npv": include_npv,
        }

    def _compute_payback(
        self,
        investment: float,
        annual_savings_y1: float,
        inverter_cost: float,
        degradation: float,
        energy_inflation: float,
        cost_inflation: float,
        horizon: int,
        discount_rate: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Oblicza payback z uwzględnieniem:
        - Wymiany falownika w roku 13 (60% ceny początkowej)
        - Kosztów serwisowych OPEX (0.5% CAPEX rocznie)
        - Opcjonalnie dyskontowania NPV
        """
        cumulative = 0.0
        
        # Roczne koszty OPEX (serwis, ubezpieczenie) = 0.5% CAPEX
        base_opex_annual = investment * 0.005
        
        for year in range(1, horizon + 1):
            # Degradacja produkcji
            degradation_factor = (1 - degradation) ** (year - 1)
            
            # Inflacja cen energii
            inflation_factor = (1 + energy_inflation) ** (year - 1)
            
            # Przychody roczne (savings)
            annual_savings = annual_savings_y1 * degradation_factor * inflation_factor
            
            # Koszty OPEX (rosnące z inflacją kosztów)
            opex_factor = (1 + cost_inflation) ** (year - 1)
            annual_opex = base_opex_annual * opex_factor
            
            # ✅ POPRAWKA: Wymiana falownika w roku 13
            inverter_replacement_cost = 0.0
            if year == 13 and inverter_cost > 0:
                inverter_replacement_cost = inverter_cost * 0.60  # 60% ceny początkowej
            
            # Przepływ netto w roku
            annual_cashflow = annual_savings - annual_opex - inverter_replacement_cost
            
            # Dyskontowanie (jeśli NPV włączone)
            if discount_rate > 0:
                discount_factor = (1 + discount_rate) ** (year - 1)
                annual_cashflow = annual_cashflow / discount_factor
            
            cumulative += annual_cashflow
            
            # Zwrot inwestycji osiągnięty
            if cumulative >= investment:
                previous_cumulative = cumulative - annual_cashflow
                fraction = (investment - previous_cumulative) / annual_cashflow if annual_cashflow > 0 else 0
                payback_years = (year - 1) + fraction
                
                return {"years": payback_years, "cumulative_cashflow": cumulative}
        
        return {"years": horizon, "cumulative_cashflow": cumulative}

    def _compute_total_savings_npv(
        self,
        annual_savings_y1: float,
        inverter_cost: float,
        degradation: float,
        energy_inflation: float,
        cost_inflation: float,
        horizon: int,
        discount_rate: float = 0.0,
    ) -> float:
        """Oblicza sumę oszczędności przez cały horyzont (z opcjonalnym NPV)."""
        total = 0.0
        base_opex_annual = annual_savings_y1 * 0.005
        
        for year in range(1, horizon + 1):
            degradation_factor = (1 - degradation) ** (year - 1)
            inflation_factor = (1 + energy_inflation) ** (year - 1)
            annual_savings = annual_savings_y1 * degradation_factor * inflation_factor
            
            opex_factor = (1 + cost_inflation) ** (year - 1)
            annual_opex = base_opex_annual * opex_factor
            
            inverter_replacement_cost = 0.0
            if year == 13 and inverter_cost > 0:
                inverter_replacement_cost = inverter_cost * 0.60
            
            annual_cashflow = annual_savings - annual_opex - inverter_replacement_cost
            
            if discount_rate > 0:
                discount_factor = (1 + discount_rate) ** (year - 1)
                annual_cashflow = annual_cashflow / discount_factor
            
            total += annual_cashflow
            
        return total

    def compute_inverter(self, total_power_kwp: float) -> Dict[str, Any]:
        """Dobiera falownik na podstawie mocy systemu."""
        from app.data.equipment import get_inverter_by_power
        
        quality_tier = self.scenario_config.get("quality_tier", "standard")
        
        inverter_model, inverter_data = get_inverter_by_power(
            power_kwp=total_power_kwp,
            tier=quality_tier,
        )
        
        return {
            "inverter_model": inverter_model,
            "inverter_power_kw": inverter_data["power_kw"],
            "inverter_efficiency": inverter_data["efficiency"],
            "inverter_cost_pln": inverter_data.get("price_pln", 0),
        }
