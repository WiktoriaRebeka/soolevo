import math
from typing import Dict, List

from app.data.climate import get_temperature
from app.data.sunlight import get_monthly_sunlight, DAYS_IN_MONTH
from app.data.physics_constants import SYSTEM_LOSS_FACTOR_BASE
from app.core.physics import calculate_monthly_irradiance_w_m2
from app.core.physics import calculate_temperature_derating
from app.schemas.scenarios import PanelPosition, FacetLayout


MONTHS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]


class ProductionEngine:

    # ---------------------------------------------------------
    # TEMPERATURA OGNIWA (NOCT model)
    # ---------------------------------------------------------
    def calculate_cell_temperature(
        self,
        ambient_temp_c: float,
        irradiance_w_m2: float,
        noct_celsius: float = 45.0,
    ) -> float:
        """Oblicza temperaturę ogniwa PV na podstawie temperatury otoczenia,
        nasłonecznienia i NOCT."""
        if irradiance_w_m2 <= 0:
            return ambient_temp_c

        delta_t_noct = noct_celsius - 20.0
        temperature_rise = (delta_t_noct / 800.0) * irradiance_w_m2

        return ambient_temp_c + temperature_rise

    # ---------------------------------------------------------
    # IAM – Incidence Angle Modifier (miesięczny)
    # ---------------------------------------------------------
    def calculate_monthly_iam(self, azimuth_deg: float, tilt_deg: float) -> dict:
        """Upraszczony model IAM zależny od odchylenia od południa i kąta nachylenia."""
        iam_factors = {}
        base_iam = 0.97  # IAM przy optymalnym kącie

        azimuth_penalty = abs(180 - azimuth_deg) / 180
        tilt_penalty = abs(30 - tilt_deg) / 60

        monthly_factor = max(0.80, base_iam - 0.10 * azimuth_penalty - 0.10 * tilt_penalty)

        for m in MONTHS:
            iam_factors[m] = round(monthly_factor, 4)

        return iam_factors

    # ---------------------------------------------------------
    # 1. MIESIĘCZNA PRODUKCJA (temperatura + IAM + straty)
    # ---------------------------------------------------------
    def calculate_monthly_production(
        self,
        panel_power_kwp: float,
        panel_area_m2: float,
        panel_efficiency: float,
        province: str,
        monthly_irradiance: Dict[str, float],
        panel_config: dict,
        azimuth_deg: float = 180.0,
        tilt_deg: float = 30.0,
    ) -> dict:

        noct_celsius = panel_config.get("noct_celsius", 45.0)
        gamma_pmax = panel_config.get("gamma_pmax_percent", -0.35)

        iam_factor = self.calculate_monthly_iam(azimuth_deg, tilt_deg)

        monthly_production: Dict[str, float] = {}
        monthly_temp_derating: Dict[str, float] = {}
        monthly_cell_temp_c: Dict[str, float] = {}

        for m in MONTHS:
            irr_kwh_m2 = monthly_irradiance.get(m, 0.0)
            days = DAYS_IN_MONTH[m]
            t_amb = get_temperature(province, m)

            avg_irr_w_m2 = calculate_monthly_irradiance_w_m2(irr_kwh_m2, days)

            t_cell = self.calculate_cell_temperature(t_amb, avg_irr_w_m2, noct_celsius)
            monthly_cell_temp_c[m] = round(t_cell, 1)

            temp_derating = calculate_temperature_derating(t_cell, gamma_pmax)
            monthly_temp_derating[m] = round(temp_derating, 4)

            iam_monthly = iam_factor.get(m, 1.0)

            production_kwh = (
                irr_kwh_m2
                * panel_area_m2
                * panel_efficiency
                * temp_derating
                * iam_monthly
                * SYSTEM_LOSS_FACTOR_BASE
            )

            monthly_production[m] = round(production_kwh, 2)

        annual_kwh = sum(monthly_production.values())

        return {
            "monthly_kwh": monthly_production,
            "annual_kwh": round(annual_kwh, 2),
            "monthly_temp_derating": monthly_temp_derating,
            "monthly_cell_temp": monthly_cell_temp_c,
        }

    # ---------------------------------------------------------
    # 2. ROZDZIELANIE PANELI + SUMARYCZNA PRODUKCJA
    # ---------------------------------------------------------
    def distribute_panels_and_calculate_yield(
        self,
        panels_to_place: int,
        power_kwp: float,
        scored_facets: List[dict],
        province: str,
        config: dict,
    ) -> dict:

        placed_total = 0
        total_prod = 0.0
        facet_layouts: List[FacetLayout] = []
        monthly_total: Dict[str, float] = {m: 0.0 for m in MONTHS}

        monthly_irradiance = get_monthly_sunlight(province)
        panel_cfg = config["panel"]
        panel_area = panel_cfg["width_m"] * panel_cfg["height_m"]

        for item in scored_facets:
            if placed_total >= panels_to_place:
                break

            to_place = min(panels_to_place - placed_total, item["max_panels"])
            if to_place <= 0:
                continue

            facet_obj = item["facet_obj"]

            m_prod = self.calculate_monthly_production(
                panel_power_kwp=power_kwp,
                panel_area_m2=panel_area * to_place,
                panel_efficiency=panel_cfg["efficiency"],
                province=province,
                monthly_irradiance=monthly_irradiance,
                panel_config=panel_cfg,
                azimuth_deg=facet_obj.azimuth_deg,
                tilt_deg=getattr(facet_obj, "tilt_deg", 30.0),
            )

            for m in MONTHS:
                monthly_total[m] += m_prod["monthly_kwh"][m]

            total_prod += m_prod["annual_kwh"]

            facet_layouts.append(
                FacetLayout(
                    facet_id=facet_obj.id,
                    panels_count=to_place,
                    azimuth_deg=facet_obj.azimuth_deg,
                    efficiency_factor=item["efficiency"],
                    layout=[
                        PanelPosition(
                            x=p.x,
                            y=p.y,
                            width=p.width,
                            height=p.height,
                            label=p.label,
                        )
                        for p in item["grid"][:to_place]
                    ],
                )
            )

            placed_total += to_place

        return {
            "placed_total": placed_total,
            "total_production_kwh": total_prod,
            "facet_layouts": facet_layouts,
            "monthly_total": monthly_total,
        }

    # ---------------------------------------------------------
    # 3. SZACOWANIE LICZBY PANELI
    # ---------------------------------------------------------
    def estimate_required_panels(
        self,
        future_demand: float,
        target_ratio: float,
        power_kwp: float,
        best_facet: dict,
        province: str,
        config: dict,
    ) -> int:

        monthly_irradiance = get_monthly_sunlight(province)
        panel_cfg = config["panel"]
        panel_area = panel_cfg["width_m"] * panel_cfg["height_m"]

        sample = self.calculate_monthly_production(
            panel_power_kwp=power_kwp,
            panel_area_m2=panel_area,
            panel_efficiency=panel_cfg["efficiency"],
            province=province,
            monthly_irradiance=monthly_irradiance,
            panel_config=panel_cfg,
            azimuth_deg=best_facet["facet_obj"].azimuth_deg,
            tilt_deg=getattr(best_facet["facet_obj"], "tilt_deg", 30.0),
        )

        if sample["annual_kwh"] <= 0:
            return 10

        return math.ceil((future_demand * target_ratio) / sample["annual_kwh"])

    # ---------------------------------------------------------
    # 4. SPRAWNOŚĆ SYSTEMU (azymut + kąt)
    # ---------------------------------------------------------
    def calculate_system_efficiency(self, azimuth_deg: float, angle: float) -> float:

        rad = math.radians(azimuth_deg)
        direction_factor = 0.8 + 0.2 * math.cos(rad - math.pi)

        if 160 <= azimuth_deg <= 200:
            direction_factor = 1.0
        elif 70 <= azimuth_deg <= 110 or 250 <= azimuth_deg <= 290:
            direction_factor = 0.90

        if angle is None or angle == 0:
            angle_factor = 0.95
        elif 25 <= angle <= 40:
            angle_factor = 1.00
        elif 10 <= angle < 25 or 40 < angle <= 55:
            angle_factor = 0.95
        else:
            angle_factor = 0.85

        return round(direction_factor * angle_factor, 4)