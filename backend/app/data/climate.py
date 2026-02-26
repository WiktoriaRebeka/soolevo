# backend/app/data/climate.py
"""
Średnie miesięczne temperatury otoczenia [°C] per województwo.
Źródło: IMGW dane historyczne 2010–2024 (normy klimatyczne).
Priorytet: Na razie Mazowieckie jako baseline. Docelowo 16 województw.
"""

MONTHLY_TEMPERATURES = {
    "dolnośląskie": {
        "jan": -1.5, "feb": -0.5, "mar": 3.5, "apr": 9.0, "may": 14.5, 
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5, 
        "nov": 4.0, "dec": 0.5
    },
    "kujawsko-pomorskie": {
        "jan": -2.0, "feb": -1.0, "mar": 3.0, "apr": 8.5, "may": 14.0,
        "jun": 17.0, "jul": 19.0, "aug": 18.5, "sep": 14.0, "oct": 9.0,
        "nov": 3.5, "dec": 0.0
    },
    "lubelskie": {
        "jan": -2.5, "feb": -1.5, "mar": 3.0, "apr": 9.5, "may": 15.0,
        "jun": 18.0, "jul": 20.0, "aug": 19.5, "sep": 14.5, "oct": 9.5,
        "nov": 3.5, "dec": -0.5
    },
    "lubuskie": {
        "jan": -1.0, "feb": 0.0, "mar": 4.0, "apr": 9.5, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 4.0, "dec": 1.0
    },
    "łódzkie": {
        "jan": -2.0, "feb": -1.0, "mar": 3.5, "apr": 9.0, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 4.0, "dec": 0.0
    },
    "małopolskie": {
        "jan": -2.5, "feb": -1.0, "mar": 3.5, "apr": 9.5, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 4.0, "dec": -0.5
    },
    "mazowieckie": {
        "jan": -2.5, "feb": -1.5, "mar": 3.0, "apr": 9.0, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 3.5, "dec": -0.5
    },
    "opolskie": {
        "jan": -1.5, "feb": -0.5, "mar": 4.0, "apr": 9.5, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 4.0, "dec": 0.5
    },
    "podkarpackie": {
        "jan": -3.0, "feb": -1.5, "mar": 3.0, "apr": 9.5, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 3.5, "dec": -1.0
    },
    "podlaskie": {
        "jan": -3.5, "feb": -2.5, "mar": 2.0, "apr": 8.5, "may": 14.0,
        "jun": 17.0, "jul": 19.0, "aug": 18.5, "sep": 13.5, "oct": 8.5,
        "nov": 2.5, "dec": -1.5
    },
    "pomorskie": {
        "jan": -1.0, "feb": -0.5, "mar": 3.0, "apr": 8.0, "may": 13.0,
        "jun": 16.5, "jul": 18.5, "aug": 18.5, "sep": 14.0, "oct": 9.5,
        "nov": 4.5, "dec": 1.0
    },
    "śląskie": {
        "jan": -2.0, "feb": -1.0, "mar": 3.5, "apr": 9.0, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 4.0, "dec": 0.0
    },
    "świętokrzyskie": {
        "jan": -2.5, "feb": -1.5, "mar": 3.0, "apr": 9.0, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 3.5, "dec": -0.5
    },
    "warmińsko-mazurskie": {
        "jan": -2.5, "feb": -2.0, "mar": 2.5, "apr": 8.5, "may": 13.5,
        "jun": 16.5, "jul": 18.5, "aug": 18.0, "sep": 13.5, "oct": 8.5,
        "nov": 3.0, "dec": -1.0
    },
    "wielkopolskie": {
        "jan": -1.5, "feb": -0.5, "mar": 3.5, "apr": 9.0, "may": 14.5,
        "jun": 17.5, "jul": 19.5, "aug": 19.0, "sep": 14.5, "oct": 9.5,
        "nov": 4.0, "dec": 0.5
    },
    "zachodniopomorskie": {
        "jan": -0.5, "feb": 0.0, "mar": 3.5, "apr": 8.5, "may": 13.5,
        "jun": 16.5, "jul": 18.5, "aug": 18.5, "sep": 14.0, "oct": 9.5,
        "nov": 4.5, "dec": 1.5
    },
}

def get_temperature(province: str, month: str) -> float:
    """
    Zwraca średnią temperaturę dla województwa i miesiąca.
    
    Args:
        province: nazwa województwa (małe litery)
        month: skrót miesiąca ('jan', 'feb', ..., 'dec')
    
    Returns:
        Średnia temperatura [°C]
    """
    province_clean = province.lower().strip()
    month_clean = month.lower().strip()
    
    if province_clean not in MONTHLY_TEMPERATURES:
        # Fallback: mazowieckie jako średnia
        return MONTHLY_TEMPERATURES["mazowieckie"].get(month_clean, 10.0)
    
    return MONTHLY_TEMPERATURES[province_clean].get(month_clean, 10.0)