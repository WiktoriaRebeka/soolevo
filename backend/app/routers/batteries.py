# backend/app/routers/batteries.py
# ─────────────────────────────────────────────────────────────
#  Porównywarka magazynów energii
#  Faza 1: dane statyczne z JSON
#  Faza 2: tabela Battery w PostgreSQL (zakomentowana logika poniżej)
# ─────────────────────────────────────────────────────────────

import json
import os
from typing import List, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/batteries", tags=["batteries"])

# Ścieżka do statycznego JSON (Faza 1)
BATTERIES_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "batteries.json")


def _load_batteries():
    with open(BATTERIES_JSON, encoding="utf-8") as f:
        return json.load(f)


@router.get("")
def list_batteries(
    min_capacity: Optional[float] = Query(None, description="Min pojemność [kWh]"),
    max_capacity: Optional[float] = Query(None, description="Max pojemność [kWh]"),
    min_price: Optional[int] = Query(None, description="Min cena [PLN]"),
    max_price: Optional[int] = Query(None, description="Max cena [PLN]"),
    chemistry: Optional[str] = Query(None, description="Technologia: LFP, NMC, itp."),
    sort_by: str = Query("capacity_kwh", description="Pole sortowania"),
    sort_dir: str = Query("asc", description="asc | desc"),
    limit: int = Query(50, ge=1, le=100),
):
    """Lista magazynów energii z filtrowaniem i sortowaniem."""
    batteries = _load_batteries()

    # Filtrowanie
    if min_capacity is not None:
        batteries = [b for b in batteries if b.get("capacity_kwh", 0) >= min_capacity]
    if max_capacity is not None:
        batteries = [b for b in batteries if b.get("capacity_kwh", 0) <= max_capacity]
    if min_price is not None:
        batteries = [b for b in batteries if b.get("price_pln") and b["price_pln"] >= min_price]
    if max_price is not None:
        batteries = [b for b in batteries if b.get("price_pln") and b["price_pln"] <= max_price]
    if chemistry:
        batteries = [b for b in batteries if b.get("chemistry", "").upper() == chemistry.upper()]

    # Sortowanie
    reverse = sort_dir.lower() == "desc"
    batteries.sort(key=lambda b: b.get(sort_by, 0) or 0, reverse=reverse)

    return batteries[:limit]


@router.get("/filters")
def battery_filters():
    """Dostępne wartości filtrów (dla frontendu)."""
    batteries = _load_batteries()
    chemistries = sorted(set(b.get("chemistry", "") for b in batteries if b.get("chemistry")))
    capacities = [b.get("capacity_kwh", 0) for b in batteries if b.get("capacity_kwh")]
    prices = [b.get("price_pln", 0) for b in batteries if b.get("price_pln")]

    return {
        "chemistries": chemistries,
        "capacity_range": {"min": min(capacities), "max": max(capacities)} if capacities else {},
        "price_range": {"min": min(prices), "max": max(prices)} if prices else {},
    }
