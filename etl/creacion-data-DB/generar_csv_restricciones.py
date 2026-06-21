import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ============================================================
# SCRIPT PARA EXPORTAR TODA LA TABLA A CSV
# ============================================================

# Cargar variables de entorno
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")

# Configurar conexión
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Crear carpeta de salida
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Nombre del archivo CSV
OUTPUT_FILE = OUTPUT_DIR / "exportacion_completa_stg_catalogo_interno.csv"

print("="*80)
print("📥 EXPORTANDO DATOS DE LA BASE DE DATOS A CSV")
print("="*80)

try:
    with engine.connect() as connection:
        # 1. Contar registros totales
        count_result = connection.execute(text("SELECT COUNT(*) FROM stg_catalogo_interno;"))
        total = count_result.fetchone()[0]
        print(f"\n📊 Total de registros en la tabla: {total}")
        
        if total == 0:
            print("❌ La tabla está vacía. No hay datos para exportar.")
            exit()
        
        # 2. Mostrar estructura de la tabla
        print("\n📋 Estructura de la tabla:")
        desc_result = connection.execute(text("DESCRIBE stg_catalogo_interno;"))
        for row in desc_result:
            print(f"   {row[0]}: {row[1]}")
        
        print(f"\n🔄 Exportando {total} registros...")
        
        # 3. Exportar TODOS los datos a DataFrame
        query = "SELECT * FROM stg_catalogo_interno;"
        df = pd.read_sql_query(query, engine)
        
        # 4. Mostrar información del DataFrame
        print(f"\n✅ Datos cargados en DataFrame:")
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {len(df.columns)}")
        print(f"   Columnas: {', '.join(df.columns)}")
        
        # 5. Guardar a CSV
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ ¡EXPORTACIÓN COMPLETADA!")
        print(f"📁 Archivo guardado en: {OUTPUT_FILE}")
        print(f"📊 Tamaño del archivo: {OUTPUT_FILE.stat().st_size / 1024:.2f} KB")
        
        # 6. Mostrar muestra de los datos
        print("\n📋 Muestra de los primeros 5 registros exportados:")
        print(df.head().to_string())
        
        # 7. Estadísticas adicionales
        print("\n📊 Estadísticas de los datos exportados:")
        print(f"   IDs únicos: {df['id_pelicula'].nunique()}")
        print(f"   Servidores únicos: {df['servidor_origen'].nunique()}")
        print(f"   Distribución por servidor:")
        for servidor, count in df['servidor_origen'].value_counts().items():
            print(f"      {servidor}: {count} registros ({count/len(df)*100:.1f}%)")
        
except Exception as e:
    print(f"\n❌ ERROR al exportar los datos: {e}")
    import traceback
    traceback.print_exc()