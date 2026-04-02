from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from utils import get_or_404, apply_updates
# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

# Create a router for this controller
router = APIRouter(
    prefix="/api/details",
    tags=["User Details"]
)

#########################################################
# CREATE function for UserDetails table
#########################################################
@router.post("/", response_model=schemas.UserDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_user_details(details: schemas.UserDetailsCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only create their own details
    if current_user["role_id"] not in (1, 2) and details.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only create your own details")

    # Check if the UserAccount actually exists
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == details.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    # Check if details already exist for this user (1-to-1 relationship rule)
    existing_details = db.query(models.UserDetails).filter(models.UserDetails.UserID == details.UserID).first()
    if existing_details:
        raise HTTPException(status_code=400, detail="Details already exist for this user. Use PUT to update.")

    # Create the record
    db_details = models.UserDetails(**details.model_dump())
    db.add(db_details)
    db.commit()
    db.refresh(db_details)
    return db_details

#########################################################
# READ function for UserDetails table (Get by ID)
#########################################################
@router.get("/{user_id}", response_model=schemas.UserDetailsResponse)
def read_user_details(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only view their own details
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only view your own details")
    details = get_or_404(db.query(models.UserDetails).filter(models.UserDetails.UserID == user_id).first(), "User details not found")
    return details

#########################################################
# UPDATE function for UserDetails table
#########################################################
@router.put("/{user_id}", response_model=schemas.UserDetailsResponse)
def update_user_details(user_id: int, details_update: schemas.UserDetailsUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only update their own details
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only update your own details")
    db_details = get_or_404(db.query(models.UserDetails).filter(models.UserDetails.UserID == user_id).first(), "User details not found")
    apply_updates(db, db_details, details_update)
    return db_details

#########################################################
# LIST function for UserDetails table
#########################################################
@router.get("/", response_model=List[schemas.UserDetailsResponse])
def list_all_details(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    return db.query(models.UserDetails).offset(skip).limit(limit).all()