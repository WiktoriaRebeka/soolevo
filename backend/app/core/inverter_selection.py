# backend/app/core/inverter_selection.py
"""
Moduł automatycznego doboru falownika do instalacji fotowoltaicznej.

Zgodnie z audytem:
- Parametry elektryczne w INVERTERS_DATABASE (V_max, V_mppt_min/max, I_max_input, strings_per_mppt)
- Walidacja 5 warunków bezpieczeństwa stringu (funkcje w app.core.physics)
- Automatyczne wyznaczanie optymalnej liczby paneli w stringu
"""

from typing import Dict, List, Optional
import math

from app.core.physics import verify_string_safety, calculate_optimal_string_size


INVERTERS_DATABASE = [
    # === MAŁE INSTALACJE (3-5 kW) ===
    {
        "brand": "Huawei",
        "model": "SUN2000-3KTL-L1",
        "power_kw": 3.0,
        "max_pv_power_kwp": 4.5,
        "max_pv_current_a": 25,
        "efficiency": 0.979,
        "price_pln": 2400,
        "mppt_count": 2,
        "hybrid": False,
        "warranty_years": 10,
        "max_input_voltage_v": 600,
        "mppt_voltage_min_v": 90,
        "mppt_voltage_max_v": 560,
        "max_input_current_a": 12.5,
        "strings_per_mppt": 1,
    },
    {
        "brand": "Fronius",
        "model": "Primo GEN24 4.0",
        "power_kw": 4.0,
        "max_pv_power_kwp": 6.0,
        "max_pv_current_a": 32,
        "efficiency": 0.980,
        "price_pln": 2800,
        "mppt_count": 2,
        "hybrid": True,
        "warranty_years": 10,
        "max_input_voltage_v": 600,
        "mppt_voltage_min_v": 80,
        "mppt_voltage_max_v": 530,
        "max_input_current_a": 16.0,
        "strings_per_mppt": 1,
    },
    {
        "brand": "SolaX",
        "model": "X1-BOOST-5.0-D",
        "power_kw": 5.0,
        "max_pv_power_kwp": 7.5,
        "max_pv_current_a": 28,
        "efficiency": 0.976,
        "price_pln": 2600,
        "mppt_count": 2,
        "hybrid": False,
        "warranty_years": 10,
        "max_input_voltage_v": 600,
        "mppt_voltage_min_v": 55,
        "mppt_voltage_max_v": 550,
        "max_input_current_a": 14.0,
        "strings_per_mppt": 1,
    },
    # === ŚREDNIE INSTALACJE (6-10 kW) ===
    {
        "brand": "Huawei",
        "model": "SUN2000-6KTL-L1",
        "power_kw": 6.0,
        "max_pv_power_kwp": 9.0,
        "max_pv_current_a": 30,
        "efficiency": 0.981,
        "price_pln": 3200,
        "mppt_count": 2,
        "hybrid": False,
        "warranty_years": 10,
        "max_input_voltage_v": 600,
        "mppt_voltage_min_v": 90,
        "mppt_voltage_max_v": 560,
        "max_input_current_a": 15.0,
        "strings_per_mppt": 2,
    },
    {
        "brand": "Fronius",
        "model": "Primo GEN24 8.0",
        "power_kw": 8.0,
        "max_pv_power_kwp": 12.0,
        "max_pv_current_a": 37,
        "efficiency": 0.980,
        "price_pln": 3800,
        "mppt_count": 2,
        "hybrid": True,
        "warranty_years": 10,
        "max_input_voltage_v": 600,
        "mppt_voltage_min_v": 80,
        "mppt_voltage_max_v": 530,
        "max_input_current_a": 18.0,
        "strings_per_mppt": 2,
    },
    {
        "brand": "SolarEdge",
        "model": "SE10K-RWS",
        "power_kw": 10.0,
        "max_pv_power_kwp": 15.0,
        "max_pv_current_a": 41,
        "efficiency": 0.979,
        "price_pln": 4500,
        "mppt_count": 2,
        "hybrid": True,
        "warranty_years": 12,
        "max_input_voltage_v": 600,
        "mppt_voltage_min_v": 380,
        "mppt_voltage_max_v": 480,
        "max_input_current_a": 20.5,
        "strings_per_mppt": 2,
    },
    # === DUŻE INSTALACJE (12-20 kW) ===
    {
        "brand": "Huawei",
        "model": "SUN2000-12KTL-M5",
        "power_kw": 12.0,
        "max_pv_power_kwp": 18.0,
        "max_pv_current_a": 44,
        "efficiency": 0.984,
        "price_pln": 5200,
        "mppt_count": 3,
        "hybrid": False,
        "warranty_years": 10,
        "max_input_voltage_v": 1100,
        "mppt_voltage_min_v": 160,
        "mppt_voltage_max_v": 950,
        "max_input_current_a": 22.0,
        "strings_per_mppt": 2,
    },
    {
        "brand": "Fronius",
        "model": "Symo GEN24 10.0",
        "power_kw": 10.0,
        "max_pv_power_kwp": 15.0,
        "max_pv_current_a": 40,
        "efficiency": 0.981,
        "price_pln": 4800,
        "mppt_count": 2,
        "hybrid": True,
        "warranty_years": 10,
        "max_input_voltage_v": 1000,
        "mppt_voltage_min_v": 80,
        "mppt_voltage_max_v": 800,
        "max_input_current_a": 20.0,
        "strings_per_mppt": 2,
    },
    {
        "brand": "SMA",
        "model": "Sunny Tripower 15000TL",
        "power_kw": 15.0,
        "max_pv_power_kwp": 22.5,
        "max_pv_current_a": 50,
        "efficiency": 0.983,
        "price_pln": 6500,
        "mppt_count": 3,
        "hybrid": False,
        "warranty_years": 10,
        "max_input_voltage_v": 1000,
        "mppt_voltage_min_v": 150,
        "mppt_voltage_max_v": 800,
        "max_input_current_a": 25.0,
        "strings_per_mppt": 3,
    },
    {
        "brand": "Huawei",
        "model": "SUN2000-20KTL-M2",
        "power_kw": 20.0,
        "max_pv_power_kwp": 30.0,
        "max_pv_current_a": 60,
        "efficiency": 0.985,
        "price_pln": 7800,
        "mppt_count": 4,
        "hybrid": False,
        "warranty_years": 10,
        "max_input_voltage_v": 1100,
        "mppt_voltage_min_v": 160,
        "mppt_voltage_max_v": 950,
        "max_input_current_a": 30.0,
        "strings_per_mppt": 2,
    },
]


