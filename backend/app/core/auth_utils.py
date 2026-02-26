# backend/app/core/auth_utils.py
# ─────────────────────────────────────────────────────────────
#  Narzędzia autentykacji — JWT + bcrypt
# ─────────────────────────────────────────────────────────────

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db import User

SECRET_KEY = os.getenv("SECRET_KEY", "ZMIEN_NA_PRODUKCJI")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "type": "access", "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "type": "refresh", "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM
    )


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nieprawidłowy lub wygasł",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency — zwraca zalogowanego użytkownika lub 401."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagane logowanie",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Nieprawidłowy typ tokenu")

    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Użytkownik nie istnieje")
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Dependency — zwraca użytkownika jeśli zalogowany, None jeśli nie."""
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None
