from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from utils import get_fullname
# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

# Create a router for this controller
router = APIRouter(
    prefix="/api/feedback",
    tags=["App Feedback"]
)

#########################################################
# CREATE function for AppFeedback table
#########################################################
@router.post("/", response_model=schemas.AppFeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(feedback: schemas.AppFeedbackCreate, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    # Verify the user exists before they can leave feedback
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

#########################################################
# READ function for AppFeedback table (Get by ID)
#########################################################
@router.get("/{feedback_id}", response_model=schemas.AppFeedbackResponse)
def read_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    feedback = db.query(models.AppFeedback).filter(models.AppFeedback.FeedbackID == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback

#########################################################
# UPDATE function for AppFeedback table
#########################################################
@router.put("/{feedback_id}", response_model=schemas.AppFeedbackResponse)
def update_feedback(feedback_id: int, feedback_update: schemas.AppFeedbackUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_feedback = db.query(models.AppFeedback).filter(models.AppFeedback.FeedbackID == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    db_feedback.Feedback = feedback_update.Feedback
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

#########################################################
# DELETE function for AppFeedback table
#########################################################
@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_feedback = db.query(models.AppFeedback).filter(models.AppFeedback.FeedbackID == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    db.delete(db_feedback)
    db.commit()
    return None

#########################################################
# LIST function for AppFeedback table
#########################################################
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

    # Filter logic if a user_id is provided
    if user_id:
        query = query.filter(models.AppFeedback.UserID == user_id)

    # Order by newest feedback first
    query = query.order_by(models.AppFeedback.CreatedAt.desc())

    # Execute the query with optional pagination
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