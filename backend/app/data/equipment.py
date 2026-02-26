# backend/app/data/equipment.py
"""
Dane sprzętowe - panele, falowniki, baterie.
Minimalny zestaw danych dla refactoringu.
"""

# =============================================================================
# STRUKTURA DANYCH
# =============================================================================

EQUIPMENT_COSTS = {
    "panels": {
        # PREMIUM
        "Longi LR5-72HIH-550M": {
            "power_wp": 550,
            "efficiency": 0.215,
            "unit_price_pln": 450,
            "warranty_years": 25,
            "tier": "premium",
        },
        "JA Solar JAM72S30-550/MR": {
            "power_wp": 550,
            "efficiency": 0.213,
            "unit_price_pln": 430,
            "warranty_years": 25,
            "tier": "premium",
        },
        
        # STANDARD
        "Trina Solar TSM-DE19-550W": {
            "power_wp": 550,
            "efficiency": 0.211,
            "unit_price_pln": 380,
            "warranty_years": 25,
            "tier": "standard",
        },
        "Canadian Solar HiKu6-CS6R-550MS": {
            "power_wp": 550,
            "efficiency": 0.210,
            "unit_price_pln": 370,
            "warranty_years": 25,
            "tier": "standard",
        },
        
        # ECONOMY
        "Risen RSM144-6-550M": {
            "power_wp": 550,
            "efficiency": 0.208,
            "unit_price_pln": 320,
            "warranty_years": 25,
            "tier": "economy",
        },
        "Jinko Solar JKM550M-72HL4-V": {
            "power_wp": 550,
            "efficiency": 0.207,
            "unit_price_pln": 310,
            "warranty_years": 25,
            "tier": "economy",
        },
    },
    
    "inverters": {
        # PREMIUM (Fronius)
        "Fronius Primo GEN24 3.0 Plus": {
            "power_kw": 3.0,
            "efficiency": 0.98,
            "price_pln": 7500,
            "warranty_years": 10,
            "tier": "premium",
        },
        "Fronius Primo GEN24 5.0 Plus": {
            "power_kw": 5.0,
            "efficiency": 0.98,
            "price_pln": 9500,
            "warranty_years": 10,
            "tier": "premium",
        },
        "Fronius Primo GEN24 6.0 Plus": {
            "power_kw": 6.0,
            "efficiency": 0.98,
            "price_pln": 10500,
            "warranty_years": 10,
            "tier": "premium",
        },
        "Fronius Primo GEN24 8.0 Plus": {
            "power_kw": 8.0,
            "efficiency": 0.98,
            "price_pln": 12000,
            "warranty_years": 10,
            "tier": "premium",
        },
        "Fronius Primo GEN24 10.0 Plus": {
            "power_kw": 10.0,
            "efficiency": 0.98,
            "price_pln": 14000,
            "warranty_years": 10,
            "tier": "premium",
        },
        
        # STANDARD (SolarEdge, Huawei)
        "SolarEdge SE3K-RWS": {
            "power_kw": 3.0,
            "efficiency": 0.97,
            "price_pln": 6500,
            "warranty_years": 12,
            "tier": "standard",
        },
        "SolarEdge SE5K-RWS": {
            "power_kw": 5.0,
            "efficiency": 0.97,
            "price_pln": 8000,
            "warranty_years": 12,
            "tier": "standard",
        },
        "Huawei SUN2000-6KTL-L1": {
            "power_kw": 6.0,
            "efficiency": 0.985,
            "price_pln": 8500,
            "warranty_years": 10,
            "tier": "standard",
        },
        "Huawei SUN2000-8KTL-M1": {
            "power_kw": 8.0,
            "efficiency": 0.985,
            "price_pln": 9500,
            "warranty_years": 10,
            "tier": "standard",
        },
        "Huawei SUN2000-10KTL-M1": {
            "power_kw": 10.0,
            "efficiency": 0.985,
            "price_pln": 11000,
            "warranty_years": 10,
            "tier": "standard",
        },
        
        # ECONOMY (Growatt, Sofar)
        "Growatt MIN 3000TL-XE": {
            "power_kw": 3.0,
            "efficiency": 0.97,
            "price_pln": 4500,
            "warranty_years": 10,
            "tier": "economy",
        },
        "Growatt MIN 5000TL-XE": {
            "power_kw": 5.0,
            "efficiency": 0.975,
            "price_pln": 5500,
            "warranty_years": 10,
            "tier": "economy",
        },
        "Sofar Solar 6KTLM-G3": {
            "power_kw": 6.0,
            "efficiency": 0.975,
            "price_pln": 6000,
            "warranty_years": 10,
            "tier": "economy",
        },
        "Sofar Solar 8.8KTLM-G3": {
            "power_kw": 8.8,
            "efficiency": 0.98,
            "price_pln": 7000,
            "warranty_years": 10,
            "tier": "economy",
        },
        "Growatt MOD 10KTL3-XH": {
            "power_kw": 10.0,
            "efficiency": 0.98,
            "price_pln": 8000,
            "warranty_years": 10,
            "tier": "economy",
        },
    },
    
    "batteries": {
        # PREMIUM
        "Tesla Powerwall 2": {
            "capacity_kwh": 13.5,
            "usable_capacity_kwh": 13.5,
            "power_kw": 5.0,
            "efficiency": 0.90,
            "price_pln": 51000,
            "warranty_years": 10,
            "tier": "premium",
        },
        "BYD Battery-Box Premium HVS 10.2": {
            "capacity_kwh": 10.2,
            "usable_capacity_kwh": 9.7,
            "power_kw": 5.0,
            "efficiency": 0.95,
            "price_pln": 38000,
            "warranty_years": 10,
            "tier": "premium",
        },
        
        # STANDARD
        "Pylontech Force H2 10.65 kWh": {
            "capacity_kwh": 10.65,
            "usable_capacity_kwh": 10.1,
            "power_kw": 5.0,
            "efficiency": 0.95,
            "price_pln": 35000,
            "warranty_years": 10,
            "tier": "standard",
        },
        "Pylontech US5000 (x2)": {
            "capacity_kwh": 9.6,
            "usable_capacity_kwh": 9.1,
            "power_kw": 4.0,
            "efficiency": 0.95,
            "price_pln": 28000,
            "warranty_years": 10,
            "tier": "standard",
        },
        
        # ECONOMY
        "Generic LiFePO4 10 kWh": {
            "capacity_kwh": 10.0,
            "usable_capacity_kwh": 9.5,
            "power_kw": 5.0,
            "efficiency": 0.92,
            "price_pln": 25000,
            "warranty_years": 10,
            "tier": "economy",
        },
    },
}


