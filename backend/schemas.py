from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import tldextract
import enum
from models import RequestStatus, ListTypeEnum, ScanStatusEnum, SuggestedStatusEnum


_PASSWORD_FIELDS = {"Password", "NewPassword"}

class TrimmedModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def strip_strings(cls, values):
        if isinstance(values, dict):
            return {k: v.strip() if isinstance(v, str) and k not in _PASSWORD_FIELDS else v for k, v in values.items()}
        return values

#########################################################
# Base properties of UserRole (used for both Create and Update)
#########################################################
class UserRoleBase(TrimmedModel):
    RoleName: str
    RoleDescription: Optional[str] = None
    IsActive: Optional[bool] = True

# Used for Creating (POST)
class UserRoleCreate(UserRoleBase):
    pass

# Used for Updating (PUT) - Everything is optional
class UserRoleUpdate(TrimmedModel):
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
class UserAccountBase(TrimmedModel):
    EmailAddress: EmailStr
    RoleID: int
    IsActive: Optional[bool] = True

# Used for Creating (Requires a raw password)
class UserAccountCreate(UserAccountBase):
    Password: str 

# Used for Updating (Everything is optional, including password)
class UserAccountUpdate(TrimmedModel):
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
class UserDetailsBase(TrimmedModel):
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
class AppFeedbackBase(TrimmedModel):
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
class BlacklistRequestBase(TrimmedModel):
    URLDomain: str

# Used by standard users to submit a request
class BlacklistRequestCreate(BlacklistRequestBase):
    UserID: int

# Used by Moderators to approve or reject the request
class BlacklistRequestUpdate(TrimmedModel):
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
class URLRulesBase(TrimmedModel):
    URLDomain: str
    ListType: ListTypeEnum

    @field_validator("URLDomain", mode="before")
    @classmethod
    def normalize_url_domain(cls, v):
        if isinstance(v, str):
            extracted = tldextract.extract(v.strip())
            registered = extracted.registered_domain
            if registered:
                return registered
        return v

# Used when an Admin manually adds a rule
class URLRulesCreate(URLRulesBase):
    AddedBy: int

# Used for Updating
class URLRulesUpdate(TrimmedModel):
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
    RedirectChain: Optional[List[str]] = None
    StatusIndicator: Optional[ScanStatusEnum] = ScanStatusEnum.PENDING
    DomainAgeDays: Optional[int] = None
    ServerLocation: Optional[str] = None
    IpAddress: Optional[str] = None
    AsnName: Optional[str] = None
    PageTitle: Optional[str] = None
    ApexDomain: Optional[str] = None
    SslInfo: Optional[dict] = None
    ScreenshotURL: Optional[str] = None
    ScriptAnalysis: Optional[dict] = None
    HomographAnalysis: Optional[dict] = None
    GsbFlagged: Optional[bool] = False
    GsbThreatTypes: Optional[List[str]] = None
    Brands: Optional[List[str]] = None
    Tags: Optional[List[str]] = None

# Used when initiating a new scan
class ScanHistoryCreate(ScanHistoryBase):
    UserID: Optional[int] = None # Optional to support guest scans

# Used when the scanning engine finishes and updates the record
class ScanHistoryUpdate(BaseModel):
    RedirectURL: Optional[str] = None
    RedirectChain: Optional[List[str]] = None
    StatusIndicator: Optional[ScanStatusEnum] = None
    DomainAgeDays: Optional[int] = None
    ServerLocation: Optional[str] = None
    ScreenshotURL: Optional[str] = None

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
class ScanFeedbackBase(TrimmedModel):
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
    CreatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True

#########################################################
# Base properties of Login
#########################################################
class ClientTypeEnum(str, enum.Enum):
    WEB = "web"
    MOBILE = "mobile"

class UserLogin(TrimmedModel):
    EmailAddress: str
    Password: str
    ClientType: ClientTypeEnum

class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    message: str

#########################################################
# Base properties of Password Reset Token
#########################################################
class ForgotPasswordRequest(TrimmedModel):
    EmailAddress: EmailStr

class ResetPasswordRequest(TrimmedModel):
    Token: str
    NewPassword: str = Field(..., min_length=8)

class UserRegistrationRequest(TrimmedModel):
    EmailAddress: EmailStr
    Password: str = Field(..., min_length=8)
    FullName: str

class VerifyEmailRequest(TrimmedModel):
    Token: str
