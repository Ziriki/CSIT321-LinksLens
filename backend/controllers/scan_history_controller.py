from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from utils import get_fullname, get_or_404, apply_updates
# Import custom files
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

_THREAT_STATUSES = [models.ScanStatusEnum.MALICIOUS, models.ScanStatusEnum.SUSPICIOUS]

# Create a router for this controller
router = APIRouter(
    prefix="/api/scans",
    tags=["Scan History"]
)

#########################################################
# CREATE function for ScanHistory table
#########################################################
@router.post("/", response_model=schemas.ScanHistoryResponse, status_code=status.HTTP_201_CREATED)
def create_scan(scan: schemas.ScanHistoryCreate, db: Session = Depends(get_db)):
    # If a UserID is provided, verify they exist
    if scan.UserID:
        account = db.query(models.UserAccount).filter(models.UserAccount.UserID == scan.UserID).first()
        if not account:
            raise HTTPException(status_code=404, detail="User Account not found")

    db_scan = models.ScanHistory(**scan.model_dump())
    db.add(db_scan)
    db.commit()
    db.refresh(db_scan)
    return db_scan

#########################################################
# Stats: Per-country threat aggregation (Admin + Moderator)
#########################################################
@router.get("/stats/threats")
def get_threat_stats(db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    """Return per-country threat counts aggregated from ScanHistory."""
    rows = (
        db.query(
            models.ScanHistory.ServerLocation,
            models.ScanHistory.StatusIndicator,
            func.count().label("count"),
        )
        .filter(
            models.ScanHistory.ServerLocation.isnot(None),
            models.ScanHistory.StatusIndicator.in_(_THREAT_STATUSES),
        )
        .group_by(models.ScanHistory.ServerLocation, models.ScanHistory.StatusIndicator)
        .all()
    )

    # Aggregate into per-location dicts
    aggregated: dict = {}
    for location, indicator, count in rows:
        if location not in aggregated:
            aggregated[location] = {"location": location, "malicious": 0, "suspicious": 0, "total": 0}
        key = indicator.value.lower()
        aggregated[location][key] = count
        aggregated[location]["total"] += count

    return list(aggregated.values())


#########################################################
# Stats: Recent malicious/suspicious scans feed (Admin + Moderator)
#########################################################
@router.get("/stats/recent-threats")
def get_recent_threats(db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    """Return the last 20 MALICIOUS/SUSPICIOUS scans with defanged URLs."""
    scans = (
        db.query(models.ScanHistory)
        .filter(models.ScanHistory.StatusIndicator.in_(_THREAT_STATUSES))
        .order_by(models.ScanHistory.ScanID.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "url": scan.InitialURL.replace("https://", "hxxps://").replace("http://", "hxxp://"),
            "status": scan.StatusIndicator.value,
            "location": scan.ServerLocation,
            "scanned_at": scan.ScannedAt.isoformat() if scan.ScannedAt else None,
        }
        for scan in scans
    ]


#########################################################
# READ function for ScanHistory table (Get by ID)
#########################################################
@router.get("/{scan_id}", response_model=schemas.ScanHistoryResponse)
def read_scan(scan_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    scan = get_or_404(db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == scan_id).first(), "Scan not found")
    # Regular users can only view their own scans
    if current_user["role_id"] not in (1, 2) and scan.UserID != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan

#########################################################
# UPDATE function for ScanHistory table
#########################################################
@router.put("/{scan_id}", response_model=schemas.ScanHistoryResponse)
def update_scan(scan_id: int, scan_update: schemas.ScanHistoryUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    db_scan = get_or_404(db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == scan_id).first(), "Scan not found")
    apply_updates(db, db_scan, scan_update)
    return db_scan

#########################################################
# DELETE function for ScanHistory table
#########################################################
@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(scan_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_scan = get_or_404(db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == scan_id).first(), "Scan not found")
    # Regular users can only delete their own scans
    if current_user["role_id"] not in (1, 2) and db_scan.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own scans")

    db.delete(db_scan)
    db.commit()
    return None

#########################################################
# LIST function for ScanHistory table
#########################################################
@router.get("/", response_model=None)
def list_scans(
    user_id: Optional[int] = None,
    status_indicator: Optional[models.ScanStatusEnum] = None,
    search_url: Optional[str] = None,
    search_user: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(models.ScanHistory).options(
        joinedload(models.ScanHistory.user).joinedload(models.UserAccount.details)
    )

    # Regular users can only see their own scans — force the filter
    if current_user["role_id"] not in (1, 2):
        query = query.filter(models.ScanHistory.UserID == current_user["user_id"])
    elif user_id:
        query = query.filter(models.ScanHistory.UserID == user_id)

    # "As a user, I want to filter my scan history by status indicator"
    if status_indicator:
        query = query.filter(models.ScanHistory.StatusIndicator == status_indicator)

    # "As a user, I want to search my scan history by keywords"
    if search_url:
        query = query.filter(models.ScanHistory.InitialURL.ilike(f"%{search_url}%"))

    # Search by user full name (use outerjoin to avoid conflicts with joinedload)
    if search_user:
        query = query.filter(
            models.ScanHistory.UserID.in_(
                db.query(models.UserDetails.UserID).filter(
                    models.UserDetails.FullName.ilike(f"%{search_user}%")
                )
            )
        )

    # Always return newest scans first (by ScanID)
    query = query.order_by(models.ScanHistory.ScanID.desc())

    results = query.offset(skip).limit(limit).all()

    return [
        {
            "ScanID": scan.ScanID,
            "UserID": scan.UserID,
            "FullName": get_fullname(scan.user),
            "InitialURL": scan.InitialURL,
            "RedirectURL": scan.RedirectURL,
            "RedirectChain": scan.RedirectChain or [],
            "StatusIndicator": scan.StatusIndicator.value if scan.StatusIndicator else None,
            "DomainAgeDays": scan.DomainAgeDays,
            "ServerLocation": scan.ServerLocation,
            "IpAddress": scan.IpAddress,
            "AsnName": scan.AsnName,
            "PageTitle": scan.PageTitle,
            "ApexDomain": scan.ApexDomain,
            "SslInfo": scan.SslInfo,
            "ScreenshotURL": scan.ScreenshotURL,
            "ScriptAnalysis": scan.ScriptAnalysis,
            "HomographAnalysis": scan.HomographAnalysis,
            "ScannedAt": scan.ScannedAt,
        }
        for scan in results
    ]

#########################################################
# DELETE ALL function for ScanHistory table
#########################################################
# "As a user, I want to clear my entire scan history so that I can protect my privacy"
@router.delete("/clear/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_user_scans(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Regular users can only clear their own scan history
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only clear your own scan history")

    get_or_404(db.query(models.UserAccount).filter(models.UserAccount.UserID == user_id).first(), "User Account not found")

    # Delete all scans belonging to this user
    db.query(models.ScanHistory).filter(models.ScanHistory.UserID == user_id).delete()
    db.commit()
    
    return None