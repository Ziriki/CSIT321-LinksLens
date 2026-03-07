from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

# Import custom files
import models
import schemas
from database import get_db

# Create a router for this controller
router = APIRouter(
    prefix="/api/url-rules",
    tags=["URL Rules (Blacklist/Whitelist)"]
)

#########################################################
# CREATE function for URLRules table
#########################################################
@router.post("/", response_model=schemas.URLRulesResponse, status_code=status.HTTP_201_CREATED)
def create_rule(rule: schemas.URLRulesCreate, db: Session = Depends(get_db)):
    # Check if the admin/moderator exists
    account = db.query(models.UserAccount).filter(models.UserAccount.UserID == rule.AddedBy).first()
    if not account:
        raise HTTPException(status_code=404, detail="Admin/Moderator account not found")

    # Prevent duplicate domains in the master list
    existing_rule = db.query(models.URLRules).filter(models.URLRules.URLDomain == rule.URLDomain).first()
    if existing_rule:
        raise HTTPException(status_code=400, detail=f"Domain already exists in the {existing_rule.ListType.value}.")

    db_rule = models.URLRules(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

#########################################################
# READ function for URLRules table (Get by ID)
#########################################################
@router.get("/{rule_id}", response_model=schemas.URLRulesResponse)
def read_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(models.URLRules).filter(models.URLRules.RuleID == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

#########################################################
# UPDATE function for URLRules table
#########################################################
@router.put("/{rule_id}", response_model=schemas.URLRulesResponse)
def update_rule(rule_id: int, rule_update: schemas.URLRulesUpdate, db: Session = Depends(get_db)):
    db_rule = db.query(models.URLRules).filter(models.URLRules.RuleID == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # If updating the domain, ensure the new domain isn't already listed elsewhere
    if rule_update.URLDomain:
        duplicate_check = db.query(models.URLRules).filter(models.URLRules.URLDomain == rule_update.URLDomain).first()
        if duplicate_check and duplicate_check.RuleID != rule_id:
            raise HTTPException(status_code=400, detail="This domain is already in the master list.")

    update_data = rule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_rule, key, value)

    db.commit()
    db.refresh(db_rule)
    return db_rule

#########################################################
# DELETE function for URLRules table
#########################################################
@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    db_rule = db.query(models.URLRules).filter(models.URLRules.RuleID == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(db_rule)
    db.commit()
    return None

#########################################################
# LIST function for URLRules table
#########################################################
@router.get("/", response_model=List[schemas.URLRulesResponse])
def list_rules(
    list_type: Optional[models.ListTypeEnum] = None, # Easily fetch by the list typex (Blacklist or Whitelist)
    search_domain: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(models.URLRules)

    # Filter logic if a list_type is provided
    if list_type:
        query = query.filter(models.URLRules.ListType == list_type)

    # Filter logic if a search_domain is provided
    if search_domain:
        query = query.filter(models.URLRules.URLDomain.ilike(f"%{search_domain}%"))

    # Execute the query with optional pagination
    return query.offset(skip).limit(limit).all()