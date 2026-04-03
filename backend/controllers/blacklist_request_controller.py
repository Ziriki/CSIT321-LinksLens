from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from utils import get_fullname, get_or_404

# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

# Create a router for this controller
router = APIRouter(
    prefix="/api/blacklist-requests",
    tags=["Blacklist Requests"]
)

_BLACKLIST_DAILY_LIMIT = 5

#########################################################
# CREATE function for BlacklistRequest table
#########################################################
@router.post("/", response_model=schemas.BlacklistRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(request: schemas.BlacklistRequestCreate, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    # Verify the user exists
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == request.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

    # Check if this exact domain is already pending (prevents spam)
    existing_req = db.query(models.BlacklistRequest).filter(
        models.BlacklistRequest.URLDomain == request.URLDomain,
        models.BlacklistRequest.Status == models.RequestStatus.PENDING
    ).first()
    if existing_req:
        raise HTTPException(status_code=400, detail="This domain is already pending review.")

    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    user_recent = db.query(models.BlacklistRequest).filter(
        models.BlacklistRequest.UserID == request.UserID,
        models.BlacklistRequest.CreatedAt >= one_day_ago,
    ).count()
    if user_recent >= _BLACKLIST_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="You can submit a maximum of 5 blacklist requests per day.")

    db_request = models.BlacklistRequest(
        UserID=request.UserID,
        URLDomain=request.URLDomain
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

#########################################################
# READ function for BlacklistRequest table (Get by ID)
#########################################################
@router.get("/{request_id}", response_model=schemas.BlacklistRequestResponse)
def read_request(request_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    req = get_or_404(db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first(), "Request not found")
    return req

#########################################################
# UPDATE function for BlacklistRequest table
#########################################################
@router.put("/{request_id}", response_model=schemas.BlacklistRequestResponse)
def update_request(request_id: int, review_data: schemas.BlacklistRequestUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    db_request = get_or_404(db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first(), "Request not found")

    # Verify the moderator exists
    get_or_404(db.query(models.UserAccount).filter(models.UserAccount.UserID == review_data.ReviewedBy).first(), "Moderator Account not found")

    # Update the status and reviewer info
    db_request.Status = review_data.Status
    db_request.ReviewedBy = review_data.ReviewedBy
    db_request.ReviewedAt = datetime.now(timezone.utc) # Automatically log the exact time of review

    if review_data.Status == models.RequestStatus.APPROVED:
        # Check if it already exists in URLRules to prevent crashing on duplicate
        existing_rule = db.query(models.URLRules).filter(models.URLRules.URLDomain == db_request.URLDomain).first()
        
        if not existing_rule:
            new_rule = models.URLRules(
                URLDomain=db_request.URLDomain,
                ListType=models.ListTypeEnum.BLACKLIST,
                AddedBy=review_data.ReviewedBy  # The moderator who approved it gets the credit
            )
            db.add(new_rule)

    db.commit()
    db.refresh(db_request)
    
    return db_request

#########################################################
# DELETE function for BlacklistRequest table
#########################################################
@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(request_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):
    db_request = get_or_404(db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first(), "Request not found")

    db.delete(db_request)
    db.commit()
    return None

#########################################################
# LIST function for BlacklistRequest table
#########################################################
@router.get("/", response_model=None)
def list_requests(
    status: Optional[models.RequestStatus] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1, 2))
):
    query = db.query(models.BlacklistRequest).options(
        joinedload(models.BlacklistRequest.requester).joinedload(models.UserAccount.details),
        joinedload(models.BlacklistRequest.reviewer).joinedload(models.UserAccount.details),
    )

    # Filter logic if a status is provided
    if status:
        query = query.filter(models.BlacklistRequest.Status == status)

    # Filter logic if a user_id is provided
    if user_id:
        query = query.filter(models.BlacklistRequest.UserID == user_id)

    # Oldest pending requests first, otherwise newest first
    if status == models.RequestStatus.PENDING:
        query = query.order_by(models.BlacklistRequest.CreatedAt.asc())
    else:
        query = query.order_by(models.BlacklistRequest.CreatedAt.desc())

    # Execute the query with optional pagination
    results = query.offset(skip).limit(limit).all()

    return [
        {
            "RequestID": req.RequestID,
            "UserID": req.UserID,
            "FullName": get_fullname(req.requester),
            "URLDomain": req.URLDomain,
            "Status": req.Status.value if req.Status else None,
            "ReviewedBy": req.ReviewedBy,
            "ReviewedByFullName": get_fullname(req.reviewer, default=None),
            "CreatedAt": req.CreatedAt,
            "ReviewedAt": req.ReviewedAt,
        }
        for req in results
    ]