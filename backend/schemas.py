from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Base properties shared across all operations
class UserRoleBase(BaseModel):
    RoleName: str
    RoleDescription: Optional[str] = None
    IsActive: Optional[bool] = True

# Used for Creating (POST)
class UserRoleCreate(UserRoleBase):
    pass

# Used for Updating (PUT) - Everything is optional
class UserRoleUpdate(BaseModel):
    RoleName: Optional[str] = None
    RoleDescription: Optional[str] = None
    IsActive: Optional[bool] = None

# Used for Reading/Listing (GET) - Includes the ID and Timestamps
class UserRoleResponse(UserRoleBase):
    RoleID: int
    CreatedAt: datetime
    UpdatedAt: datetime

    class Config:
        from_attributes = True # Tells Pydantic to read SQLAlchemy models