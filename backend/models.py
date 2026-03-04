from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from Database import Base

class UserRole(Base):
    __tablename__ = "UserRole"

    RoleID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    RoleName = Column(String(50), nullable=False)
    RoleDescription = Column(String(255))
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime(timezone=True), server_default=func.now())
    UpdatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())