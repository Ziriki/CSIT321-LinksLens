from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

from utils import get_client_ip, verify_password

import models
import schemas
from database import get_db

load_dotenv()

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("FATAL ERROR: SECRET_KEY environment variable is not set!")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

try:
    # Cast to int — timedelta requires an integer, not a string
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))
except ValueError:
    print("Warning: ACCESS_TOKEN_EXPIRE_MINUTES is not a valid integer. Defaulting to 120.")
    ACCESS_TOKEN_EXPIRE_MINUTES = 120

def create_access_token(data: dict):
    """Sign and return a JWT with an expiry claim appended to the payload."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

_LOGIN_MAX_FAILURES = 10
_LOGIN_WINDOW_MINUTES = 15

@router.post("/login", response_model=schemas.TokenResponse)
def login(credentials: schemas.UserLogin, http_request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = get_client_ip(http_request)
    window_start = datetime.now(timezone.utc) - timedelta(minutes=_LOGIN_WINDOW_MINUTES)

    recent_failures = db.query(models.FailedLoginAttempt).filter(
        models.FailedLoginAttempt.IPAddress == client_ip,
        models.FailedLoginAttempt.AttemptedAt >= window_start,
    ).count()
    if recent_failures >= _LOGIN_MAX_FAILURES:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

    user = db.query(models.UserAccount).filter(
        models.UserAccount.EmailAddress == credentials.EmailAddress
    ).first()

    if not user or not verify_password(credentials.Password, user.PasswordHash):
        db.add(models.FailedLoginAttempt(IPAddress=client_ip))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if recent_failures > 0:
        db.query(models.FailedLoginAttempt).filter(
            models.FailedLoginAttempt.IPAddress == client_ip,
        ).delete()

    # IsActive covers both unverified and admin-deactivated accounts
    if not user.IsActive:
        # Only query verification tokens when needed (inactive accounts are rare)
        has_pending_verification = db.query(models.EmailVerificationToken).filter(
            models.EmailVerificationToken.UserID == user.UserID,
            models.EmailVerificationToken.IsUsed == False,
        ).first() is not None
        if has_pending_verification:
            raise HTTPException(status_code=403, detail="Please verify your email address before logging in.")
        raise HTTPException(status_code=403, detail="This account has been deactivated. Please contact support.")

    is_staff = user.RoleID in (1, 2)
    is_web   = credentials.ClientType == schemas.ClientTypeEnum.WEB
    if is_staff and not is_web:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if not is_staff and is_web:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token_data = {"sub": str(user.UserID), "role": user.RoleID}
    token = create_access_token(token_data)

    if credentials.ClientType == schemas.ClientTypeEnum.WEB:
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        # Also return token in body — server-side clients (e.g. Streamlit) read it directly;
        # browsers use the HttpOnly cookie instead.
        return {"access_token": token, "token_type": "bearer", "message": "Web login successful"}

    elif credentials.ClientType == schemas.ClientTypeEnum.MOBILE:
        return {
            "access_token": token,
            "token_type": "bearer",
            "message": "Mobile login successful"
        }

@router.post("/logout")
def logout(client_type: schemas.ClientTypeEnum, response: Response):
    if client_type == schemas.ClientTypeEnum.WEB:
        response.delete_cookie("access_token")
        return {"message": "Web logout successful. Cookie cleared."}
    # Mobile token lives in the app — the backend has no session to clear.
    return {"message": "Mobile logout successful. Please clear local token."}