# backend/app/routers/reports.py
# ─────────────────────────────────────────────────────────────
#  Raporty — tworzenie (płatny flow), lista, pobieranie PDF
#
#  POPRAWKI:
#  1. /create — przyjmuje teraz bezpośrednio ScenariosRequest (nie owinięty
#     w input_json: dict), bo ReportPaywall.jsx wysyła surowy payload.
#     Jeśli ktoś NADAL wysyła {input_json: {...}}, też obsługujemy.
#  2. Logika budowania ReportData przeniesiona 1:1 z calculator.py get_report_data.
#  3. highlighted_scenario_name dodane do ReportData.
# ─────────────────────────────────────────────────────────────

import os
import logging
import uuid
import traceback
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


# ── Upewnia się, że tabele DB istnieją ───────────────────────────────────────
def ensure_tables_exist():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabele DB zweryfikowane / utworzone")
    except Exception as e:
        logger.error(f"Błąd tworzenia tabel: {e}")


# ── Helper: generuje PDF z ScenariosRequest ───────────────────────────────────
def _build_report_data_and_pdf(scenarios_request):
    """
    Identyczna logika co calculator.py:get_report_data + ReportGenerator.generate().
    Centralny helper — używany zarówno przez /create jak i przez webhook.
    """
    from app.schemas.scenarios import ScenariosRequest, RoofFacet
    from app.schemas.report import ReportData
    from app.core.engine import (
        calculate_scenarios_engine,
        _prepare_context_from_facet,
        _compute_annual_consumption,
    )
    from app.core.warnings_engine import WarningEngine
    from app.core.report_generator import ReportGenerator

    # 1. Oblicz scenariusze
    results = calculate_scenarios_engine(scenarios_request)

    # 2. Wyodrębnij pierwszy facet
    first_facet_raw = scenarios_request.facets[0]
    first_facet = (
        RoofFacet(**first_facet_raw)
        if isinstance(first_facet_raw, dict)
        else first_facet_raw
    )

    # 3. Zużycie roczne
    consumption_data = _compute_annual_consumption(scenarios_request)
    annual_consumption_kwh = consumption_data["annual_consumption_kwh"]

    # 4. Kontekst
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

    # 5. Podsumowanie danych wejściowych
    input_data_summary = {
        "annual_consumption_kwh": annual_consumption_kwh,
        "roof_area_m2":           context.get("roof_area_m2"),
        "roof_slope_length_m":    context.get("roof_slope_length_m"),
        "roof_offset_x":          context.get("roof_offset_x"),
        "roof_type":              first_facet.roof_type,
    }

    # 6. Scenariusz standard + warnings
    standard_scenario = next(
        (s for s in results.scenarios if s.scenario_name == "standard"),
        results.scenarios[0],
    )
    warnings_list = WarningEngine(context).generate_warnings(standard_scenario, context)

    # 7. Zbuduj ReportData
    report_data = ReportData(
        input_request=scenarios_request,
        highlighted_scenario_name="standard",
        input_data_summary=input_data_summary,
        all_scenarios_results={
            s.scenario_name: s.model_dump()
            for s in results.scenarios
        },
        warnings_and_confirmations=warnings_list,
    )

    # 8. Wygeneruj PDF
    generator = ReportGenerator()
    pdf_bytes = generator.generate(report_data)

    return pdf_bytes


# ── Mock PDF (fallback gdy WeasyPrint niedostępny) ────────────────────────────
def _generate_mock_pdf(report_token: str) -> str:
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


# ── Modele Pydantic ───────────────────────────────────────────────────────────

class CreateReportRequest(BaseModel):
    """
    POPRAWKA: Akceptujemy DWA formaty:
    1. Surowy payload ScenariosRequest (jak wysyła ReportPaywall.jsx)
    2. Owinięty w input_json: dict (stary format)

    Używamy model_extra="allow" żeby móc przyjąć pola ScenariosRequest bezpośrednio.
    """
    input_json: Optional[dict] = None

    model_config = {"extra": "allow"}


class ReportSummary(BaseModel):
    token: str
    status: str
    created_at: str
    paid_at: Optional[str]
    pdf_ready: bool
    amount_pln: Optional[float]


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.post("/create")
def create_report(
    req: CreateReportRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Tworzy rekord raportu w bazie i generuje PDF.
    Używany przez flow płatności: ReportPaywall → /api/reports/create → /api/payments/create.

    Akceptuje payload w dwóch formatach:
    - {input_json: {...ScenariosRequest fields...}}  (stary format)
    - {...ScenariosRequest fields...}                (nowy format — bezpośrednio z frontendu)
    """
    ensure_tables_exist()

    from app.schemas.scenarios import ScenariosRequest

    try:
        # ── Wyodrębnij dane wejściowe ────────────────────────────────────────
        # Obsługujemy oba formaty: owinięty (input_json) i bezpośredni
        if req.input_json:
            raw_input = req.input_json
        else:
            # Bezpośredni format — zbierz wszystkie extra pola
            raw_input = req.model_extra or {}
            # Usuń None input_json żeby nie kolidowało
            raw_input.pop("input_json", None)

        if not raw_input:
            raise HTTPException(
                status_code=400,
                detail="Brak danych wejściowych. Wyślij payload ScenariosRequest."
            )

        scenarios_request = ScenariosRequest(**raw_input)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd parsowania ScenariosRequest: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Nieprawidłowy format danych wejściowych: {str(e)}"
        )

    # ── Wygeneruj PDF ────────────────────────────────────────────────────────
    try:
        pdf_bytes = _build_report_data_and_pdf(scenarios_request)
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Błąd generowania PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Błąd generowania raportu PDF: {str(e)}"
        )

    # ── Zapisz do bazy i na dysk ──────────────────────────────────────────────
    token = str(uuid.uuid4())
    os.makedirs(PDF_REPORTS_DIR, exist_ok=True)
    pdf_path = os.path.join(PDF_REPORTS_DIR, f"{token}.pdf")

    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    try:
        report = Report(
            token=token,
            user_id=user.id if user else None,
            status="generated",
            input_json=raw_input,
            pdf_path=pdf_path,
            created_at=datetime.utcnow(),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception as e:
        logger.error(f"Błąd zapisu raportu do bazy: {e}")
        # PDF wygenerowany — zwracamy token nawet jeśli baza nie zadziałała
        return {
            "report_token": token,
            "pdf_ready": True,
            "warning": "PDF wygenerowany, ale błąd zapisu do bazy.",
        }

    return {
        "report_token": token,
        "pdf_ready": True,
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
    """Pobiera PDF raportu po tokenie."""
    pdf_path = os.path.join(PDF_REPORTS_DIR, f"{token}.pdf")

    if not os.path.exists(pdf_path):
        # Fallback: spróbuj znaleźć po starym nazewnictwie
        alt_path = os.path.join(PDF_REPORTS_DIR, f"raport_{token}.pdf")
        if os.path.exists(alt_path):
            pdf_path = alt_path
        else:
            try:
                pdf_path = _generate_mock_pdf(token)
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
        },
    )