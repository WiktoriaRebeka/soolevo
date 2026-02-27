# backend/app/core/hourly_engine.py
"""
HourlyEngine v3.3 — ŹRÓDŁO PRAWDY dla rocznych oszczędności.

Poprawki v3.3:
✅ Realistyczny profil zużycia — szczyt wieczorny, nie dzienny
✅ Bateria: charge i discharge NIGDY jednocześnie > 0
✅ SOC zawsze w [0, capacity] — bez przepełnienia i ujemnych wartości
✅ battery_soc_history zbierany CO GODZINĘ (nie tylko przy nadwyżce)
✅ energy_flow_chart_data na poziomie głównej pętli (nie wewnątrz gałęzi)
✅ batteryCharge / batteryDischarge zawsze >= 0
✅ Miesięczne agregaty energii (produkcja, zużycie, autokonsumpcja, nadwyżka, pobór z sieci)
"""

from typing import Dict, Any, List, Optional
import math

from app.data.usage_profiles import (
    PERSON_TYPES,
    HOUSEHOLD_SIZE_MULTIPLIER,
    WEEKEND_MULTIPLIER_DAY,
    WEEKEND_MULTIPLIER_EVENING,
)


class HourlyEngine:

    def __init__(
        self,
        annual_production_kwh: float,
        annual_consumption_kwh: float,
        electricity_tariff_pln_per_kwh: float,
        rcem_hourly: List[float],
        tariff_type: str = "G11",
        tariff_zones: Optional[Dict[int, float]] = None,
        battery_config: Optional[Dict[str, Any]] = None,
        heating_kwh: float = 0.0,
        cooling_kwh: float = 0.0
    ):
        self.annual_production_kwh = annual_production_kwh
        self.annual_consumption_kwh = annual_consumption_kwh
        self.electricity_tariff = electricity_tariff_pln_per_kwh
        self.rcem_hourly = rcem_hourly
        self.tariff_type = tariff_type
        self.battery_config = battery_config or {}
        self.heating_kwh = heating_kwh
        self.cooling_kwh = cooling_kwh

        self.household_size = self.battery_config.get("household_size", 3)
        self.people_home_weekday = self.battery_config.get("people_home_weekday", 1)

        if len(rcem_hourly) != 8760:
            raise ValueError(f"rcem_hourly must have 8760 values, got {len(rcem_hourly)}")

        if tariff_zones:
            self.tariff_zones = tariff_zones
        else:
            self.tariff_zones = {h: electricity_tariff_pln_per_kwh for h in range(24)}

        from app.data.energy_rates import decompose_electricity_tariff
        op = self.battery_config.get("operator", "pge")
        self.tariff_components = decompose_electricity_tariff(operator=op, tariff=tariff_type)


    def run_hourly_simulation(
        self,
        production_profile: Optional[List[float]] = None,
        consumption_profile: Optional[List[float]] = None,
    ) -> Dict[str, Any]:

        if production_profile is None:
            production_profile = self._generate_production_profile()
        if consumption_profile is None:
            consumption_profile = self._generate_consumption_profile()

        if len(production_profile) != 8760 or len(consumption_profile) != 8760:
            raise ValueError("Profile muszą mieć 8760 wartości")

        # Zabezpieczenie przed brakiem produkcji (np. 0 paneli)
        total_production = sum(production_profile)
        if total_production <= 0:
            # Zwracamy pusty wynik, aby system się nie zawiesił
            return self._generate_empty_result(consumption_profile)

        # ── Parametry baterii ─────────────────────────────────────────────────
        battery_soc_kwh    = 0.0
        battery_capacity   = float(self.battery_config.get("capacity_kwh", 0) or 0)
        battery_power      = float(self.battery_config.get("power_kw",     0) or 0)
        battery_efficiency = float(self.battery_config.get("efficiency", 0.95) or 0.95)
        has_battery        = battery_capacity > 0 and battery_power > 0

        # ── Akumulatory energii ───────────────────────────────────────────────
        total_autoconsumption_kwh     = 0.0
        total_surplus_kwh             = 0.0
        total_grid_import_kwh         = 0.0
        total_battery_stored_kwh      = 0.0
        total_battery_discharged_kwh  = 0.0

        # ── Akumulatory finansowe ─────────────────────────────────────────────
        total_autoconsumption_value           = 0.0
        total_net_billing_value               = 0.0
        total_battery_discharge_benefit       = 0.0
        total_battery_charge_opportunity_cost = 0.0
        total_grid_import_cost                = 0.0

        monthly_surplus_kwh   = {i: 0.0 for i in range(1, 13)}
        monthly_surplus_value = {i: 0.0 for i in range(1, 13)}

        battery_soc_history: List[float]   = []
        summer_chart_data: List[Dict] = []
        winter_chart_data: List[Dict] = []

        energy_rate       = self.tariff_components["energy_pln_per_kwh"]
        distribution_rate = self.tariff_components["distribution_pln_per_kwh"]

        SUMMER_START = 4032
        WINTER_START = 336

        # ── Mapa godzina → miesiąc (0–11) dla agregatów miesięcznych ─────────
        DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        month_of_hour: List[int] = []
        for m_idx, days in enumerate(DAYS_PER_MONTH):
            for _ in range(days * 24):
                month_of_hour.append(m_idx)
        # Bez roku przestępnego — 365 dni
        if len(month_of_hour) != 8760:
            # awaryjnie dopasuj długość
            if len(month_of_hour) > 8760:
                month_of_hour = month_of_hour[:8760]
            else:
                month_of_hour += [11] * (8760 - len(month_of_hour))

        monthly_production_kwh: List[float]   = [0.0] * 12
        monthly_consumption_kwh: List[float]  = [0.0] * 12
        monthly_autoconsumption: List[float]  = [0.0] * 12
        monthly_surplus_list: List[float]     = [0.0] * 12
        monthly_grid_import_list: List[float] = [0.0] * 12

        # =====================================================================
        # SYMULACJA GODZINOWA (8760 iteracji)
        # =====================================================================
        for hour in range(8760):

            pv_kwh   = production_profile[hour]
            load_kwh = consumption_profile[hour]

            hour_of_day      = hour % 24
            # stary month (1–12) dla net_billing
            month            = min(12, (hour // 24 // 30) + 1)
            rcem_this_hour   = self.rcem_hourly[hour]
            tariff_this_hour = self.tariff_zones.get(hour_of_day, self.electricity_tariff)

            balance = pv_kwh - load_kwh

            # Zmienne kroku — zawsze startują od 0, nigdy jednocześnie > 0
            charge_kwh    = 0.0
            discharge_kwh = 0.0
            deficit_kwh   = 0.0

            # ── NADWYŻKA PV ───────────────────────────────────────────────────
            if balance >= 0:
                autoconsumption_kwh = load_kwh
                surplus_kwh         = balance

                total_autoconsumption_value += autoconsumption_kwh * tariff_this_hour

                # Ładowanie baterii z nadwyżki — discharge_kwh zostaje 0
                if has_battery and battery_soc_kwh < battery_capacity:
                    room_kwh   = battery_capacity - battery_soc_kwh
                    # Ograniczenie: moc, dostępna nadwyżka, wolne miejsce (z uwzgl. strat)
                    max_charge = min(surplus_kwh, battery_power, room_kwh / battery_efficiency)
                    charge_kwh = max(0.0, max_charge)

                    battery_soc_kwh = min(
                        battery_capacity,
                        battery_soc_kwh + charge_kwh * battery_efficiency
                    )
                    total_battery_stored_kwh              += charge_kwh
                    total_battery_charge_opportunity_cost += charge_kwh * rcem_this_hour
                    surplus_kwh -= charge_kwh

                surplus_value = surplus_kwh * rcem_this_hour
                total_net_billing_value      += surplus_value
                total_surplus_kwh            += surplus_kwh
                monthly_surplus_kwh[month]   += surplus_kwh
                monthly_surplus_value[month] += surplus_value
                total_autoconsumption_kwh    += autoconsumption_kwh

            # ── NIEDOBÓR ENERGII ──────────────────────────────────────────────
            else:
                autoconsumption_kwh = pv_kwh
                deficit_kwh         = abs(balance)

                total_autoconsumption_value += autoconsumption_kwh * tariff_this_hour

                # Rozładowanie baterii — charge_kwh zostaje 0
                if has_battery and battery_soc_kwh > 0:
                    max_discharge = min(deficit_kwh, battery_power, battery_soc_kwh)
                    discharge_kwh = max(0.0, max_discharge)

                    battery_soc_kwh = max(0.0, battery_soc_kwh - discharge_kwh)
                    total_battery_discharged_kwh    += discharge_kwh
                    total_battery_discharge_benefit += discharge_kwh * tariff_this_hour
                    deficit_kwh                     -= discharge_kwh

                deficit_kwh = max(0.0, deficit_kwh)

                total_grid_import_kwh  += deficit_kwh
                total_grid_import_cost += deficit_kwh * tariff_this_hour
                total_autoconsumption_kwh += autoconsumption_kwh

            # ── SOC zapisywany CO GODZINĘ — poza if/else ─────────────────────
            battery_soc_history.append(round(battery_soc_kwh, 4))

            # ── Agregacja miesięczna (NOWE) ──────────────────────────────────
            m_idx = month_of_hour[hour]  # 0–11
            monthly_production_kwh[m_idx]   += pv_kwh
            monthly_consumption_kwh[m_idx]  += load_kwh
            monthly_autoconsumption[m_idx]  += autoconsumption_kwh
            monthly_surplus_list[m_idx]     += max(0.0, balance)  # nadwyżka brutto
            monthly_grid_import_list[m_idx] += deficit_kwh

            # ── Zapis do wykresów sezonowych (v3.7) ───────────────────────────
            chart_entry = {
                "hour": f"{hour_of_day:02d}:00",
                "pv": round(pv_kwh, 3),
                "consumption": round(load_kwh, 3),
                "batteryCharge": round(charge_kwh, 3),
                "batteryDischarge": round(discharge_kwh, 3),
                "gridImport": round(deficit_kwh, 3),
                "soc": round(battery_soc_kwh / battery_capacity * 100, 1) if battery_capacity > 0 else 0
            }

            if SUMMER_START <= hour < SUMMER_START + 24:
                summer_chart_data.append(chart_entry)
            elif WINTER_START <= hour < WINTER_START + 24:
                winter_chart_data.append(chart_entry)

        # =====================================================================
        # FINALIZACJA FINANSOWA
        # =====================================================================
        autoconsumption_value_pln = total_autoconsumption_value
        net_billing_value_pln     = total_net_billing_value

        lost_deposit_pln = 0.0
        refund_20pct_pln = 0.0
        if total_surplus_kwh > self.annual_consumption_kwh:
            unused_kwh       = total_surplus_kwh - self.annual_consumption_kwh
            avg_rcem         = sum(self.rcem_hourly) / len(self.rcem_hourly)
            unused_value     = unused_kwh * avg_rcem
            refund_20pct_pln = unused_value * 0.20
            lost_deposit_pln = unused_value * 0.80
            net_billing_value_pln -= lost_deposit_pln

        distribution_cost_pln = total_grid_import_kwh * distribution_rate
        battery_benefit_pln   = (
            total_battery_discharge_benefit - total_battery_charge_opportunity_cost
        )
        annual_savings_pln = (
            autoconsumption_value_pln + net_billing_value_pln + battery_benefit_pln
        )

        total_production  = sum(production_profile)
        total_consumption = sum(consumption_profile)

        # Suma energii, która nie opuściła domu (zużyta od razu + zużyta z baterii)
        total_internal_usage_kwh = total_autoconsumption_kwh + total_battery_discharged_kwh

        # Autokonsumpcja: Jaki % produkcji został w domu
        autoconsumption_rate = (
            total_internal_usage_kwh / total_production if total_production > 0 else 0.0
        )
        
        # Samowystarczalność: Jaki % potrzeb domu pokryło PV+Bateria
        self_sufficiency = (
            total_internal_usage_kwh / total_consumption if total_consumption > 0 else 0.0
        )
        effective_surplus_rate = (
            net_billing_value_pln / total_surplus_kwh if total_surplus_kwh > 0 else 0.0
        )

        return {
            "annual_cashflow": {
                "autoconsumption_pln":              round(autoconsumption_value_pln, 2),
                "net_billing_pln":                  round(net_billing_value_pln, 2),
                "battery_benefit_pln":              round(battery_benefit_pln, 2),
                "battery_discharge_benefit_pln":    round(total_battery_discharge_benefit, 2),
                "battery_opportunity_cost_pln":     round(total_battery_charge_opportunity_cost, 2),
                "lost_deposit_pln":                 round(lost_deposit_pln, 2),
                "refund_20pct_pln":                 round(refund_20pct_pln, 2),
                "distribution_cost_pln":            round(distribution_cost_pln, 2),
                "net":                              round(annual_savings_pln, 2),
            },
            "energy_flow": {
                "total_production_kwh":   round(total_production, 1),
                "total_consumption_kwh":  round(total_consumption, 1),
                "autoconsumption_kwh":    round(total_autoconsumption_kwh, 1),
                "surplus_kwh":            round(total_surplus_kwh, 1),
                "grid_import_kwh":        round(total_grid_import_kwh, 1),
                "battery_stored_kwh":     round(total_battery_stored_kwh, 1),
                "battery_discharged_kwh": round(total_battery_discharged_kwh, 1),
                "production_profile":     production_profile,
                "consumption_profile":    consumption_profile,
                "soc_profile":            battery_soc_history,
                # ── NOWE: miesięczne agregaty ────────────────────────────────
                "monthly_production_kwh":      [round(v, 1) for v in monthly_production_kwh],
                "monthly_consumption_kwh":     [round(v, 1) for v in monthly_consumption_kwh],
                "monthly_autoconsumption_kwh": [round(v, 1) for v in monthly_autoconsumption],
                "monthly_surplus_kwh_list":    [round(v, 1) for v in monthly_surplus_list],
                "monthly_grid_import_kwh":     [round(v, 1) for v in monthly_grid_import_list],
            },
            "rates": {
                "autoconsumption_rate":  round(autoconsumption_rate, 3),
                "self_sufficiency_rate": round(self_sufficiency, 3),
            },
            "net_billing": {
                "monthly_surplus_kwh":        monthly_surplus_kwh,
                "monthly_surplus_value_pln":  monthly_surplus_value,
                "annual_deposit_pln":         round(net_billing_value_pln + lost_deposit_pln, 2),
                "annual_deposit_used_pln":    round(net_billing_value_pln, 2),
                "annual_deposit_lost_pln":    round(lost_deposit_pln, 2),
                "refund_20pct_pln":           round(refund_20pct_pln, 2),
                "effective_rate_pln_per_kwh": round(effective_surplus_rate, 3),
            },
            "tariff_info": {
                "tariff_type":                        self.tariff_type,
                "avg_tariff_pln_per_kwh":             self.electricity_tariff,
                "energy_component_pln_per_kwh":       energy_rate,
                "distribution_component_pln_per_kwh": distribution_rate,
            },
            "energy_flow_chart_data": summer_chart_data,  # dla kompatybilności wstecznej
            "seasonal_charts": {
                "summer": summer_chart_data,
                "winter": winter_chart_data
            },
        
        }

    # =========================================================================
    # GENERATORY PROFILI
    # =========================================================================

    def _generate_production_profile(self) -> List[float]:
        """Paraboliczny profil PV z sezonowością."""
        profile: List[float] = []
        for day in range(365):
            seasonal = 0.7 + 0.3 * math.sin(2 * math.pi (day - 80) / 365)
            for h in range(24):
                hf = (4 * (h - 6) * (18 - h) / 144) if 6 <= h <= 18 else 0.0
                profile.append((self.annual_production_kwh / 365) * seasonal * hf)
        total = sum(profile)
        if total > 0:
            s = self.annual_production_kwh / total
            profile = [p * s for p in profile]
        return profile

    def _generate_consumption_profile(self) -> List[float]:
        """
        MODEL SEZONOWY v4.5: Separacja Bazy, Grzania i Chłodzenia.
        """
        profile = []
        
        # 1. Wagi miesięczne (Sezonowość)
        # HEATING: Szczyt w grudniu/styczniu
        W_HEAT = {1:0.19, 2:0.16, 3:0.13, 4:0.07, 5:0.02, 6:0.0, 7:0.0, 8:0.0, 9:0.02, 10:0.08, 11:0.14, 12:0.19}
        # COOLING: Szczyt w lipcu/sierpniu
        W_COOL = {1:0.0, 2:0.0, 3:0.0, 4:0.0, 5:0.10, 6:0.25, 7:0.35, 8:0.25, 9:0.05, 10:0.0, 11:0.0, 12:0.0}

        # 2. Wagi godzinowe (Behawioralne)
        HOURLY_WEIGHTS = {
            "at_home": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 1.5, 1.2, 1.0, 2.5, 3.5, 3.0, 2.5, 2.0, 1.5, 2.5, 4.0, 5.0, 4.5, 3.0, 1.5, 0.5, 0.0],
            "away":    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5, 2.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.5, 4.5, 5.5, 4.5, 3.0, 1.5, 0.5, 0.0]
        }

        # 3. Obliczamy bazę (AGD/RTV)
        base_total = max(0, self.annual_consumption_kwh - self.heating_kwh - self.cooling_kwh)
        BASE_LOAD_KW = 0.15  # 150W tła (lodówka, standby)
        activity_total = max(0, base_total - (365 * 24 * BASE_LOAD_KW))

        n_people = max(1, int(self.household_size))
        ph = max(0, min(n_people, int(self.people_home_weekday)))
        pa = n_people - ph

        # FIX: Oblicz rzeczywistą sumę wag dla TEGO konkretnego składu domowników.
        annual_weight_sum = 0.0
        for _day in range(365):
            _is_weekend = (_day % 7) in [5, 6]
            for _h in range(24):
                if _is_weekend:
                    annual_weight_sum += n_people * HOURLY_WEIGHTS["at_home"][_h]
                else:
                    annual_weight_sum += (ph * HOURLY_WEIGHTS["at_home"][_h]) + (pa * HOURLY_WEIGHTS["away"][_h])
        norm_factor = annual_weight_sum if annual_weight_sum > 0 else 15640

        for day in range(365):
            month = min(12, (day // 30) + 1)
            is_weekend = (day % 7) in [5, 6]
            
            # Budżet na ten dzień
            d_heat = (self.heating_kwh * W_HEAT[month]) / 30
            d_cool = (self.cooling_kwh * W_COOL[month]) / 30

            for h in range(24):
                # A. Baza (Ludzie)
                if is_weekend:
                    w = n_people * HOURLY_WEIGHTS["at_home"][h]
                else:
                    w = (ph * HOURLY_WEIGHTS["at_home"][h]) + (pa * HOURLY_WEIGHTS["away"][h])
                
                # FIX: norm_factor zamiast hardcoded 15640
                h_base = (w * (activity_total / norm_factor)) if activity_total > 0 else 0
                h_base += BASE_LOAD_KW
                
                # B. Grzanie (Płasko w dobie - inercja budynku)
                if 9 <= h <= 16:
                    h_heat = (d_heat * 0.35) / 8  # 35% zużycia w 8h słonecznych
                else:
                    h_heat = (d_heat * 0.65) / 16 # 65% zużycia w 16h ciemnych
                
                # C. Chłodzenie (Szczyt w dzień 12-18)
                h_cool = (d_cool * 0.8 / 6) if 12 <= h <= 18 else (d_cool * 0.2 / 18)

                profile.append(h_base + h_heat + h_cool)

        # FIX: Normalizacja końcowa — profil musi sumować się dokładnie
        # do annual_consumption_kwh niezależnie od składu domowników.
        profile_sum = sum(profile)
        if profile_sum > 0 and abs(profile_sum - self.annual_consumption_kwh) > 1.0:
            scale = self.annual_consumption_kwh / profile_sum
            profile = [p * scale for p in profile]

        return profile

    def _generate_empty_result(self, consumption_profile: List[float]) -> Dict[str, Any]:
        """
        Generuje bezpieczny, pusty wynik symulacji (v4.3).
        Wywoływane, gdy instalacja ma 0 paneli (limit dachu).
        """
        zero_8760 = [0.0] * 8760
        total_cons = sum(consumption_profile)
        avg_month_cons = total_cons / 12 if total_cons > 0 else 0.0
        
        return {
            "annual_cashflow": {
                "autoconsumption_pln": 0.0, "net_billing_pln": 0.0, "battery_benefit_pln": 0.0,
                "battery_discharge_benefit_pln": 0.0, "battery_opportunity_cost_pln": 0.0,
                "lost_deposit_pln": 0.0, "refund_20pct_pln": 0.0, "distribution_cost_pln": 0.0, "net": 0.0
            },
            "energy_flow": {
                "total_production_kwh": 0.0,
                "total_consumption_kwh": round(total_cons, 1),
                "autoconsumption_kwh": 0.0,
                "surplus_kwh": 0.0,
                "grid_import_kwh": round(total_cons, 1),
                "battery_stored_kwh": 0.0,
                "battery_discharged_kwh": 0.0,
                "production_profile": zero_8760,
                "consumption_profile": consumption_profile,
                "soc_profile": zero_8760,
                # miesięczne — sensowny fallback
                "monthly_production_kwh":      [0.0] * 12,
                "monthly_consumption_kwh":     [round(avg_month_cons, 1)] * 12,
                "monthly_autoconsumption_kwh": [0.0] * 12,
                "monthly_surplus_kwh_list":    [0.0] * 12,
                "monthly_grid_import_kwh":     [round(avg_month_cons, 1)] * 12,
            },
            "rates": {"autoconsumption_rate": 0.0, "self_sufficiency_rate": 0.0},
            "net_billing": {
                "monthly_surplus_kwh": {i: 0.0 for i in range(1, 13)},
                "monthly_surplus_value_pln": {i: 0.0 for i in range(1, 13)},
                "annual_deposit_pln": 0.0, "annual_deposit_used_pln": 0.0,
                "annual_deposit_lost_pln": 0.0, "refund_20pct_pln": 0.0, "effective_rate_pln_per_kwh": 0.0
            },
            "tariff_info": {
                "tariff_type": self.tariff_type,
                "avg_tariff_pln_per_kwh": self.electricity_tariff,
                "energy_component_pln_per_kwh": self.tariff_components["energy_pln_per_kwh"],
                "distribution_component_pln_per_kwh": self.tariff_components["distribution_pln_per_kwh"]
            },
            "energy_flow_chart_data": [],
            "seasonal_charts": {"summer": [], "winter": []}
        }

# ── Standalone helper (backward compat) ──────────────────────────────────────
def simulate_year(
    annual_production_kwh: float,
    annual_consumption_kwh: float,
    electricity_tariff_pln_per_kwh: float,
    rcem_hourly: List[float],
    tariff_type: str = "G11",
    tariff_zones: Optional[Dict[int, float]] = None,
    battery_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return HourlyEngine(
        annual_production_kwh=annual_production_kwh,
        annual_consumption_kwh=annual_consumption_kwh,
        electricity_tariff_pln_per_kwh=electricity_tariff_pln_per_kwh,
        rcem_hourly=rcem_hourly,
        tariff_type=tariff_type,
        tariff_zones=tariff_zones,
        battery_config=battery_config,
    ).run_hourly_simulation()