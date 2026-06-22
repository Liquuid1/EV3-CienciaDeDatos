import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# 1. CONFIGURACIÓN DEL PROYECTO
# ============================================================

# etl_proyecto.py está dentro de la carpeta "etl".
# parents[1] permite llegar a la carpeta principal del proyecto.
BASE_DIR = Path(__file__).resolve().parents[1]

# Agregar la carpeta principal del proyecto a las rutas de Python.
# Esto permite importar extract_api.py desde la carpeta api.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from api.extract_api import obtener_datos_faltantes_api

# Ruta del archivo CSV.
RUTA_CSV = BASE_DIR / "data" / "restricciones_locales.csv"

# ============================================================
# UMBRALES PARA LAS REGLAS DE NEGOCIO
# ============================================================

UMBRAL_POPULARIDAD_ALTA = 80
UMBRAL_REPRODUCCIONES_BAJAS = 3000
UMBRAL_REPRODUCCIONES_ALTAS = 7000
UMBRAL_VOTOS_BAJOS = 5.0

# Leer las variables del archivo .env sin modificarlo.
load_dotenv(BASE_DIR / ".env")

# Control de carga a la tabla final.
# False: ejecuta el ETL, pero no modifica la tabla final.
# True: crea, limpia y carga dw_peliculas_analitica.
EJECUTAR_CARGA = True

# ============================================================
# 2. VARIABLES DE CONEXIÓN
# ============================================================

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")


variables_requeridas = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_USERNAME": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_DATABASE": DB_NAME
}

variables_faltantes = [
    nombre
    for nombre, valor in variables_requeridas.items()
    if not valor
]

if variables_faltantes:
    raise ValueError(
        f"Faltan variables en el archivo .env: {variables_faltantes}"
    )


# ============================================================
# 3. CREACIÓN DE LA CONEXIÓN A TIDB CLOUD
# ============================================================

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME
)

connect_args = {
    "ssl": {
        "fake_user_to_enable_ssl": True
    }
}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,

    # Comprueba que la conexión siga activa antes de utilizarla.
    pool_pre_ping=True,

    # Renueva las conexiones que tengan 5 minutos de antigüedad.
    pool_recycle=300
)


# ============================================================
# 4. PRUEBA DE CONEXIÓN
# ============================================================

def probar_conexion():
    """
    Comprueba la conexión con TiDB Cloud y cuenta los registros
    existentes en la tabla stg_catalogo_interno.

    Esta función se conserva como evidencia de la prueba inicial.
    """

    try:
        with engine.connect() as connection:
            total_registros = connection.execute(
                text("SELECT COUNT(*) FROM stg_catalogo_interno;")
            ).scalar_one()

        print("Conexión exitosa con TiDB Cloud.")
        print(
            "Registros encontrados en stg_catalogo_interno: "
            f"{total_registros}"
        )

        return True

    except Exception as error:
        print(f"Error al conectar con la base de datos: {error}")
        return False


# ============================================================
# 5. EXTRACCIÓN DE LA TABLA STAGING
# ============================================================

def extraer_staging():
    """
    Extrae los datos crudos desde stg_catalogo_interno
    y los almacena en un DataFrame de Pandas.
    """

    consulta = text("""
        SELECT
            id_pelicula,
            titulo_original,
            reproducciones_mensuales,
            fecha_estreno_plataforma,
            servidor_origen
        FROM stg_catalogo_interno;
    """)

    try:
        with engine.connect() as connection:
            df_staging = pd.read_sql(
                consulta,
                connection
            )

        print("\n========================================")
        print("EXTRACCIÓN DE STAGING")
        print("========================================")

        print("Datos extraídos correctamente desde staging.")
        print(f"Cantidad de filas: {len(df_staging)}")
        print(f"Cantidad de columnas: {len(df_staging.columns)}")

        print("\nPrimeros 10 registros:")
        print(df_staging.head(10))

        print("\nTipos de datos:")
        print(df_staging.dtypes)

        print("\nValores nulos por columna:")
        print(df_staging.isna().sum())

        return df_staging

    except Exception as error:
        print(f"Error al extraer los datos de staging: {error}")
        return None


# ============================================================
# 6. EXTRACCIÓN DEL ARCHIVO CSV
# ============================================================

def extraer_csv():
    """
    Lee el archivo restricciones_locales.csv y almacena
    su contenido en un DataFrame de Pandas.
    """

    try:
        # Comprobar que el archivo existe antes de intentar leerlo.
        if not RUTA_CSV.exists():
            raise FileNotFoundError(
                f"No se encontró el archivo CSV en: {RUTA_CSV}"
            )

        df_csv = pd.read_csv(
            RUTA_CSV,
            sep=",",
            encoding="utf-8"
        )

        print("\n========================================")
        print("EXTRACCIÓN DEL CSV")
        print("========================================")

        print("Archivo CSV leído correctamente.")
        print(f"Ruta utilizada: {RUTA_CSV}")
        print(f"Cantidad de filas: {len(df_csv)}")
        print(f"Cantidad de columnas: {len(df_csv.columns)}")

        print("\nPrimeros 10 registros:")
        print(df_csv.head(10))

        print("\nTipos de datos:")
        print(df_csv.dtypes)

        print("\nValores nulos por columna:")
        print(df_csv.isna().sum())

        print("\nFilas completamente duplicadas:")
        print(df_csv.duplicated().sum())

        print("\nIDs duplicados:")
        print(df_csv["id_pelicula"].duplicated().sum())

        return df_csv

    except Exception as error:
        print(f"Error al extraer el archivo CSV: {error}")
        return None

