from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

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