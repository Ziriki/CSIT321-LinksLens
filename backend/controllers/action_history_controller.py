from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from utils import get_fullname, get_or_404
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/history",
    tags=["Action History"]
)

@router.post("/", response_model=schemas.ActionHistoryResponse, status_code=status.HTTP_201_CREATED)
def create_log(log: schemas.ActionHistoryCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and log.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only create logs for your own actions")

    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == log.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    db_log = models.ActionHistory(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/{log_id}", response_model=schemas.ActionHistoryResponse)
def read_log(log_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    log = get_or_404(db.query(models.ActionHistory).filter(models.ActionHistory.LogID == log_id).first(), "Log entry not found")
    return log

@router.get("/", response_model=None)
def list_logs(
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1))
):
    query = db.query(models.ActionHistory).options(
        joinedload(models.ActionHistory.account).joinedload(models.UserAccount.details)
    )

    if user_id:
        query = query.filter(models.ActionHistory.UserID == user_id)

    if action_type:
        query = query.filter(models.ActionHistory.ActionType.ilike(f"%{action_type}%"))

    query = query.order_by(models.ActionHistory.Timestamp.desc())

    results = query.offset(skip).limit(limit).all()

    return [
        {
            "LogID": log.LogID,
            "UserID": log.UserID,
            "FullName": get_fullname(log.account),
            "ActionType": log.ActionType,
            "Action": log.Action,
            "Timestamp": log.Timestamp,
        }
        for log in results
    ]