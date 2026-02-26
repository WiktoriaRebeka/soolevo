# backend/app/core/physics.py
import math
from app.data.energy_rates import get_rate_data
from app.core.consumption_engine import ConsumptionEngine

def calculate_degradation_factor(year: int) -> float:
    """
    Zwraca współczynnik degradacji paneli dla danego roku.
    Rok 1: -0.5%, kolejne lata: -0.3% rocznie.
    """
    if year <= 1:
        return 0.995
    return round(0.995 * ((1 - 0.003) ** (year - 1)), 4)



def calculate_temperature_derating(
    cell_temp_c: float,
    gamma_pmax_percent: float = -0.35,
    t_stc: float = 25.0,
) -> float:
    """
    Współczynnik korekcji mocy ze względu na temperaturę.

    η_temp = 1 + γ × (T_cell - 25°C)
    """
    delta_t = cell_temp_c - t_stc
    gamma_decimal = gamma_pmax_percent / 100.0

    derating_factor = 1.0 + (gamma_decimal * delta_t)

    # Sanity check: [0.50, 1.10]
    return max(0.50, min(1.10, derating_factor))


def calculate_monthly_irradiance_w_m2(
    monthly_kwh_m2: float,
    days: int,
) -> float:
    """
    Konwertuje miesięczną irradiancję na średnie natężenie [W/m²].
    """
    monthly_wh_m2 = monthly_kwh_m2 * 1000.0
    effective_hours_per_day = 6.0  # Średnio 6h efektywnego słońca
    total_effective_hours = days * effective_hours_per_day

    if total_effective_hours == 0:
        return 0.0

    return monthly_wh_m2 / total_effective_hours




def calculate_voc_at_temp(
    voc_stc: float,
    beta_voc_percent: float,
    cell_temp_c: float,
    t_stc: float = 25.0,
) -> float:
    """
    Oblicza V_oc w danej temperaturze.

    V_oc(T) = V_oc(STC) × [1 + β_Voc × (T - T_STC)]
    """
    beta_decimal = beta_voc_percent / 100.0
    delta_t = cell_temp_c - t_stc
    voc_at_temp = voc_stc * (1.0 + beta_decimal * delta_t)
    return voc_at_temp


def calculate_vmp_at_temp(
    vmp_stc: float,
    beta_vmp_percent: float,
    cell_temp_c: float,
    t_stc: float = 25.0,
) -> float:
    """
    Oblicza V_mp w danej temperaturze.

    V_mp(T) = V_mp(STC) × [1 + β_Vmp × (T - T_STC)]
    """
    beta_decimal = beta_vmp_percent / 100.0
    delta_t = cell_temp_c - t_stc
    vmp_at_temp = vmp_stc * (1.0 + beta_decimal * delta_t)
    return vmp_at_temp


