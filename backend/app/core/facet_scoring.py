import math
from app.core.shading import calculate_shading_loss
from app.core.production_engine import ProductionEngine
from app.core.facet_geometry import compute_facet_area_and_length

def score_facets(facets, panel_width_m, panel_height_m, compute_max_panels_for_facet):
    """
    Zwraca listę scored_facets:
    [
        {
            "facet_obj": f,
            "efficiency": <float>,
            "max_panels": <int>,
            "row_distribution": [...],
            "warnings": [...],
            "grid": [...],
        }
    ]
    """

    production_engine = ProductionEngine()
    scored = []

    for f in facets:
        # 1. Efektywność połaci (azymut + kąt)
        eff = production_engine.calculate_system_efficiency(f.azimuth_deg, f.angle)

        # 2. Straty zacienienia
        shading = calculate_shading_loss(f.has_shading, f.shading_direction, "south")

        # 3. Maksymalna liczba paneli
        max_panels_result = compute_max_panels_for_facet(
            facet=f,
            panel_width_m=panel_width_m,
            panel_height_m=panel_height_m,
        )

        # 4. Placeholder grid (do wizualizacji)
        grid = max_panels_result["grid"]

        scored.append(
            {
                "facet_obj": f,
                "efficiency": eff * (1 - shading),
                "max_panels": max_panels_result["placed_count"],
                "row_distribution": max_panels_result["row_distribution"],
                "warnings": max_panels_result["warnings"],
                "grid": grid,
            }
        )

    # sortowanie od najlepszej połaci
    scored.sort(key=lambda x: x["efficiency"], reverse=True)
    return scored
