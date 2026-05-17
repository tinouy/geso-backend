"""Script para inicializar la base de datos con datos por defecto."""
from database import Base, engine, SessionLocal
from models import MemberType, User, ClubConfig, UserRole
from auth import get_password_hash
from config import config
import sys

# Crear las tablas
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Crear tipos de socios por defecto si no existen
    default_types = [
        {"name": "ACTIVO", "description": "Socio activo"},
        {"name": "BAJA", "description": "Baja por no pago de cuota"},
    ]
    
    for type_data in default_types:
        existing = db.query(MemberType).filter(MemberType.name == type_data["name"]).first()
        if not existing:
            member_type = MemberType(**type_data)
            db.add(member_type)
            print(f"Created member type: {type_data['name']}")
        else:
            print(f"Member type already exists: {type_data['name']}")
    
    # Crear configuración del club desde geso.conf/variables de entorno si no existe
    club_config = db.query(ClubConfig).first()
    if not club_config:
        club_config = ClubConfig(
            club_name=config.club_name,
            annual_fee_amount=config.annual_fee_amount,
            period_type=config.period_type,
            prorrate_type=config.prorrate_type,
            initialized="false"  # Se inicializará mediante el wizard
        )
        db.add(club_config)
        print(f"Created club config: {config.club_name}")
    else:
        print(f"Club config already exists: {club_config.club_name}")
    
    # Crear usuario administrador desde geso.conf/variables de entorno si no existe
    user_count = db.query(User).count()
    if user_count == 0:
        admin_username = config.admin_username
        admin_email = config.admin_email
        admin_password = config.admin_password
        
        if admin_username and admin_email and admin_password:
            # Verificar que no exista ya un usuario con ese username o email
            existing_user = db.query(User).filter(
                (User.username == admin_username) | (User.email == admin_email)
            ).first()
            
            if not existing_user:
                hashed_password = get_password_hash(admin_password)
                admin_user = User(
                    username=admin_username,
                    email=admin_email,
                    hashed_password=hashed_password,
                    role=UserRole.ADMIN,
                    is_active="true"
                )
                db.add(admin_user)
                print(f"Created admin user: {admin_username}")
            else:
                print(f"Admin user already exists: {admin_username}")
        else:
            print("Admin credentials not found in geso.conf/variables de entorno. User will be created via wizard.")
    else:
        print("Users already exist in database.")
    
    db.commit()
    print("Database initialized successfully!")
    
except Exception as e:
    print(f"Error initializing database: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
    sys.exit(1)
finally:
    db.close()