def verify_string_safety(
    panels_in_string: int,
    panel_config: dict,
    inverter_config: dict,
    t_min: float = -20.0,
    t_max_cell: float = 75.0,
) -> dict:
    """
    Weryfikuje 5 WARUNKÓW BEZPIECZEŃSTWA elektrycznego stringu.

    Warunki:
    1. V_oc(zimą) ≤ V_max (KRYTYCZNY)
    2. V_mp(latem) ≥ V_min_MPPT
    3. V_oc(STC) w zakresie MPPT
    4. I_sc × 1.25 ≤ I_max
    5. DC/AC ratio 0.8–1.2 (soft check)
    """
    n = panels_in_string

    # Parametry panelu
    voc_stc = panel_config.get("voc_v", 45.0)
    vmp_stc = panel_config.get("vmp_v", 38.0)
    isc_stc = panel_config.get("isc_a", 11.0)
    panel_power_kw = panel_config.get("power_wp", 400) / 1000.0
    beta_voc = panel_config.get("beta_voc_percent", -0.29)
    beta_vmp = panel_config.get("beta_vmp_percent", -0.35)

    # Parametry inwertera
    inverter_vmax = inverter_config.get("max_input_voltage_v", 600)
    inverter_vmppt_min = inverter_config.get("mppt_voltage_min_v", 80)
    inverter_vmppt_max = inverter_config.get("mppt_voltage_max_v", 550)
    inverter_imax = inverter_config.get("max_input_current_a", 15)
    inverter_power_ac_kw = inverter_config.get("power_kw", 5.0)

    warnings = []

    # WARUNEK 1: V_oc(zimą) ≤ V_max
    voc_cold = calculate_voc_at_temp(voc_stc, beta_voc, t_min)
    string_voc_cold = voc_cold * n
    voc_cold_safe = string_voc_cold <= inverter_vmax
    if not voc_cold_safe:
        warnings.append(
            f"🔴 KRYTYCZNY! V_oc(zimą)={string_voc_cold:.0f}V > V_max={inverter_vmax}V. "
            f"RYZYKO USZKODZENIA INWERTERA! Zmniejsz liczbę paneli w stringu."
        )

    # WARUNEK 2: V_mp(latem) ≥ V_min_MPPT
    vmp_hot = calculate_vmp_at_temp(vmp_stc, beta_vmp, t_max_cell)
    string_vmp_hot = vmp_hot * n
    vmp_hot_safe = string_vmp_hot >= inverter_vmppt_min
    if not vmp_hot_safe:
        warnings.append(
            f"⚠️ V_mp(latem)={string_vmp_hot:.0f}V < V_min_MPPT={inverter_vmppt_min}V. "
            f"Inwerter nie uruchomi się w wysokich temperaturach!"
        )

    # WARUNEK 3: V_oc(STC) w zakresie MPPT
    string_voc_stc = voc_stc * n
    voc_in_range = inverter_vmppt_min <= string_voc_stc <= inverter_vmppt_max
    if not voc_in_range and string_voc_stc > inverter_vmppt_max:
        warnings.append(
            f"⚠️ V_oc(STC)={string_voc_stc:.0f}V > V_max_MPPT={inverter_vmppt_max}V. "
            f"String poza optymalnym zakresem MPPT."
        )

    # WARUNEK 4: I_sc × 1.25 ≤ I_max
    isc_with_margin = isc_stc * 1.25
    isc_safe = isc_with_margin <= inverter_imax
    if not isc_safe:
        warnings.append(
            f"⚠️ I_sc×1.25={isc_with_margin:.1f}A > I_max={inverter_imax}A. "
            f"Ryzyko przepalenia bezpieczników!"
        )

    # WARUNEK 5: DC/AC ratio (soft check)
    total_dc_kw = n * panel_power_kw
    if inverter_power_ac_kw > 0:
        dc_ac_ratio = total_dc_kw / inverter_power_ac_kw
        ac_range_ok = 0.8 <= dc_ac_ratio <= 1.2
    else:
        ac_range_ok = True

    return {
        "all_safe": voc_cold_safe and vmp_hot_safe and voc_in_range and isc_safe,
        "panels_in_string": n,
        "voc_cold_safe": voc_cold_safe,
        "string_voc_cold_V": round(string_voc_cold, 1),
        "vmp_hot_safe": vmp_hot_safe,
        "string_vmp_hot_V": round(string_vmp_hot, 1),
        "voc_in_mppt_range": voc_in_range,
        "isc_safe": isc_safe,
        "ac_range_ok": ac_range_ok,
        "warnings": warnings,
    }


def calculate_optimal_string_size(
    panel_config: dict,
    inverter_config: dict,
    t_min: float = -20.0,
    t_max_cell: float = 75.0,
) -> dict:
    """
    Automatycznie wyznacza optymalną liczbę paneli w stringu.

    1. n_max: V_oc(zimą) × n ≤ V_max
    2. n_min: V_mp(latem) × n ≥ V_min_MPPT
    3. n_optimal: V_oc(STC) ≈ 75% V_max_MPPT
    """
    voc_stc = panel_config.get("voc_v", 45.0)
    vmp_stc = panel_config.get("vmp_v", 38.0)
    beta_voc = panel_config.get("beta_voc_percent", -0.29)
    beta_vmp = panel_config.get("beta_vmp_percent", -0.35)

    inverter_vmax = inverter_config.get("max_input_voltage_v", 600)
    inverter_vmppt_min = inverter_config.get("mppt_voltage_min_v", 80)
    inverter_vmppt_max = inverter_config.get("mppt_voltage_max_v", 550)

    # V_oc w zimie
    voc_cold = calculate_voc_at_temp(voc_stc, beta_voc, t_min)
    # V_mp w lecie
    vmp_hot = calculate_vmp_at_temp(vmp_stc, beta_vmp, t_max_cell)

    # Max paneli: V_oc(zimą) × n ≤ V_max
    if voc_cold > 0:
        max_panels = int(inverter_vmax / voc_cold)
    else:
        max_panels = 20

    # Min paneli: V_mp(latem) × n ≥ V_min_MPPT
    if vmp_hot > 0:
        min_panels = math.ceil(inverter_vmppt_min / vmp_hot)
    else:
        min_panels = 1

    is_valid = min_panels <= max_panels

    # Optymalne: 75% zakresu MPPT
    target_voltage = inverter_vmppt_max * 0.75
    optimal_panels = max(min_panels, min(max_panels, round(target_voltage / voc_stc)))

    return {
        "min_panels": min_panels,
        "max_panels": max_panels,
        "optimal_panels": optimal_panels,
        "is_valid": is_valid,
    }