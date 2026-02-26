# backend/app/data/sunlight.py

DAYS_IN_MONTH = {
    "jan": 31,
    "feb": 28,
    "mar": 31,
    "apr": 30,
    "may": 31,
    "jun": 30,
    "jul": 31,
    "aug": 31,
    "sep": 30,
    "oct": 31,
    "nov": 30,
    "dec": 31,
}

SUNLIGHT_DATA = {
    "dolnoslaskie": {
        "jan": 31.56, "feb": 45.75, "mar": 102.88, "apr": 163.5, "may": 159.84, "jun": 138.48,
        "jul": 173.27, "aug": 148.63, "sep": 108.76, "oct": 47.64, "nov": 27.93, "dec": 23.62,
        "annual": 1171.86
    },
    "kujawsko-pomorskie": {
        "jan": 18.48, "feb": 41.02, "mar": 93.78, "apr": 151.27, "may": 158.02, "jun": 151.0,
        "jul": 174.87, "aug": 147.17, "sep": 97.94, "oct": 43.63, "nov": 17.28, "dec": 15.19,
        "annual": 1119.55
    },
    "lubelskie": {
        "jan": 26.95, "feb": 45.0, "mar": 100.27, "apr": 163.76, "may": 151.66, "jun": 162.66,
        "jul": 174.77, "aug": 155.54, "sep": 103.8, "oct": 47.47, "nov": 25.31, "dec": 15.78,
        "annual": 1175.87
    },
    "lubuskie": {
        "jan": 25.27, "feb": 39.61, "mar": 98.84, "apr": 162.01, "may": 169.23, "jun": 157.34,
        "jul": 175.42, "aug": 141.28, "sep": 108.48, "oct": 46.6, "nov": 26.41, "dec": 20.41,
        "annual": 1170.1
    },
    "lodzkie": {
        "jan": 23.84, "feb": 40.25, "mar": 95.2, "apr": 158.75, "may": 149.52, "jun": 146.6,
        "jul": 180.07, "aug": 152.69, "sep": 104.22, "oct": 45.71, "nov": 22.44, "dec": 15.94,
        "annual": 1130.03
    },
    "malopolskie": {
        "jan": 33.72, "feb": 47.03, "mar": 99.55, "apr": 171.75, "may": 144.76, "jun": 138.51,
        "jul": 178.77, "aug": 160.75, "sep": 102.2, "oct": 53.36, "nov": 32.01, "dec": 21.56,
        "annual": 1183.97
    },
    "mazowieckie": {
        "jan": 22.03, "feb": 40.26, "mar": 93.11, "apr": 155.03, "may": 156.57, "jun": 158.39,
        "jul": 176.85, "aug": 151.89, "sep": 105.16, "oct": 42.83, "nov": 21.12, "dec": 14.74,
        "annual": 1137.99
    },
    "opolskie": {
        "jan": 30.21, "feb": 45.4, "mar": 100.61, "apr": 165.12, "may": 157.61, "jun": 142.53,
        "jul": 176.05, "aug": 153.94, "sep": 111.37, "oct": 50.63, "nov": 30.04, "dec": 21.66,
        "annual": 1145.57
    },
    "podkarpackie": {
        "jan": 34.56, "feb": 46.51, "mar": 99.6, "apr": 167.8, "may": 148.42, "jun": 140.98,
        "jul": 175.02, "aug": 166.13, "sep": 106.74, "oct": 50.0, "nov": 29.37, "dec": 21.17,
        "annual": 1186.3
    },
    "podlaskie": {
        "jan": 30.21, "feb": 45.4, "mar": 100.61, "apr": 165.12, "may": 157.61, "jun": 142.53,
        "jul": 176.05, "aug": 153.94, "sep": 111.37, "oct": 50.63, "nov": 30.04, "dec": 21.66,
        "annual": 1095.07
    },
    "pomorskie": {
        "jan": 16.62, "feb": 42.78, "mar": 88.78, "apr": 142.86, "may": 159.01, "jun": 168.85,
        "jul": 159.8, "aug": 150.57, "sep": 97.54, "oct": 41.34, "nov": 18.52, "dec": 11.15,
        "annual": 1097.42
    },
    "slaskie": {
        "jan": 32.0, "feb": 45.15, "mar": 100.13, "apr": 167.41, "may": 145.37, "jun": 137.7,
        "jul": 179.37, "aug": 157.14, "sep": 102.37, "oct": 49.88, "nov": 29.26, "dec": 20.77,
        "annual": 1088.25
    },
    "swietokrzyskie": {
        "jan": 28.0, "feb": 42.96, "mar": 103.78, "apr": 166.8, "may": 150.06, "jun": 149.76,
        "jul": 172.15, "aug": 153.97, "sep": 102.68, "oct": 50.95, "nov": 23.14, "dec": 18.69,
        "annual": 1103.84
    },
    "warminsko-mazurskie": {
        "jan": 15.24, "feb": 36.31, "mar": 89.76, "apr": 142.38, "may": 161.96, "jun": 167.64,
        "jul": 158.82, "aug": 149.46, "sep": 97.33, "oct": 44.0, "nov": 18.74, "dec": 11.49,
        "annual": 1133.89
    },
    "wielkopolskie": {
        "jan": 24.35, "feb": 38.39, "mar": 97.71, "apr": 161.98, "may": 164.34, "jun": 154.12,
        "jul": 173.45, "aug": 151.99, "sep": 100.14, "oct": 46.02, "nov": 21.27, "dec": 17.13,
        "annual": 1130.99
    },
    "zachodniopomorskie": {
        "jan": 19.15, "feb": 35.2, "mar": 88.78, "apr": 152.52, "may": 167.71, "jun": 169.33,
        "jul": 149.16, "aug": 146.22, "sep": 101.09, "oct": 44.44, "nov": 20.87, "dec": 13.23,
        "annual": 1147.4
    }
}

def get_monthly_sunlight(province: str) -> dict:
    """Zwraca dict z 12 wartościami kWh/kWp per miesiąc."""
    data = SUNLIGHT_DATA.get(province.lower())
    if not data:
        data = SUNLIGHT_DATA.get("mazowieckie")
    return {k: v for k, v in data.items() if k != "annual"}

def get_annual_total(province: str) -> float:
    """Zwraca sumę roczną kWh/kWp dla województwa."""
    data = SUNLIGHT_DATA.get(province.lower())
    if not data:
        data = SUNLIGHT_DATA.get("mazowieckie")
    return data.get("annual", 1100.0)
