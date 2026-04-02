from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified # For JSON updates
from typing import List

from utils import get_or_404
# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

# Create a router for this controller
router = APIRouter(
    prefix="/api/preferences",
    tags=["User Preferences"]
)

#########################################################
# CREATE function for UserPreferences table
#########################################################
@router.post("/", response_model=schemas.UserPreferencesResponse, status_code=status.HTTP_201_CREATED)
def create_preferences(prefs: schemas.UserPreferencesCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only create their own preferences
    if current_user["role_id"] not in (1, 2) and prefs.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only create your own preferences")

    # Check if the UserAccount exists
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == prefs.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    # Check if preferences already exist
    existing_prefs = db.query(models.UserPreferences).filter(models.UserPreferences.UserID == prefs.UserID).first()
    if existing_prefs:
        raise HTTPException(status_code=400, detail="Preferences already exist for this user. Use PUT to update.")

    # Create the record
    db_prefs = models.UserPreferences(
        UserID=prefs.UserID,
        Preferences=prefs.Preferences
    )
    db.add(db_prefs)
    db.commit()
    db.refresh(db_prefs)
    return db_prefs

#########################################################
# READ function for UserPreferences table (Get by ID)
#########################################################
@router.get("/{user_id}", response_model=schemas.UserPreferencesResponse)
def read_preferences(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only view their own preferences
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only view your own preferences")
    prefs = get_or_404(db.query(models.UserPreferences).filter(models.UserPreferences.UserID == user_id).first(), "Preferences not found")
    return prefs

#########################################################
# UPDATE function for UserPreferences table
#########################################################
@router.put("/{user_id}", response_model=schemas.UserPreferencesResponse)
def update_preferences(user_id: int, prefs_update: schemas.UserPreferencesUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only update their own preferences
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only update your own preferences")
    db_prefs = get_or_404(db.query(models.UserPreferences).filter(models.UserPreferences.UserID == user_id).first(), "Preferences not found")

    # Merge the existing JSON with the new JSON. 
    # This way, if a user only updates "Theme", it doesn't delete "ReportLanguage"
    merged_preferences = {**db_prefs.Preferences, **prefs_update.Preferences}
    
    db_prefs.Preferences = merged_preferences
    
    # Force SQLAlchemy to recognize the JSON dictionary was modified
    flag_modified(db_prefs, "Preferences")
    
    db.commit()
    db.refresh(db_prefs)
    return db_prefs

#########################################################
# DELETE function for UserPreferences table
#########################################################
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preferences(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only delete their own preferences
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own preferences")
    db_prefs = get_or_404(db.query(models.UserPreferences).filter(models.UserPreferences.UserID == user_id).first(), "Preferences not found")

    db.delete(db_prefs)
    db.commit()
    return None

#########################################################
# LIST function for UserPreferences table
#########################################################
@router.get("/", response_model=List[schemas.UserPreferencesResponse])
def list_preferences(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    return db.query(models.UserPreferences).offset(skip).limit(limit).all()