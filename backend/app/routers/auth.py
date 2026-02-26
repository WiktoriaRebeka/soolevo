# backend/app/routers/auth.py
# ─────────────────────────────────────────────────────────────
#  Autentykacja — rejestracja, logowanie, refresh tokenów
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user
)
from app.models.db import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schematy ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Hasło musi mieć minimum 8 znaków")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool


# ── Endpointy ─────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Rejestracja nowego konta."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email jest już zajęty"
        )

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Logowanie — zwraca JWT."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło"
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto jest dezaktywowane")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    """Odświeżenie access tokenu za pomocą refresh tokenu."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Nieprawidłowy typ tokenu")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Użytkownik nie istnieje")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    """Zwraca dane zalogowanego użytkownika."""
    return UserResponse(id=user.id, email=user.email, is_active=user.is_active)
