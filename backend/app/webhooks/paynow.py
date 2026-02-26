# backend/app/webhooks/paynow.py
# ─────────────────────────────────────────────────────────────
#  mBank PayNow — obsługa webhooków
#  PayNow wysyła notyfikację po każdej zmianie statusu płatności
#  Docs: https://docs.paynow.pl/#notifications
# ─────────────────────────────────────────────────────────────

import os
import hmac
import hashlib
import base64
import json
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db import Payment, Report

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

PAYNOW_SIGNATURE_KEY = os.getenv("PAYNOW_SIGNATURE_KEY", "")
PDF_REPORTS_DIR = os.getenv("PDF_REPORTS_DIR", "/app/reports")


def _verify_signature(body_bytes: bytes, received_sig: str) -> bool:
    """Weryfikuje podpis HMAC-SHA256 od PayNow."""
    expected = base64.b64encode(
        hmac.new(
            PAYNOW_SIGNATURE_KEY.encode(),
            body_bytes,
            hashlib.sha256
        ).digest()
    ).decode()
    return hmac.compare_digest(expected, received_sig)


@router.post("/paynow")
async def paynow_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook od mBank PayNow.
    PayNow wysyła POST z nagłówkiem Signature i JSON body.
    Musimy odpowiedzieć 200 OK, inaczej PayNow będzie ponawiać.
    """
    body_bytes = await request.body()
    received_sig = request.headers.get("Signature", "")

    # 1. Weryfikacja podpisu
    if PAYNOW_SIGNATURE_KEY and not _verify_signature(body_bytes, received_sig):
        raise HTTPException(status_code=401, detail="Nieprawidłowy podpis")

    # 2. Parsuj payload
    try:
        data = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowy JSON")

    paynow_payment_id = data.get("paymentId")
    status = data.get("status")           # CONFIRMED | PENDING | ERROR | EXPIRED | DECLINED
    external_id = data.get("externalId")  # nasz report.token

    if not paynow_payment_id or not status:
        return {"ok": True}  # PayNow czasem wysyła puste notyfikacje

    # 3. Znajdź płatność
    payment = db.query(Payment).filter(
        Payment.paynow_payment_id == paynow_payment_id
    ).first()

    if not payment:
        # Może raport był jeszcze nie zapisany — spróbuj przez external_id
        if external_id:
            report = db.query(Report).filter(Report.token == external_id).first()
            if report:
                payment = db.query(Payment).filter(Payment.report_id == report.id).first()

    if not payment:
        # Brak płatności — loguj ale odpowiedz 200 (nie ponawia)
        print(f"⚠️ PayNow webhook: płatność {paynow_payment_id} nie znaleziona")
        return {"ok": True}

    # 4. Aktualizuj status płatności
    payment.status = status
    if status == "CONFIRMED":
        payment.confirmed_at = datetime.utcnow()

    # 5. Jeśli CONFIRMED → generuj PDF
    report = payment.report
    if status == "CONFIRMED" and report and report.status not in ("generated",):
        report.status = "paid"
        report.paid_at = datetime.utcnow()
        db.commit()

        # Generuj PDF w tle (synchronicznie na razie)
        try:
            _generate_pdf_for_report(report, db)
        except Exception as e:
            print(f"❌ Błąd generowania PDF dla raportu {report.token}: {e}")
            report.status = "paid"  # zapłacone, ale PDF nieudany — retry możliwy
    else:
        db.commit()

    return {"ok": True}


def _generate_pdf_for_report(report: Report, db: Session):
    """Generuje PDF i zapisuje ścieżkę w bazie."""
    import os
    from app.schemas.scenarios import ScenariosRequest
    from app.core.report_generator import ReportGenerator

    # Odtwórz request z zapisanego JSON
    input_data = report.input_json
    scenarios_request = ScenariosRequest(**input_data)

    # Pobierz dane raportu (ta sama logika co w /report/pdf)
    from app.main import get_report_data  # import lokalny żeby uniknąć circular
    report_data = get_report_data(scenarios_request)

    # Generuj PDF
    generator = ReportGenerator()
    pdf_bytes = generator.generate(report_data)

    # Zapisz plik
    os.makedirs(PDF_REPORTS_DIR, exist_ok=True)
    pdf_filename = f"raport_{report.token}.pdf"
    pdf_path = os.path.join(PDF_REPORTS_DIR, pdf_filename)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Zaktualizuj bazę
    report.pdf_path = pdf_path
    report.status = "generated"
    db.commit()

    print(f"✅ PDF wygenerowany: {pdf_path}")
