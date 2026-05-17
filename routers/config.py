from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from auth import get_current_active_user, require_admin, get_current_user
from schemas import ClubConfig, ClubConfigCreate, ClubConfigUpdate
from models import ClubConfig as ClubConfigModel
from models import User, UserRole
from jose import JWTError, jwt
from config import config as app_config
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api/config", tags=["config"])

# Security scheme opcional para endpoints que pueden ser públicos
optional_security = HTTPBearer(auto_error=False)


@router.get("", response_model=ClubConfig)
async def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene la configuración del club."""
    config = db.query(ClubConfigModel).first()
    if not config:
        # Crear configuración por defecto
        config = ClubConfigModel(
            club_name="Club",
            annual_fee_amount=1000.0,
            period_type="yearly",
            prorrate_type="monthly",
            initialized="false"
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.post("", response_model=ClubConfig)
async def create_config(
    config_data: ClubConfigCreate,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
):
    """
    Crea o actualiza la configuración del club (público para inicialización).
    Una vez inicializado, este endpoint está bloqueado. Para reinicializar,
    debe cambiarse manualmente el campo 'initialized' a 'false' en la base de datos.
    """
    existing_config = db.query(ClubConfigModel).first()
    
    # Si ya está inicializado, bloquear completamente (ni siquiera con admin)
    if existing_config and existing_config.initialized == "true":
        raise HTTPException(
            status_code=403, 
            detail="El sistema ya está inicializado. Para reinicializar, cambie manualmente el campo 'initialized' a 'false' en la base de datos."
        )
    
    config = existing_config
    if config:
        # Actualizar configuración existente (solo si no está inicializado)
        config.club_name = config_data.club_name
        config.annual_fee_amount = config_data.annual_fee_amount
        config.period_type = config_data.period_type
        config.prorrate_type = config_data.prorrate_type
        config.initialized = "true"
    else:
        # Crear nueva configuración
        config = ClubConfigModel(
            club_name=config_data.club_name,
            annual_fee_amount=config_data.annual_fee_amount,
            period_type=config_data.period_type,
            prorrate_type=config_data.prorrate_type,
            initialized="true"
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config


@router.put("", response_model=ClubConfig, dependencies=[Depends(require_admin)])
async def update_config(
    config_update: ClubConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza la configuración del club (solo admin).
    Nota: El campo 'initialized' no puede ser modificado mediante la API.
    Para cambiar el estado de inicialización, debe modificarse manualmente en la base de datos.
    """
    config = db.query(ClubConfigModel).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found. Please initialize first.")
    
    update_data = config_update.dict(exclude_unset=True)
    
    # Prevenir que se cambie el campo 'initialized' mediante la API
    if 'initialized' in update_data:
        del update_data['initialized']
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    return config


@router.get("/conf")
async def get_conf_file():
    """
    Lee el archivo geso.conf (endpoint público para el wizard).
    Retorna el contenido del archivo de configuración.
    """
    try:
        conf_data = app_config.read_config_file()
        return {"conf": conf_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading config file: {str(e)}")


@router.post("/conf")
async def update_conf_file(
    conf_data: dict,
    db: Session = Depends(get_db)
):
    """
    Actualiza el archivo geso.conf (endpoint público para el wizard durante inicialización).
    """
    # Verificar si el sistema ya está inicializado
    db_config = db.query(ClubConfigModel).first()
    if db_config and db_config.initialized == "true":
        raise HTTPException(
            status_code=403,
            detail="El sistema ya está inicializado. No se puede modificar geso.conf."
        )
    
    # Verificar si hay CLUB_NAME configurado
    club_name = app_config.club_name
    if club_name and club_name != "Club":
        raise HTTPException(
            status_code=403,
            detail="El sistema ya está inicializado. No se puede modificar geso.conf."
        )
    
    try:
        # Actualizar cada sección y clave del archivo
        for section, items in conf_data.items():
            if isinstance(items, dict):
                for key, value in items.items():
                    app_config.write_config(section, key, value)
        
        return {"message": "Config file updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing config file: {str(e)}")


@router.get("/initialized")
async def check_initialized(db: Session = Depends(get_db)):
    """
    Verifica si el sistema está inicializado (endpoint público para el wizard).
    El wizard está desactivado si:
    1. Variable de entorno DISABLE_WIZARD está configurada (cualquier valor desactiva el wizard), O
    2. Hay configuración en BD con initialized == "true", O
    3. Hay usuarios en la BD (si hay usuarios, se considera inicializado)
    """
    import os
    from models import User as UserModel
    
    # Si hay variable de entorno DISABLE_WIZARD, desactivar wizard inmediatamente
    if os.getenv("DISABLE_WIZARD"):
        return {"initialized": True}
    
    # Verificar en la base de datos
    db_config = db.query(ClubConfigModel).first()
    if db_config and db_config.initialized == "true":
        return {"initialized": True}
    
    # Contar usuarios en la base de datos
    # Si hay usuarios, el sistema se considera inicializado
    user_count = db.query(UserModel).count()
    if user_count > 0:
        return {"initialized": True}
    
    return {"initialized": False}
