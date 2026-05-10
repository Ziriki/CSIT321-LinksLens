from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from utils import get_fullname, get_or_404

import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/blacklist-requests",
    tags=["Blacklist Requests"]
)

_BLACKLIST_DAILY_LIMIT = 5

############################################
# This function is to submit a new blacklist request after verifying
# the user exists, checking for duplicate pending requests, and
# enforcing a daily submission limit of 5 per user.
############################################
@router.post("/", response_model=schemas.BlacklistRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(request: schemas.BlacklistRequestCreate, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == request.UserID).first()
    if not account:
        raise HTTPException(status_code=404, detail="User Account not found")

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

############################################
# This function is to retrieve a single blacklist request by ID,
# restricted to administrators and moderators.
############################################
@router.get("/{request_id}", response_model=schemas.BlacklistRequestResponse)
def read_request(request_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):  # 1 = Administrator, 2 = Moderator
    req = get_or_404(db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first(), "Request not found")
    return req

############################################
# This function is to update the status of a blacklist request and
# automatically create a URLRules BLACKLIST entry when the request
# is approved, restricted to administrators and moderators.
############################################
@router.put("/{request_id}", response_model=schemas.BlacklistRequestResponse)
def update_request(request_id: int, review_data: schemas.BlacklistRequestUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):  # 1 = Administrator, 2 = Moderator
    db_request = get_or_404(db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first(), "Request not found")

    get_or_404(db.query(models.UserAccount).filter(models.UserAccount.UserID == review_data.ReviewedBy).first(), "Moderator Account not found")

    db_request.Status = review_data.Status
    db_request.ReviewedBy = review_data.ReviewedBy
    db_request.ReviewedAt = datetime.now(timezone.utc)

    if review_data.Status == models.RequestStatus.APPROVED:
        # Guard against duplicate in URLRules — the domain may already be listed
        existing_rule = db.query(models.URLRules).filter(models.URLRules.URLDomain == db_request.URLDomain).first()

        if not existing_rule:
            new_rule = models.URLRules(
                URLDomain=db_request.URLDomain,
                ListType=models.ListTypeEnum.BLACKLIST,
                AddedBy=review_data.ReviewedBy
            )
            db.add(new_rule)

    db.commit()
    db.refresh(db_request)
    
    return db_request

############################################
# This function is to permanently delete a blacklist request record,
# restricted to administrators.
############################################
@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(request_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    db_request = get_or_404(db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first(), "Request not found")

    db.delete(db_request)
    db.commit()
    return None

############################################
# This function is to retrieve a filtered and paginated list of
# blacklist requests with requester and reviewer details, restricted
# to administrators and moderators.
############################################
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

    if status:
        query = query.filter(models.BlacklistRequest.Status == status)

    if user_id:
        query = query.filter(models.BlacklistRequest.UserID == user_id)

    # Oldest pending first so reviewers work the queue in order
    if status == models.RequestStatus.PENDING:
        query = query.order_by(models.BlacklistRequest.CreatedAt.asc())
    else:
        query = query.order_by(models.BlacklistRequest.CreatedAt.desc())

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