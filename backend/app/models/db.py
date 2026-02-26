# backend/app/models/db.py
# ─────────────────────────────────────────────────────────────
#  SQLAlchemy models — Użytkownicy, Raporty, Płatności, Magazyny
# ─────────────────────────────────────────────────────────────

from datetime import datetime
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Float,
    ForeignKey, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="user")
    payments = relationship("Payment", back_populates="user")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    # Unikalny token do pobierania PDF — przekazywany do PayNow
    token = Column(String(64), unique=True, nullable=False, index=True, default=lambda: uuid.uuid4().hex)
    # Pełne dane wejściowe z frontendu (JSON)
    input_json = Column(JSON, nullable=False)
    # Ścieżka do pliku PDF (po opłaceniu)
    pdf_path = Column(String(512), nullable=True)
    # Status: pending | paid | generated | failed
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="reports")
    payment = relationship("Payment", back_populates="report", uselist=False)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    report_id = Column(UUID(as_uuid=False), ForeignKey("reports.id"), nullable=False)
    # PayNow payment ID
    paynow_payment_id = Column(String(128), unique=True, nullable=True, index=True)
    # Status PayNow: NEW | PENDING | CONFIRMED | ERROR | EXPIRED | DECLINED | REFUNDED
    status = Column(String(32), default="NEW", nullable=False)
    amount_groszy = Column(Integer, nullable=False)  # 4900 = 49.00 zł
    currency = Column(String(3), default="PLN")
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="payments")
    report = relationship("Report", back_populates="payment")


class Battery(Base):
    __tablename__ = "batteries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(128), nullable=False)
    capacity_kwh = Column(Float, nullable=False)
    price_pln = Column(Integer, nullable=True)   # orientacyjna cena
    warranty_years = Column(Integer, nullable=True)
    chemistry = Column(String(64), nullable=True)   # LFP, NMC, etc.
    max_power_kw = Column(Float, nullable=True)
    cycles = Column(Integer, nullable=True)
    dod_percent = Column(Integer, nullable=True)   # Depth of Discharge
    image_url = Column(String(512), nullable=True)
    datasheet_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    specs_json = Column(JSON, nullable=True)  # dodatkowe parametry
