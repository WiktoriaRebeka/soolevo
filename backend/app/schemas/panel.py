# backend/app/schemas/panel.py
from pydantic import BaseModel

class Panel(BaseModel):
    id: str
    brand: str
    model_name: str
    power_wp: int        # Moc (np. 450)
    width_m: float       # Szerokość (np. 1.13)
    height_m: float      # Wysokość (np. 1.72)
    price: float     # Cena netto
    efficiency: float    # Sprawność (np. 0.21)
    temp_coeff_voc: float # Współczynnik temp. (ważne dla EPIC 4!)