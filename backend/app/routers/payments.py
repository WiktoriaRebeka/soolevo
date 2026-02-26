# backend/app/routers/payments.py
# ─────────────────────────────────────────────────────────────
#  Płatności — mBank PayNow
#  Docs: https://docs.paynow.pl/
# ─────────────────────────────────────────────────────────────

import os
import uuid
import hashlib
import hmac
import json
import base64
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_utils import get_current_user, get_current_user_optional
from app.models.db import User, Report, Payment

router = APIRouter(prefix="/api/payments", tags=["payments"])

# ── Konfiguracja PayNow ──────────────────────────────────────
PAYNOW_API_KEY = os.getenv("PAYNOW_API_KEY", "")
PAYNOW_SIGNATURE_KEY = os.getenv("PAYNOW_SIGNATURE_KEY", "")
PAYNOW_SANDBOX = os.getenv("PAYNOW_SANDBOX", "true").lower() == "true"
REPORT_PRICE_GROSZY = int(os.getenv("REPORT_PRICE_GROSZY", "4900"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://soolevo.com")

PAYNOW_BASE = (
    "https://api.sandbox.paynow.pl/v1" if PAYNOW_SANDBOX
    else "https://api.paynow.pl/v1"
)


def _paynow_signature(body_bytes: bytes) -> str:
    """Oblicza podpis HMAC-SHA256 dla PayNow."""
    return base64.b64encode(
        hmac.new(
            PAYNOW_SIGNATURE_KEY.encode(),
            body_bytes,
            hashlib.sha256
        ).digest()
    ).decode()


def _paynow_headers(body_bytes: bytes, idempotency_key: str) -> dict:
    return {
        "Api-Key": PAYNOW_API_KEY,
        "Signature": _paynow_signature(body_bytes),
        "Idempotency-Key": idempotency_key,
        "Content-Type": "application/json",
    }


# ── Schematy ──────────────────────────────────────────────────

class CreatePaymentRequest(BaseModel):
    report_token: str    # token raportu z bazy
    buyer_email: Optional[str] = None   # email kupującego (jeśli nie zalogowany)


class PaymentResponse(BaseModel):
    payment_id: str
    redirect_url: str
    report_token: str
    amount_pln: float


# ── Endpointy ─────────────────────────────────────────────────

@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    req: CreatePaymentRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Tworzy płatność PayNow dla raportu PDF."""

    # Pobierz raport z bazy
    report = db.query(Report).filter(Report.token == req.report_token).first()
    if not report:
        raise HTTPException(status_code=404, detail="Raport nie istnieje")
    if report.status == "paid" or report.status == "generated":
        raise HTTPException(status_code=409, detail="Raport już opłacony")

    # Email kupującego
    buyer_email = None
    if user:
        buyer_email = user.email
        if not report.user_id:
            report.user_id = user.id
            db.commit()
    elif req.buyer_email:
        buyer_email = req.buyer_email

    if not buyer_email:
        raise HTTPException(status_code=400, detail="Podaj adres email")

    # Przygotuj żądanie do PayNow
    idempotency_key = str(uuid.uuid4())
    payment_payload = {
        "amount": REPORT_PRICE_GROSZY,
        "currency": "PLN",
        "externalId": report.token,           # nasz identyfikator (raport token)
        "description": "Raport fotowoltaiczny PDF — soolevo.com",
        "buyer": {"email": buyer_email},
        "continueUrl": f"{FRONTEND_URL}/konto/raporty?token={report.token}",
    }

    body_bytes = json.dumps(payment_payload).encode()
    headers = _paynow_headers(body_bytes, idempotency_key)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYNOW_BASE}/payments",
            content=body_bytes,
            headers=headers,
            timeout=15,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Błąd PayNow: {resp.text}"
        )

    data = resp.json()
    paynow_id = data.get("paymentId")
    redirect_url = data.get("redirectUrl", "")

    # Zapisz płatność w bazie
    payment = Payment(
        user_id=user.id if user else None,
        report_id=report.id,
        paynow_payment_id=paynow_id,
        status="NEW",
        amount_groszy=REPORT_PRICE_GROSZY,
    )
    db.add(payment)
    db.commit()

    return PaymentResponse(
        payment_id=paynow_id,
        redirect_url=redirect_url,
        report_token=report.token,
        amount_pln=REPORT_PRICE_GROSZY / 100,
    )


@router.get("/status/{report_token}")
def payment_status(
    report_token: str,
    db: Session = Depends(get_db),
):
    """Sprawdza status płatności dla raportu."""
    report = db.query(Report).filter(Report.token == report_token).first()
    if not report:
        raise HTTPException(status_code=404, detail="Raport nie istnieje")

    return {
        "report_token": report_token,
        "status": report.status,
        "pdf_ready": report.status in ("paid", "generated") and report.pdf_path is not None,
    }
