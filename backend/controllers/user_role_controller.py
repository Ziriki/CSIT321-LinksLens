from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

import models
import schemas
from database import get_db
from dependencies import require_role
from utils import get_or_404, apply_updates

router = APIRouter(
    prefix="/api/roles",
    tags=["User Roles"]
)

############################################
# This function is to create a new user role after verifying no role
# with the same name already exists, restricted to administrators.
############################################
@router.post("/", response_model=schemas.UserRoleResponse)
def create_role(role: schemas.UserRoleCreate, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    existing_role = db.query(models.UserRole).filter(models.UserRole.RoleName == role.RoleName).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="A role with this name already exists")

    db_role = models.UserRole(
        RoleName=role.RoleName,
        RoleDescription=role.RoleDescription,
        IsActive=role.IsActive
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

############################################
# This function is to retrieve a single user role by ID, restricted
# to administrators.
############################################
@router.get("/{role_id}", response_model=schemas.UserRoleResponse)
def read_role(role_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    role = get_or_404(db.query(models.UserRole).filter(models.UserRole.RoleID == role_id).first(), "Role not found")
    return role

############################################
# This function is to update a user role's fields, checking for name
# conflicts with other roles, restricted to administrators.
############################################
@router.put("/{role_id}", response_model=schemas.UserRoleResponse)
def update_role(role_id: int, role_update: schemas.UserRoleUpdate, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    db_role = get_or_404(db.query(models.UserRole).filter(models.UserRole.RoleID == role_id).first(), "Role not found")

    if role_update.RoleName:
        name_check = db.query(models.UserRole).filter(models.UserRole.RoleName == role_update.RoleName).first()
        if name_check and name_check.RoleID != role_id:
            raise HTTPException(status_code=400, detail="Name already in use by another role")
    
    apply_updates(db, db_role, role_update)
    return db_role

############################################
# This function is to soft-deactivate a user role by setting IsActive
# to False, restricted to administrators.
############################################
@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: int, db: Session = Depends(get_db), _: dict = Depends(require_role(1))):  # 1 = Administrator
    db_role = get_or_404(db.query(models.UserRole).filter(models.UserRole.RoleID == role_id).first(), "Role not found")

    db_role.IsActive = False
    db.commit()
    return None

############################################
# This function is to retrieve a filtered and paginated list of active
# user roles, restricted to administrators.
############################################
@router.get("/", response_model=List[schemas.UserRoleResponse])
def list_roles(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_role(1))
):
    query = db.query(models.UserRole).filter(models.UserRole.IsActive == True)

    if search:
        query = query.filter(models.UserRole.RoleName.ilike(f"%{search}%"))

    return query.offset(skip).limit(limit).all()