# =============================================================================
# FUNKCJE POMOCNICZE
# =============================================================================

def get_panel_by_tier(tier: str = "standard"):
    """Zwraca domyślny panel dla danego tier."""
    defaults = {
        "premium": "Longi LR5-72HIH-550M",
        "standard": "Trina Solar TSM-DE19-550W",
        "economy": "Risen RSM144-6-550M",
    }
    panel_model = defaults.get(tier, defaults["standard"])
    return panel_model, EQUIPMENT_COSTS["panels"][panel_model]


def get_inverter_by_power(power_kwp: float, tier: str = "standard"):
    """Zwraca odpowiedni falownik dla mocy systemu."""
    inverters_by_tier = {
        key: data for key, data in EQUIPMENT_COSTS["inverters"].items()
        if data["tier"] == tier
    }
    
# Szukamy falownika, który obsłuży moc DC (z dopuszczalnym przewymiarowaniem 120%)
    suitable = [
        (model, data) for model, data in inverters_by_tier.items()
        if data["power_kw"] * 1.25 >= power_kwp
    ]
    
    if not suitable:
        # Jeśli system jest za duży, bierzemy najmocniejszy dostępny w danym tierze
        suitable = sorted(inverters_by_tier.items(), key=lambda x: x[1]["power_kw"], reverse=True)
    
    if not suitable:
        suitable = list(inverters_by_tier.items())
    
    suitable.sort(key=lambda x: x[1]["power_kw"])
    
    if suitable:
        return suitable[0]
    
    return list(EQUIPMENT_COSTS["inverters"].items())[0]


def get_battery_by_capacity(capacity_kwh: float, tier: str = "standard"):
    """Zwraca odpowiednią baterię dla pojemności."""
    batteries_by_tier = {
        key: data for key, data in EQUIPMENT_COSTS["batteries"].items()
        if data["tier"] == tier
    }
    
    if not batteries_by_tier:
        batteries_by_tier = EQUIPMENT_COSTS["batteries"]
    
    suitable = [
        (model, data) for model, data in batteries_by_tier.items()
        if data["capacity_kwh"] >= capacity_kwh * 0.8
    ]
    
    if not suitable:
        suitable = list(batteries_by_tier.items())
    
    suitable.sort(key=lambda x: x[1]["capacity_kwh"])
    
    if suitable:
        return suitable[0]
    
    return list(batteries_by_tier.items())[0]
