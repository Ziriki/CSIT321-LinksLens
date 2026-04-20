from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from urllib.parse import urlparse

from utils import get_fullname, get_or_404, apply_updates
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

_THREAT_STATUSES = [models.ScanStatusEnum.MALICIOUS, models.ScanStatusEnum.SUSPICIOUS]

router = APIRouter(
    prefix="/api/scans",
    tags=["Scan History"]
)

@router.post("/", response_model=schemas.ScanHistoryResponse, status_code=status.HTTP_201_CREATED)
def create_scan(scan: schemas.ScanHistoryCreate, db: Session = Depends(get_db)):
    if scan.UserID:
        account = db.query(models.UserAccount).filter(models.UserAccount.UserID == scan.UserID).first()
        if not account:
            raise HTTPException(status_code=404, detail="User Account not found")

    db_scan = models.ScanHistory(**scan.model_dump())
    db.add(db_scan)
    db.commit()
    db.refresh(db_scan)
    return db_scan

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

    aggregated: dict = {}
    for location, indicator, count in rows:
        if location not in aggregated:
            aggregated[location] = {"location": location, "malicious": 0, "suspicious": 0, "total": 0}
        key = indicator.value.lower()
        aggregated[location][key] = count
        aggregated[location]["total"] += count

    return list(aggregated.values())


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


@router.get("/{scan_id}", response_model=schemas.ScanHistoryResponse)
def read_scan(scan_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    scan = get_or_404(db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == scan_id).first(), "Scan not found")
    if current_user["role_id"] not in (1, 2) and scan.UserID != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan

@router.put("/{scan_id}", response_model=schemas.ScanHistoryResponse)
def update_scan(scan_id: int, scan_update: schemas.ScanHistoryUpdate, db: Session = Depends(get_db), current_user: dict = Depends(require_role(1, 2))):
    db_scan = get_or_404(db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == scan_id).first(), "Scan not found")
    apply_updates(db, db_scan, scan_update)

    new_status = scan_update.StatusIndicator
    if new_status in (models.ScanStatusEnum.MALICIOUS, models.ScanStatusEnum.SAFE):
        domain = urlparse(db_scan.InitialURL).netloc
        target_list_type = (
            models.ListTypeEnum.BLACKLIST if new_status == models.ScanStatusEnum.MALICIOUS
            else models.ListTypeEnum.WHITELIST
        )
        if domain:
            existing_rule = db.query(models.URLRules).filter(models.URLRules.URLDomain == domain).first()
            if existing_rule:
                if existing_rule.ListType != target_list_type:
                    existing_rule.ListType = target_list_type
                    existing_rule.AddedBy = current_user["user_id"]
                    db.commit()
            else:
                db.add(models.URLRules(
                    URLDomain=domain,
                    ListType=target_list_type,
                    AddedBy=current_user["user_id"]
                ))
                db.commit()

    return db_scan

@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(scan_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_scan = get_or_404(db.query(models.ScanHistory).filter(models.ScanHistory.ScanID == scan_id).first(), "Scan not found")
    if current_user["role_id"] not in (1, 2) and db_scan.UserID != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own scans")

    db.delete(db_scan)
    db.commit()
    return None

@router.get("/", response_model=None)
def list_scans(
    user_id: Optional[int] = None,
    status_indicator: Optional[models.ScanStatusEnum] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(models.ScanHistory).options(
        joinedload(models.ScanHistory.user).joinedload(models.UserAccount.details)
    )

    if current_user["role_id"] not in (1, 2):
        query = query.filter(models.ScanHistory.UserID == current_user["user_id"])
    elif user_id:
        query = query.filter(models.ScanHistory.UserID == user_id)

    if status_indicator:
        query = query.filter(models.ScanHistory.StatusIndicator == status_indicator)

    # Subquery avoids conflicts with the existing joinedload on UserAccount.details
    if search:
        matching_user_ids = db.query(models.UserDetails.UserID).filter(
            models.UserDetails.FullName.ilike(f"%{search}%")
        )
        query = query.filter(
            models.ScanHistory.InitialURL.ilike(f"%{search}%")
            | models.ScanHistory.UserID.in_(matching_user_ids)
        )

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

@router.delete("/clear/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_user_scans(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role_id"] not in (1, 2) and user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only clear your own scan history")

    get_or_404(db.query(models.UserAccount).filter(models.UserAccount.UserID == user_id).first(), "User Account not found")

    db.query(models.ScanHistory).filter(models.ScanHistory.UserID == user_id).delete()
    db.commit()
    
    return None