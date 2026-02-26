from fastapi import APIRouter, HTTPException, Response
import traceback
import warnings

from app.schemas.scenarios import ScenariosRequest, ScenariosResponse, RoofFacet
from app.schemas.report import ReportData, Warning
from app.core.engine import calculate_scenarios_engine
from app.core.roof_geometry import validate_roof_dimensions
from app.core.warnings_engine import WarningEngine
from app.data.energy_prices_tge import get_rcem_monthly
from app.core.finance import calculate_monthly_net_billing_value

router = APIRouter(prefix="/calculator", tags=["calculator"])


@router.post("/calculate/scenarios")
def calculate_scenarios(request: ScenariosRequest) -> ScenariosResponse:
    try:
        return calculate_scenarios_engine(request)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/report/data")
def get_report_data(request: ScenariosRequest) -> ReportData:
    try:
        from app.core.engine import _prepare_context_from_facet, _compute_annual_consumption
        from typing import List

        scenarios_response = calculate_scenarios_engine(request)

        first_facet_raw = request.facets[0]
        first_facet = RoofFacet(**first_facet_raw) if isinstance(first_facet_raw, dict) else first_facet_raw

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
            request=request
        )

        warnings_list: List[Warning] = []
        standard_scenario = next(
            (s for s in scenarios_response.scenarios if s.scenario_name == "standard"),
            scenarios_response.scenarios[0]
        )
        warnings_list = WarningEngine(context).generate_warnings(standard_scenario, context)

        return ReportData(
            input_request=request,
            highlighted_scenario_name="standard",
            all_scenarios_results={s.scenario_name: s.model_dump() for s in scenarios_response.scenarios},
            warnings_and_confirmations=warnings_list,
            input_data_summary={
                "annual_consumption_kwh": annual_consumption_kwh,
                "roof_area_m2": context.get("roof_area_m2"),
                "roof_slope_length_m": context.get("roof_slope_length_m"),
                "roof_offset_x": context.get("roof_offset_x"),
                "roof_type": first_facet.roof_type,
            }
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/report/pdf")
def generate_report_pdf(request: ScenariosRequest):
    from app.core.report_generator import ReportGenerator
    report_data = get_report_data(request)

    generator = ReportGenerator()
    pdf_bytes = generator.generate(report_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=\"raport-pv.pdf\""}
    )


@router.post("/calculate/net-billing")
def calculate_net_billing_endpoint(monthly_surplus_kwh: dict = None, year: int = 2025):
    try:
        if monthly_surplus_kwh is None:
            monthly_surplus_kwh = {}

        rcem_monthly = get_rcem_monthly(year)
        result = calculate_monthly_net_billing_value(
            monthly_surplus_kwh=monthly_surplus_kwh,
            rcem_monthly=rcem_monthly,
            year=year,
        )

        result["warning"] = "Ten endpoint używa uproszczonego modelu. Użyj /calculate/scenarios dla pełnej kalkulacji."
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))