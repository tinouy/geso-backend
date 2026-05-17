from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database import get_db
from auth import get_current_active_user
from schemas import Member, MemberCreate, MemberUpdate, MemberBulkUpdate, MemberWithType
from models import Member as MemberModel, MemberType
from models import User
import csv
import io

router = APIRouter(prefix="/api/members", tags=["members"])


def calculate_member_status(member: MemberModel) -> str:
    """Calcula el estado del socio basado en el último pago."""
    if not member.last_payment_date:
        return "INACTIVE"
    
    today = date.today()
    months_since_payment = (today.year - member.last_payment_date.year) * 12 + \
                          (today.month - member.last_payment_date.month)
    
    if months_since_payment <= 12:
        return "ACTIVE"
    else:
        return "INACTIVE"


@router.post("", response_model=Member)
async def create_member(
    member: MemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Crea un nuevo socio."""
    # Obtener el siguiente número de socio
    max_number = db.query(func.max(MemberModel.member_number)).scalar()
    if max_number is None:
        member_number = 660  # Valor inicial
    else:
        member_number = max_number + 1
    
    # Verificar que el tipo de socio existe
    member_type = db.query(MemberType).filter(MemberType.id == member.member_type_id).first()
    if not member_type:
        raise HTTPException(status_code=404, detail="Member type not found")
    
    db_member = MemberModel(
        member_number=member_number,
        first_name=member.first_name,
        last_name=member.last_name,
        email=member.email,
        identity_document=member.identity_document,
        phone_number=member.phone_number,
        is_bjcp_judge=member.is_bjcp_judge or "false",
        business_name=member.business_name,
        member_type_id=member.member_type_id,
        last_payment_date=member.last_payment_date
    )
    
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


@router.get("", response_model=List[MemberWithType])
async def list_members(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=50000),  # Aumentado para soportar "todos"
    search: str = Query(None),
    member_type_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista los socios con paginación y filtros."""
    query = db.query(MemberModel).options(joinedload(MemberModel.member_type))
    
    if search:
        from sqlalchemy import or_
        search_filter = f"%{search}%"
        search_conditions = [
            MemberModel.first_name.ilike(search_filter),
            MemberModel.last_name.ilike(search_filter),
            MemberModel.email.ilike(search_filter),
            MemberModel.identity_document.ilike(search_filter),
            MemberModel.phone_number.ilike(search_filter),
            MemberModel.business_name.ilike(search_filter),
        ]
        # Si es un número, también buscar por número de socio
        if search.isdigit():
            search_conditions.append(MemberModel.member_number == int(search))
        query = query.filter(or_(*search_conditions))
    
    if member_type_id:
        query = query.filter(MemberModel.member_type_id == member_type_id)
    
    members = query.order_by(MemberModel.member_number).offset(skip).limit(limit).all()
    
    # Incluir el tipo de socio en la respuesta
    result = []
    for member in members:
        member_dict = {
            **{c.name: getattr(member, c.name) for c in member.__table__.columns},
            "member_type": member.member_type
        }
        # Validar y limpiar email si es inválido
        if member_dict.get("email"):
            import re
            email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
            if not re.match(email_pattern, member_dict["email"]):
                member_dict["email"] = None
        
        result.append(MemberWithType(**member_dict))
    
    return result


@router.get("/export")
async def export_members(
    member_type_id: str = Query(None, description="ID del tipo de socio para filtrar (opcional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Exporta los socios a un archivo CSV.
    Si se proporciona member_type_id, exporta solo los socios de ese tipo.
    Si no se proporciona, exporta todos los socios.
    """
    # Construir query
    query = db.query(MemberModel)
    
    # Filtrar por tipo de socio si se proporciona
    if member_type_id:
        # Verificar que el tipo existe
        member_type = db.query(MemberType).filter(MemberType.id == member_type_id).first()
        if not member_type:
            raise HTTPException(status_code=404, detail="Member type not found")
        query = query.filter(MemberModel.member_type_id == member_type_id)
    
    # Obtener todos los miembros (sin paginación para la exportación)
    members = query.order_by(MemberModel.member_number).all()
    
    # Crear el contenido CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Escribir encabezados
    writer.writerow([
        'Número de Socio',
        'Nombre',
        'Apellido',
        'Email',
        'Teléfono',
        'Documento',
        'Tipo de Socio',
        'Juez BJCP',
        'Nombre Comercial',
        'Último Pago',
        'Fecha de Creación'
    ])
    
    # Escribir datos
    for member in members:
        writer.writerow([
            member.member_number,
            member.first_name,
            member.last_name,
            member.email or '',
            member.phone_number or '',
            member.identity_document or '',
            member.member_type.name if member.member_type else '',
            'Sí' if member.is_bjcp_judge == 'true' else 'No',
            member.business_name or '',
            member.last_payment_date.strftime('%Y-%m-%d') if member.last_payment_date else '',
            member.created_at.strftime('%Y-%m-%d %H:%M:%S') if member.created_at else ''
        ])
    
    # Generar nombre del archivo
    filename = 'socios'
    if member_type_id:
        member_type = db.query(MemberType).filter(MemberType.id == member_type_id).first()
        if member_type:
            filename = f'socios_{member_type.name.lower()}'
    
    filename = f'{filename}.csv'
    
    # Preparar respuesta con encoding UTF-8 BOM para Excel
    output.seek(0)
    content = '\ufeff' + output.getvalue()  # UTF-8 BOM para Excel
    output_bytes = io.BytesIO(content.encode('utf-8-sig'))
    
    return StreamingResponse(
        output_bytes,
        media_type='text/csv; charset=utf-8-sig',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@router.get("/{member_id}", response_model=MemberWithType)
async def get_member(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene un socio por ID."""
    member = db.query(MemberModel).options(joinedload(MemberModel.member_type)).filter(MemberModel.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    member_dict = {
        **{c.name: getattr(member, c.name) for c in member.__table__.columns},
        "member_type": member.member_type
    }
    # Validar y limpiar email si es inválido
    if member_dict.get("email"):
        import re
        email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
        if not re.match(email_pattern, member_dict["email"]):
            member_dict["email"] = None
    
    return MemberWithType(**member_dict)


@router.put("/{member_id}", response_model=Member)
async def update_member(
    member_id: str,
    member_update: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Actualiza un socio."""
    member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    update_data = member_update.dict(exclude_unset=True)
    
    # Si se cambia el tipo de socio, verificar que existe
    if "member_type_id" in update_data:
        member_type = db.query(MemberType).filter(MemberType.id == update_data["member_type_id"]).first()
        if not member_type:
            raise HTTPException(status_code=404, detail="Member type not found")
    
    # Si se actualiza la fecha de pago y no es NOVATO, actualizar tipo automáticamente
    if "last_payment_date" in update_data and update_data["last_payment_date"]:
        new_payment_date = update_data["last_payment_date"]
        if isinstance(new_payment_date, str):
            new_payment_date = date.fromisoformat(new_payment_date)
        
        today = date.today()
        months_since_payment = (today.year - new_payment_date.year) * 12 + \
                              (today.month - new_payment_date.month)
        
        # Si el pago es de los últimos 12 meses y no es NOVATO, cambiar a ACTIVO
        if months_since_payment <= 12:
            current_type = db.query(MemberType).filter(MemberType.id == member.member_type_id).first()
            if current_type and current_type.name != "NOVATO":
                # Buscar tipo ACTIVO
                active_type = db.query(MemberType).filter(MemberType.name == "ACTIVO").first()
                if active_type:
                    update_data["member_type_id"] = active_type.id
    
    for field, value in update_data.items():
        setattr(member, field, value)
    
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}")
async def delete_member(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Elimina un socio."""
    member = db.query(MemberModel).filter(MemberModel.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    return {"message": "Member deleted successfully"}


@router.post("/bulk-update")
async def bulk_update_members(
    bulk_update: MemberBulkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Actualiza múltiples socios a la vez."""
    members = db.query(MemberModel).filter(MemberModel.id.in_(bulk_update.member_ids)).all()
    
    if not members:
        raise HTTPException(status_code=404, detail="No members found")
    
    update_data = bulk_update.dict(exclude_unset=True, exclude={"member_ids"})
    
    for member in members:
        # Si se actualiza el tipo de socio, verificar que existe
        if "member_type_id" in update_data:
            member_type = db.query(MemberType).filter(MemberType.id == update_data["member_type_id"]).first()
            if not member_type:
                continue  # Saltar este miembro si el tipo no existe
        
        # Si se actualiza la fecha de pago y no es NOVATO, actualizar tipo automáticamente
        if "last_payment_date" in update_data and update_data["last_payment_date"]:
            new_payment_date = update_data["last_payment_date"]
            if isinstance(new_payment_date, str):
                new_payment_date = date.fromisoformat(new_payment_date)
            
            today = date.today()
            months_since_payment = (today.year - new_payment_date.year) * 12 + \
                                  (today.month - new_payment_date.month)
            
            # Si el pago es de los últimos 12 meses y no es NOVATO, cambiar a ACTIVO
            if months_since_payment <= 12:
                current_type = db.query(MemberType).filter(MemberType.id == member.member_type_id).first()
                if current_type and current_type.name != "NOVATO":
                    # Buscar tipo ACTIVO
                    active_type = db.query(MemberType).filter(MemberType.name == "ACTIVO").first()
                    if active_type:
                        update_data["member_type_id"] = active_type.id
        
        for field, value in update_data.items():
            setattr(member, field, value)
    
    db.commit()
    return {"message": f"Updated {len(members)} members successfully"}


