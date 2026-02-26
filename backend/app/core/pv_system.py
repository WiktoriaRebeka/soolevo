# backend/app/core/pv_system.py
import math
from typing import Dict, List

from app.schemas.scenarios import PanelPosition, FacetLayout, ScenariosRequest
from app.data.climate import get_temperature
from app.data.sunlight import get_monthly_sunlight, DAYS_IN_MONTH
from app.data.physics_constants import SYSTEM_LOSS_FACTOR_BASE
from app.core.production_engine import ProductionEngine

MONTHS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]


def _azimuth_to_direction(azimuth_deg: float) -> str:
    """
    Pomocnicza funkcja mapująca azymut na kierunek świata.
    Używana przy ewentualnych modyfikatorach zależnych od kierunku.
    """
    az = azimuth_deg % 360
    if az >= 340 or az < 20:
        return "N"
    elif 20 <= az < 70:
        return "NE"
    elif 70 <= az < 110:
        return "E"
    elif 110 <= az < 160:
        return "SE"
    elif 160 <= az < 200:
        return "S"
    elif 200 <= az < 250:
        return "SW"
    elif 250 <= az < 290:
        return "W"
    else:
        return "NW"


