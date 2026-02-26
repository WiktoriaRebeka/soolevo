# backend/app/core/warnings_engine.py
from typing import List, Dict, Any
from app.schemas.report import Warning # Używamy nowego modelu Warning
from app.schemas.scenarios import ScenarioResponseItem # Używamy tego jako wzorca wyniku

class WarningEngine:
    """
    Silnik generujący ustrukturyzowane ostrzeżenia i potwierdzenia
    na podstawie wyników kalkulacji.
    """
    
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        # W kontekście z /api/report/data mamy dostęp do requesta
        self.request = context.get("request") 

    def generate_warnings(self, scenario_result: ScenarioResponseItem, context_summary: Dict[str, Any]) -> List[Warning]:
        """
        Generuje listę ostrzeżeń i potwierdzeń dla danego scenariusza.
        """
        warnings: List[Warning] = []
        
        # --- A. OSTRZEŻENIA (RED/YELLOW) ---
        
        # W1: Ostrzeżenie o niskiej liczbie paneli (np. < 8)
        if scenario_result.panels_count < 8:
            warnings.append(
                Warning(
                    type="red",
                    code="W1",
                    title="Niska liczba paneli",
                    message=f"Zainstalowano tylko {scenario_result.panels_count} paneli. Może to być nieoptymalne ze względu na koszty stałe instalacji."
                )
            )

        # W2: Ostrzeżenie o niskim pokryciu (np. < 30%)
        if scenario_result.coverage_percent is not None and scenario_result.coverage_percent < 30.0:
            warnings.append(
                Warning(
                    type="yellow",
                    code="W2",
                    title="Niskie pokrycie zapotrzebowania",
                    message=f"Instalacja pokryje tylko {scenario_result.coverage_percent:.0f}% Twojego rocznego zużycia energii."
                )
            )
            
        # W3: Ostrzeżenie o zacienieniu
        if scenario_result.shading_loss_percent and scenario_result.shading_loss_percent > 5.0:
            warnings.append(
                Warning(
                    type="red",
                    code="W3",
                    title="Znaczące zacienienie",
                    message=f"Zacienienie powoduje stratę {scenario_result.shading_loss_percent:.1f}% produkcji. Rozważ mikroinwertery."
                )
            )

        # --- B. POTWIERDZENIA (GREEN) ---
        
        # U1: Potwierdzenie opłacalności (PV-only)
        if scenario_result.pv_payback_years and scenario_result.pv_payback_years < 15:
            warnings.append(
                Warning(
                    type="green",
                    code="U1",
                    title="Dobra opłacalność PV",
                    message=f"Szacowany czas zwrotu inwestycji (PV-only) to {scenario_result.pv_payback_years:.1f} lat."
                )
            )
            
        # U2: Potwierdzenie efektywności baterii (jeśli jest)
        if scenario_result.battery_recommended and scenario_result.is_economically_justified:
            warnings.append(
                Warning(
                    type="green",
                    code="U2",
                    title="Ekonomiczne uzasadnienie magazynu",
                    message=f"Magazyn energii jest opłacalny. Zwiększy autokonsumpcję do {scenario_result.autoconsumption_rate_with_battery*100:.0f}%."
                )
            )
            
        # U3: Potwierdzenie typu taryfy
        tariff_name = self.request.tariff.upper() if self.request else "G11"
        if tariff_name in ["G12", "G12W"]:
             warnings.append(
                Warning(
                    type="green",
                    code="U3",
                    title="Taryfa dwustrefowa",
                    message=f"Analiza przeprowadzona w taryfie {tariff_name}. Oszczędności z magazynem mogą być wyższe."
                )
            )

        return warnings