from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Import custom files
import models
import schemas
from database import get_db

# Create a router for this controller
router = APIRouter(
    prefix="/api/details",
    tags=["User Details"]
)

#########################################################
# CREATE function for UserDetails table
#########################################################
@router.post("/", response_model=schemas.UserDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_user_details(details: schemas.UserDetailsCreate, db: Session = Depends(get_db)):
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
def read_user_details(user_id: int, db: Session = Depends(get_db)):
    details = db.query(models.UserDetails).filter(models.UserDetails.UserID == user_id).first()
    if not details:
        raise HTTPException(status_code=404, detail="User details not found")
    return details

#########################################################
# UPDATE function for UserDetails table
#########################################################
@router.put("/{user_id}", response_model=schemas.UserDetailsResponse)
def update_user_details(user_id: int, details_update: schemas.UserDetailsUpdate, db: Session = Depends(get_db)):
    db_details = db.query(models.UserDetails).filter(models.UserDetails.UserID == user_id).first()
    if not db_details:
        raise HTTPException(status_code=404, detail="User details not found")

    update_data = details_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_details, key, value)

    db.commit()
    db.refresh(db_details)
    return db_details

#########################################################
# DELETE function for UserDetails table
#########################################################
# When a user account is deleted (soft delete), the details will simply become inaccessible. 
# It is not necessary to implement a delete function for UserDetails table

#########################################################
# LIST function for UserDetails table
#########################################################
@router.get("/", response_model=List[schemas.UserDetailsResponse])
def list_all_details(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.UserDetails).offset(skip).limit(limit).all()