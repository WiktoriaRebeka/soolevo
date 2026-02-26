# app/core/layout_engine.py

from typing import Dict, Any
import math

from app.core.facet_geometry import compute_facet_area_and_length
from app.core.max_panels_engine import compute_max_panels_for_facet
from app.core.geometry import generate_layout_for_facet


class LayoutEngine:
    """
    Odpowiada za całą logikę układania paneli:
    - obliczenie maksymalnej liczby paneli na połaci
    - generowanie layoutu paneli
    - obliczanie offsetów dla dachów rombowych
    - obliczanie slope height
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        self.scenario_config = scenario_config

    def compute_max_panels(self, facet, panel_width_m: float, panel_height_m: float):
        """
        Zwraca wynik compute_max_panels_for_facet na podstawie przekazanych wymiarów.
        """
        return compute_max_panels_for_facet(
            facet=facet,
            panel_width_m=panel_width_m,
            panel_height_m=panel_height_m,
        )

    def generate_layout(self, facet, count: int, panel_width_m: float, panel_height_m: float):
        """
        Generuje layout paneli na połaci na podstawie przekazanych wymiarów.
        """
        return generate_layout_for_facet(
            facet=facet,
            panel_width=panel_width_m,
            panel_height=panel_height_m,
            count=count,
        )

    def compute_offset(self, facet):
        """
        Oblicza offset X dla dachów rombowych na podstawie canonical geometry.
        """
        geom = compute_facet_area_and_length(facet)

        if facet.roof_type == "rhombus":
            return geom.get("offset_x") or 0.0

        return 0.0

    def compute_slope_height(self, facet):
        """
        Zwraca slope height połaci z canonical geometry.
        """
        geom = compute_facet_area_and_length(facet)
        return geom.get("slope_length") or 0.0