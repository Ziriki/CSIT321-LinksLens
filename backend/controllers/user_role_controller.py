from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

# Import custom files
import models
import schemas
from database import get_db

# Create a router for this controller
router = APIRouter(
    prefix="/api/roles",
    tags=["User Roles"]
)

#########################################################
# CREATE function for UserRole table
#########################################################
@router.post("/", response_model=schemas.UserRoleResponse)
def create_role(role: schemas.UserRoleCreate, db: Session = Depends(get_db)):
    # Check if the RoleName already exists
    existing_role = db.query(models.UserRole).filter(models.UserRole.RoleName == role.RoleName).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="A role with this name already exists")

    # Create a new SQLAlchemy model instance
    db_role = models.UserRole(
        RoleName=role.RoleName,
        RoleDescription=role.RoleDescription,
        IsActive=role.IsActive
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

#########################################################
# READ function for UserRole table (Get by ID)
#########################################################
@router.get("/{role_id}", response_model=schemas.UserRoleResponse)
def read_role(role_id: int, db: Session = Depends(get_db)):
    # Look up a specific role by ID (FastAPI guarantees role_id is a valid integer)
    role = db.query(models.UserRole).filter(models.UserRole.RoleID == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

#########################################################
# UPDATE function for UserRole table
#########################################################
@router.put("/{role_id}", response_model=schemas.UserRoleResponse)
def update_role(role_id: int, role_update: schemas.UserRoleUpdate, db: Session = Depends(get_db)):
    # Find the existing role
    db_role = db.query(models.UserRole).filter(models.UserRole.RoleID == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Ensure the new RoleName is not the same as existing role
    if role_update.RoleName:
        name_check = db.query(models.UserRole).filter(models.UserRole.RoleName == role_update.RoleName).first()
        if name_check and name_check.RoleID != role_id:
            raise HTTPException(status_code=400, detail="Name already in use by another role")
    
    # Update only the provided fields (exclude_unset=True ignores fields that were not sent in the request)
    update_data = role_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_role, key, value)
        
    db.commit()
    db.refresh(db_role)
    return db_role

#########################################################
# DELETE function for UserRole table (Soft Delete)
#########################################################
@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: int, db: Session = Depends(get_db)):
    # Find the existing role
    db_role = db.query(models.UserRole).filter(models.UserRole.RoleID == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Soft Delete
    db_role.IsActive = False
    db.commit()
    
    return None  # 204 No Content does not return a body

#########################################################
# LIST function for UserRole table
#########################################################
@router.get("/", response_model=List[schemas.UserRoleResponse])
def list_roles(
    search: Optional[str] = None, # Optional search parameter
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    # Start with a base query
    query = db.query(models.UserRole).filter(models.UserRole.IsActive == True)

    # Filter logic if a search term is provided
    if search:
        # .ilike() provides case-insensitive matching in MySQL
        query = query.filter(models.UserRole.RoleName.ilike(f"%{search}%"))

    # Execute the query with optional pagination
    return query.offset(skip).limit(limit).all()
