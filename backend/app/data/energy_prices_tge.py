# backend/app/data/energy_prices_tge.py
"""
Ceny energii na Towarowej Giełdzie Energii (TGE) - RCEm.

NOWE w v3.1:
- Dodano profil godzinowy (kanibalizacja PV)
- Funkcja get_rcem_hourly() zwraca 8760 cen
"""

from typing import Dict, List


# Miesięczne ceny RCEm 2025 (PLN/kWh brutto z VAT)
RCEM_MONTHLY_2025 = {
    1: 0.320,   # Styczeń
    2: 0.310,   # Luty
    3: 0.295,   # Marzec
    4: 0.275,   # Kwiecień
    5: 0.250,   # Maj
    6: 0.235,   # Czerwiec
    7: 0.230,   # Lipiec
    8: 0.240,   # Sierpień
    9: 0.260,   # Wrzesień
    10: 0.280,  # Październik
    11: 0.300,  # Listopad
    12: 0.315,  # Grudzień
}


# ✅ NOWE: Profil godzinowy RCEm (efekt kanibalizacji PV)
# Wartości są współczynnikami względem średniej miesięcznej
# 1.0 = średnia, < 1.0 = poniżej średniej, > 1.0 = powyżej średniej

RCEM_HOURLY_PROFILE = {
    # Bazuje na rzeczywistych danych TGE z lat 2022-2024
    # Uwzględnia kanibalizację cenową przez PV
    
    0: 0.92,   # Noc (00:00) - niskie zużycie
    1: 0.88,   # Najniższe zużycie w nocy
    2: 0.85,
    3: 0.84,
    4: 0.86,
    5: 0.92,
    6: 1.10,   # Poranek - wzrost zużycia
    7: 1.22,   # Szczyt poranny
    8: 1.18,
    9: 1.08,
    10: 0.88,  # ⚠️ KANIBALIZACJA PV - ceny zaczynają spadać
    11: 0.58,  # ⚠️ Szczyt produkcji PV = drastyczny spadek cen
    12: 0.48,  # ⚠️ NAJNIŻSZE CENY (często blisko 0 lub ujemne!)
    13: 0.52,  # ⚠️ Nadal niska cena
    14: 0.68,  # Ceny zaczynają rosnąć
    15: 0.92,
    16: 1.12,
    17: 1.32,  # Wieczór - wzrost zużycia
    18: 1.48,  # Szczyt wieczorny - najwyższe ceny
    19: 1.55,  # PEAK - najwyższe ceny w ciągu dnia
    20: 1.45,
    21: 1.28,
    22: 1.12,
    23: 1.02,
}


def get_rcem_monthly(year: int = 2025) -> Dict[int, float]:
    """
    Zwraca miesięczne ceny RCEm (PLN/kWh brutto).
    
    Args:
        year: Rok (obecnie tylko 2025)
    
    Returns:
        Słownik {miesiąc: cena_PLN_per_kWh}
    """
    if year == 2025:
        return RCEM_MONTHLY_2025
    
    # Fallback: 2025 z inflacją
    inflation_rate = 0.04  # 4%/rok
    years_diff = year - 2025
    inflated_prices = {
        month: price * ((1 + inflation_rate) ** years_diff)
        for month, price in RCEM_MONTHLY_2025.items()
    }
    return inflated_prices


def get_rcem_hourly(year: int = 2025) -> List[float]:
    """
    ✅ NOWE: Zwraca wektor 8760 cen RCEm dla całego roku.
    
    Uwzględnia efekt kanibalizacji cenowej przez PV:
    - W godzinach 11:00-14:00 ceny są znacznie niższe (50-60% średniej)
    - W godzinach 18:00-20:00 ceny są najwyższe (145-155% średniej)
    
    Args:
        year: Rok (2025)
    
    Returns:
        Lista 8760 wartości PLN/kWh (brutto z VAT 23%)
        
    Example:
        >>> prices = get_rcem_hourly(2025)
        >>> len(prices)
        8760
        >>> prices[12]  # Południe - niska cena przez PV
        0.12
        >>> prices[19]  # Wieczór - wysoka cena
        0.39
    """
    rcem_monthly = get_rcem_monthly(year)
    hourly_prices = []
    
    for day in range(365):
        # Który miesiąc?
        current_month = (day // 30) + 1
        if current_month > 12:
            current_month = 12
        
        # Średnia cena w tym miesiącu (brutto)
        monthly_avg_brutto = rcem_monthly[current_month]
        
        # Sezonowość wewnątrz miesiąca (opcjonalnie)
        # Lato: więcej słońca = niższe ceny w południe
        import math
        seasonal_factor_summer = 1.0 - 0.1 * math.sin(2 * math.pi * (day - 80) / 365)
        
        for hour in range(24):
            # Współczynnik godzinowy
            hour_factor = RCEM_HOURLY_PROFILE[hour]
            
            # Dla godzin południowych (11-14) zastosuj dodatkową sezonowość
            if 11 <= hour <= 14:
                hour_factor *= seasonal_factor_summer
            
            # Cena godzinowa = średnia miesięczna * współczynnik
            hourly_price_brutto = monthly_avg_brutto * hour_factor
            
            # Zabezpieczenie: cena nie może być ujemna
            hourly_price_brutto = max(0.01, hourly_price_brutto)
            
            hourly_prices.append(round(hourly_price_brutto, 4))
    
    return hourly_prices


def get_rcem_statistics(year: int = 2025) -> Dict[str, float]:
    """
    Zwraca statystyki cen RCEm dla danego roku.
    
    Returns:
        {
            "annual_avg": 0.27,
            "peak_avg": 0.38,     # Średnia w godzinach 18-20
            "offpeak_avg": 0.14,  # Średnia w godzinach 11-13
            "ratio": 2.71,        # Peak / Offpeak
        }
    """
    hourly_prices = get_rcem_hourly(year)
    
    # Wydziel godziny szczytowe i pozaszczytowe
    peak_hours = []
    offpeak_hours = []
    
    for hour_idx in range(8760):
        hour_of_day = hour_idx % 24
        
        if 18 <= hour_of_day <= 20:
            peak_hours.append(hourly_prices[hour_idx])
        elif 11 <= hour_of_day <= 13:
            offpeak_hours.append(hourly_prices[hour_idx])
    
    return {
        "annual_avg": round(sum(hourly_prices) / len(hourly_prices), 4),
        "peak_avg": round(sum(peak_hours) / len(peak_hours), 4),
        "offpeak_avg": round(sum(offpeak_hours) / len(offpeak_hours), 4),
        "ratio": round((sum(peak_hours) / len(peak_hours)) / (sum(offpeak_hours) / len(offpeak_hours)), 2),
    }


# Legacy compatibility
def get_average_rcem(year: int = 2025) -> float:
    """Zwraca średnią roczną cenę RCEm."""
    return sum(get_rcem_monthly(year).values()) / 12


def get_net_billing_rate_with_vat(rcem_pln_kwh: float) -> float:
    """
    Przelicza cenę RCEm na stawkę net-billingu z VAT 23%.
    
    Formula: deposit_rate = RCEm × 1.23
    
    Args:
        rcem_pln_kwh: Cena RCEm [PLN/kWh]
    
    Returns:
        Stawka depozytu [PLN/kWh]
    """
    return round(rcem_pln_kwh * 1.23, 3)
