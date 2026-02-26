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
    """
    Tworzy rekord raportu w bazie (przed płatnością).
    Zwraca token raportu potrzebny do stworzenia płatności.
    """
    report = Report(
        user_id=user.id if user else None,
        input_json=req.input_json,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_token": report.token,
        "status": report.status,
        "price_pln": int(os.getenv("REPORT_PRICE_GROSZY", "4900")) / 100,
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
