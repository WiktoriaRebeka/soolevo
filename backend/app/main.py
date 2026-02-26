# backend/app/main.py
# ─────────────────────────────────────────────────────────────
#  SOOLEVO.COM — Główny plik FastAPI
#  Zachowuje wszystkie istniejące endpointy + nowe moduły
# ─────────────────────────────────────────────────────────────

import os
import warnings
import traceback
import json

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

# ── Istniejące moduły (bez zmian) ────────────────────────────
from app.schemas.scenarios import ScenariosRequest, ScenariosResponse, ScenarioResponseItem, RoofFacet
from app.schemas.report import ReportData, ReportRequest, Warning
from app.core.engine import calculate_scenarios_engine
from app.core.roof_geometry import validate_roof_dimensions
from app.core.warnings_engine import WarningEngine
from app.data.energy_prices_tge import get_rcem_monthly
from app.core.finance import calculate_monthly_net_billing_value

# ── Nowe moduły ───────────────────────────────────────────────
from app.routers import auth, payments, reports, batteries
from app.webhooks import paynow
from app.core.database import engine
from app.models.db import Base
from app.routers import calculator
app.include_router(calculator.router)
# ── Inicjalizacja bazy danych ────────────────────────────────
# W produkcji używamy Alembic — poniższe tylko do dev/pierwszego uruchomienia
# Base.metadata.create_all(bind=engine)

# ── Konfiguracja CORS ─────────────────────────────────────────
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
)
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_STR.split(",")]

app = FastAPI(
    title="Soolevo API",
    version="3.0.0",
    description="API kalkulatora PV, magazynów energii i płatności — soolevo.com",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rejestracja routerów ──────────────────────────────────────
app.include_router(auth.router)
app.include_router(payments.router)
app.include_router(reports.router)
app.include_router(batteries.router)
app.include_router(paynow.router)


# ── Health check ──────────────────────────────────────────────
@app.get("/health")
@app.get("/")
def health_check():
    return {"status": "ok", "version": "3.0.0", "service": "soolevo-api"}


# ── ISTNIEJĄCE ENDPOINTY (bez zmian) ─────────────────────────

@app.post("/calculate/scenarios")
def calculate_scenarios(request: ScenariosRequest) -> ScenariosResponse:
    print("=" * 80)
    print("🔵 OTRZYMANO REQUEST:")
    print(f"  bill: {request.bill}")
    print("=" * 80)

    try:
        result = calculate_scenarios_engine(request)
        print("✅ Obliczenia zakończone sukcesem")
        return result

    except Exception as e:
        print("❌ BŁĄD:", str(e))
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "type": type(e).__name__}
        )


@app.post("/report/data")
def get_report_data(request: ScenariosRequest) -> ReportData:
    try:
        from app.core.engine import _prepare_context_from_facet, _compute_annual_consumption
        from typing import List

        scenarios_response = calculate_scenarios_engine(request)

        first_facet_raw = request.facets[0]
        if isinstance(first_facet_raw, dict):
            first_facet = RoofFacet(**first_facet_raw)
        else:
            first_facet = first_facet_raw

        consumption_data = _compute_annual_consumption(request)
        annual_consumption_kwh = consumption_data["annual_consumption_kwh"]

        context = _prepare_context_from_facet(
            facet=first_facet,
            annual_consumption_kwh=annual_consumption_kwh,
            province=request.province,
            tariff_type=request.tariff.upper().replace("-", ""),
            operator=request.operator,
            household_size=request.household_size,
            people_home_weekday=getattr(request, "people_home_weekday", 1),
            request=request,
        )

        standard_scenario = next(
            (s for s in scenarios_response.scenarios if s.scenario_name == "standard"),
            scenarios_response.scenarios[0],
        )
        warnings_list = WarningEngine(context).generate_warnings(standard_scenario, context)

        return ReportData(
            input_request=request,
            highlighted_scenario_name="standard",
            all_scenarios_results={
                s.scenario_name: s.model_dump()
                for s in scenarios_response.scenarios
            },
            warnings_and_confirmations=warnings_list,
            input_data_summary={
                "annual_consumption_kwh": annual_consumption_kwh,
                "roof_area_m2": context.get("roof_area_m2"),
                "roof_slope_length_m": context.get("roof_slope_length_m"),
                "roof_offset_x": context.get("roof_offset_x"),
                "roof_type": first_facet.roof_type,
            },
        )

    except Exception as e:
        print("❌ BŁĄD W GET_REPORT_DATA:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=400, detail={"error": str(e)})


@app.post("/report/pdf")
def generate_report_pdf_free(request: ScenariosRequest):
    """
    UWAGA: Ten endpoint generuje PDF bezpłatnie (stary flow).
    W nowym flow: użyj /api/reports/create → /api/payments/create → webhook → /api/reports/download/{token}
    Zachowany dla kompatybilności wstecznej / testów.
    """
    from app.core.report_generator import ReportGenerator
    report_data = get_report_data(request)
    generator = ReportGenerator()
    pdf_bytes = generator.generate(report_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=\"raport-pv.pdf\""},
    )
