import hashlib
import os
from datetime import datetime, timezone
from passlib.context import CryptContext
from fastapi import HTTPException, Request as FastAPIRequest
from sqlalchemy.orm import Session
import resend as resend_lib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

############################################
# This function is to hash a plain-text password using bcrypt
# and return the resulting hash string for secure storage.
############################################
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

############################################
# This function is to verify a plain-text password against its
# stored bcrypt hash, returning True if they match.
############################################
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

############################################
# This function is to retrieve the FullName from a UserAccount's
# related UserDetails record, returning a default value if the
# details relationship is unavailable.
############################################
def get_fullname(user_account, default="N/A"):
    if user_account and user_account.details:
        return user_account.details.FullName
    return default

############################################
# This function is to SHA-256 hash a token string for safe storage
# in the database. The raw token is sent to the user while only
# the hash is persisted.
############################################
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

############################################
# This function is to ensure a datetime object is timezone-aware
# in UTC, converting naive datetimes by attaching the UTC timezone
# so they can be safely compared with datetime.now(timezone.utc).
############################################
def normalize_expiry(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

############################################
# This function is to raise an HTTP 404 exception if the provided
# object is None, otherwise return the object unchanged.
############################################
def get_or_404(obj, detail: str):
    if not obj:
        raise HTTPException(status_code=404, detail=detail)
    return obj

############################################
# This function is to apply a Pydantic update schema's non-unset
# fields to a SQLAlchemy model instance, commit the transaction,
# and refresh the model to reflect the latest database state.
############################################
def apply_updates(db: Session, obj, update_schema) -> None:
    for key, value in update_schema.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)

############################################
# This function is to extract the real client IP address from the
# request, reading from the X-Forwarded-For header set by the Nginx
# proxy if present, otherwise falling back to the direct connection IP.
############################################
def get_client_ip(request: FastAPIRequest) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

############################################
# This function is to send an HTML email via Resend using the
# RESEND_KEY environment variable, raising an exception on failure.
############################################
def send_email(to: str, subject: str, html: str, from_name: str = "LinksLens") -> None:
    resend_lib.api_key = os.getenv("RESEND_KEY")
    resend_lib.Emails.send({
        "from": f"{from_name} <noreply@linkslens.com>",
        "to": [to],
        "subject": subject,
        "html": html,
    })
