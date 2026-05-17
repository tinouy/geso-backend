from pydantic import BaseModel, EmailStr, field_validator, field_serializer
from typing import Optional, List, Union
from datetime import date, datetime
from models import UserRole
import re


# Schemas para usuarios
class UserBase(BaseModel):
    username: str
    email: EmailStr  # Para usuarios mantenemos EmailStr estricto


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class User(UserBase):
    id: str
    role: UserRole
    is_active: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Schemas para tipos de miembros
class MemberTypeBase(BaseModel):
    name: str
    description: Optional[str] = None


class MemberTypeCreate(MemberTypeBase):
    pass


class MemberTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class MemberType(MemberTypeBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Función para validar email de forma más permisiva
def validate_email(value: Optional[str]) -> Optional[str]:
    """Valida email, retorna None si es inválido."""
    if not value or value.strip() == "":
        return None
    # Validar formato básico de email
    email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
    if re.match(email_pattern, value.strip()):
        return value.strip()
    return None

# Schemas para miembros
class MemberBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    identity_document: Optional[str] = None
    phone_number: Optional[str] = None
    is_bjcp_judge: Optional[str] = "false"  # "true" o "false" como string
    business_name: Optional[str] = None  # Solo para ADHERENTE
    member_type_id: str
    last_payment_date: Optional[date] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return validate_email(v)


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    identity_document: Optional[str] = None
    phone_number: Optional[str] = None
    is_bjcp_judge: Optional[str] = None
    business_name: Optional[str] = None
    member_type_id: Optional[str] = None
    last_payment_date: Optional[date] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return validate_email(v)


class MemberBulkUpdate(BaseModel):
    member_ids: List[str]
    member_type_id: Optional[str] = None
    last_payment_date: Optional[date] = None


class Member(MemberBase):
    id: str
    member_number: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MemberWithType(Member):
    member_type: MemberType


# Schemas para configuración del club
class ClubConfigBase(BaseModel):
    club_name: str
    annual_fee_amount: float
    period_type: str  # yearly o december_to_december
    prorrate_type: str  # monthly, bimonthly, quarterly, fourmonthly


class ClubConfigCreate(ClubConfigBase):
    pass


class ClubConfigUpdate(BaseModel):
    club_name: Optional[str] = None
    annual_fee_amount: Optional[float] = None
    period_type: Optional[str] = None
    prorrate_type: Optional[str] = None


class ClubConfig(ClubConfigBase):
    id: str
    initialized: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Schemas para autenticación
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Schema para verificación pública de beneficios
class BenefitCheckResponse(BaseModel):
    member_number: int
    has_benefit: bool
    message: str