# ============================================================
# 7. EXTRACCIÓN DE LA API DE TMDB
# ============================================================

def extraer_api():
    """
    Ejecuta la función existente en api/extract_api.py
    y recibe los datos obtenidos desde TMDB en un DataFrame.
    """

    try:
        df_api = obtener_datos_faltantes_api()

        if df_api is None:
            raise ValueError(
                "La función de extracción de la API no devolvió datos."
            )

        print("\n========================================")
        print("EXTRACCIÓN DE LA API")
        print("========================================")

        print("Datos de TMDB extraídos correctamente.")
        print(f"Cantidad de filas: {len(df_api)}")
        print(f"Cantidad de columnas: {len(df_api.columns)}")

        print("\nPrimeros 10 registros:")
        print(df_api.head(10))

        print("\nTipos de datos:")
        print(df_api.dtypes)

        print("\nValores nulos por columna:")
        print(df_api.isna().sum())

        print("\nFilas completamente duplicadas:")
        print(df_api.duplicated().sum())

        if "id_pelicula_api" in df_api.columns:
            print("\nIDs duplicados:")
            print(df_api["id_pelicula_api"].duplicated().sum())

        return df_api

    except Exception as error:
        print(f"Error al extraer los datos desde TMDB: {error}")
        return None

# ============================================================
# TRANSFORMACIÓN DEL ID DE STAGING
# ============================================================

def limpiar_id_staging(df_staging):
    """
    Limpia la columna id_pelicula de staging.

    - Conserva el ID original como evidencia.
    - Elimina espacios al inicio y al final.
    - Convierte el ID a un tipo numérico.
    - Identifica valores inválidos y duplicados.

    En esta etapa todavía no se eliminan los duplicados.
    """

    try:
        # Crear una copia para conservar intacto el DataFrame original.
        df_limpio = df_staging.copy()

        # Conservar el valor original para comparar antes y después.
        df_limpio["id_pelicula_original"] = df_limpio["id_pelicula"]

        # Eliminar espacios y convertir a número.
        # errors="coerce" convierte valores inválidos en nulos.
        df_limpio["id_pelicula"] = pd.to_numeric(
            df_limpio["id_pelicula"]
            .astype("string")
            .str.strip(),
            errors="coerce"
        )

        # Utilizar Int64 porque permite almacenar enteros y valores nulos.
        df_limpio["id_pelicula"] = df_limpio[
            "id_pelicula"
        ].astype("Int64")

        ids_invalidos = df_limpio["id_pelicula"].isna().sum()

        ids_unicos = df_limpio[
            "id_pelicula"
        ].nunique(dropna=True)

        duplicados_adicionales = df_limpio[
            "id_pelicula"
        ].duplicated().sum()

        filas_duplicadas = df_limpio[
            "id_pelicula"
        ].duplicated(keep=False).sum()

        print("\n========================================")
        print("TRANSFORMACIÓN DE ID_PELICULA")
        print("========================================")

        print(f"Filas antes de limpiar: {len(df_staging)}")
        print(f"Filas después de limpiar: {len(df_limpio)}")
        print(f"IDs inválidos después de limpiar: {ids_invalidos}")
        print(f"IDs únicos después de limpiar: {ids_unicos}")
        print(
            "Registros duplicados adicionales: "
            f"{duplicados_adicionales}"
        )
        print(
            "Filas involucradas en duplicados: "
            f"{filas_duplicadas}"
        )

        print("\nEjemplo de IDs antes y después:")
        print(
            df_limpio[
                [
                    "id_pelicula_original",
                    "id_pelicula"
                ]
            ].head(10)
        )

        print("\nEjemplo de registros con ID duplicado:")

        muestra_duplicados = df_limpio[
            df_limpio["id_pelicula"].duplicated(
                keep=False
            )
        ].sort_values("id_pelicula")

        print(
            muestra_duplicados[
                [
                    "id_pelicula_original",
                    "id_pelicula",
                    "titulo_original",
                    "reproducciones_mensuales",
                    "servidor_origen"
                ]
            ].head(10)
        )

        return df_limpio

    except Exception as error:
        print(f"Error al limpiar id_pelicula: {error}")
        return None

# ============================================================
# TRANSFORMACIÓN DE REPRODUCCIONES MENSUALES
# ============================================================

