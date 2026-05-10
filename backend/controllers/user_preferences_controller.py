from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List

from utils import get_or_404
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/preferences",
    tags=["User Preferences"]
)

############################################
# This function is to create a preferences record for a user after
# verifying the account exists and no preferences record already exists.
############################################
@router.post("/", response_model=schemas.UserPreferencesResponse, status_code=status.HTTP_201_CREATED)
def create_preferences(prefs: schemas.UserPreferencesCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and prefs.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only create your own preferences")

    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == prefs.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    existing_prefs = db.query(models.UserPreferences).filter(models.UserPreferences.UserID == prefs.UserID).first()
    if existing_prefs:
        raise HTTPException(status_code=400, detail="Preferences already exist for this user. Use PUT to update.")

    db_prefs = models.UserPreferences(
        UserID=prefs.UserID,
        Preferences=prefs.Preferences
    )
    db.add(db_prefs)
    db.commit()
    db.refresh(db_prefs)
    return db_prefs

############################################
# This function is to retrieve user preferences by user ID, enforcing
# that non-admin users can only view their own preferences.
############################################
@router.get("/{user_id}", response_model=schemas.UserPreferencesResponse)
def read_preferences(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only view your own preferences")
    prefs = get_or_404(db.query(models.UserPreferences).filter(models.UserPreferences.UserID == user_id).first(), "Preferences not found")
    return prefs

############################################
# This function is to merge new preference values into the existing
# record so unrelated preference keys are not overwritten, enforcing
# that non-admin users can only update their own preferences.
############################################
@router.put("/{user_id}", response_model=schemas.UserPreferencesResponse)
def update_preferences(user_id: int, prefs_update: schemas.UserPreferencesUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only update your own preferences")
    db_prefs = get_or_404(db.query(models.UserPreferences).filter(models.UserPreferences.UserID == user_id).first(), "Preferences not found")

    # Merge so partial updates don't clobber unrelated preference keys
    merged_preferences = {**db_prefs.Preferences, **prefs_update.Preferences}
    db_prefs.Preferences = merged_preferences
    # SQLAlchemy does not detect in-place dict mutations without this call
    flag_modified(db_prefs, "Preferences")
    
    db.commit()
    db.refresh(db_prefs)
    return db_prefs

############################################
# This function is to delete a user preferences record, enforcing that
# non-admin users can only delete their own preferences.
############################################
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preferences(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own preferences")
    db_prefs = get_or_404(db.query(models.UserPreferences).filter(models.UserPreferences.UserID == user_id).first(), "Preferences not found")

    db.delete(db_prefs)
    db.commit()
    return None

############################################
# This function is to retrieve a paginated list of all user preferences
# records, restricted to administrators.
############################################
@router.get("/", response_model=List[schemas.UserPreferencesResponse])
def list_preferences(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    return db.query(models.UserPreferences).offset(skip).limit(limit).all()