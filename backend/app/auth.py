"""JWT authentication: register, login, and token-based user extraction."""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

from . import db

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 h

bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str = Field(min_length=1, max_length=120)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


def _create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def register(req: RegisterRequest) -> TokenResponse:
    """Create a new user account and return a JWT."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (req.email,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        import uuid

        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, email, name, password_hash) VALUES (%s, %s, %s, %s)",
            (user_id, req.email, req.name, _hash_password(req.password)),
        )
    token = _create_token(user_id)
    return TokenResponse(
        access_token=token, user_id=user_id, name=req.name, email=req.email
    )


def login(req: LoginRequest) -> TokenResponse:
    """Authenticate and return a JWT."""
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = %s",
            (req.email,),
        )
        row = cur.fetchone()
    if not row or not _verify_password(req.password, row[3]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = _create_token(row[0])
    return TokenResponse(
        access_token=token, user_id=row[0], name=row[1], email=row[2]
    )


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency – returns the authenticated user_id."""
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise JWTError("missing sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id
