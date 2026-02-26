# backend/app/routers/reports.py
# ─────────────────────────────────────────────────────────────
#  Raporty — tworzenie, lista, pobieranie PDF
# ─────────────────────────────────────────────────────────────

import os
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_utils import get_current_user, get_current_user_optional
from app.models.db import Report, Payment, User

router = APIRouter(prefix="/api/reports", tags=["reports"])

PDF_REPORTS_DIR = os.getenv("PDF_REPORTS_DIR", "/app/reports")

def generate_mock_pdf(report_token: str) -> str:
    """
    Generuje prosty PDF w trybie deweloperskim.
    Zwraca ścieżkę do wygenerowanego pliku.
    """
    from reportlab.pdfgen import canvas

    # Upewnij się, że katalog istnieje
    os.makedirs(PDF_REPORTS_DIR, exist_ok=True)

    pdf_path = os.path.join(PDF_REPORTS_DIR, f"{report_token}.pdf")

    c = canvas.Canvas(pdf_path)
    c.setFont("Helvetica", 16)
    c.drawString(100, 750, "Raport PV — tryb deweloperski")
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Token raportu: {report_token}")
    c.drawString(100, 700, "Ten PDF został wygenerowany automatycznie.")
    c.save()

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
@router.post("/create")
def create_report(
    req: CreateReportRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    report = Report(
        user_id=user.id if user else None,
        input_json=req.input_json,
        status="generated",   # <-- od razu gotowy
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Generowanie PDF w trybie dev
    pdf_path = generate_mock_pdf(report.token)
    report.pdf_path = pdf_path
    db.commit()

    return {
        "report_token": report.token,
        "status": report.status,
        "pdf_ready": True,
        "pdf_path": pdf_path,
        "price_pln": 0.0,  # w dev raport jest darmowy
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
    """Pobieranie PDF raportu — tylko po opłaceniu."""
    report = db.query(Report).filter(Report.token == token).first()
    if not report:
        raise HTTPException(status_code=404, detail="Raport nie istnieje")

    # Sprawdź uprawnienia — albo właściciel, albo token wystarczy (jednorazowy link)
    if user and report.user_id and report.user_id != user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego raportu")

    if report.status not in ("paid", "generated") or not report.pdf_path:
        raise HTTPException(
            status_code=402,
            detail="Raport nie jest jeszcze opłacony lub nie jest gotowy"
        )

    if not os.path.exists(report.pdf_path):
        raise HTTPException(status_code=404, detail="Plik PDF nie istnieje na serwerze")

    with open(report.pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="raport-pv-soolevo.pdf"',
            "Cache-Control": "no-store",
        }
    )