def limpiar_reproducciones_staging(df_staging):
    """
    Limpia la columna reproducciones_mensuales.

    Ejemplos:
    "8578 views" -> 8578
    "6863"       -> 6863
    "N/A"        -> valor nulo
    None         -> valor nulo

    En esta etapa todavía no se eliminan duplicados.
    """

    try:
        # Crear una copia para no modificar el DataFrame anterior.
        df_limpio = df_staging.copy()

        # Conservar el valor original como evidencia.
        df_limpio["reproducciones_original"] = (
            df_limpio["reproducciones_mensuales"]
        )

        # Convertir temporalmente a texto y quitar espacios.
        reproducciones_texto = (
            df_limpio["reproducciones_mensuales"]
            .astype("string")
            .str.strip()
        )

        # Extraer únicamente la parte numérica.
        reproducciones_numericas = (
            reproducciones_texto
            .str.extract(r"(\d+)", expand=False)
        )

        # Convertir el resultado a número.
        # Los valores como N/A y None se transforman en nulos.
        df_limpio["reproducciones_mensuales"] = pd.to_numeric(
            reproducciones_numericas,
            errors="coerce"
        ).astype("Int64")

        total_filas = len(df_limpio)

        reproducciones_validas = (
            df_limpio["reproducciones_mensuales"]
            .notna()
            .sum()
        )

        reproducciones_invalidas = (
            df_limpio["reproducciones_mensuales"]
            .isna()
            .sum()
        )

        print("\n========================================")
        print("TRANSFORMACIÓN DE REPRODUCCIONES")
        print("========================================")

        print(f"Total de filas: {total_filas}")
        print(
            "Reproducciones válidas después de limpiar: "
            f"{reproducciones_validas}"
        )
        print(
            "Reproducciones nulas o inválidas: "
            f"{reproducciones_invalidas}"
        )

        if reproducciones_validas > 0:
            print(
                "Reproducción mínima válida: "
                f"{df_limpio['reproducciones_mensuales'].min()}"
            )
            print(
                "Reproducción máxima válida: "
                f"{df_limpio['reproducciones_mensuales'].max()}"
            )

        # Mostrar casos que originalmente venían sucios.
        mascara_sucios = (
            reproducciones_texto.str.contains(
                "views",
                case=False,
                na=False
            )
            | reproducciones_texto.eq("N/A")
            | reproducciones_texto.isna()
        )

        print("\nEjemplos antes y después de limpiar:")

        print(
            df_limpio.loc[
                mascara_sucios,
                [
                    "id_pelicula",
                    "reproducciones_original",
                    "reproducciones_mensuales"
                ]
            ].head(15)
        )

        return df_limpio

    except Exception as error:
        print(
            "Error al limpiar reproducciones_mensuales: "
            f"{error}"
        )
        return None

# ============================================================
# TRANSFORMACIÓN DE FECHAS DE ESTRENO
# ============================================================

def limpiar_fechas_staging(df_staging):
    """
    Limpia la columna fecha_estreno_plataforma.

    Formatos válidos esperados:
    - AAAA-MM-DD
    - DD/MM/AAAA

    Valores como Próximamente, PENDIENTE, vacío y 00/00/0000
    se convierten en fecha nula.

    En esta etapa todavía no se eliminan duplicados.
    """

    try:
        # Crear una copia para no modificar directamente
        # el DataFrame recibido.
        df_limpio = df_staging.copy()

        # Conservar el valor original como evidencia.
        df_limpio["fecha_estreno_original"] = (
            df_limpio["fecha_estreno_plataforma"]
        )

        # Convertir temporalmente a texto y quitar espacios.
        fechas_texto = (
            df_limpio["fecha_estreno_plataforma"]
            .astype("string")
            .str.strip()
        )

        # Intentar interpretar primero el formato ISO.
        fechas_iso = pd.to_datetime(
            fechas_texto,
            format="%Y-%m-%d",
            errors="coerce"
        )

        # Intentar interpretar el formato chileno.
        fechas_chile = pd.to_datetime(
            fechas_texto,
            format="%d/%m/%Y",
            errors="coerce"
        )

        # Usar la fecha ISO cuando sea válida.
        # Si no lo es, intentar utilizar la fecha chilena.
        df_limpio["fecha_estreno_plataforma"] = (
            fechas_iso.fillna(fechas_chile)
        )

        fechas_validas = (
            df_limpio["fecha_estreno_plataforma"]
            .notna()
            .sum()
        )

        fechas_invalidas = (
            df_limpio["fecha_estreno_plataforma"]
            .isna()
            .sum()
        )

        print("\n========================================")
        print("TRANSFORMACIÓN DE FECHAS")
        print("========================================")

        print(f"Total de filas: {len(df_limpio)}")
        print(
            "Fechas válidas después de limpiar: "
            f"{fechas_validas}"
        )
        print(
            "Fechas nulas o inválidas: "
            f"{fechas_invalidas}"
        )

        if fechas_validas > 0:
            print(
                "Fecha mínima válida: "
                f"{df_limpio['fecha_estreno_plataforma'].min().date()}"
            )
            print(
                "Fecha máxima válida: "
                f"{df_limpio['fecha_estreno_plataforma'].max().date()}"
            )

        # Mostrar valores originales que no pudieron
        # convertirse en una fecha válida.
        mascara_invalidas = (
            df_limpio["fecha_estreno_plataforma"].isna()
        )

        print("\nEjemplos de fechas inválidas:")

        print(
            df_limpio.loc[
                mascara_invalidas,
                [
                    "id_pelicula",
                    "fecha_estreno_original",
                    "fecha_estreno_plataforma"
                ]
            ].head(15)
        )

        print("\nEjemplos de fechas convertidas:")

        print(
            df_limpio.loc[
                ~mascara_invalidas,
                [
                    "id_pelicula",
                    "fecha_estreno_original",
                    "fecha_estreno_plataforma"
                ]
            ].head(15)
        )

        return df_limpio

    except Exception as error:
        print(
            "Error al limpiar fecha_estreno_plataforma: "
            f"{error}"
        )
        return None

