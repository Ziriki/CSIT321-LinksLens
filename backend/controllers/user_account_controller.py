from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import secrets
import os
from dotenv import load_dotenv

from utils import get_client_ip, get_fullname, get_or_404, get_password_hash, hash_token, normalize_expiry, send_email

load_dotenv()

import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/accounts",
    tags=["User Accounts"]
)

@router.post("/", response_model=schemas.UserAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: schemas.UserAccountCreate, db: Session = Depends(get_db)):
    if db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == account.EmailAddress).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if not db.query(models.UserRole).filter(models.UserRole.RoleID == account.RoleID).first():
        raise HTTPException(status_code=400, detail="Invalid RoleID provided")

    hashed_pwd = get_password_hash(account.Password)
    db_account = models.UserAccount(
        EmailAddress=account.EmailAddress,
        PasswordHash=hashed_pwd,
        RoleID=account.RoleID,
        IsActive=account.IsActive
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/{account_id}", response_model=schemas.UserAccountResponse)
def read_account(account_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and account_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only view your own account")
    account = get_or_404(db.query(models.UserAccount).filter(models.UserAccount.UserID == account_id).first(), "Account not found")
    return account

@router.put("/{account_id}", response_model=schemas.UserAccountResponse)
def update_account(account_id: int, account_update: schemas.UserAccountUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and account_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only update your own account")

    update_data = account_update.model_dump(exclude_unset=True)
    if current_user["role_id"] != 1:
        if "RoleID" in update_data or "IsActive" in update_data:
            raise HTTPException(status_code=403, detail="Only administrators can change roles or account status")

    db_account = get_or_404(db.query(models.UserAccount).filter(models.UserAccount.UserID == account_id).first(), "Account not found")

    if account_update.EmailAddress:
        email_check = db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == account_update.EmailAddress).first()
        if email_check and email_check.UserID != account_id:
            raise HTTPException(status_code=400, detail="Email already in use")

    if account_update.RoleID:
        if not db.query(models.UserRole).filter(models.UserRole.RoleID == account_update.RoleID).first():
            raise HTTPException(status_code=400, detail="Invalid RoleID provided")

    if "Password" in update_data:
        db_account.PasswordHash = get_password_hash(update_data.pop("Password"))

    for key, value in update_data.items():
        setattr(db_account, key, value)

    db.commit()
    db.refresh(db_account)
    return db_account

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_account = get_or_404(db.query(models.UserAccount).filter(models.UserAccount.UserID == account_id).first(), "Account not found")

    db_account.IsActive = False
    db.commit()
    return None

@router.get("/", response_model=None)
def list_accounts(
    search_email: Optional[str] = None,
    role_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1))
):
    query = db.query(models.UserAccount).options(
        joinedload(models.UserAccount.details)
    )

    if search_email:
        query = query.filter(models.UserAccount.EmailAddress.ilike(f"%{search_email}%"))

    if role_id:
        query = query.filter(models.UserAccount.RoleID == role_id)

    results = query.offset(skip).limit(limit).all()

    return [
        {
            "UserID": acc.UserID,
            "EmailAddress": acc.EmailAddress,
            "RoleID": acc.RoleID,
            "IsActive": acc.IsActive,
            "FullName": get_fullname(acc),
        }
        for acc in results
    ]

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: schemas.UserRegistrationRequest, db: Session = Depends(get_db)):
    if db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == request.EmailAddress).first():
        raise HTTPException(status_code=400, detail="Registration failed. Please check your details.")

    hashed_pwd = get_password_hash(request.Password)
    db_account = models.UserAccount(
        EmailAddress=request.EmailAddress,
        PasswordHash=hashed_pwd,
        RoleID=3,
        IsActive=False,
    )
    db.add(db_account)
    db.flush()  # needed to get auto-generated UserID

    db.add(models.UserDetails(UserID=db_account.UserID, FullName=request.FullName))

    raw_token = secrets.token_urlsafe(32)
    db.add(models.EmailVerificationToken(
        Token=hash_token(raw_token),
        UserID=db_account.UserID,
        ExpiresAt=datetime.now(timezone.utc) + timedelta(minutes=15),
        IsUsed=False,
    ))

    verify_link = f"https://linkslens.com/verify-email.html?token={raw_token}"
    email_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">

        <!-- Logo -->
        <tr><td align="center" style="padding-bottom:28px;">
          <img src="https://linkslens.com/images/logo.svg" alt="LinksLens" width="44" height="44"
               style="background:#ffffff;border-radius:10px;display:block;">
          <p style="margin:10px 0 0;font-size:20px;font-weight:700;color:#1e293b;letter-spacing:-0.3px;">LinksLens</p>
        </td></tr>

        <!-- Card -->
        <tr><td style="background-color:#ffffff;border-radius:16px;border:1px solid #e2e8f0;padding:40px 36px;">

          <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#1e293b;">Verify your email address</h1>
          <p style="margin:0 0 24px;font-size:15px;color:#64748b;line-height:1.6;">
            Hi {request.FullName}, welcome to LinksLens! Please confirm your email address to activate your account and start scanning links safely.
          </p>

          <!-- CTA Button -->
          <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
            <tr><td style="border-radius:8px;background-color:#1d4ed8;">
              <a href="{verify_link}"
                 style="display:inline-block;padding:13px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;letter-spacing:0.1px;">
                Verify Email Address
              </a>
            </td></tr>
          </table>

          <!-- Fallback link -->
          <p style="margin:0 0 6px;font-size:13px;color:#94a3b8;">Or copy and paste this link into your browser:</p>
          <p style="margin:0 0 28px;font-size:12px;word-break:break-all;">
            <a href="{verify_link}" style="color:#1d4ed8;text-decoration:none;">{verify_link}</a>
          </p>

          <!-- Divider -->
          <hr style="border:none;border-top:1px solid #e2e8f0;margin:0 0 24px;">

          <!-- Expiry notice -->
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td width="18" valign="top" style="padding-top:1px;">
                <span style="font-size:15px;">⏰</span>
              </td>
              <td style="padding-left:8px;font-size:13px;color:#64748b;line-height:1.5;">
                This link expires in <strong style="color:#1e293b;">15 minutes</strong>. After that you will need to register again.
              </td>
            </tr>
            <tr><td colspan="2" style="padding-top:10px;"></td></tr>
            <tr>
              <td width="18" valign="top" style="padding-top:1px;">
                <span style="font-size:15px;">🔒</span>
              </td>
              <td style="padding-left:8px;font-size:13px;color:#64748b;line-height:1.5;">
                If you did not create a LinksLens account, you can safely ignore this email.
              </td>
            </tr>
          </table>

        </td></tr>

        <!-- Footer -->
        <tr><td align="center" style="padding-top:24px;">
          <p style="margin:0 0 6px;font-size:12px;color:#94a3b8;">
            This is an automated email — please do not reply to this message.
          </p>
          <p style="margin:0;font-size:12px;color:#94a3b8;">
            &copy; 2026 LinksLens &nbsp;&bull;&nbsp;
            <a href="https://linkslens.com" style="color:#1d4ed8;text-decoration:none;">linkslens.com</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        send_email(request.EmailAddress, "Verify your email address — LinksLens", email_html)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please try again.")

    db.commit()
    return {"message": "Account created. Please check your email to verify your account."}


