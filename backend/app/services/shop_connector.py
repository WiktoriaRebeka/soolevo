from app.schemas.panel import Panel

class ShopConnector:
    async def get_mock_panels(self):
        # To są nasze "Mock Data" - udajemy, że przyszły ze sklepu
        return [
            Panel(
                id="jinko-450", brand="Jinko", model_name="Tiger Neo",
                power_wp=450, width_m=1.13, height_m=1.72,
                price=450.0, efficiency=0.22, temp_coeff_voc=-0.25
            )
        ]