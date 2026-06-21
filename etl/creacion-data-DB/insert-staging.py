import os
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Cargar configuración y entorno
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE)

TMDB_API_KEY = os.getenv('API_KEY')
UPLOAD_TO_DB = os.getenv("UPLOAD_TO_DB", "false").lower() in {"1", "true", "yes", "on"}

engine = None
if UPLOAD_TO_DB:
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_USER = os.getenv("DB_USERNAME")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_DATABASE")

    # Configuración de la URL de TiDB Cloud
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)

print("Iniciando recolección de IDs reales desde TMDB API...")

# 2. Extraer IDs reales desde la API (recorriendo varias páginas para tener variedad)
peliculas_reales = []
paginas_a_recorrer = 15  # Cada página trae 20 películas. 15 * 20 = ~300 películas base únicas.

for page in range(1, paginas_a_recorrer + 1):
    url = f"https://api.themoviedb.org/3/discover/movie?language=es-ES&sort_by=popularity.desc&page={page}"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('API_KEY')}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            for movie in data.get("results", []):
                peliculas_reales.append({
                    "id": movie["id"],
                    "titulo": movie["title"]
                })
        else:
            print(f"{response.text}")
            print(f"No se pudo leer la página {page} de la API.")
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API en página {page}: {e}")

if not peliculas_reales:
    print("No se pudieron obtener IDs de la API. Verifica tu TMDB_KEY en el .env")
    exit()

print(f"Se obtuvieron {len(peliculas_reales)} películas base reales de la API.")

# 3. Multiplicar y "Ensuciar" los datos en Python para llegar a más de 1,000 registros
print("\nGenerando +1000 registros sucios basados en IDs reales...")
datos_sucios = []
servidores = ["Servidor_CL_Principal", "Servidor_Latam_Backup", "Node_Santiago_East", "Null_Server"]

# Formatos de fecha desordenados para obligar a limpiar en el ETL de la Semana 2
formatos_fecha = [
    "%Y-%m-%d",  # Correcto ISO: 2025-05-12
    "%d/%m/%Y",  # Formato Chile: 12/05/2025
    "TEXTO_SUCIO" # Para simular un error crítico de tipeo
]

# Para cumplir la pauta de +1000 registros, clonaremos las películas base 
# simulando que están alojadas en diferentes servidores o que tienen registros duplicados defectuosos
while len(datos_sucios) < 1050:
    pelicula_base = random.choice(peliculas_reales)
    
    # Introducir anomalía de duplicación: algunos IDs irán limpios, otros con espacios vacíos indeseados
    id_pelicula_sucio = str(pelicula_base["id"])
    if random.random() < 0.15:  # 15% de probabilidad de ID con espacios sucios
        id_pelicula_sucio = f"  {id_pelicula_sucio}  "

    # Inconsistencia en reproducciones mensuales (texto mezclado con números, nulos o "N/A")
    rand_repro = random.random()
    if rand_repro < 0.10:
        reproducciones = "N/A"
    elif rand_repro < 0.20:
        reproducciones = None
    elif rand_repro < 0.50:
        reproducciones = f"{random.randint(500, 10000)} views"
    else:
        reproducciones = f"{random.randint(500, 10000)}" # Número limpio en formato texto

    # Inconsistencia en fechas de estreno en la plataforma
    formato = random.choice(formatos_fecha)
    if formato == "TEXTO_SUCIO":
        fecha_sucia = random.choice(["Próximamente", "PENDIENTE", "", "00/00/0000"])
    else:
        fecha_sucia = datetime.now().strftime(formato)

    datos_sucios.append({
        "id_pelicula": id_pelicula_sucio,
        "titulo_original": pelicula_base["titulo"].upper() if random.random() < 0.3 else pelicula_base["titulo"], # 30% en mayúsculas locas
        "reproducciones_mensuales": reproducciones,
        "fecha_estreno_plataforma": fecha_sucia,
        "servidor_origen": random.choice(servidores)
    })

# Convertir a DataFrame de Pandas para el CSV sucio
# No se deben eliminar duplicados ni corregir valores: el archivo debe seguir siendo crudo.
df_staging = pd.DataFrame(datos_sucios)

# Guardar el archivo sucio para que otra persona lo limpie después
output_csv = Path(__file__).resolve().with_name("stg_catalogo_interno_sucio.csv")
output_csv.parent.mkdir(parents=True, exist_ok=True)
print(f"Ruta donde se guardará el CSV: {output_csv}")
print(f"Archivo .env usado: {ENV_FILE}")
print("Se está escribiendo el archivo CSV sucio...")
df_staging.to_csv(output_csv, index=False, encoding="utf-8-sig")

print(f"DataFrame listo. Total de filas creadas para el CSV sucio: {len(df_staging)}")
print(f"Archivo CSV generado en: {output_csv}")
print("\nCSV listo para descargar.")
print("El archivo está en esta carpeta: " + os.path.dirname(output_csv))
print("Objetivo del entregable: este CSV sucio debe pasarse al compañero para que lo limpie.")

# 4. Cargar los datos a TiDB Cloud solo si se habilita explícitamente
if UPLOAD_TO_DB:
    print("\nConectando e inyectando datos sucios en TiDB Cloud...")
    try:
        with engine.connect() as connection:
            # Asegurarnos de que la tabla existe
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS stg_catalogo_interno (
                    id_pelicula VARCHAR(50) PRIMARY KEY,
                    titulo_original VARCHAR(255),
                    reproducciones_mensuales VARCHAR(100),
                    fecha_estreno_plataforma VARCHAR(50),
                    servidor_origen VARCHAR(100)
                );
            """))
            connection.commit()

            # Limpiar la tabla por si había basura antes
            connection.execute(text("TRUNCATE TABLE stg_catalogo_interno;"))
            connection.commit()

        # Usar Pandas .to_sql para subir los registros en un segundo
        df_staging.to_sql(
            name="stg_catalogo_interno",
            con=engine,
            if_exists="append",
            index=False,
            chunksize=500
        )

        print("¡ÉXITO! La tabla 'stg_catalogo_interno' en la nube ha sido poblada con datos sucios basados en IDs reales de la API.")

    except Exception as e:
        print(f"Error al inyectar los datos en la base de datos: {e}")
else:
    print("Se omitió la carga a la base de datos porque UPLOAD_TO_DB no está habilitado.")
    print("Este script solo debe entregar el CSV sucio; la limpieza la realizará otra persona.")