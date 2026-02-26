# backend/app/core/battery_engine.py
"""
BatteryEngine - ŹRÓDŁO PRAWDY dla rekomendacji baterii.

Po refactoringu:
- TYLKO rekomenduje konfigurację baterii (pojemność, moc)
- NIE LICZY SAVINGS (to robi HourlyEngine poprzez porównanie symulacji)
- NIE LICZY ROI (to robi FinancialEngine)
- Usunięto wszystkie magiczne współczynniki związane z finansami
"""

from typing import Dict, Any, Optional


class BatteryEngine:
    """
    Odpowiada WYŁĄCZNIE za rekomendację konfiguracji magazynu energii:
    1. Decyduje czy bateria jest potrzebna
    2. Określa optymalną pojemność (kWh)
    3. Określa optymalną moc ładowania/rozładowania (kW)
    
    NIE LICZY SAVINGS ani ROI - to jest zadanie HourlyEngine i FinancialEngine.
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        """
        Args:
            scenario_config: Konfiguracja scenariusza (premium/standard/economy)
        """
        self.scenario_config = scenario_config
        self.quality_tier = scenario_config.get("quality_tier", "standard")

    def recommend_battery(
        self,
        annual_production_kwh: float,
        annual_consumption_kwh: float,
        annual_surplus_kwh: float,
        autoconsumption_rate: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Decyduje czy bateria jest potrzebna i rekomenduje jej parametry.
        
        Kryteria decyzji:
        1. Nadwyżka > 20% produkcji rocznej
        2. Autoconsumption < 40%
        3. Minimalna produkcja: 3000 kWh/rok
        
        Args:
            annual_production_kwh: Roczna produkcja PV (kWh)
            annual_consumption_kwh: Roczne zapotrzebowanie (kWh)
            annual_surplus_kwh: Roczna nadwyżka (kWh)
            autoconsumption_rate: Współczynnik autokonsumpcji (0-1)
            
        Returns:
            None (jeśli bateria nieopłacalna)
            Dict (jeśli bateria rekomendowana):
            {
                "recommended": bool,
                "capacity_kwh": float,
                "power_kw": float,
                "model": str,
                "rationale": str,
            }
        """
        # Kryterium 1: Minimalna produkcja
        if annual_production_kwh < 3000:
            return None

        # Kryterium 2: Nadwyżka musi być znacząca
        surplus_ratio = annual_surplus_kwh / annual_production_kwh if annual_production_kwh > 0 else 0
        if surplus_ratio < 0.20:
            return None


        # ✅ Bateria rekomendowana - oblicz parametry
        # ZAWSZE obliczamy parametry, nawet jeśli autokonsumpcja jest wysoka
        capacity_kwh = self._compute_optimal_capacity(annual_surplus_kwh, annual_consumption_kwh)
        power_kw = self._compute_optimal_power(capacity_kwh, self.quality_tier)
        model = self._select_battery_model(capacity_kwh, self.quality_tier)

        # Decyzja o rekomendacji (flaga logiczna)
        is_economically_justified = autoconsumption_rate <= 0.45
        
        rationale = (
            f"Rekomendujemy magazyn {model} ({capacity_kwh} kWh). "
            "Pozwoli on przechować nadwyżki z dnia na wieczór."
        ) if is_economically_justified else (
            "Magazyn energii jest w Twoim przypadku opcjonalny. Ze względu na wysoką "
            "autokonsumpcję bezpośrednią w dzień, czas zwrotu będzie dłuższy, ale "
            "zyskasz niezależność energetyczną w nocy."
        )

        return {
            "recommended": True, # Zmieniamy na True, aby ScenarioRunner zawsze liczył baterię
            "is_economically_justified": is_economically_justified,
            "capacity_kwh": capacity_kwh,
            "power_kw": power_kw,
            "model": model,
            "rationale": rationale,
        }

    def _compute_optimal_capacity(
        self,
        annual_surplus_kwh: float,
        annual_consumption_kwh: float,
    ) -> float:
        """
        Oblicza optymalną pojemność baterii.
        
        Logika:
        - Bazowa pojemność: 30% nadwyżki rocznej / 300 dni
        - Min: 5 kWh
        - Max: 20 kWh (dla residentialnych instalacji)
        
        Args:
            annual_surplus_kwh: Roczna nadwyżka (kWh)
            annual_consumption_kwh: Roczne zapotrzebowanie (kWh)
            
        Returns:
            Pojemność baterii (kWh)
        """
        # Średnia dzienna nadwyżka
        daily_surplus_avg = annual_surplus_kwh / 365

        # Bateria powinna pokrywać ~50% dziennej nadwyżki
        # (reszta idzie do net-billing)
        base_capacity = daily_surplus_avg * 0.5

        # Zaokrąglij do pełnych kWh
        capacity = round(base_capacity, 0)

        # Limity
        capacity = max(5.0, min(capacity, 20.0))

        return capacity

    def _compute_optimal_power(
        self,
        capacity_kwh: float,
        quality_tier: str,
    ) -> float:
        """
        Oblicza optymalną moc ładowania/rozładowania.
        
        Logika:
        - Premium: 1.0 C-rate (np. 10 kWh -> 10 kW)
        - Standard: 0.7 C-rate (np. 10 kWh -> 7 kW)
        - Economy: 0.5 C-rate (np. 10 kWh -> 5 kW)
        
        Args:
            capacity_kwh: Pojemność baterii (kWh)
            quality_tier: Tier jakościowy (premium/standard/economy)
            
        Returns:
            Moc (kW)
        """
        c_rate_map = {
            "premium": 1.0,
            "standard": 0.7,
            "economy": 0.5,
        }

        c_rate = c_rate_map.get(quality_tier, 0.7)
        power_kw = capacity_kwh * c_rate

        # Zaokrąglij do 0.5 kW
        power_kw = round(power_kw * 2) / 2

        return power_kw

    def _select_battery_model(
        self,
        capacity_kwh: float,
        quality_tier: str,
    ) -> str:
        """
        Wybiera model baterii na podstawie pojemności i tier'u.
        """
        if quality_tier == "premium":
            if capacity_kwh <= 6:
                return "Huawei LUNA2000 5kWh"
            elif capacity_kwh <= 11:
                return "BYD Battery-Box HVS 10.2"
            else:
                return "Tesla Powerwall 2 (13.5 kWh)"
        
        elif quality_tier == "standard":
            if capacity_kwh <= 6:
                return "Pylontech US3000C (3.5 kWh)"
            else:
                return "Pylontech Force H2 (10.6 kWh)"
        
        else:  # economy
            return f"Magazyn LiFePO4 {int(capacity_kwh)} kWh"

    def get_battery_specs(self, model: str) -> Dict[str, Any]:
        """
        Zwraca specyfikację techniczną baterii.
        
        Args:
            model: Nazwa modelu baterii
            
        Returns:
            Słownik z parametrami technicznymi
        """
        # Przykładowe dane (w produkcji: pobierać z app/data/equipment.py)
        specs = {
            "Tesla Powerwall 2 (13.5 kWh)": {
                "capacity_kwh": 13.5,
                "usable_capacity_kwh": 13.5,
                "power_kw": 5.0,
                "efficiency": 0.90,
                "dod": 1.0,  # Depth of Discharge
                "warranty_years": 10,
            },
            "Pylontech US5000 (4.8 kWh x2)": {
                "capacity_kwh": 9.6,
                "usable_capacity_kwh": 9.1,
                "power_kw": 4.0,
                "efficiency": 0.95,
                "dod": 0.95,
                "warranty_years": 10,
            },
            # ... dodać więcej modeli
        }

        return specs.get(model, {
            "capacity_kwh": 10.0,
            "usable_capacity_kwh": 9.5,
            "power_kw": 5.0,
            "efficiency": 0.92,
            "dod": 0.95,
            "warranty_years": 10,
        })


# =============================================================================
# HELPER FUNCTIONS (pozostawione bez zmian)
# =============================================================================

def recommend_battery(
    annual_production_kwh: float,
    annual_surplus_kwh: float,
    autoconsumption_rate: float,
    annual_consumption_kwh: float = 5000,
    quality_tier: str = "standard",
) -> Optional[Dict[str, Any]]:
    """
    Standalone helper function dla recommend_battery.
    Używany przez backward compatibility.
    """
    engine = BatteryEngine(scenario_config={"quality_tier": quality_tier})
    return engine.recommend_battery(
        annual_production_kwh=annual_production_kwh,
        annual_consumption_kwh=annual_consumption_kwh,
        annual_surplus_kwh=annual_surplus_kwh,
        autoconsumption_rate=autoconsumption_rate,
    )
