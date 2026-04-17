from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from utils import get_fullname, get_or_404, apply_updates
import models
import schemas
from database import get_db
from dependencies import get_current_user, require_role

router = APIRouter(
    prefix="/api/url-rules",
    tags=["URL Rules (Blacklist/Whitelist)"]
)

@router.post("/", response_model=schemas.URLRulesResponse, status_code=status.HTTP_201_CREATED)
def create_rule(rule: schemas.URLRulesCreate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == rule.AddedBy).first()
    if not account:
        raise HTTPException(status_code=404, detail="Admin/Moderator account not found")

    existing_rule = db.query(models.URLRules).filter(models.URLRules.URLDomain == rule.URLDomain).first()
    if existing_rule:
        raise HTTPException(status_code=400, detail=f"Domain already exists in the {existing_rule.ListType.value}.")

    db_rule = models.URLRules(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.get("/{rule_id}", response_model=schemas.URLRulesResponse)
def read_rule(rule_id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    rule = get_or_404(db.query(models.URLRules).filter(models.URLRules.RuleID == rule_id).first(), "Rule not found")
    return rule

@router.put("/{rule_id}", response_model=schemas.URLRulesResponse)
def update_rule(rule_id: int, rule_update: schemas.URLRulesUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    db_rule = get_or_404(db.query(models.URLRules).filter(models.URLRules.RuleID == rule_id).first(), "Rule not found")

    if rule_update.URLDomain:
        duplicate_check = db.query(models.URLRules).filter(models.URLRules.URLDomain == rule_update.URLDomain).first()
        if duplicate_check and duplicate_check.RuleID != rule_id:
            raise HTTPException(status_code=400, detail="This domain is already in the master list.")

    apply_updates(db, db_rule, rule_update)
    return db_rule

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1, 2))):
    db_rule = get_or_404(db.query(models.URLRules).filter(models.URLRules.RuleID == rule_id).first(), "Rule not found")

    db.delete(db_rule)
    db.commit()
    return None

@router.get("/", response_model=None)
def list_rules(
    list_type: Optional[models.ListTypeEnum] = None,
    search_domain: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    query = db.query(models.URLRules).options(
        joinedload(models.URLRules.admin).joinedload(models.UserAccount.details)
    )

    if list_type:
        query = query.filter(models.URLRules.ListType == list_type)

    if search_domain:
        query = query.filter(models.URLRules.URLDomain.ilike(f"%{search_domain}%"))

    results = query.offset(skip).limit(limit).all()

    return [
        {
            "RuleID": rule.RuleID,
            "URLDomain": rule.URLDomain,
            "ListType": rule.ListType.value if rule.ListType else None,
            "AddedBy": rule.AddedBy,
            "AddedByFullName": get_fullname(rule.admin),
            "CreatedAt": rule.CreatedAt,
        }
        for rule in results
    ]