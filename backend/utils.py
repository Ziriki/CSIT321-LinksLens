import hashlib
import os
from datetime import datetime, timezone
from passlib.context import CryptContext
from fastapi import HTTPException
from sqlalchemy.orm import Session
import resend as resend_lib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_fullname(user_account, default="N/A"):
    if user_account and user_account.details:
        return user_account.details.FullName
    return default

def hash_token(token: str) -> str:
    """SHA-256 hash a token for safe storage — raw token goes to user, hash goes to DB."""
    return hashlib.sha256(token.encode()).hexdigest()

def normalize_expiry(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC) for comparison with datetime.now(timezone.utc)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def get_or_404(obj, detail: str):
    """Raise HTTP 404 if obj is None, otherwise return it."""
    if not obj:
        raise HTTPException(status_code=404, detail=detail)
    return obj

def apply_updates(db: Session, obj, update_schema) -> None:
    """Apply a Pydantic update schema to a SQLAlchemy model, commit, and refresh."""
    for key, value in update_schema.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)

def send_email(to: str, subject: str, html: str, from_name: str = "LinksLens") -> None:
    """Send an email via Resend. Raises Exception on failure."""
    resend_lib.api_key = os.getenv("RESEND_KEY")
    resend_lib.Emails.send({
        "from": f"{from_name} <noreply@linkslens.com>",
        "to": [to],
        "subject": subject,
        "html": html,
    })
