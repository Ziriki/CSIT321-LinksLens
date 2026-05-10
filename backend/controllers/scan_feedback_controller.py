from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from utils import get_fullname, get_or_404
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/scan-feedback",
    tags=["Scan Feedback"]
)

############################################
# This function is to submit feedback for a scan, enforcing that the
# user can only submit feedback for their own scans and has not already
# submitted feedback for the same scan.
############################################
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

############################################
# This function is to retrieve a single scan feedback entry by ID,
# restricted to administrators and moderators.
############################################
@router.get("/{feedback_id}", response_model=schemas.ScanFeedbackResponse)
def read_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):  # 1 = Administrator, 2 = Moderator
    feedback = get_or_404(db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first(), "Feedback not found")
    return feedback

############################################
# This function is to update the resolved status of a scan feedback
# entry, restricted to administrators and moderators.
############################################
@router.put("/{feedback_id}", response_model=schemas.ScanFeedbackResponse)
def update_feedback(feedback_id: int, feedback_update: schemas.ScanFeedbackUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):  # 1 = Administrator, 2 = Moderator
    db_feedback = get_or_404(db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first(), "Feedback not found")

    if feedback_update.IsResolved is not None:
        db_feedback.IsResolved = feedback_update.IsResolved

    db.commit()
    db.refresh(db_feedback)
    return db_feedback

############################################
# This function is to permanently delete a scan feedback entry,
# restricted to administrators.
############################################
@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    db_feedback = get_or_404(db.query(models.ScanFeedback).filter(models.ScanFeedback.FeedbackID == feedback_id).first(), "Feedback not found")

    db.delete(db_feedback)
    db.commit()
    return None

############################################
# This function is to retrieve a filtered and paginated list of scan
# feedback entries with user details, restricted to administrators
# and moderators.
############################################
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

    if is_resolved is not None:
        query = query.filter(models.ScanFeedback.IsResolved == is_resolved)

    if scan_id:
        query = query.filter(models.ScanFeedback.ScanID == scan_id)

    if user_id:
        query = query.filter(models.ScanFeedback.UserID == user_id)

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

############################################
# This function is to retrieve a filtered and paginated list of scan
# feedback entries enriched with full scan details for the admin
# review panel, restricted to administrators and moderators.
############################################
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
            "CreatedAt": str(fb.CreatedAt) if fb.CreatedAt else None,
            # Extra fields for the admin detail panel
            "RedirectURL": fb.scan.RedirectURL if fb.scan else None,
            "RedirectChain": fb.scan.RedirectChain if fb.scan else None,
            "DomainAgeDays": fb.scan.DomainAgeDays if fb.scan else None,
            "ServerLocation": fb.scan.ServerLocation if fb.scan else None,
            "IpAddress": fb.scan.IpAddress if fb.scan else None,
            "AsnName": fb.scan.AsnName if fb.scan else None,
            "PageTitle": fb.scan.PageTitle if fb.scan else None,
            "ApexDomain": fb.scan.ApexDomain if fb.scan else None,
            "SslInfo": fb.scan.SslInfo if fb.scan else None,
            "ScreenshotURL": fb.scan.ScreenshotURL if fb.scan else None,
            "ScannedAt": str(fb.scan.ScannedAt) if fb.scan and fb.scan.ScannedAt else None,
            "ScriptAnalysis": fb.scan.ScriptAnalysis if fb.scan else None,
            "HomographAnalysis": fb.scan.HomographAnalysis if fb.scan else None,
        })

    return enriched