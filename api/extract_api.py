import os
import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Cargar variables de entorno (.env)
load_dotenv()

TMDB_API_KEY = os.getenv("API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")

def obtener_datos_faltantes_api():
    """
    Busca los IDs de las películas en la tabla sucia de la base de datos,
    consulta la API de TMDB para obtener sus datos en bruto y los
    devuelve en un DataFrame listo para ser procesado después.
    """
    print("🔍 Conectando a TiDB Cloud para extraer los IDs de Staging...")
    
    # 1. Conectar a la base de datos y extraer los IDs en bruto
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    
    try:
        with engine.connect() as connection:
            # Traemos los IDs tal cual están en la tabla sucia
            query = "SELECT id_pelicula FROM stg_catalogo_interno;"
            result = connection.execute(text(query)).fetchall()
            
        ids_sucios = [row[0] for row in result]
        
        # Hacemos una limpieza mínima en memoria SOLO para que la API no falle al recibir espacios
        # (Quitamos espacios y nos aseguramos de que sean números antes de llamar a la URL)
        ids_para_api = sorted(list(set([str(i).strip() for i in ids_sucios if str(i).strip().isdigit()])))
        
        print(f"✅ Se identificaron {len(ids_para_api)} IDs únicos para consultar en TMDB.")
        
    except Exception as e:
        print(f"❌ Error al leer los IDs de la base de datos: {e}")
        return None

    # 2. Ir a buscar los datos faltantes a la API de TMDB
    print("\n🌐 Conectando con la API de TMDB para extraer metadatos...")
    registros_api = []
    contador = 0
    
    for id_peli in ids_para_api:
        # Endpoint para obtener el detalle de una película por su ID

        url = f"https://api.themoviedb.org/3/movie/{id_peli}?language=en-US"

        headers = {"accept": "application/json",
                   "Authorization": f"Bearer {TMDB_API_KEY}"}

        response = requests.get(url, headers=headers)
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                movie_detail = response.json()
                
                # Guardamos los datos en bruto en nuestra lista
                registros_api.append({
                    "id_pelicula_api": int(id_peli),
                    "titulo_api": movie_detail.get("title"),
                    "popularidad_api": movie_detail.get("popularity"),
                    "votos_promedio_api": movie_detail.get("vote_average")
                })
            else:
                # Si la película no existe en la API por algún motivo, dejamos los campos vacíos
                registros_api.append({
                    "id_pelicula_api": int(id_peli),
                    "titulo_api": None,
                    "popularidad_api": None,
                    "votos_promedio_api": None
                })
        except Exception as e:
            print(f"⚠️ Error de conexión en ID {id_peli}: {e}")
            
        contador += 1
        if contador % 100 == 0:
            print(f"   ... {contador} películas consultadas.")

    # 3. Construir el DataFrame final con los datos crudos de la API
    df_api_faltantes = pd.DataFrame(registros_api)
    print(f"\n✨ ¡Extracción completada! DataFrame de la API generado con {len(df_api_faltantes)} filas.")
    
    return df_api_faltantes

# Bloque de prueba local para verificar que la función levanta el DataFrame
if __name__ == "__main__":
    df_resultado = obtener_datos_faltantes_api()
    if df_resultado is not None:
        print("\n👀 Previsualización del DataFrame de la API (Datos en bruto obtenidos):")
        print(df_resultado.head(10))