from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import secrets
import os
import resend
from dotenv import load_dotenv

from utils import get_fullname, get_password_hash

load_dotenv()

# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

# Create a router for this controller
router = APIRouter(
    prefix="/api/accounts",
    tags=["User Accounts"]
)

#########################################################
# CREATE function for UserAccount table
#########################################################
@router.post("/", response_model=schemas.UserAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: schemas.UserAccountCreate, db: Session = Depends(get_db)):
    # Check if Email already exists
    if db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == account.EmailAddress).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if the RoleID actually exists in the UserRole table
    if not db.query(models.UserRole).filter(models.UserRole.RoleID == account.RoleID).first():
        raise HTTPException(status_code=400, detail="Invalid RoleID provided")

    # Hash the password and create the record
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

#########################################################
# READ function for UserAccount table (Get by ID)
#########################################################
@router.get("/{account_id}", response_model=schemas.UserAccountResponse)
def read_account(account_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only view their own account; admins can view any
    if current_user["role_id"] not in (1, 2) and account_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only view your own account")
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

#########################################################
# UPDATE function for UserAccount table
#########################################################
@router.put("/{account_id}", response_model=schemas.UserAccountResponse)
def update_account(account_id: int, account_update: schemas.UserAccountUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only update their own account
    if current_user["role_id"] not in (1, 2) and account_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only update your own account")

    # Only admins can change RoleID or IsActive
    update_data = account_update.model_dump(exclude_unset=True)
    if current_user["role_id"] != 1:
        if "RoleID" in update_data or "IsActive" in update_data:
            raise HTTPException(status_code=403, detail="Only administrators can change roles or account status")

    db_account = db.query(models.UserAccount).filter(models.UserAccount.UserID == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")

    # If updating email, check if the new email is taken by someone else
    if account_update.EmailAddress:
        email_check = db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == account_update.EmailAddress).first()
        if email_check and email_check.UserID != account_id:
            raise HTTPException(status_code=400, detail="Email already in use")

    # If updating RoleID, check if it exists
    if account_update.RoleID:
        if not db.query(models.UserRole).filter(models.UserRole.RoleID == account_update.RoleID).first():
            raise HTTPException(status_code=400, detail="Invalid RoleID provided")

    # Extract update data, handle password hashing separately if provided
    update_data = account_update.model_dump(exclude_unset=True)
    
    if "Password" in update_data:
        db_account.PasswordHash = get_password_hash(update_data.pop("Password"))

    for key, value in update_data.items():
        setattr(db_account, key, value)

    db.commit()
    db.refresh(db_account)
    return db_account

#########################################################
# DELETE function for UserAccount table (Soft Delete)
#########################################################
@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_account = db.query(models.UserAccount).filter(models.UserAccount.UserID == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    db_account.IsActive = False
    db.commit()
    return None

#########################################################
# LIST function for UserAccount table
#########################################################
@router.get("/", response_model=None)
def list_accounts(
    search_email: Optional[str] = None,
    role_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1))
):
    # Start with a base query
    query = db.query(models.UserAccount).options(
        joinedload(models.UserAccount.details)
    ).filter(models.UserAccount.IsActive == True)

    # Filter logic if a search term is provided
    if search_email:
        # .ilike() provides case-insensitive matching in MySQL
        query = query.filter(models.UserAccount.EmailAddress.ilike(f"%{search_email}%"))

    # Additional filter for RoleID if provided
    if role_id:
        query = query.filter(models.UserAccount.RoleID == role_id)

    # Execute the query with optional pagination
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

#########################################################
# FORGOT PASSWORD - Create Token Record & Send Email
#########################################################
@router.post("/forgot-password")
def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    generic_message = {"message": "If that email exists in our system, a password reset link has been sent."}
    user = db.query(models.UserAccount).filter(models.UserAccount.EmailAddress == request.EmailAddress).first()

    if not user:
        return generic_message

    # Invalidate any existing unused tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.UserID == user.UserID,
        models.PasswordResetToken.IsUsed == False
    ).update({"IsUsed": True})

    token = secrets.token_urlsafe(32)
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=15)

    db_token = models.PasswordResetToken(
        Token=token,
        UserID=user.UserID,
        ExpiresAt=expiry_time,
        IsUsed=False
    )
    db.add(db_token)
    db.flush()

    reset_link = f"https://linkslens.com/reset-password?token={token}"
    email_html = f"""
    <h2>LinksLens Password Reset</h2>
    <p>You requested a password reset. Click the link below to choose a new password. This link expires in 15 minutes.</p>
    <a href="{reset_link}" style="display:inline-block; padding:10px 20px; background-color:#1565c0; color:white; text-decoration:none; border-radius:5px;">Reset Password</a>
    """

    resend.api_key = os.getenv("RESEND_KEY")
    try:
        resend.Emails.send({
            "from": "LinksLens Security <noreply@linkslens.com>",
            "to": [user.EmailAddress],
            "subject": "Reset your LinksLens Password",
            "html": email_html
        })
    except Exception:
        db.rollback()
        return generic_message

    db.commit()
    return generic_message

#########################################################
# RESET PASSWORD - Verify Token Record & Update Password
#########################################################
@router.post("/reset-password")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    token_record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.Token == request.Token
    ).first()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    if token_record.IsUsed:
        raise HTTPException(status_code=400, detail="This token has already been used.")

    current_time = datetime.now(timezone.utc)
    expiry_time = token_record.ExpiresAt
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    if current_time > expiry_time:
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    user = token_record.user
    if not user:
        raise HTTPException(status_code=404, detail="User account no longer exists.")

    user.PasswordHash = get_password_hash(request.NewPassword)
    token_record.IsUsed = True

    db.commit()

    return {"message": "Password successfully updated. You may now log in."}