@router.post("/verify-email")
def verify_email(request: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    token_record = db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.Token == hash_token(request.Token)
    ).first()

    if not token_record or token_record.IsUsed:
        raise HTTPException(status_code=400, detail="Invalid or already used verification link.")

    if datetime.now(timezone.utc) > normalize_expiry(token_record.ExpiresAt):
        raise HTTPException(status_code=400, detail="Verification link has expired. Please register again.")

    user = token_record.user
    if not user:
        raise HTTPException(status_code=404, detail="User account no longer exists.")
    user.IsActive = True
    token_record.IsUsed = True
    db.commit()

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/forgot-password")
def forgot_password(request: schemas.ForgotPasswordRequest, http_request: Request, db: Session = Depends(get_db)):
    generic_message = {"message": "If that email exists in our system, a password reset link has been sent."}
    user = db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == request.EmailAddress).first()

    if not user:
        return generic_message

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    email_recent = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.UserID == user.UserID,
        models.PasswordResetToken.CreatedAt >= one_hour_ago,
    ).count()
    if email_recent >= 3:
        return generic_message

    client_ip = get_client_ip(http_request)
    ip_recent = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.RequestIP == client_ip,
        models.PasswordResetToken.CreatedAt >= one_hour_ago,
    ).count()
    if ip_recent >= 10:
        return generic_message

    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.UserID == user.UserID,
        models.PasswordResetToken.IsUsed == False,
    ).update({"IsUsed": True})

    raw_token = secrets.token_urlsafe(32)
    db.add(models.PasswordResetToken(
        Token=hash_token(raw_token),
        UserID=user.UserID,
        ExpiresAt=datetime.now(timezone.utc) + timedelta(minutes=15),
        IsUsed=False,
        RequestIP=client_ip,
    ))
    db.flush()

    reset_link = f"https://linkslens.com/reset-password.html?token={raw_token}"
    email_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">

        <!-- Logo -->
        <tr><td align="center" style="padding-bottom:28px;">
          <img src="https://linkslens.com/images/logo.svg" alt="LinksLens" width="44" height="44"
               style="background:#ffffff;border-radius:10px;display:block;">
          <p style="margin:10px 0 0;font-size:20px;font-weight:700;color:#1e293b;letter-spacing:-0.3px;">LinksLens</p>
        </td></tr>

        <!-- Card -->
        <tr><td style="background-color:#ffffff;border-radius:16px;border:1px solid #e2e8f0;padding:40px 36px;">

          <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#1e293b;">Reset your password</h1>
          <p style="margin:0 0 24px;font-size:15px;color:#64748b;line-height:1.6;">
            We received a request to reset the password for your LinksLens account. Click the button below to choose a new password.
          </p>

          <!-- CTA Button -->
          <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
            <tr><td style="border-radius:8px;background-color:#1d4ed8;">
              <a href="{reset_link}"
                 style="display:inline-block;padding:13px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;letter-spacing:0.1px;">
                Reset Password
              </a>
            </td></tr>
          </table>

          <!-- Fallback link -->
          <p style="margin:0 0 6px;font-size:13px;color:#94a3b8;">Or copy and paste this link into your browser:</p>
          <p style="margin:0 0 28px;font-size:12px;word-break:break-all;">
            <a href="{reset_link}" style="color:#1d4ed8;text-decoration:none;">{reset_link}</a>
          </p>

          <!-- Divider -->
          <hr style="border:none;border-top:1px solid #e2e8f0;margin:0 0 24px;">

          <!-- Notices -->
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td width="18" valign="top" style="padding-top:1px;">
                <span style="font-size:15px;">⏰</span>
              </td>
              <td style="padding-left:8px;font-size:13px;color:#64748b;line-height:1.5;">
                This link expires in <strong style="color:#1e293b;">15 minutes</strong> and can only be used once.
              </td>
            </tr>
            <tr><td colspan="2" style="padding-top:10px;"></td></tr>
            <tr>
              <td width="18" valign="top" style="padding-top:1px;">
                <span style="font-size:15px;">🔒</span>
              </td>
              <td style="padding-left:8px;font-size:13px;color:#64748b;line-height:1.5;">
                If you did not request a password reset, your password has not been changed. You can safely ignore this email.
              </td>
            </tr>
          </table>

        </td></tr>

        <!-- Footer -->
        <tr><td align="center" style="padding-top:24px;">
          <p style="margin:0 0 6px;font-size:12px;color:#94a3b8;">
            This is an automated email — please do not reply to this message.
          </p>
          <p style="margin:0;font-size:12px;color:#94a3b8;">
            &copy; 2026 LinksLens &nbsp;&bull;&nbsp;
            <a href="https://linkslens.com" style="color:#1d4ed8;text-decoration:none;">linkslens.com</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        send_email(user.EmailAddress, "Reset your LinksLens password", email_html, from_name="LinksLens Security")
    except Exception:
        db.rollback()
        return generic_message

    db.commit()
    return generic_message

@router.post("/reset-password")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    token_record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.Token == hash_token(request.Token)
    ).first()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    if token_record.IsUsed:
        raise HTTPException(status_code=400, detail="This token has already been used.")

    if datetime.now(timezone.utc) > normalize_expiry(token_record.ExpiresAt):
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    user = token_record.user
    if not user:
        raise HTTPException(status_code=404, detail="User account no longer exists.")

    user.PasswordHash = get_password_hash(request.NewPassword)
    token_record.IsUsed = True

    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.UserID == token_record.UserID,
        models.PasswordResetToken.IsUsed == False,
    ).update({"IsUsed": True})

    db.commit()

    return {"message": "Password successfully updated. You may now log in."}