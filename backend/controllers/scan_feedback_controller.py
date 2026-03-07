from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

# Import custom files
import models
import schemas
from database import get_db

# Create a router for this controller
router = APIRouter(
    prefix="/api/scan-feedback",
    tags=["Scan Feedback"]
)

#########################################################
# CREATE function for ScanFeedback table
#########################################################
@router.post("/", response_model=schemas.ScanFeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(feedback: schemas.ScanFeedbackCreate, db: Session = Depends(get_db)):
    # Verify the user exists
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == feedback.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    # Verify the scan exists
    scan = db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == feedback.ScanID).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan History record not found")

    # Optional: Prevent duplicate feedback from the same user on the same scan
    existing_feedback = db.query(models.ScanFeedback).filter(
        models.ScanFeedback.ScanID == feedback.ScanID,
        models.ScanFeedback.UserID == feedback.UserID
    ).first()
    if existing_feedback:
        raise HTTPException(status_code=400, detail="You have already submitted feedback for this scan.")

    db_feedback = models.ScanFeedback(**feedback.model_dump())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

#########################################################
# READ function for ScanFeedback table (Get by ID)
#########################################################
@router.get("/{feedback_id}", response_model=schemas.ScanFeedbackResponse)
def read_feedback(feedback_id: int, db: Session = Depends(get_db)):
    feedback = db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback

#########################################################
# UPDATE function for ScanFeedback table
#########################################################
@router.put("/{feedback_id}", response_model=schemas.ScanFeedbackResponse)
def update_feedback(feedback_id: int, feedback_update: schemas.ScanFeedbackUpdate, db: Session = Depends(get_db)):
    db_feedback = db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Generally, we only update the 'IsResolved' status here.
    if feedback_update.IsResolved is not None:
        db_feedback.IsResolved = feedback_update.IsResolved

    db.commit()
    db.refresh(db_feedback)
    return db_feedback

#########################################################
# DELETE function for ScanFeedback table
#########################################################
@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    db_feedback = db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    db.delete(db_feedback)
    db.commit()
    return None

#########################################################
# LIST function for ScanFeedback table
#########################################################
@router.get("/", response_model=List[schemas.ScanFeedbackResponse])
def list_feedback(
    is_resolved: Optional[bool] = None, # Moderators can easily pull up all unresolved feedback
    scan_id: Optional[int] = None,      # See all feedback for one specific scan
    user_id: Optional[int] = None,      # See all feedback submitted by a specific user
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(models.ScanFeedback)

    # Filter logic if optional query parameters are provided
    if is_resolved is not None:
        query = query.filter(models.ScanFeedback.IsResolved == is_resolved)

    # Filter logic if scan_id is provided
    if scan_id:
        query = query.filter(models.ScanFeedback.ScanID == scan_id)

    # Filter logic if user_id is provided
    if user_id:
        query = query.filter(models.ScanFeedback.UserID == user_id)

    # Execute the query with optional pagination
    return query.offset(skip).limit(limit).all()