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
from sqlalchemy import text

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
    """
    Generuje prosty PDF w trybie deweloperskim.
    Zwraca ścieżkę do wygenerowanego pliku.
    """
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
        # reportlab nie zainstalowany — zapisz placeholder
        os.makedirs(PDF_REPORTS_DIR, exist_ok=True)
        pdf_path = os.path.join(PDF_REPORTS_DIR, f"{report_token}.pdf")
        with open(pdf_path, "wb") as f:
            # Minimalny prawidłowy PDF (1-stronicowy placeholder)
            f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
                    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
                    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
                    b"xref\n0 4\n0000000000 65535 f\n"
                    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF")
        return pdf_path


# ── Schematy ──────────────────────────────────────────────────

class CreateReportRequest(BaseModel):
    input_json: dict    # pełny obiekt ScenariosRequest z frontendu


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
    # Upewnij się że tabele istnieją (dev bez Alembic)
    ensure_tables_exist()

        # TRYB DEV — BEZ BAZY DANYCH
    # Generujemy token i PDF bez zapisu do DB
    from app.core.report_generator import ReportGenerator
    from app.schemas.report import ReportData

    generator = ReportGenerator()

    from app.core.engine import calculate_scenarios_engine
    from app.core.report_generator import ReportGenerator
    from app.schemas.report import ReportData
    import uuid

    # 1. Uruchamiamy kalkulator
    from app.schemas.scenarios import ScenariosRequest

    scenarios_request = ScenariosRequest(**req.input_json)
    results = calculate_scenarios_engine(scenarios_request)

    # 2. Tworzymy obiekt ReportData

    report_data = ReportData(
        input_request=req.input_json,
        input_data_summary=results.input_data_summary,
        all_scenarios_results={
            s.scenario_name: s.model_dump()
            for s in results.scenarios
        },
        warnings_and_confirmations=results.warnings or []
    )

    # 3. Generujemy PDF
    generator = ReportGenerator()
    pdf_bytes = generator.generate(report_data)

    # 4. Zapisujemy PDF
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
    """Lista raportów zalogowanego użytkownika."""
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


        # TRYB DEV — BEZ BAZY DANYCH
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