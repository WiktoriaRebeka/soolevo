# backend/app/data/physics_constants.py

# Wydajność w zależności od kąta nachylenia
SLOPE_EFFICIENCY = {
    20: 0.95, 25: 0.97, 30: 1.00, 35: 0.99, 40: 0.97,
    45: 0.94, 50: 0.90, 55: 0.85, 60: 0.80, 65: 0.74,
    70: 0.68, 75: 0.61, 80: 0.54
}

# Wydajność w zależności od kierunku świata
DIRECTION_EFFICIENCY = {
    "east": 0.80,
    "south_east": 0.90,
    "south": 1.00,
    "south_west": 0.90,
    "west": 0.80
}

# Stare straty systemowe (pozostają dla kompatybilności)
SYSTEM_LOSS_FACTOR = 0.83

# NOWY — używany w nowym modelu produkcji PV
SYSTEM_LOSS_FACTOR_BASE = 0.92
# Straty stałe BEZ temperatury i IAM:
# - kable DC ~1.5%
# - kable AC ~0.5%
# - mismatch ~2%
# - zabrudzenie ~2%
# - sprawność falownika ~3%
# - inne ~1%
# SUMA ≈ 8% → 1 - 0.08 = 0.92

# Miesięczne współczynniki IAM dla instalacji S/30° na 52°N
# Źródło: symulacja PVSyst Warszawa, szkło standardowe mono-Si
IAM_MONTHLY_S30 = {
    "jan": 0.96, "feb": 0.97, "mar": 0.98, "apr": 0.99,
    "may": 0.99, "jun": 0.99, "jul": 0.99, "aug": 0.99,
    "sep": 0.98, "oct": 0.97, "nov": 0.96, "dec": 0.95,
}

# Modyfikator IAM zależny od orientacji (delta od optymalnego S)
IAM_DIRECTION_MODIFIER = {
    "S": 1.00, "SE": 0.99, "SW": 0.99,
    "E": 0.97, "W": 0.97,
    "NE": 0.94, "NW": 0.94, "N": 0.90,
}