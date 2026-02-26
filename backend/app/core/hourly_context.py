# backend/app/core/hourly_context.py

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd


@dataclass
class HourlyContext:
    """
    Kontekst godzinowy dla symulacji net-billing + bateria.
    """
    hourly_prices: pd.DataFrame
    hourly_production: pd.Series
    hourly_consumption: pd.Series
    hourly_tariff: pd.Series
    battery_config: Dict[str, Any] = None