# ============================================================
# TRANSFORMACIÓN DE TEXTOS DE STAGING
# ============================================================

def limpiar_textos_staging(df_staging):
    """
    Limpia los campos de texto de staging.

    - Quita espacios innecesarios.
    - Reduce espacios repetidos dentro de los títulos.
    - Convierte títulos completamente en mayúsculas.
    - Convierte Null_Server en un valor nulo real.
    """

    try:
        df_limpio = df_staging.copy()

        # Limpiar los títulos.
        titulos = (
            df_limpio["titulo_original"]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .replace("", pd.NA)
        )

        # Solo convertir a formato título cuando el texto completo
        # viene escrito en mayúsculas.
        mascara_mayusculas = (
            titulos.str.isupper().fillna(False)
        )

        df_limpio["titulo_limpio"] = titulos.mask(
            mascara_mayusculas,
            titulos.str.title()
        )

        # Limpiar servidor de origen.
        servidores = (
            df_limpio["servidor_origen"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

        mascara_null_server = (
            servidores.str.lower()
            .eq("null_server")
            .fillna(False)
        )

        df_limpio["servidor_origen"] = servidores.mask(
            mascara_null_server,
            pd.NA
        )

        print("\n========================================")
        print("TRANSFORMACIÓN DE TEXTOS")
        print("========================================")

        print(
            "Títulos nulos después de limpiar: "
            f"{df_limpio['titulo_limpio'].isna().sum()}"
        )

        print(
            "Servidores nulos después de limpiar: "
            f"{df_limpio['servidor_origen'].isna().sum()}"
        )

        print("\nEjemplos de títulos antes y después:")

        print(
            df_limpio[
                [
                    "titulo_original",
                    "titulo_limpio"
                ]
            ].head(15)
        )

        return df_limpio

    except Exception as error:
        print(f"Error al limpiar textos de staging: {error}")
        return None


# ============================================================
# CONSOLIDACIÓN Y ELIMINACIÓN DE DUPLICADOS DE STAGING
# ============================================================

def consolidar_staging(df_staging):
    """
    Consolida los registros duplicados de una misma película.

    Regla utilizada:
    - Un solo registro por id_pelicula.
    - Primer título válido.
    - Mayor cantidad válida de reproducciones.
    - Fecha válida más antigua.
    - Se conservan los servidores como dato de auditoría.

    Se utiliza el máximo de reproducciones para evitar sumar
    registros que podrían corresponder a duplicados defectuosos.
    """

    try:
        def primer_valor_valido(serie):
            valores_validos = serie.dropna()

            if valores_validos.empty:
                return pd.NA

            return valores_validos.iloc[0]

        def combinar_servidores(serie):
            servidores_validos = sorted(
                set(
                    str(valor)
                    for valor in serie.dropna()
                    if str(valor).strip()
                )
            )

            if not servidores_validos:
                return pd.NA

            return ", ".join(servidores_validos)

        df_consolidado = (
            df_staging
            .groupby(
                "id_pelicula",
                as_index=False
            )
            .agg(
                titulo_interno=(
                    "titulo_limpio",
                    primer_valor_valido
                ),
                reproducciones_mensuales=(
                    "reproducciones_mensuales",
                    "max"
                ),
                fecha_estreno=(
                    "fecha_estreno_plataforma",
                    "min"
                ),
                cantidad_registros_origen=(
                    "id_pelicula_original",
                    "size"
                ),
                servidores_origen=(
                    "servidor_origen",
                    combinar_servidores
                )
            )
        )

        df_consolidado["id_pelicula"] = (
            df_consolidado["id_pelicula"]
            .astype("Int64")
        )

        df_consolidado["reproducciones_mensuales"] = (
            df_consolidado["reproducciones_mensuales"]
            .astype("Int64")
        )

        cantidad_duplicados_resueltos = (
            df_consolidado["cantidad_registros_origen"]
            .gt(1)
            .sum()
        )

        print("\n========================================")
        print("CONSOLIDACIÓN DE STAGING")
        print("========================================")

        print(
            "Filas antes de consolidar: "
            f"{len(df_staging)}"
        )

        print(
            "Películas después de consolidar: "
            f"{len(df_consolidado)}"
        )

        print(
            "IDs duplicados resueltos: "
            f"{cantidad_duplicados_resueltos}"
        )

        print(
            "IDs duplicados restantes: "
            f"{df_consolidado['id_pelicula'].duplicated().sum()}"
        )

        print("\nPrimeros registros consolidados:")

        print(df_consolidado.head(10))

        return df_consolidado

    except Exception as error:
        print(f"Error al consolidar staging: {error}")
        return None


# ============================================================
# TRANSFORMACIÓN DEL CSV
# ============================================================

def transformar_csv(df_csv):
    """
    Prepara el archivo de restricciones para su integración.

    - Convierte id_pelicula a entero.
    - Limpia espacios.
    - Normaliza clasificación y bloqueo.
    - Valida los valores permitidos.
    - Elimina posibles duplicados por ID.
    """

    try:
        df_limpio = df_csv.copy()

        columnas_esperadas = {
            "id_pelicula",
            "clasificacion_chile",
            "advertencia_contenido",
            "bloqueo_horario_infantil"
        }

        columnas_faltantes = (
            columnas_esperadas - set(df_limpio.columns)
        )

        if columnas_faltantes:
            raise ValueError(
                "Faltan columnas en el CSV: "
                f"{columnas_faltantes}"
            )

        df_limpio["id_pelicula"] = pd.to_numeric(
            df_limpio["id_pelicula"],
            errors="coerce"
        ).astype("Int64")

        df_limpio["clasificacion_chile"] = (
            df_limpio["clasificacion_chile"]
            .astype("string")
            .str.strip()
            .str.upper()
            .replace("", pd.NA)
        )

        df_limpio["advertencia_contenido"] = (
            df_limpio["advertencia_contenido"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

        df_limpio["bloqueo_horario_infantil"] = (
            df_limpio["bloqueo_horario_infantil"]
            .astype("string")
            .str.strip()
            .str.upper()
            .replace("", pd.NA)
        )

        clasificaciones_validas = {
            "TE",
            "TE+7",
            "14",
            "18"
        }

        bloqueos_validos = {
            "SI",
            "NO"
        }

        mascara_clasificacion_invalida = (
            df_limpio["clasificacion_chile"].notna()
            & ~df_limpio["clasificacion_chile"].isin(
                clasificaciones_validas
            )
        )

        mascara_bloqueo_invalido = (
            df_limpio["bloqueo_horario_infantil"].notna()
            & ~df_limpio["bloqueo_horario_infantil"].isin(
                bloqueos_validos
            )
        )

        clasificaciones_invalidas = (
            mascara_clasificacion_invalida.sum()
        )

        bloqueos_invalidos = (
            mascara_bloqueo_invalido.sum()
        )

        # Convertir valores no permitidos en nulos.
        df_limpio.loc[
            mascara_clasificacion_invalida,
            "clasificacion_chile"
        ] = pd.NA

        df_limpio.loc[
            mascara_bloqueo_invalido,
            "bloqueo_horario_infantil"
        ] = pd.NA

        ids_invalidos = (
            df_limpio["id_pelicula"].isna().sum()
        )

        # Eliminar únicamente registros que no tengan un ID válido.
        df_limpio = df_limpio.dropna(
            subset=["id_pelicula"]
        )

        df_limpio = df_limpio.drop_duplicates(
            subset=["id_pelicula"],
            keep="first"
        )

        print("\n========================================")
        print("TRANSFORMACIÓN DEL CSV")
        print("========================================")

        print(f"Filas preparadas: {len(df_limpio)}")
        print(f"IDs inválidos: {ids_invalidos}")

        print(
            "Clasificaciones inválidas: "
            f"{clasificaciones_invalidas}"
        )

        print(
            "Bloqueos inválidos: "
            f"{bloqueos_invalidos}"
        )

        print(
            "IDs duplicados restantes: "
            f"{df_limpio['id_pelicula'].duplicated().sum()}"
        )

        return df_limpio

    except Exception as error:
        print(f"Error al transformar el CSV: {error}")
        return None


# ============================================================
# TRANSFORMACIÓN DE LA API
# ============================================================

def transformar_api(df_api):
    """
    Prepara los datos obtenidos desde TMDB.

    - Renombra id_pelicula_api.
    - Convierte los campos numéricos.
    - Limpia los títulos.
    - Elimina posibles duplicados por ID.
    """

    try:
        df_limpio = df_api.copy()

        columnas_esperadas = {
            "id_pelicula_api",
            "titulo_api",
            "popularidad_api",
            "votos_promedio_api"
        }

        columnas_faltantes = (
            columnas_esperadas - set(df_limpio.columns)
        )

        if columnas_faltantes:
            raise ValueError(
                "Faltan columnas en los datos de la API: "
                f"{columnas_faltantes}"
            )

        df_limpio = df_limpio.rename(
            columns={
                "id_pelicula_api": "id_pelicula"
            }
        )

        df_limpio["id_pelicula"] = pd.to_numeric(
            df_limpio["id_pelicula"],
            errors="coerce"
        ).astype("Int64")

        df_limpio["titulo_api"] = (
            df_limpio["titulo_api"]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .replace("", pd.NA)
        )

        df_limpio["popularidad_api"] = pd.to_numeric(
            df_limpio["popularidad_api"],
            errors="coerce"
        )

        df_limpio["votos_promedio_api"] = pd.to_numeric(
            df_limpio["votos_promedio_api"],
            errors="coerce"
        )

        ids_invalidos = (
            df_limpio["id_pelicula"].isna().sum()
        )

        df_limpio = df_limpio.dropna(
            subset=["id_pelicula"]
        )

        df_limpio = df_limpio.drop_duplicates(
            subset=["id_pelicula"],
            keep="first"
        )

        print("\n========================================")
        print("TRANSFORMACIÓN DE LA API")
        print("========================================")

        print(f"Filas preparadas: {len(df_limpio)}")
        print(f"IDs inválidos: {ids_invalidos}")

        print(
            "Popularidad nula: "
            f"{df_limpio['popularidad_api'].isna().sum()}"
        )

        print(
            "Votos promedio nulos: "
            f"{df_limpio['votos_promedio_api'].isna().sum()}"
        )

        print(
            "IDs duplicados restantes: "
            f"{df_limpio['id_pelicula'].duplicated().sum()}"
        )

        return df_limpio

    except Exception as error:
        print(f"Error al transformar los datos de la API: {error}")
        return None


# ============================================================
# INTEGRACIÓN DE LAS TRES FUENTES
# ============================================================

def integrar_fuentes(
    df_staging,
    df_csv,
    df_api
):
    """
    Une staging, API y CSV mediante id_pelicula.

    Staging se utiliza como fuente principal.
    API y CSV se incorporan mediante LEFT JOIN.
    """

    try:
        # Primer cruce: staging con API.
        df_integrado = df_staging.merge(
            df_api,
            on="id_pelicula",
            how="left",
            validate="one_to_one",
            indicator="_resultado_api"
        )

        peliculas_sin_api = (
            df_integrado["_resultado_api"]
            .eq("left_only")
            .sum()
        )

        df_integrado = df_integrado.drop(
            columns=["_resultado_api"]
        )

        # Segundo cruce: resultado anterior con CSV.
        df_integrado = df_integrado.merge(
            df_csv,
            on="id_pelicula",
            how="left",
            validate="one_to_one",
            indicator="_resultado_csv"
        )

        peliculas_sin_csv = (
            df_integrado["_resultado_csv"]
            .eq("left_only")
            .sum()
        )

        df_integrado = df_integrado.drop(
            columns=["_resultado_csv"]
        )

        # Utilizar el título interno.
        # Si faltara, se utiliza el título de la API.
        df_integrado["titulo"] = (
            df_integrado["titulo_interno"]
            .fillna(df_integrado["titulo_api"])
        )

        df_integrado = df_integrado.rename(
            columns={
                "clasificacion_chile":
                    "clasificacion_edad_local"
            }
        )

        columnas_resultado = [
            "id_pelicula",
            "titulo",
            "reproducciones_mensuales",
            "fecha_estreno",
            "popularidad_api",
            "votos_promedio_api",
            "clasificacion_edad_local",
            "advertencia_contenido",
            "bloqueo_horario_infantil",
            "cantidad_registros_origen",
            "servidores_origen"
        ]

        df_integrado = df_integrado[
            columnas_resultado
        ]

        print("\n========================================")
        print("INTEGRACIÓN DE LAS TRES FUENTES")
        print("========================================")

        print(
            "Películas después de integrar: "
            f"{len(df_integrado)}"
        )

        print(
            "Películas sin datos de API: "
            f"{peliculas_sin_api}"
        )

        print(
            "Películas sin datos de CSV: "
            f"{peliculas_sin_csv}"
        )

        print(
            "IDs duplicados en el resultado: "
            f"{df_integrado['id_pelicula'].duplicated().sum()}"
        )

        print("\nValores nulos del resultado integrado:")

        print(df_integrado.isna().sum())

        print("\nPrimeros 10 registros integrados:")

        print(df_integrado.head(10))

        return df_integrado

    except Exception as error:
        print(f"Error al integrar las fuentes: {error}")
        return None

# ============================================================
# APLICACIÓN DE REGLAS DE NEGOCIO
# ============================================================

def aplicar_reglas_negocio(df_integrado):
    """
    Evalúa la información integrada de cada película y genera
    la columna alerta_accion.

    Las reglas se aplican siguiendo un orden de prioridad.
    """

    try:
        df_resultado = df_integrado.copy()

        def determinar_alerta(fila):
            """
            Determina la acción correspondiente para una película.
            """

            reproducciones = fila["reproducciones_mensuales"]
            popularidad = fila["popularidad_api"]
            votos = fila["votos_promedio_api"]
            bloqueo = fila["bloqueo_horario_infantil"]

            # ------------------------------------------------
            # PRIORIDAD 1: faltan datos de reproducciones
            # ------------------------------------------------

            if pd.isna(reproducciones):
                return "Revisar dato de reproducciones"

            # ------------------------------------------------
            # PRIORIDAD 2: oportunidad comercial restringida
            # ------------------------------------------------

            if (
                popularidad >= UMBRAL_POPULARIDAD_ALTA
                and reproducciones < UMBRAL_REPRODUCCIONES_BAJAS
                and bloqueo == "SI"
            ):
                return (
                    "Mover a banner principal nocturno "
                    "y bloquear de portada infantil"
                )

            # ------------------------------------------------
            # PRIORIDAD 3: restricción de audiencia infantil
            # ------------------------------------------------

            if bloqueo == "SI":
                return "Bloquear de portada infantil"

            # ------------------------------------------------
            # PRIORIDAD 4: alta popularidad y bajo rendimiento
            # ------------------------------------------------

            if (
                popularidad >= UMBRAL_POPULARIDAD_ALTA
                and reproducciones < UMBRAL_REPRODUCCIONES_BAJAS
            ):
                return "Potenciar en portada principal"

            # ------------------------------------------------
            # PRIORIDAD 5: buen rendimiento global e interno
            # ------------------------------------------------

            if (
                popularidad >= UMBRAL_POPULARIDAD_ALTA
                and reproducciones >= UMBRAL_REPRODUCCIONES_ALTAS
            ):
                return "Mantener contenido destacado"

            # ------------------------------------------------
            # PRIORIDAD 6: baja valoración de usuarios
            # ------------------------------------------------

            if votos < UMBRAL_VOTOS_BAJOS:
                return "Revisar calidad antes de promocionar"

            # ------------------------------------------------
            # PRIORIDAD 7: sin condición especial
            # ------------------------------------------------

            return "Monitorear sin acción inmediata"

        # Aplicar la función a cada película.
        df_resultado["alerta_accion"] = df_resultado.apply(
            determinar_alerta,
            axis=1
        )

        print("\n========================================")
        print("APLICACIÓN DE REGLAS DE NEGOCIO")
        print("========================================")

        print(
            f"Películas evaluadas: "
            f"{len(df_resultado)}"
        )

        print("\nCantidad de películas por alerta:")

        print(
            df_resultado["alerta_accion"]
            .value_counts(dropna=False)
        )

        print("\nEjemplos de alertas generadas:")

        print(
            df_resultado[
                [
                    "id_pelicula",
                    "titulo",
                    "reproducciones_mensuales",
                    "popularidad_api",
                    "votos_promedio_api",
                    "clasificacion_edad_local",
                    "bloqueo_horario_infantil",
                    "alerta_accion"
                ]
            ].head(15)
        )

        return df_resultado

    except Exception as error:
        print(
            "Error al aplicar las reglas de negocio: "
            f"{error}"
        )
        return None

# ============================================================
# PREPARACIÓN DEL DATAFRAME FINAL PARA CARGA
# ============================================================

def preparar_dataframe_final(df_resultado):
    """
    Prepara las columnas definitivas que serán cargadas en
    dw_peliculas_analitica y agrega la fecha de actualización.
    """

    try:
        df_carga = df_resultado.copy()

        # Registrar el momento de ejecución del ETL.
        # Todas las películas de esta carga tendrán la misma fecha y hora.
        df_carga["fecha_actualizacion"] = (
            pd.Timestamp.now().floor("s")
        )

        # Seleccionar únicamente las columnas definidas
        # para la tabla analítica final.
        columnas_finales = [
            "id_pelicula",
            "titulo",
            "reproducciones_mensuales",
            "fecha_estreno",
            "popularidad_api",
            "votos_promedio_api",
            "clasificacion_edad_local",
            "alerta_accion",
            "fecha_actualizacion"
        ]

        df_carga = df_carga[columnas_finales]

        print("\n========================================")
        print("PREPARACIÓN DEL DATAFRAME FINAL")
        print("========================================")

        print(f"Filas preparadas para carga: {len(df_carga)}")
        print(f"Columnas finales: {len(df_carga.columns)}")

        print("\nTipos de datos finales:")
        print(df_carga.dtypes)

        print("\nValores nulos finales:")
        print(df_carga.isna().sum())

        print("\nPrimeros registros preparados:")
        print(df_carga.head(10))

        return df_carga

    except Exception as error:
        print(
            "Error al preparar el DataFrame final: "
            f"{error}"
        )
        return None

# ============================================================
# CARGA EN LA TABLA ANALÍTICA
# ============================================================

def cargar_tabla_analitica(df_carga):
    """
    Crea la tabla dw_peliculas_analitica si no existe,
    elimina la carga anterior e inserta los registros
    procesados por el ETL.

    La eliminación e inserción se ejecutan dentro de una
    transacción para evitar dejar la tabla incompleta.
    """

    try:
        consulta_creacion = text("""
            CREATE TABLE IF NOT EXISTS dw_peliculas_analitica (
                id_pelicula INT PRIMARY KEY,
                titulo VARCHAR(255) NOT NULL,
                reproducciones_mensuales INT NULL,
                fecha_estreno DATE NULL,
                popularidad_api FLOAT NULL,
                votos_promedio_api FLOAT NULL,
                clasificacion_edad_local VARCHAR(20) NULL,
                alerta_accion VARCHAR(255) NOT NULL,
                fecha_actualizacion DATETIME NOT NULL
            );
        """)

        # Preparar los valores nulos para que Pandas los
        # inserte correctamente como NULL en la base de datos.
        df_para_carga = df_carga.copy()

        df_para_carga = (
            df_para_carga
            .astype(object)
            .where(pd.notna(df_para_carga), None)
        )

        with engine.begin() as connection:

            # Crear la tabla si todavía no existe.
            connection.execute(consulta_creacion)

            # Carga completa:
            # eliminar los registros anteriores y reemplazarlos
            # por los datos generados en la ejecución actual.
            connection.execute(
                text("DELETE FROM dw_peliculas_analitica;")
            )

            # Insertar el DataFrame final.
            df_para_carga.to_sql(
                name="dw_peliculas_analitica",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=500
            )

            # Validar la cantidad cargada.
            total_cargado = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM dw_peliculas_analitica;
                """)
            ).scalar_one()

            # Comprobar que no existan IDs duplicados.
            ids_duplicados = connection.execute(
                text("""
                    SELECT
                        COUNT(*) - COUNT(DISTINCT id_pelicula)
                    FROM dw_peliculas_analitica;
                """)
            ).scalar_one()

            # Leer una pequeña muestra como evidencia.
            muestra_carga = pd.read_sql(
                text("""
                    SELECT
                        id_pelicula,
                        titulo,
                        reproducciones_mensuales,
                        popularidad_api,
                        clasificacion_edad_local,
                        alerta_accion,
                        fecha_actualizacion
                    FROM dw_peliculas_analitica
                    ORDER BY id_pelicula
                    LIMIT 10;
                """),
                connection
            )

        print("\n========================================")
        print("CARGA EN DW_PELICULAS_ANALITICA")
        print("========================================")

        print("Carga completada correctamente.")
        print(f"Registros cargados: {total_cargado}")
        print(f"IDs duplicados encontrados: {ids_duplicados}")

        print("\nMuestra de registros cargados:")
        print(muestra_carga)

        return True

    except Exception as error:
        print(
            "Error al cargar dw_peliculas_analitica: "
            f"{error}"
        )
        return False

# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main():
    """
    Ejecuta la extracción y transformación de las tres fuentes.
    """

    print("\n========================================")
    print("INICIO DEL PROCESO ETL")
    print("========================================")

    # --------------------------------------------------------
    # EXTRACCIÓN
    # --------------------------------------------------------

    # Prueba inicial realizada correctamente.
    # Se conserva comentada como evidencia.
    # probar_conexion()

    df_staging = extraer_staging()
    df_csv = extraer_csv()
    df_api = extraer_api()

    if (
        df_staging is None
        or df_csv is None
        or df_api is None
    ):
        print(
            "\nEl proceso se detuvo porque falló "
            "la extracción de una o más fuentes."
        )
        return

    print("\n========================================")
    print("RESUMEN DE LA EXTRACCIÓN")
    print("========================================")

    print(f"Staging: {len(df_staging)} filas")
    print(f"CSV: {len(df_csv)} filas")
    print(f"API: {len(df_api)} filas")

    # --------------------------------------------------------
    # TRANSFORMACIÓN DE STAGING
    # --------------------------------------------------------

    df_staging_transformado = limpiar_id_staging(
        df_staging
    )

    if df_staging_transformado is None:
        print("\nFalló la limpieza de id_pelicula.")
        return

    df_staging_transformado = (
        limpiar_reproducciones_staging(
            df_staging_transformado
        )
    )

    if df_staging_transformado is None:
        print("\nFalló la limpieza de reproducciones.")
        return

    df_staging_transformado = limpiar_fechas_staging(
        df_staging_transformado
    )

    if df_staging_transformado is None:
        print("\nFalló la limpieza de fechas.")
        return

    df_staging_transformado = limpiar_textos_staging(
        df_staging_transformado
    )

    if df_staging_transformado is None:
        print("\nFalló la limpieza de textos.")
        return

    df_staging_consolidado = consolidar_staging(
        df_staging_transformado
    )

    if df_staging_consolidado is None:
        print("\nFalló la consolidación de staging.")
        return

    # --------------------------------------------------------
    # TRANSFORMACIÓN DE CSV Y API
    # --------------------------------------------------------

    df_csv_transformado = transformar_csv(
        df_csv
    )

    if df_csv_transformado is None:
        print("\nFalló la transformación del CSV.")
        return

    df_api_transformado = transformar_api(
        df_api
    )

    if df_api_transformado is None:
        print("\nFalló la transformación de la API.")
        return

    # --------------------------------------------------------
    # INTEGRACIÓN
    # --------------------------------------------------------

    df_integrado = integrar_fuentes(
        df_staging_consolidado,
        df_csv_transformado,
        df_api_transformado
    )

    if df_integrado is None:
        print("\nFalló la integración de las fuentes.")
        return

    # --------------------------------------------------------
    # REGLAS DE NEGOCIO
    # --------------------------------------------------------

    df_final = aplicar_reglas_negocio(
        df_integrado
    )

    if df_final is None:
        print(
            "\nFalló la aplicación de las reglas "
            "de negocio."
        )
        return

    # --------------------------------------------------------
    # PREPARACIÓN PARA LA CARGA
    # --------------------------------------------------------

    df_carga = preparar_dataframe_final(
        df_final
    )

    if df_carga is None:
        print(
            "\nFalló la preparación del DataFrame "
            "para la carga."
        )
        return

    # --------------------------------------------------------
    # CARGA EN LA TABLA ANALÍTICA
    # --------------------------------------------------------

    if EJECUTAR_CARGA:

        carga_correcta = cargar_tabla_analitica(
            df_carga
        )

        if not carga_correcta:
            print(
                "\nEl proceso terminó porque falló "
                "la carga en la tabla analítica."
            )
            return

    else:
        print("\n========================================")
        print("CARGA OMITIDA")
        print("========================================")

        print(
            "El DataFrame fue preparado correctamente, "
            "pero no se cargó en TiDB porque "
            "EJECUTAR_CARGA está configurado en False."
        )

    print("\n========================================")
    print("TRANSFORMACIÓN Y REGLAS COMPLETADAS")
    print("========================================")

    print(
        "El DataFrame final quedó preparado "
        "para ser cargado en la tabla analítica."
    )

    print(
        f"Total de películas preparadas: "
        f"{len(df_carga)}"
    )


if __name__ == "__main__":
    main()