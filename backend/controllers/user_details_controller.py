from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from utils import get_or_404, apply_updates
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/details",
    tags=["User Details"]
)

############################################
# This function is to create a user details record for an account after
# verifying the account exists and no details record already exists.
############################################
@router.post("/", response_model=schemas.UserDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_user_details(details: schemas.UserDetailsCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and details.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only create your own details")

    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == details.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    existing_details = db.query(models.UserDetails).filter(models.UserDetails.UserID == details.UserID).first()
    if existing_details:
        raise HTTPException(status_code=400, detail="Details already exist for this user. Use PUT to update.")

    db_details = models.UserDetails(**details.model_dump())
    db.add(db_details)
    db.commit()
    db.refresh(db_details)
    return db_details

############################################
# This function is to retrieve user details by user ID, enforcing that
# non-admin users can only view their own details.
############################################
@router.get("/{user_id}", response_model=schemas.UserDetailsResponse)
def read_user_details(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only view your own details")
    details = get_or_404(db.query(models.UserDetails).filter(models.UserDetails.UserID == user_id).first(), "User details not found")
    return details

############################################
# This function is to update user details fields for a user, enforcing
# that non-admin users can only update their own details.
############################################
@router.put("/{user_id}", response_model=schemas.UserDetailsResponse)
def update_user_details(user_id: int, details_update: schemas.UserDetailsUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only update your own details")
    db_details = get_or_404(db.query(models.UserDetails).filter(models.UserDetails.UserID == user_id).first(), "User details not found")
    apply_updates(db, db_details, details_update)
    return db_details

############################################
# This function is to retrieve a paginated list of all user details
# records, restricted to administrators.
############################################
@router.get("/", response_model=List[schemas.UserDetailsResponse])
def list_all_details(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    return db.query(models.UserDetails).offset(skip).limit(limit).all()