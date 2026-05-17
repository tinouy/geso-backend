"""Script para verificar la importación de socios."""
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importar modelos
from models import Base, Member, MemberType

def verify_import(db_path: str):
    """Verifica los datos importados."""
    abs_path = Path(db_path).absolute()
    engine_url = f"sqlite:///{abs_path}"
    engine = create_engine(engine_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Contar total de socios
        total_members = db.query(Member).count()
        print(f"Total de socios en la base de datos: {total_members}")
        
        # Contar por tipo de socio
        print("\n=== Socios por tipo ===")
        member_types = db.query(MemberType).all()
        for mt in member_types:
            count = db.query(Member).filter(Member.member_type_id == mt.id).count()
            if count > 0:
                print(f"  {mt.name}: {count} socios")
        
        # Mostrar algunos ejemplos
        print("\n=== Primeros 10 socios importados ===")
        members = db.query(Member).order_by(Member.member_number).limit(10).all()
        for member in members:
            print(f"  #{member.member_number}: {member.first_name} {member.last_name} - {member.member_type.name} - Último pago: {member.last_payment_date or 'N/A'}")
        
        # Estadísticas adicionales
        print("\n=== Estadísticas adicionales ===")
        with_email = db.query(Member).filter(Member.email.isnot(None)).count()
        with_document = db.query(Member).filter(Member.identity_document.isnot(None)).count()
        with_payment = db.query(Member).filter(Member.last_payment_date.isnot(None)).count()
        
        print(f"  Socios con email: {with_email} ({with_email*100//total_members if total_members > 0 else 0}%)")
        print(f"  Socios con documento: {with_document} ({with_document*100//total_members if total_members > 0 else 0}%)")
        print(f"  Socios con fecha de pago: {with_payment} ({with_payment*100//total_members if total_members > 0 else 0}%)")
        
        # Rango de números de socio
        min_num = db.query(Member.member_number).order_by(Member.member_number).first()
        max_num = db.query(Member.member_number).order_by(Member.member_number.desc()).first()
        print(f"\n  Rango de números de socio: {min_num[0] if min_num else 'N/A'} - {max_num[0] if max_num else 'N/A'}")
        
    except Exception as e:
        print(f"Error al verificar: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verificar importación de socios')
    parser.add_argument('--db', help='Ruta a la base de datos SQLite', 
                        default='geso_db/geso.db')
    
    args = parser.parse_args()
    verify_import(args.db)

