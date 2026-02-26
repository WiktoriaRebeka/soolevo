# backend/app/schemas/inverter.py
from pydantic import BaseModel

class Inverter(BaseModel):
    id: str
    brand: str
    model_name: str
    power_ac_watts: int   # Moc wyjściowa AC
    max_input_voltage: int # Max napięcie (bezpieczeństwo)
    mppt_range_min: int    # Dolny zakres pracy
    mppt_range_max: int    # Górny zakres pracy
    number_of_mppt: int    # Ile rzędów paneli można podpiąć
    price: float