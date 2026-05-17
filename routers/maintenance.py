"""Rutas para mantenimiento automático del sistema."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
from database import get_db
from auth import get_current_active_user, require_admin
from models import Member as MemberModel, MemberType, User
from routers.members import calculate_member_status

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.post("/update-member-statuses")
async def update_member_statuses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Actualiza los estados de los socios basándose en la fecha de último pago.
    Los socios que tengan más de 12 meses sin pagar pasan a PENDIENTE.
    """
    today = date.today()
    updated_count = 0
    
    # Obtener todos los socios activos que no sean NOVATO, PENDIENTE, o tipos de baja
    active_types = db.query(MemberType).filter(
        MemberType.name.in_(["ACTIVO", "HONORARIO", "ADHERENTE", "REINGRESO"])
    ).all()
    
    active_type_ids = [mt.id for mt in active_types]
    pendiente_type = db.query(MemberType).filter(MemberType.name == "PENDIENTE").first()
    novato_type = db.query(MemberType).filter(MemberType.name == "NOVATO").first()
    
    if not pendiente_type:
        raise HTTPException(status_code=500, detail="Tipo de socio PENDIENTE no encontrado")
    
    if not novato_type:
        raise HTTPException(status_code=500, detail="Tipo de socio NOVATO no encontrado")
    
    # Buscar socios activos con último pago mayor a 12 meses
    members = db.query(MemberModel).filter(
        MemberModel.member_type_id.in_(active_type_ids),
        MemberModel.last_payment_date.isnot(None)
    ).all()
    
    for member in members:
        if member.last_payment_date:
            months_since_payment = (today.year - member.last_payment_date.year) * 12 + \
                                  (today.month - member.last_payment_date.month)
            
            # Si pasaron más de 12 meses y no es NOVATO, cambiar a PENDIENTE
            if months_since_payment > 12 and member.member_type_id != novato_type.id:
                member.member_type_id = pendiente_type.id
                updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Actualizados {updated_count} socios a estado PENDIENTE",
        "updated_count": updated_count
    }


@router.get("/status-update-info")
async def get_status_update_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene información sobre cuántos socios necesitarían actualizarse."""
    today = date.today()
    
    active_types = db.query(MemberType).filter(
        MemberType.name.in_(["ACTIVO", "HONORARIO", "ADHERENTE", "REINGRESO"])
    ).all()
    
    active_type_ids = [mt.id for mt in active_types]
    novato_type = db.query(MemberType).filter(MemberType.name == "NOVATO").first()
    
    members = db.query(MemberModel).filter(
        MemberModel.member_type_id.in_(active_type_ids),
        MemberModel.last_payment_date.isnot(None)
    ).all()
    
    pending_update = 0
    for member in members:
        if member.last_payment_date and member.member_type_id != novato_type.id:
            months_since_payment = (today.year - member.last_payment_date.year) * 12 + \
                                  (today.month - member.last_payment_date.month)
            if months_since_payment > 12:
                pending_update += 1
    
    return {
        "members_pending_update": pending_update,
        "last_check_date": today.isoformat()
    }

