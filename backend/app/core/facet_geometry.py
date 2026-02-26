import math

def compute_facet_area_and_length(f):
    """
    Canonical geometry function.
    Zwraca słownik:
    - area: pole połaci [m2]
    - slope_length: długość połaci (skosu) [m]
    - offset_x: przesunięcie dla rombu [m] (w innych typach None)
    """
    rtype = f.roof_type
    use_real = getattr(f, "roof_mode", "building_length") == "real_roof_length"
    real_val = getattr(f, "real_roof_length", 0.0) or 0.0

    angle = getattr(f, "angle", None)

    # Dachy płaskie i naziemne nie mają kąta
    if rtype in ["flat", "ground"]:
        angle_rad = 0.0
        cos_angle = 1.0
    else:
        if angle is None or angle <= 0 or angle >= 89:
            raise ValueError("Roof angle must be between 1 and 88 degrees")
        angle_rad = math.radians(angle)
        cos_angle = math.cos(angle_rad)

    # 1) DACHY SKOŚNE (v4.2 - Poprawka rzutu budynku)
    if rtype in ["rectangular", "gable", "hip"]:
        width_val = f.width or 0.0
        length_val = f.length or 0.0

        if use_real:
            # Użytkownik podał wymiar skosu "z natury"
            slope_h = real_val
        else:
            # Użytkownik podał wymiar budynku (rzut). 
            # Zgodnie z Twoją logiką: dzielimy na pół i liczymy przeciwprostokątną.
            run = length_val / 2.0
            slope_h = run / cos_angle if run > 0 and cos_angle > 0 else 0.0

        area = width_val * slope_h
        return {
            "area": area,
            "slope_length": slope_h,
            "offset_x": None,
        }

    if rtype in ["flat", "ground"]:
        # Dla dachu płaskiego i gruntu wymiary są zawsze "z natury" (rzut = skos konstrukcji)
        return {
            "area": (f.width or 0.0) * (f.length or 0.0),
            "slope_length": f.length or 0.0,
            "offset_x": None,
        }

    # 2) DACH TRÓJKĄTNY
    if rtype == "triangle":
        base = f.triangle_base or 0.0
        if use_real:
            slope_h = real_val
        else:
            # Zgodnie z zasadą: rzut wysokości na planie to połowa wymiaru budynku
            h_rzut = (f.triangle_height or 0.0) / 2.0
            slope_h = h_rzut / cos_angle if h_rzut > 0 and cos_angle > 0 else 0.0

        area = 0.5 * base * slope_h if base > 0 and slope_h > 0 else 0.0
        return {"area": area, "slope_length": slope_h, "offset_x": None}

# 3) DACH TRAPEZOWY RÓWNORAMIENNY
    if rtype == "trapezoid":
        base_a = f.trapezoid_base_a or 0.0
        base_b = f.trapezoid_base_b or 0.0
        if use_real:
            slope_h = real_val
        else:
            # Rzut wysokości na planie to połowa wymiaru budynku
            h_rzut = (f.trapezoid_height or 0.0) / 2.0
            slope_h = h_rzut / cos_angle if h_rzut > 0 and cos_angle > 0 else 0.0

        area = 0.5 * (base_a + base_b) * slope_h
        return {
            "area": area,
            "slope_length": slope_h,
            "offset_x": None,
        }

    # 4) DACH TRAPEZOWY PROSTOKĄTNY (90 stopni z jednej strony)
    if rtype == "trapezoid_right":
        base_a = f.trapezoid_base_a or 0.0
        base_b = f.trapezoid_base_b or 0.0
        if use_real:
            slope_h = real_val
        else:
            # Rzut wysokości na planie to połowa wymiaru budynku
            h_rzut = (f.trapezoid_height or 0.0) / 2.0
            slope_h = h_rzut / cos_angle if h_rzut > 0 and cos_angle > 0 else 0.0

        area = 0.5 * (base_a + base_b) * slope_h
        return {
            "area": area,
            "slope_length": slope_h,
            "offset_x": 0.0, # Lewa krawędź pionowa
        }


    # 5) RÓWNOLEGŁOBOK (Rhombus)
    if rtype == "rhombus":
        a = f.rhombus_diagonal_1 or 0.0  # Podstawa (szerokość)
        side_b_input = getattr(f, "rhombus_side_b", 0.0) or 0.0
        
        if use_real:
            slope_h = real_val
            # W trybie "z natury" side_b jest już długością krawędzi na dachu
            side_b_slope = side_b_input
        else:
            # Rzut wysokości to połowa głębokości budynku
            h_plan = (f.rhombus_diagonal_2 or 0.0) / 2.0
            slope_h = h_plan / cos_angle if h_plan > 0 and cos_angle > 0 else 0.0
            # Rzut boku b również musi zostać przeliczony na skos dachu
            side_b_slope = side_b_input / cos_angle if side_b_input > 0 and cos_angle > 0 else 0.0

        area = a * slope_h
        
        # Obliczamy offset_x na płaszczyźnie dachu (Pitagoras na wymiarach skosu)
        if side_b_slope > 0 and slope_h > 0 and side_b_slope >= slope_h:
            offset_x = math.sqrt(side_b_slope**2 - slope_h**2)
        else:
            offset_x = 0.0

        return {
            "area": area,
            "slope_length": slope_h,
            "offset_x": offset_x,
        }

    # 5) DACH PŁASKI / NAZIEMNY
    if rtype in ["flat", "ground"]:
        w = f.width or 0.0
        l = f.length or 0.0
        area = w * l if w > 0 and l > 0 else 0.0
        return {
            "area": area,
            "slope_length": l,
            "offset_x": None,
        }

    return {
        "area": 0.0,
        "slope_length": 0.0,
        "offset_x": None,
    }