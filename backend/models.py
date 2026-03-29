from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, JSON, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import LONGTEXT
from database import Base
from pydantic import BaseModel, field_validator
from typing import Union
import enum

class UserRole(Base):
    __tablename__ = "UserRole"

    RoleID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    RoleName = Column(String(50), nullable=False)
    RoleDescription = Column(String(255))
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class UserAccount(Base):
    __tablename__ = "UserAccount"

    UserID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    EmailAddress = Column(String(255), unique=True, nullable=False)
    PasswordHash = Column(String(255), nullable=False)
    RoleID = Column(Integer, ForeignKey("UserRole.RoleID"), nullable=False)
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Set up a relationship for easier access to the role details from an account
    role = relationship("UserRole")
    details = relationship("UserDetails", uselist=False, back_populates="account")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")

class UserDetails(Base):
    __tablename__ = "UserDetails"

    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), primary_key=True)
    FullName = Column(String(255))
    PhoneNumber = Column(String(20))
    Address = Column(String(255))
    Gender = Column(String(6))
    DateOfBirth = Column(Date)
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Set up a relationship for easier access to the user account details
    account = relationship("UserAccount")

class UserPreferences(Base):
    __tablename__ = "UserPreferences"

    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), primary_key=True)
    Preferences = Column(JSON, nullable=False)

class ActionHistory(Base):
    __tablename__ = "ActionHistory"

    LogID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("UserAccount.UserID"), nullable=False)
    ActionType = Column(String(100), nullable=False)
    Action = Column(Text, nullable=False)
    Timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Set up a relationship for easier access to the user account details
    account = relationship("UserAccount")

class AppFeedback(Base):
    __tablename__ = "AppFeedback"

    FeedbackID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), nullable=False)
    Feedback = Column(Text, nullable=False)
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("UserAccount")


# Define the strict Enum for the BlacklistRequest status
class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class BlacklistRequest(Base):
    __tablename__ = "BlacklistRequest"

    RequestID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), nullable=False)
    URLDomain = Column(String(255), nullable=False)
    Status = Column(Enum(RequestStatus), default=RequestStatus.PENDING) # Use the Enum defined above. Default is always PENDING.
    ReviewedBy = Column(Integer, ForeignKey("UserAccount.UserID"), nullable=True) # This is null until a moderator actually reviews it  
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    ReviewedAt = Column(DateTime(timezone=True), nullable=True)

    # Set up relationships for easier access to the user account details (user and reviewer data)
    requester = relationship("UserAccount", foreign_keys=[UserID])
    reviewer = relationship("UserAccount", foreign_keys=[ReviewedBy])

# Define the strict Enum for the URL list type
class ListTypeEnum(str, enum.Enum):
    BLACKLIST = "BLACKLIST"
    WHITELIST = "WHITELIST"

class URLRules(Base):
    __tablename__ = "URLRules"

    RuleID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    URLDomain = Column(String(255), nullable=False, unique=True) # unique=True prevents duplicates
    ListType = Column(Enum(ListTypeEnum), nullable=False)
    AddedBy = Column(Integer, ForeignKey("UserAccount.UserID"), nullable=False) # Tracks which Admin or Moderator added this rule
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())

    # Set up relationship for easier access to the user account details (the admin's details)
    admin = relationship("UserAccount")

# Define the strict Enum for the scan status
class ScanStatusEnum(str, enum.Enum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS = "MALICIOUS"
    PENDING = "PENDING"

class ScanHistory(Base):
    __tablename__ = "ScanHistory"

    ScanID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), nullable=True) 
    InitialURL = Column(String(2048), nullable=False)
    RedirectURL = Column(String(2048), nullable=True)
    RedirectChain = Column(JSON, nullable=True)  # Ordered list of all redirect URLs
    StatusIndicator = Column(Enum(ScanStatusEnum), default=ScanStatusEnum.PENDING, nullable=False)
    DomainAgeDays = Column(Integer, nullable=True)
    ServerLocation = Column(String(100), nullable=True)
    ScreenshotURL = Column(String(2048), nullable=True)
    RawText = Column(LONGTEXT, nullable=True)
    AssociatedPerson = Column(String(255), nullable=True)
    ScannedAt = Column(DateTime(timezone=True), server_default=func.now())

    # Set up relationship for easier access to the user account details
    user = relationship("UserAccount")

# Define the strict Enum for the suggested status
class SuggestedStatusEnum(str, enum.Enum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS = "MALICIOUS"

class ScanFeedback(Base):
    __tablename__ = "ScanFeedback"

    FeedbackID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ScanID = Column(Integer, ForeignKey("ScanHistory.ScanID", ondelete="CASCADE"), nullable=False)
    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), nullable=False)
    SuggestedStatus = Column(Enum(SuggestedStatusEnum), nullable=False)
    Comments = Column(Text, nullable=True)
    IsResolved = Column(Boolean, default=False) # Allows moderators to check off feedback they have reviewed

    # Set up relationships for easier access to ScanHistory and UserAccount details
    scan = relationship("ScanHistory")
    user = relationship("UserAccount")


class ScanRequest(BaseModel):
    urls: Union[str, list[str]]

    @field_validator("urls")
    @classmethod
    def normalize_urls(cls, v):
        """Accept a single URL string or a list; always normalise to a list internally."""
        if isinstance(v, str):
            return [v]
        return v
    
class PasswordResetToken(Base):
    __tablename__ = "PasswordResetToken"

    TokenID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Token = Column(String(255), unique=True, nullable=False, index=True)
    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), nullable=False)
    ExpiresAt = Column(DateTime(timezone=True), nullable=False)
    IsUsed = Column(Boolean, default=False)
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserAccount", back_populates="reset_tokens")

class EmailVerificationToken(Base):
    __tablename__ = "EmailVerificationToken"

    TokenID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Token = Column(String(255), unique=True, nullable=False, index=True)
    UserID = Column(Integer, ForeignKey("UserAccount.UserID", ondelete="CASCADE"), nullable=False)
    ExpiresAt = Column(DateTime(timezone=True), nullable=False)
    IsUsed = Column(Boolean, default=False)
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserAccount", back_populates="verification_tokens")
