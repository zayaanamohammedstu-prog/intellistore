"""Google OAuth endpoint stub.

Flow
----
1. Frontend completes Google Sign-In and sends the ID token here.
2. API verifies the token with Google's public keys (google-auth library).
3. API upserts a User row in Postgres.
4. API returns a signed application JWT (python-jose).

Production TODOs
----------------
- Store JWT secret in a secrets manager (not .env).
- Add token refresh / revocation.
- Enforce HTTPS (GOOGLE_CLIENT_ID audience check is already transport-agnostic).
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID: str = os.environ["GOOGLE_CLIENT_ID"]
JWT_SECRET: str = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


class GoogleTokenRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _create_app_jwt(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@router.post("/google", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def google_oauth(body: GoogleTokenRequest, db: Session = Depends(get_db)):
    """Verify a Google ID token and return an application JWT."""
    try:
        id_info = id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {exc}",
        ) from exc

    google_sub: str = id_info["sub"]
    email: str = id_info.get("email", "")
    name: str | None = id_info.get("name")
    picture: str | None = id_info.get("picture")

    # Upsert user
    user = db.query(User).filter_by(google_sub=google_sub).first()
    if user is None:
        user = User(
            google_sub=google_sub,
            email=email,
            name=name,
            picture=picture,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update profile fields on re-login
        user.email = email
        user.name = name
        user.picture = picture
        db.commit()
        db.refresh(user)

    token = _create_app_jwt(str(user.id), user.email)
    return TokenResponse(access_token=token)
