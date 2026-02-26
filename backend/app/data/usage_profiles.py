# backend/app/data/usage_profiles.py

PERSON_TYPES = {
    "at_home": {
        "label": "Osoba przebywająca w domu (Home Office / Opieka)",
        "weights": {
            "morning": 0.8,   # Śniadanie, kawa
            "day":     1.8,   # KLUCZ: Praca, gotowanie obiadu, pralka (zjada PV!)
            "evening": 1.4,   # Kolacja, TV, światło
            "night":   0.2,   # Sen
        },
    },
    "away": {
        "label": "Osoba poza domem (Praca / Szkoła)",
        "weights": {
            "morning": 1.2,   # Szybki pik przed wyjściem
            "day":     0.05,  # Dom pusty (tylko standby)
            "evening": 2.5,   # Kumulacja wszystkiego po powrocie
            "night":   0.2,
        },
    },
}

HOUSEHOLD_SIZE_MULTIPLIER = {
    1: 1.0,
    2: 1.2,
    3: 1.5,
    4: 1.8,
    5: 2.2,
}

WEEKEND_MULTIPLIER_DAY     = 1.25
WEEKEND_MULTIPLIER_EVENING = 1.25
