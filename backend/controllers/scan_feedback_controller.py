from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from utils import get_fullname, get_or_404
# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

# Create a router for this controller
router = APIRouter(
    prefix="/api/scan-feedback",
    tags=["Scan Feedback"]
)

#########################################################
# CREATE function for ScanFeedback table
#########################################################
@router.post("/", response_model=schemas.ScanFeedbackResponse, status_code=status.HTTP_201_CREATED)
def create_feedback(feedback: schemas.ScanFeedbackCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    scan = get_or_404(db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == feedback.ScanID).first(), "Scan not found")

    if scan.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only submit feedback for your own scans.")

    existing_feedback = db.query(models.ScanFeedback).filter(
        models.ScanFeedback.ScanID == feedback.ScanID,
        models.ScanFeedback.UserID == current_user["user_id"],
    ).first()
    if existing_feedback:
        raise HTTPException(status_code=400, detail="You have already submitted feedback for this scan.")

    db_feedback = models.ScanFeedback(**{**feedback.model_dump(), "UserID": current_user["user_id"]})
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

#########################################################
# READ function for ScanFeedback table (Get by ID)
#########################################################
@router.get("/{feedback_id}", response_model=schemas.ScanFeedbackResponse)
def read_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    feedback = get_or_404(db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first(), "Feedback not found")
    return feedback

#########################################################
# UPDATE function for ScanFeedback table
#########################################################
@router.put("/{feedback_id}", response_model=schemas.ScanFeedbackResponse)
def update_feedback(feedback_id: int, feedback_update: schemas.ScanFeedbackUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    db_feedback = get_or_404(db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first(), "Feedback not found")

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
def delete_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_feedback = get_or_404(db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first(), "Feedback not found")

    db.delete(db_feedback)
    db.commit()
    return None

#########################################################
# LIST function for ScanFeedback table
#########################################################
@router.get("/", response_model=None)
def list_feedback(
    is_resolved: Optional[bool] = None,
    scan_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1, 2))
):
    query = db.query(models.ScanFeedback).options(
        joinedload(models.ScanFeedback.user).joinedload(models.UserAccount.details)
    )

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
    results = query.offset(skip).limit(limit).all()

    return [
        {
            "FeedbackID": fb.FeedbackID,
            "ScanID": fb.ScanID,
            "UserID": fb.UserID,
            "FullName": get_fullname(fb.user),
            "SuggestedStatus": fb.SuggestedStatus.value if fb.SuggestedStatus else None,
            "Comments": fb.Comments,
            "IsResolved": fb.IsResolved,
        }
        for fb in results
    ]

#########################################################
# LIST ENRICHED — returns feedback with joined scan + user info
#########################################################
@router.get("/enriched/", response_model=None)
def list_feedback_enriched(
    is_resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1, 2))
):
    query = db.query(models.ScanFeedback).options(
        joinedload(models.ScanFeedback.scan),
        joinedload(models.ScanFeedback.user).joinedload(models.UserAccount.details)
    )

    if is_resolved is not None:
        query = query.filter(models.ScanFeedback.IsResolved == is_resolved)

    results = query.order_by(models.ScanFeedback.FeedbackID.desc()).offset(skip).limit(limit).all()

    enriched = []
    for fb in results:
        enriched.append({
            "FeedbackID": fb.FeedbackID,
            "ScanID": fb.ScanID,
            "UserID": fb.UserID,
            "UserEmail": fb.user.EmailAddress if fb.user else "Unknown",
            "UserName": get_fullname(fb.user),
            "InitialURL": fb.scan.InitialURL if fb.scan else "N/A",
            "CurrentStatus": fb.scan.StatusIndicator.value if fb.scan and fb.scan.StatusIndicator else "N/A",
            "SuggestedStatus": fb.SuggestedStatus.value if fb.SuggestedStatus else "N/A",
            "Comments": fb.Comments or "",
            "IsResolved": fb.IsResolved,
            # Extra scan details for the drill-down panel
            "RedirectURL": fb.scan.RedirectURL if fb.scan else None,
            "DomainAgeDays": fb.scan.DomainAgeDays if fb.scan else None,
            "ServerLocation": fb.scan.ServerLocation if fb.scan else None,
            "ScreenshotURL": fb.scan.ScreenshotURL if fb.scan else None,
            "ScannedAt": str(fb.scan.ScannedAt) if fb.scan and fb.scan.ScannedAt else None,
        })

    return enriched