def _score_inverter(
    inverter: dict,
    total_power_kwp: float,
    has_shading: bool,
    prefer_hybrid: bool,
    budget_limit_pln: Optional[float],
) -> float:
    """
    Prosty scoring falownika:
    - preferujemy wyższą sprawność,
    - moc AC blisko mocy DC (DC/AC ~ 1.1),
    - premiujemy hybrydę jeśli prefer_hybrid,
    - karzemy za przekroczenie budżetu.
    """
    power_kw = inverter["power_kw"]
    efficiency = inverter.get("efficiency", 0.97)
    price = inverter.get("price_pln", 999999)

    dc_ac_ratio = total_power_kwp / power_kw if power_kw > 0 else 0.0
    ratio_penalty = abs(dc_ac_ratio - 1.1)  # optimum ~1.1

    score = efficiency * 100 - ratio_penalty * 10

    if prefer_hybrid and inverter.get("hybrid", False):
        score += 5

    if budget_limit_pln is not None and price > budget_limit_pln:
        score -= 50  # mocna kara za wyjście poza budżet

    if has_shading and inverter.get("mppt_count", 2) < 2:
        score -= 10

    return score


def select_optimal_inverter(
    total_power_kwp: float,
    has_shading: bool = False,
    prefer_hybrid: bool = False,
    budget_limit_pln: Optional[float] = None,
    panel_config: Optional[dict] = None,
    panels_count: int = 0,
) -> dict:
    """
    Dobiera falownik z weryfikacją bezpieczeństwa stringów (5 warunków).

    Zwraca:
        {
            "inverter": dict,
            "quantity": 1,
            "dc_ac_ratio": float,
            "oversizing_percent": float,
            "total_cost_pln": float,
            "alternative_microinverters": dict,
            "rationale": str,
            "string_safety": dict | None,
            "optimal_string_size": dict | None,
        }
    """
    # KROK 1: filtracja po mocy DC
    suitable_inverters = [
        inv for inv in INVERTERS_DATABASE
        if inv["max_pv_power_kwp"] >= total_power_kwp
    ]
    if not suitable_inverters:
        # fallback: bierzemy najmocniejszy dostępny
        suitable_inverters = sorted(INVERTERS_DATABASE, key=lambda x: x["power_kw"], reverse=True)

    # KROK 2: scoring
    suitable_inverters.sort(
        key=lambda inv: _score_inverter(inv, total_power_kwp, has_shading, prefer_hybrid, budget_limit_pln),
        reverse=True,
    )
    selected = suitable_inverters[0]

    # KROK 3: metryki DC/AC
    dc_ac_ratio = total_power_kwp / selected["power_kw"] if selected["power_kw"] > 0 else 0.0
    oversizing = (dc_ac_ratio - 1.0) * 100.0

    string_safety = None
    optimal_string_info = None

    # KROK 4: weryfikacja bezpieczeństwa stringów (jeśli mamy dane paneli)
    if panel_config and panels_count > 0:
        optimal_string_info = calculate_optimal_string_size(
            panel_config=panel_config,
            inverter_config=selected,
        )

        mppt_count = selected.get("mppt_count", 2)
        strings_per_mppt = selected.get("strings_per_mppt", 1)
        total_strings = max(1, mppt_count * strings_per_mppt)

        panels_per_string = max(1, panels_count // total_strings)

        string_safety = verify_string_safety(
            panels_in_string=panels_per_string,
            panel_config=panel_config,
            inverter_config=selected,
        )

        # Jeśli wybrany falownik jest niebezpieczny → szukamy alternatywy
        if not string_safety["all_safe"]:
            for alt_inv in suitable_inverters[1:]:
                alt_safety = verify_string_safety(
                    panels_in_string=panels_per_string,
                    panel_config=panel_config,
                    inverter_config=alt_inv,
                )
                if alt_safety["all_safe"]:
                    selected = alt_inv
                    string_safety = alt_safety
                    dc_ac_ratio = total_power_kwp / selected["power_kw"] if selected["power_kw"] > 0 else 0.0
                    oversizing = (dc_ac_ratio - 1.0) * 100.0
                    break

    rationale_parts = [
        f"{selected['brand']} {selected['model']} ({selected['power_kw']} kW)",
        f"DC/AC: {dc_ac_ratio:.2f}",
    ]
    if selected.get("hybrid", False):
        rationale_parts.append("Hybrydowy")
    if string_safety and not string_safety["all_safe"]:
        rationale_parts.append("⚠️ UWAGA: string nie spełnia wszystkich warunków bezpieczeństwa!")

    rationale = " | ".join(rationale_parts)

    return {
        "inverter": selected,
        "quantity": 1,
        "dc_ac_ratio": round(dc_ac_ratio, 2),
        "oversizing_percent": round(oversizing, 1),
        "total_cost_pln": selected["price_pln"],
        "alternative_microinverters": _get_microinverter_alternative(total_power_kwp),
        "rationale": rationale,
        "string_safety": string_safety,
        "optimal_string_size": optimal_string_info,
    }


def recommend_microinverters(
    has_shading: bool,
    shading_loss: float,
    panels_count: int,
    roof_type: str,
) -> dict:
    """Rekomenduje mikroinwertery na podstawie warunków dachu."""
    recommended = False
    reason = "Brak potrzeby stosowania mikroinwerterów."
    cost_per_panel = 350
    total_cost = 0

    if has_shading or shading_loss > 0.10:
        recommended = True
        reason = "Zacienienie dachu — mikroinwertery poprawią wydajność."
    if roof_type in ["hip", "complex"]:
        recommended = True
        reason = "Dach wielospadowy — mikroinwertery poprawią pracę paneli."
    if panels_count > 20 and not recommended:
        recommended = True
        reason = "Duża liczba paneli — mikroinwertery poprawią niezależną pracę modułów."

    if recommended:
        total_cost = panels_count * cost_per_panel

    return {
        "recommended": recommended,
        "reason": reason,
        "total_cost_pln": round(total_cost, 2),
    }


def _get_microinverter_alternative(total_power_kwp: float) -> Dict:
    """Helper: Zwraca dane o alternatywie z mikroinwerterami."""
    panels_count = int(total_power_kwp / 0.45)
    cost_per_panel = 450
    return {
        "brand": "Enphase",
        "model": "IQ8+ Microinverters",
        "quantity": panels_count,
        "cost_per_panel": cost_per_panel,
        "total_cost_pln": panels_count * cost_per_panel,
        "benefits": [
            "Eliminacja wpływu zacienienia na cały system",
            "Monitoring każdego panelu osobno",
            "Wyższa niezawodność (brak single point of failure)",
            "Łatwiejsza rozbudowa w przyszłości",
        ],
    }


def calculate_required_mppt_trackers(
    total_power_kwp: float,
    roof_sections: int = 1,
    has_shading: bool = False,
) -> int:
    """Oblicza wymaganą liczbę MPPT trackerów."""
    required_mppt = roof_sections
    if has_shading:
        required_mppt += 1
    if total_power_kwp > 12:
        required_mppt = max(required_mppt, 3)
    return max(2, min(4, required_mppt))