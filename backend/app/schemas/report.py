from typing import Dict, Any, List, Optional

from pydantic import BaseModel

from app.schemas.scenarios import ScenariosRequest


class Warning(BaseModel):
    """Pojedyncze ostrzeżenie / potwierdzenie używane w raporcie."""

    level: Optional[str] = None        # np. "info" / "warning" / "error"
    code: Optional[str] = None         # opcjonalny kod ostrzeżenia
    message: str                       # treść komunikatu (wymagana)
    details: Optional[str] = None      # dodatkowe szczegóły
    category: Optional[str] = None     # np. "roof", "consumption", "finance"


class ReportData(BaseModel):
    """
    Główna struktura wejściowa dla generatora PDF.
    Używana przez:
      - /calculator/report/data
      - /calculator/report/pdf
      - /report/data (w main.py)
      - /report/pdf (w main.py)
      - app/core/report_generator.py
    """

    # Oryginalny request, na podstawie którego liczono scenariusze
    input_request: ScenariosRequest

    # Nazwa scenariusza wyróżnionego w raporcie (np. "standard")
    highlighted_scenario_name: Optional[str] = None

    # Podsumowanie danych wejściowych wykorzystywane w szablonie HTML
    input_data_summary: Dict[str, Any]

    # Mapa wyników wszystkich scenariuszy:
    #   { "standard": {...}, "premium": {...}, "economy": {...} }
    # Każda wartość to dict (model_dump() ScenarioResponseItem) albo kompatybilny obiekt.
    all_scenarios_results: Dict[str, Any]

    # Lista ostrzeżeń / potwierdzeń wygenerowanych przez WarningEngine
    warnings_and_confirmations: List[Warning] = []


class ReportRequest(ScenariosRequest):
    """
    Historyczny alias — zachowany dla kompatybilności z istniejącymi importami.
    W praktyce to po prostu ScenariosRequest używany w kontekście raportu.
    """

    pass

