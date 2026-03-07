from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from models import RequestStatus, ListTypeEnum, ScanStatusEnum, SuggestedStatusEnum

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

#########################################################
# Base properties of BlacklistRequest (used for both Create and Update)
#########################################################
class BlacklistRequestBase(BaseModel):
    URLDomain: str

# Used by standard users to submit a request
class BlacklistRequestCreate(BlacklistRequestBase):
    UserID: int

# Used by Moderators to approve or reject the request
class BlacklistRequestUpdate(BaseModel):
    Status: RequestStatus
    ReviewedBy: int # The ID of the moderator reviewing it

# Used for Responses
class BlacklistRequestResponse(BlacklistRequestBase):
    RequestID: int
    UserID: int
    Status: RequestStatus
    ReviewedBy: Optional[int] = None
    CreatedAt: datetime
    ReviewedAt: Optional[datetime] = None

    class Config:
        from_attributes = True

#########################################################
# Base properties of URLRules (used for both Create and Update)
#########################################################
class URLRulesBase(BaseModel):
    URLDomain: str
    ListType: ListTypeEnum

# Used when an Admin manually adds a rule
class URLRulesCreate(URLRulesBase):
    AddedBy: int

# Used for Updating
class URLRulesUpdate(BaseModel):
    URLDomain: Optional[str] = None
    ListType: Optional[ListTypeEnum] = None

# Used for Responses
class URLRulesResponse(URLRulesBase):
    RuleID: int
    AddedBy: int
    CreatedAt: datetime

    class Config:
        from_attributes = True

#########################################################
# Base properties of ScanHistory (used for both Create and Update)
#########################################################
class ScanHistoryBase(BaseModel):
    InitialURL: str
    RedirectURL: Optional[str] = None
    StatusIndicator: Optional[ScanStatusEnum] = ScanStatusEnum.PENDING
    DomainAgeDays: Optional[int] = None
    ServerLocation: Optional[str] = None
    ScreenshotURL: Optional[str] = None
    RawText: Optional[str] = None
    AssociatedPerson: Optional[str] = None

# Used when initiating a new scan
class ScanHistoryCreate(ScanHistoryBase):
    UserID: Optional[int] = None # Optional to support guest scans

# Used when the scanning engine finishes and updates the record
class ScanHistoryUpdate(BaseModel):
    RedirectURL: Optional[str] = None
    StatusIndicator: Optional[ScanStatusEnum] = None
    DomainAgeDays: Optional[int] = None
    ServerLocation: Optional[str] = None
    ScreenshotURL: Optional[str] = None
    RawText: Optional[str] = None
    AssociatedPerson: Optional[str] = None

# Used for Responses
class ScanHistoryResponse(ScanHistoryBase):
    ScanID: int
    UserID: Optional[int] = None
    ScannedAt: datetime

    class Config:
        from_attributes = True

#########################################################
# Base properties of ScanFeedback (used for both Create and Update)
#########################################################
class ScanFeedbackBase(BaseModel):
    SuggestedStatus: SuggestedStatusEnum
    Comments: Optional[str] = None

# Used when a user submits new feedback
class ScanFeedbackCreate(ScanFeedbackBase):
    ScanID: int
    UserID: int

# Used by Moderators to mark feedback as resolved
class ScanFeedbackUpdate(BaseModel):
    IsResolved: Optional[bool] = None

# Used for Responses
class ScanFeedbackResponse(ScanFeedbackBase):
    FeedbackID: int
    ScanID: int
    UserID: int
    IsResolved: bool

    class Config:
        from_attributes = True

#########################################################
# Base properties of Login
#########################################################
class ClientTypeEnum(str, enum.Enum):
    WEB = "web"
    MOBILE = "mobile"

class UserLogin(BaseModel):
    EmailAddress: str
    Password: str
    ClientType: ClientTypeEnum

class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    message: str