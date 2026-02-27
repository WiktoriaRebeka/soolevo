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

    try:
        report = Report(
            user_id=user.id if user else None,
            input_json=req.input_json,
            status="generated",
        )
        db.add(report)
        db.commit()
        db.refresh(report)

    except Exception as e:
        db.rollback()
        logger.error(f"Błąd tworzenia raportu w DB: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Błąd bazy danych: {str(e)}. Upewnij się że tabele zostały utworzone (alembic upgrade head)."
        )

    # Generowanie PDF w trybie dev
    try:
        pdf_path = generate_mock_pdf(report.token)
        report.pdf_path = pdf_path
        db.commit()
    except Exception as e:
        logger.error(f"Błąd generowania PDF: {e}")
        # Nie przerywamy — raport już jest w DB, PDF można wygenerować później
        pdf_path = None

    return {
        "report_token": report.token,
        "status": report.status,
        "pdf_ready": pdf_path is not None,
        "pdf_path": pdf_path,
        "price_pln": 0.0,
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
    """Pobieranie PDF raportu."""
    report = db.query(Report).filter(Report.token == token).first()
    if not report:
        raise HTTPException(status_code=404, detail="Raport nie istnieje")

    if user and report.user_id and report.user_id != user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego raportu")

    if report.status not in ("paid", "generated") or not report.pdf_path:
        raise HTTPException(
            status_code=402,
            detail="Raport nie jest jeszcze opłacony lub nie jest gotowy"
        )

    if not os.path.exists(report.pdf_path):
        # Spróbuj wygenerować ponownie
        try:
            pdf_path = generate_mock_pdf(report.token)
            report.pdf_path = pdf_path
            db.commit()
        except Exception:
            raise HTTPException(status_code=404, detail="Plik PDF nie istnieje na serwerze")

    with open(report.pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="raport-pv-soolevo.pdf"',
            "Cache-Control": "no-store",
        }
    )