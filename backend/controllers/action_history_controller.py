from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

# Create a router for this controller
router = APIRouter(
    prefix="/api/history",
    tags=["Action History"]
)

#########################################################
# CREATE function for ActionHistory table
#########################################################
@router.post("/", response_model=schemas.ActionHistoryResponse, status_code=status.HTTP_201_CREATED)
def create_log(log: schemas.ActionHistoryCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only create logs for themselves
    if current_user["role_id"] not in (2, 3) and log.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only create logs for your own actions")

    # Verify the user performing the action actually exists
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == log.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    db_log = models.ActionHistory(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

#########################################################
# READ function for ActionHistory table (Get by ID)
#########################################################
@router.get("/{log_id}", response_model=schemas.ActionHistoryResponse)
def read_log(log_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(3))):
    log = db.query(models.ActionHistory).filter(models.ActionHistory.LogID == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return log

#########################################################
# UPDATE function for ActionHistory table
#########################################################
# NO UPDATE FUNCTION! Audit logs must remain immutable.

#########################################################
# DELETE function for ActionHistory table
#########################################################
# NO DELETE FUNCTION! Audit logs must remain their availability.

#########################################################
# LIST function for ActionHistory table
#########################################################
@router.get("/", response_model=List[schemas.ActionHistoryResponse])
def list_logs(
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(3))
):
    query = db.query(models.ActionHistory)

    # Filter logic if a user_id is provided
    if user_id:
        query = query.filter(models.ActionHistory.UserID == user_id)

    # Filter logic if an action_type is provided
    if action_type:
        query = query.filter(models.ActionHistory.ActionType.ilike(f"%{action_type}%"))

    # Order by newest first (Descending)
    query = query.order_by(models.ActionHistory.Timestamp.desc())

    # Execute the query with optional pagination
    return query.offset(skip).limit(limit).all()