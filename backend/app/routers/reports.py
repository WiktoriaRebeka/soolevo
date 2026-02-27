# backend/app/routers/reports.py
# ─────────────────────────────────────────────────────────────
#  Raporty — tworzenie, lista, pobieranie PDF
# ─────────────────────────────────────────────────────────────

import os
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, engine
from app.core.auth_utils import get_current_user, get_current_user_optional
from app.models.db import Report, Payment, User, Base

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

PDF_REPORTS_DIR = os.getenv("PDF_REPORTS_DIR", "/app/reports")


def ensure_tables_exist():
    """Tworzy tabele jeśli nie istnieją — bezpieczne dla dev bez migracji."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabele DB zweryfikowane / utworzone")
    except Exception as e:
        logger.error(f"Błąd tworzenia tabel: {e}")


def generate_mock_pdf(report_token: str) -> str:
    """Generuje prosty PDF w trybie deweloperskim."""
    try:
        from reportlab.pdfgen import canvas as rl_canvas

        os.makedirs(PDF_REPORTS_DIR, exist_ok=True)
        pdf_path = os.path.join(PDF_REPORTS_DIR, f"{report_token}.pdf")

        c = rl_canvas.Canvas(pdf_path)
        c.setFont("Helvetica", 16)
        c.drawString(100, 750, "Raport PV — tryb deweloperski")
        c.setFont("Helvetica", 12)
        c.drawString(100, 720, f"Token raportu: {report_token}")
        c.drawString(100, 700, "Ten PDF został wygenerowany automatycznie.")
        c.save()

        return pdf_path

    except ImportError:
        os.makedirs(PDF_REPORTS_DIR, exist_ok=True)
        pdf_path = os.path.join(PDF_REPORTS_DIR, f"{report_token}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(
                b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
                b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
                b"xref\n0 4\n0000000000 65535 f\n"
                b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
            )
        return pdf_path


# ── Schematy ──────────────────────────────────────────────────

class CreateReportRequest(BaseModel):
    input_json: dict


class ReportSummary(BaseModel):
    token: str
    status: str
    created_at: str
    paid_at: Optional[str]
    pdf_ready: bool
    amount_pln: Optional[float]


# ── Endpointy ─────────────────────────────────────────────────

@router.post("/create")
def create_report(
    req: CreateReportRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    ensure_tables_exist()

    # Importy lokalne
    from app.core.engine import (
        calculate_scenarios_engine,
        _prepare_context_from_facet,
        _compute_annual_consumption
    )
    from app.schemas.scenarios import ScenariosRequest, RoofFacet
    from app.core.report_generator import ReportGenerator
    from app.schemas.report import ReportData
    import uuid

    # 1. Zamieniamy dict → ScenariosRequest
    scenarios_request = ScenariosRequest(**req.input_json)

    # 2. Uruchamiamy kalkulator
    results = calculate_scenarios_engine(scenarios_request)

    # 3. Przygotowujemy dane wejściowe (tak samo jak w /report/data)
    first_facet_raw = scenarios_request.facets[0]
    first_facet = RoofFacet(**first_facet_raw) if isinstance(first_facet_raw, dict) else first_facet_raw

    consumption_data = _compute_annual_consumption(scenarios_request)
    annual_consumption_kwh = consumption_data["annual_consumption_kwh"]

    context = _prepare_context_from_facet(
        facet=first_facet,
        annual_consumption_kwh=annual_consumption_kwh,
        province=scenarios_request.province,
        tariff_type=scenarios_request.tariff.upper().replace("-", ""),
        operator=scenarios_request.operator,
        household_size=scenarios_request.household_size,
        people_home_weekday=getattr(scenarios_request, "people_home_weekday", 1),
        request=scenarios_request,
    )

    input_data_summary = {
        "annual_consumption_kwh": annual_consumption_kwh,
        "roof_area_m2": context.get("roof_area_m2"),
        "roof_slope_length_m": context.get("roof_slope_length_m"),
        "roof_offset_x": context.get("roof_offset_x"),
        "roof_type": first_facet.roof_type,
    }

    # 4. Budujemy ReportData
    report_data = ReportData(
        input_request=scenarios_request,
        input_data_summary=input_data_summary,
        all_scenarios_results={
            s.scenario_name: s.model_dump()
            for s in results.scenarios
        },
        warnings_and_confirmations=results.warnings or []
    )

    # 5. Generujemy PDF
    generator = ReportGenerator()
    pdf_bytes = generator.generate(report_data)

    # 6. Zapisujemy PDF
    token = str(uuid.uuid4())
    os.makedirs(PDF_REPORTS_DIR, exist_ok=True)
    pdf_path = os.path.join(PDF_REPORTS_DIR, f"{token}.pdf")

    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    return {
        "report_token": token,
        "pdf_ready": True
    }


@router.get("/my", response_model=List[ReportSummary])
def my_reports(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reports = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )

    result = []
    for r in reports:
        payment = r.payment
        result.append(ReportSummary(
            token=r.token,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else "",
            paid_at=r.paid_at.isoformat() if r.paid_at else None,
            pdf_ready=r.status in ("paid", "generated") and r.pdf_path is not None,
            amount_pln=payment.amount_groszy / 100 if payment else None,
        ))
    return result


@router.get("/download/{token}")
def download_pdf(
    token: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    pdf_path = os.path.join(PDF_REPORTS_DIR, f"{token}.pdf")

    if not os.path.exists(pdf_path):
        try:
            pdf_path = generate_mock_pdf(token)
        except Exception:
            raise HTTPException(status_code=404, detail="Plik PDF nie istnieje")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="raport-pv-soolevo.pdf"',
            "Cache-Control": "no-store",
        }
    )