from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_active_user, require_admin
from schemas import MemberType, MemberTypeCreate, MemberTypeUpdate
from models import MemberType as MemberTypeModel
from models import User

router = APIRouter(prefix="/api/member-types", tags=["member-types"])


@router.post("", response_model=MemberType, dependencies=[Depends(require_admin)])
async def create_member_type(
    member_type: MemberTypeCreate,
    db: Session = Depends(get_db)
):
    """Crea un nuevo tipo de socio (solo admin)."""
    db_member_type = db.query(MemberTypeModel).filter(
        MemberTypeModel.name == member_type.name
    ).first()
    if db_member_type:
        raise HTTPException(status_code=400, detail="Member type name already exists")
    
    db_member_type = MemberTypeModel(
        name=member_type.name,
        description=member_type.description
    )
    db.add(db_member_type)
    db.commit()
    db.refresh(db_member_type)
    return db_member_type


@router.get("", response_model=List[MemberType])
async def list_member_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos los tipos de socios."""
    member_types = db.query(MemberTypeModel).all()
    return member_types


@router.get("/{member_type_id}", response_model=MemberType)
async def get_member_type(
    member_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene un tipo de socio por ID."""
    member_type = db.query(MemberTypeModel).filter(MemberTypeModel.id == member_type_id).first()
    if not member_type:
        raise HTTPException(status_code=404, detail="Member type not found")
    return member_type


@router.put("/{member_type_id}", response_model=MemberType, dependencies=[Depends(require_admin)])
async def update_member_type(
    member_type_id: str,
    member_type_update: MemberTypeUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza un tipo de socio (solo admin)."""
    member_type = db.query(MemberTypeModel).filter(MemberTypeModel.id == member_type_id).first()
    if not member_type:
        raise HTTPException(status_code=404, detail="Member type not found")
    
    update_data = member_type_update.dict(exclude_unset=True)
    
    # Si se cambia el nombre, verificar que no existe otro con ese nombre
    if "name" in update_data and update_data["name"] != member_type.name:
        existing = db.query(MemberTypeModel).filter(MemberTypeModel.name == update_data["name"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Member type name already exists")
    
    for field, value in update_data.items():
        setattr(member_type, field, value)
    
    db.commit()
    db.refresh(member_type)
    return member_type


@router.delete("/{member_type_id}", dependencies=[Depends(require_admin)])
async def delete_member_type(
    member_type_id: str,
    db: Session = Depends(get_db)
):
    """Elimina un tipo de socio (solo admin)."""
    member_type = db.query(MemberTypeModel).filter(MemberTypeModel.id == member_type_id).first()
    if not member_type:
        raise HTTPException(status_code=404, detail="Member type not found")
    
    # Verificar que no haya socios usando este tipo
    from models import Member
    members_count = db.query(Member).filter(Member.member_type_id == member_type_id).count()
    if members_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete member type: {members_count} members are using it"
        )
    
    db.delete(member_type)
    db.commit()
    return {"message": "Member type deleted successfully"}

