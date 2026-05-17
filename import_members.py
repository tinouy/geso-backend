"""Script para importar socios desde un archivo CSV a la base de datos."""
import csv
import sys
from datetime import date, datetime
from pathlib import Path
from sqlalchemy.orm import Session

# Importar módulos del backend
from database import SessionLocal, engine
from models import Base, Member, MemberType

# Mapeo de TipoSocioId del CSV a nombres de tipos de la nueva base de datos
# Basado en los valores encontrados en el CSV
TYPE_MAPPING = {
    "1": "ACTIVO",
    "3": "ADHERENTE", 
    "4": "NOVATO",
    "7": "BAJA_S",  # Baja solicitada
    "8": "BAJAVJ",  # Baja previa a 2018 (valor por defecto en el CSV)
    "10": "REINGRESO",
    # Si hay otros valores, se usarán como ACTIVO por defecto
}

def get_member_type_by_name(db: Session, type_name: str) -> MemberType:
    """Obtiene un tipo de socio por nombre."""
    member_type = db.query(MemberType).filter(MemberType.name == type_name).first()
    if not member_type:
        # Si no existe, crear ACTIVO como fallback
        member_type = db.query(MemberType).filter(MemberType.name == "ACTIVO").first()
        if not member_type:
            raise ValueError(f"Tipo de socio '{type_name}' no encontrado en la base de datos")
    return member_type

def parse_payment_date(year_str: str) -> date | None:
    """Convierte un año en string a una fecha de último pago (31 de diciembre de ese año)."""
    if not year_str or year_str == "NULL" or year_str.strip() == "":
        return None
    try:
        year = int(year_str.strip())
        # Si el año es válido y razonable (entre 1900 y año actual + 1)
        if 1900 <= year <= datetime.now().year + 1:
            return date(year, 12, 31)  # Último día del año
    except (ValueError, TypeError):
        pass
    return None

def import_members_from_csv(csv_path: str, db_path: str = None):
    """Importa miembros desde un archivo CSV."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Configurar la URL de la base de datos si se proporciona
    if db_path:
        # Asegurarse de que la ruta sea absoluta
        abs_path = Path(db_path).absolute()
        engine_url = f"sqlite:///{abs_path}"
        engine = create_engine(engine_url, connect_args={"check_same_thread": False})
        Base.metadata.bind = engine
        SessionLocal = sessionmaker(bind=engine)
    else:
        # Usar la configuración por defecto
        from database import SessionLocal
    
    db = SessionLocal()
    
    try:
        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"Error: El archivo {csv_path} no existe")
            sys.exit(1)
        
        # Leer el CSV - intentar diferentes codificaciones
        imported_count = 0
        skipped_count = 0
        errors = []
        
        # Intentar diferentes codificaciones
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        file_handle = None
        encoding_used = None
        
        for enc in encodings:
            try:
                file_handle = open(csv_file, 'r', encoding=enc)
                # Intentar leer la primera línea para verificar
                file_handle.readline()
                file_handle.seek(0)
                encoding_used = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                if file_handle:
                    file_handle.close()
                continue
        
        if not encoding_used:
            print("Error: No se pudo determinar la codificación del archivo CSV")
            sys.exit(1)
        
        print(f"Usando codificación: {encoding_used}")
        
        # Leer el CSV con delimitador punto y coma
        reader = csv.DictReader(file_handle, delimiter=';')
        
        for row_num, row in enumerate(reader, start=2):  # Empezar en 2 porque la línea 1 es el encabezado
                try:
                    # Obtener los datos del CSV
                    member_number_str = row.get('Numero', '').strip().strip('"')
                    if not member_number_str:
                        skipped_count += 1
                        continue
                    
                    member_number = int(member_number_str)
                    
                    # Verificar si el socio ya existe
                    existing = db.query(Member).filter(Member.member_number == member_number).first()
                    if existing:
                        print(f"Fila {row_num}: Socio número {member_number} ya existe, omitiendo...")
                        skipped_count += 1
                        continue
                    
                    # Obtener nombres
                    first_name = row.get('Nombres', '').strip().strip('"') or "Sin nombre"
                    last_name = row.get('Apellidos', '').strip().strip('"') or "Sin apellido"
                    
                    # Email
                    email = row.get('correo', '').strip().strip('"')
                    if not email or email.lower() in ['null', 'none', '']:
                        email = None
                    
                    # Documento
                    identity_document = row.get('Documento', '').strip().strip('"')
                    if not identity_document or identity_document == "1" or identity_document.lower() == 'null':
                        identity_document = None
                    
                    # Tipo de socio
                    tipo_socio_id = row.get('TipoSocioId', '8').strip().strip('"')  # Default a 8 (BAJAVJ)
                    type_name = TYPE_MAPPING.get(tipo_socio_id, "ACTIVO")
                    member_type = get_member_type_by_name(db, type_name)
                    
                    # Fecha de último pago
                    ultimo_ano_pago = row.get('UltimoAnoPago', '').strip().strip('"')
                    last_payment_date = parse_payment_date(ultimo_ano_pago)
                    
                    # Crear el miembro
                    member = Member(
                        member_number=member_number,
                        first_name=first_name,
                        last_name=last_name,
                        email=email if email else None,
                        identity_document=identity_document,
                        member_type_id=member_type.id,
                        last_payment_date=last_payment_date
                    )
                    
                    db.add(member)
                    imported_count += 1
                    
                    if imported_count % 50 == 0:
                        db.commit()  # Commit cada 50 registros para mejor rendimiento
                        print(f"Importados {imported_count} socios...")
                
                except Exception as e:
                    error_msg = f"Error en fila {row_num}: {str(e)}"
                    errors.append(error_msg)
                    print(f"Error en fila {row_num}: {e}")
                    skipped_count += 1
                    continue
        
        # Cerrar el archivo
        file_handle.close()
        
        # Commit final
        db.commit()
        
        print(f"\n=== Resumen de importación ===")
        print(f"Socios importados: {imported_count}")
        print(f"Socios omitidos: {skipped_count}")
        if errors:
            print(f"\nErrores encontrados: {len(errors)}")
            for error in errors[:10]:  # Mostrar solo los primeros 10 errores
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... y {len(errors) - 10} errores más")
        
    except Exception as e:
        db.rollback()
        print(f"Error fatal durante la importación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Importar socios desde CSV a la base de datos')
    parser.add_argument('csv_file', help='Ruta al archivo CSV')
    parser.add_argument('--db', help='Ruta a la base de datos SQLite (opcional)', 
                        default=None)
    
    args = parser.parse_args()
    
    # Si no se especifica db, usar la ruta por defecto del proyecto
    if not args.db:
        # Intentar encontrar geso.db en geso_db/
        project_root = Path(__file__).parent.parent
        default_db = project_root / "geso_db" / "geso.db"
        if default_db.exists():
            args.db = str(default_db)
            print(f"Usando base de datos por defecto: {args.db}")
        else:
            print("Advertencia: No se encontró la base de datos. Usando configuración por defecto.")
    
    import_members_from_csv(args.csv_file, args.db)

