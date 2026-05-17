from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import config
import os

# Asegurar permisos del directorio de la base de datos si es SQLite
if "sqlite" in config.database_url:
    db_path = config.database_url.replace("sqlite:///", "")
    if db_path and not db_path.startswith(":memory:"):
        db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else "."
        # Asegurar que el directorio tenga permisos de escritura
        try:
            os.makedirs(db_dir, mode=0o777, exist_ok=True)
            if os.path.exists(db_dir):
                os.chmod(db_dir, 0o777)
        except Exception:
            pass  # Si falla, continuar de todas formas

engine = create_engine(
    config.database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 20  # Aumentar timeout para SQLite
    } if "sqlite" in config.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency para obtener la sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

