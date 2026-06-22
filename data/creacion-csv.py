import os
import random
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Cargar variables de entorno
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")

# Configurar conexión a TiDB Cloud
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

print("🔍 Extrayendo IDs únicos de la tabla sucia en TiDB Cloud...")

try:
    # 2. Leer los IDs directamente de la base de datos
    with engine.connect() as connection:
        query = "SELECT id_pelicula FROM stg_catalogo_interno;"
        result = connection.execute(text(query)).fetchall()
        
    # Extraer IDs y limpiar posibles espacios en blanco que metimos en la ingesta sucia
    ids_sucios = [row[0] for row in result]
    ids_limpios = sorted(list(set([int(str(i).strip()) for i in ids_sucios if str(i).strip().isdigit()])))
    
    print(f"✅ Se encontraron {len(ids_limpios)} IDs válidos y únicos en la base de datos.")

    # 3. Definir opciones de restricciones para simular la data de operaciones
    clasificaciones = ["TE", "TE+7", "14", "18"]
    advertencias = ["Ninguna", "Violencia explícita", "Lenguaje inapropiado", "Consumo de sustancias", "Terror psicológico"]

    # 4. Construir las filas del CSV combinando los IDs con las reglas
    lista_restricciones = []
    
    for id_peli in ids_limpios:
        # Elegimos una clasificación aleatoria
        clasif = random.choice(clasificaciones)
        
        # Coherencia: si es TE, la advertencia debería ser "Ninguna" y sin bloqueo infantil
        if clasif in ["TE", "TE+7"]:
            advertencia = "Ninguna"
            bloqueo = "NO"
        else:
            advertencia = random.choice(advertencias[1:]) # Evita "Ninguna" para 14 y 18
            bloqueo = "SI" if clasif == "18" else random.choice(["SI", "NO"])

        lista_restricciones.append({
            "id_pelicula": id_peli,
            "clasificacion_chile": clasif,
            "advertencia_contenido": advertencia,
            "bloqueo_horario_infantil": bloqueo
        })

    # 5. Convertir a DataFrame y guardar como archivo plano CSV
    df_csv = pd.DataFrame(lista_restricciones)
    
    # Asegurar que exista la carpeta data
    os.makedirs("data", exist_ok=True)
    ruta_salida = "data/restricciones_locales.csv"
    
    # Guardar usando punto y coma (;) como separador común en Latam o coma (,) estándar.
    df_csv.to_csv(ruta_salida, index=False, sep=",", encoding="utf-8")
    
    print(f"🎉 ¡ÉxITO! El archivo plano ha sido creado en: '{ruta_salida}'")
    print(df_csv.head(10)) # Mostrar las primeras 10 filas de ejemplo en consola

except Exception as e:
    print(f"Error al generar el archivo CSV: {e}")