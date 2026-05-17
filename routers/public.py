from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import BenefitCheckResponse
from models import Member as MemberModel, MemberType
from datetime import date

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/check-benefit", response_model=BenefitCheckResponse)
async def check_benefit(
    member_number: int = Query(..., description="Número de socio"),
    db: Session = Depends(get_db)
):
    """
    Endpoint público para verificar si un socio puede usar los beneficios del club.
    Solo verifica socios ACTIVOS, NOVATOS y HONORARIOS.
    """
    member = db.query(MemberModel).filter(MemberModel.member_number == member_number).first()
    
    if not member:
        return BenefitCheckResponse(
            member_number=member_number,
            has_benefit=False,
            message="No se encontró ningún socio con ese número."
        )
    
    # Obtener el tipo de socio
    member_type = db.query(MemberType).filter(MemberType.id == member.member_type_id).first()
    
    if not member_type:
        return BenefitCheckResponse(
            member_number=member_number,
            has_benefit=False,
            message="El socio no tiene un tipo válido."
        )
    
    # Tipos que tienen derecho a beneficios
    benefit_types = ["ACTIVO", "NOVATO", "HONORARIO"]
    
    has_benefit = member_type.name in benefit_types
    
    # Para ACTIVO, también verificar que el último pago sea de los últimos 12 meses
    if member_type.name == "ACTIVO" and member.last_payment_date:
        today = date.today()
        months_since_payment = (today.year - member.last_payment_date.year) * 12 + \
                              (today.month - member.last_payment_date.month)
        if months_since_payment > 12:
            has_benefit = False
    
    if has_benefit:
        message = f"Sí, el socio {member.first_name} {member.last_name} puede usar los beneficios."
    else:
        message = f"No, el socio {member.first_name} {member.last_name} no puede usar los beneficios."
    
    return BenefitCheckResponse(
        member_number=member_number,
        has_benefit=has_benefit,
        message=message
    )

