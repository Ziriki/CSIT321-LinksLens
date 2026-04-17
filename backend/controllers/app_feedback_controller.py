from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from utils import get_fullname, get_or_404, apply_updates
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/feedback",
    tags=["App Feedback"]
)

@router.post("/", response_model=schemas.AppFeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(feedback: schemas.AppFeedbackCreate, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == feedback.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    db_feedback = models.AppFeedback(
        UserID=feedback.UserID,
        Feedback=feedback.Feedback
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.get("/{feedback_id}", response_model=schemas.AppFeedbackResponse)
def read_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    feedback = get_or_404(db.query(models.AppFeedback).filter(models.AppFeedback.FeedbackID == feedback_id).first(), "Feedback not found")
    return feedback

@router.put("/{feedback_id}", response_model=schemas.AppFeedbackResponse)
def update_feedback(feedback_id: int, feedback_update: schemas.AppFeedbackUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_feedback = get_or_404(db.query(models.AppFeedback).filter(models.AppFeedback.FeedbackID == feedback_id).first(), "Feedback not found")
    apply_updates(db, db_feedback, feedback_update)
    return db_feedback

@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_feedback = get_or_404(db.query(models.AppFeedback).filter(models.AppFeedback.FeedbackID == feedback_id).first(), "Feedback not found")

    db.delete(db_feedback)
    db.commit()
    return None

@router.get("/", response_model=None)
def list_feedback(
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1))
):
    query = db.query(models.AppFeedback).options(
        joinedload(models.AppFeedback.account).joinedload(models.UserAccount.details)
    )

    if user_id:
        query = query.filter(models.AppFeedback.UserID == user_id)

    query = query.order_by(models.AppFeedback.CreatedAt.desc())

    results = query.offset(skip).limit(limit).all()

    return [
        {
            "FeedbackID": fb.FeedbackID,
            "UserID": fb.UserID,
            "FullName": get_fullname(fb.account),
            "Feedback": fb.Feedback,
            "CreatedAt": fb.CreatedAt,
        }
        for fb in results
    ]