from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from auth import authenticate_user, create_access_token, get_current_active_user, get_password_hash, require_admin
from schemas import Token, LoginRequest, User, UserCreate, UserUpdate, UserPasswordUpdate
from models import User as UserModel, UserRole
from config import config
from typing import Optional
from jose import JWTError, jwt
from config import config as app_config

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Endpoint de login."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/json", response_model=Token)
async def login_json(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Endpoint de login con JSON."""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """Obtiene el usuario actual."""
    return current_user


@router.put("/me/password")
async def update_own_password(
    password_data: UserPasswordUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualiza la contraseña del usuario actual."""
    from auth import verify_password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.put("/me")
async def update_own_profile(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualiza el perfil del usuario actual."""
    update_data = user_update.dict(exclude_unset=True)
    
    # No permitir cambiar el rol a sí mismo
    if "role" in update_data:
        del update_data["role"]
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user


# Security scheme opcional para verificar autenticación condicionalmente
optional_security = HTTPBearer(auto_error=False)

@router.post("/users", response_model=User)
async def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
):
    """
    Crea un nuevo usuario. 
    - Durante la inicialización (sistema no inicializado): permite crear el primer usuario como admin
    - Si hay valores en geso.conf para admin, los usa automáticamente
    - Después de la inicialización: requiere autenticación y ser admin
    """
    from models import ClubConfig as ClubConfigModel
    from fastapi.security import HTTPAuthorizationCredentials
    
    # Verificar estado de inicialización
    config = db.query(ClubConfigModel).first()
    is_initialized = config and config.initialized == "true"
    
    # Verificar si hay usuarios en el sistema
    user_count = db.query(UserModel).count()
    
    # Si es el primer usuario y hay valores de admin en geso.conf, usarlos
    username = user.username
    email = user.email
    password = user.password
    
    if user_count == 0:
        # Es el primer usuario - verificar si hay valores en geso.conf
        admin_username = app_config.admin_username
        admin_email = app_config.admin_email
        admin_password = app_config.admin_password
        
        # Si existen valores en geso.conf, usarlos (sobrescribiendo los del request)
        if admin_username:
            username = admin_username
        if admin_email:
            email = admin_email
        if admin_password:
            password = admin_password
    
    # Si el sistema está inicializado o hay usuarios, requerir autenticación y ser admin
    if is_initialized or user_count > 0:
        # Verificar autenticación manualmente
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        try:
            token = credentials.credentials
            payload = jwt.decode(token, app_config.secret_key, algorithms=[app_config.algorithm])
            username_from_token = payload.get("sub")
            if not username_from_token:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            db_user = db.query(UserModel).filter(UserModel.username == username_from_token).first()
            if not db_user or db_user.is_active != "true" or db_user.role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Not enough permissions")
            
            user_role = user.role  # Permitir cualquier rol si es admin
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        # Durante la inicialización, forzar el rol a admin si es el primer usuario
        user_role = UserRole.ADMIN
    
    db_user = db.query(UserModel).filter(
        (UserModel.username == username) | (UserModel.email == email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_password = get_password_hash(password)
    db_user = UserModel(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=user_role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/users", response_model=list[User], dependencies=[Depends(require_admin)])
async def list_users(db: Session = Depends(get_db)):
    """Lista todos los usuarios (solo admin)."""
    users = db.query(UserModel).all()
    return users


@router.put("/users/{user_id}", response_model=User, dependencies=[Depends(require_admin)])
async def update_user(user_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Actualiza un usuario (solo admin)."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

