from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
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

#########################################################
# Base properties of UserDetails (used for both Create and Update)
#########################################################
class UserDetailsBase(BaseModel):
    FullName: Optional[str] = None
    PhoneNumber: Optional[str] = None
    Address: Optional[str] = None
    Gender: Optional[str] = None
    DateOfBirth: Optional[date] = None

# Used for Creating
class UserDetailsCreate(UserDetailsBase):
    UserID: int  # We must know WHICH account these details belong to!

# Used for Updating (UserID is in the URL, not the body)
class UserDetailsUpdate(UserDetailsBase):
    pass 

# Used for Responses
class UserDetailsResponse(UserDetailsBase):
    UserID: int
    CreatedAt: datetime
    UpdatedAt: datetime

    class Config:
        from_attributes = True

#########################################################
# Base properties of UserPreferences (used for both Create and Update)
#########################################################
class UserPreferencesBase(BaseModel):
    # This accepts a JSON object (dictionary in Python)
    Preferences: Dict[str, Any]

# Used for Creating
class UserPreferencesCreate(UserPreferencesBase):
    UserID: int

# Used for Updating
class UserPreferencesUpdate(UserPreferencesBase):
    pass 

# Used for Responses
class UserPreferencesResponse(UserPreferencesBase):
    UserID: int

    class Config:
        from_attributes = True

#########################################################
# Base properties of ActionHistory (used for both Create and Update)
#########################################################
class ActionHistoryBase(BaseModel):
    UserID: int
    ActionType: str
    Action: str

# Used for Creating
class ActionHistoryCreate(ActionHistoryBase):
    pass 

# Used for Responses
class ActionHistoryResponse(ActionHistoryBase):
    LogID: int
    Timestamp: datetime

    class Config:
        from_attributes = True

#########################################################
# Base properties of AppFeedback (used for both Create and Update)
#########################################################
class AppFeedbackBase(BaseModel):
    Feedback: str

# Used for Creating
class AppFeedbackCreate(AppFeedbackBase):
    UserID: int

# Used for Updating
class AppFeedbackUpdate(AppFeedbackBase):
    pass

# Used for Responses
class AppFeedbackResponse(AppFeedbackBase):
    FeedbackID: int
    UserID: int
    CreatedAt: datetime

    class Config:
        from_attributes = True