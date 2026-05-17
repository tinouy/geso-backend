"""
Script de migración para agregar los nuevos campos a la tabla members:
- phone_number
- is_bjcp_judge
- business_name
"""
import sqlite3
import os
from pathlib import Path

# Obtener la ruta de la base de datos
db_path = os.getenv("DATABASE_URL", "sqlite:///geso_db/geso.db").replace("sqlite:///", "")

if not db_path or db_path.startswith(":memory:"):
    print("Error: No se pudo determinar la ruta de la base de datos")
    exit(1)

# Asegurar que la ruta sea absoluta
if not os.path.isabs(db_path):
    # Si es relativa, buscar desde el directorio del script
    script_dir = Path(__file__).parent
    db_path = os.path.join(script_dir.parent, db_path)

print(f"Migrando base de datos: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar qué columnas existen
    cursor.execute("PRAGMA table_info(members)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    print(f"Columnas existentes: {existing_columns}")
    
    # Agregar phone_number si no existe
    if "phone_number" not in existing_columns:
        print("Agregando columna phone_number...")
        cursor.execute("ALTER TABLE members ADD COLUMN phone_number VARCHAR")
        print("✓ Columna phone_number agregada")
    else:
        print("✓ Columna phone_number ya existe")
    
    # Agregar is_bjcp_judge si no existe
    if "is_bjcp_judge" not in existing_columns:
        print("Agregando columna is_bjcp_judge...")
        cursor.execute("ALTER TABLE members ADD COLUMN is_bjcp_judge VARCHAR DEFAULT 'false' NOT NULL")
        # Actualizar registros existentes
        cursor.execute("UPDATE members SET is_bjcp_judge = 'false' WHERE is_bjcp_judge IS NULL")
        print("✓ Columna is_bjcp_judge agregada")
    else:
        print("✓ Columna is_bjcp_judge ya existe")
    
    # Agregar business_name si no existe
    if "business_name" not in existing_columns:
        print("Agregando columna business_name...")
        cursor.execute("ALTER TABLE members ADD COLUMN business_name VARCHAR")
        print("✓ Columna business_name agregada")
    else:
        print("✓ Columna business_name ya existe")
    
    conn.commit()
    print("\n✓ Migración completada exitosamente")
    
    # Verificar las columnas finales
    cursor.execute("PRAGMA table_info(members)")
    final_columns = [row[1] for row in cursor.fetchall()]
    print(f"\nColumnas finales: {final_columns}")
    
except sqlite3.Error as e:
    print(f"Error durante la migración: {e}")
    conn.rollback()
    exit(1)
finally:
    conn.close()
