from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

#########################################################
# Base properties of UserRole (used for both Create and Update)
#########################################################
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

#########################################################
# Base properties of UserAccount (used for both Create and Update)
#########################################################
class UserAccountBase(BaseModel):
    EmailAddress: EmailStr
    RoleID: int
    IsActive: Optional[bool] = True

# Used for Creating (Requires a raw password)
class UserAccountCreate(UserAccountBase):
    Password: str 

# Used for Updating (Everything is optional, including password)
class UserAccountUpdate(BaseModel):
    EmailAddress: Optional[EmailStr] = None
    RoleID: Optional[int] = None
    Password: Optional[str] = None
    IsActive: Optional[bool] = None

# Used for Responses (Excludes password)
class UserAccountResponse(UserAccountBase):
    UserID: int
    CreatedAt: datetime
    UpdatedAt: datetime

    class Config:
        from_attributes = True