from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone

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
    req = db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req

#########################################################
# UPDATE function for BlacklistRequest table
#########################################################
@router.put("/{request_id}", response_model=schemas.BlacklistRequestResponse)
def update_request(request_id: int, review_data: schemas.BlacklistRequestUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    db_request = db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Verify the moderator exists
    moderator = db.query(models.UserAccount).filter(models.UserAccount.UserID == review_data.ReviewedBy).first()
    if not moderator:
        raise HTTPException(status_code=404, detail="Moderator Account not found")

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
    db_request = db.query(models.BlacklistRequest).filter(models.BlacklistRequest.RequestID == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
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
            "FullName": req.requester.details.FullName if req.requester and req.requester.details else "N/A",
            "URLDomain": req.URLDomain,
            "Status": req.Status.value if req.Status else None,
            "ReviewedBy": req.ReviewedBy,
            "ReviewedByFullName": req.reviewer.details.FullName if req.reviewer and req.reviewer.details else None,
            "CreatedAt": req.CreatedAt,
            "ReviewedAt": req.ReviewedAt,
        }
        for req in results
    ]