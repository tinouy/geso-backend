from sqlalchemy import Column, String, Integer, Date, DateTime, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class MemberType(Base):
    __tablename__ = "member_types"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(String, default="true", nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Member(Base):
    __tablename__ = "members"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    member_number = Column(Integer, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    identity_document = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    is_bjcp_judge = Column(String, default="false", nullable=False)  # "true" o "false" como string
    business_name = Column(String, nullable=True)  # Solo para ADHERENTE
    member_type_id = Column(String, ForeignKey("member_types.id"), nullable=False)
    last_payment_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    member_type = relationship("MemberType", backref="members")


class ClubConfig(Base):
    __tablename__ = "club_config"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    club_name = Column(String, nullable=False)
    annual_fee_amount = Column(Float, nullable=False, default=1000.0)
    period_type = Column(String, nullable=False, default="yearly")  # yearly o december_to_december
    prorrate_type = Column(String, nullable=False, default="monthly")  # monthly, bimonthly, quarterly, fourmonthly
    initialized = Column(String, default="false", nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

