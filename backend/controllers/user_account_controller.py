from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext

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

# Setup password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

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
@router.get("/", response_model=List[schemas.UserAccountResponse])
def list_accounts(
    search_email: Optional[str] = None,
    role_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1))
):
    # Start with a base query
    query = db.query(models.UserAccount).filter(models.UserAccount.IsActive == True)

    # Filter logic if a search term is provided
    if search_email:
        # .ilike() provides case-insensitive matching in MySQL
        query = query.filter(models.UserAccount.EmailAddress.ilike(f"%{search_email}%"))

    # Additional filter for RoleID if provided
    if role_id:
        query = query.filter(models.UserAccount.RoleID == role_id)

    # Execute the query with optional pagination
    return query.offset(skip).limit(limit).all()