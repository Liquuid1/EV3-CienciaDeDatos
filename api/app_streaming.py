import os
from pathlib import Path

import numpy as np
from datetime import date, datetime

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")

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
# CONEXIÓN A TIDB CLOUD
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
    pool_pre_ping=True,
    pool_recycle=300
)


# ============================================================
# CREACIÓN DE LA API
# ============================================================

app = FastAPI(
    title="API Streaming - Proyecto Ciencia de Datos",
    description=(
        "API REST para exponer la tabla analítica final "
        "del pipeline ETL del proyecto de streaming."
    ),
    version="1.0.0"
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def convertir_dataframe_a_json(df):
    """
    Convierte un DataFrame a una lista de diccionarios compatible con JSON.

    Corrige valores nulos, NaN, fechas y tipos numéricos de numpy
    para evitar errores al devolver respuestas desde FastAPI.
    """

    def limpiar_valor(valor):
        if pd.isna(valor):
            return None

        if isinstance(valor, (pd.Timestamp, datetime, date)):
            return valor.isoformat()

        if isinstance(valor, np.integer):
            return int(valor)

        if isinstance(valor, np.floating):
            return float(valor)

        return valor

    registros = []

    for _, fila in df.iterrows():
        registro = {
            columna: limpiar_valor(valor)
            for columna, valor in fila.items()
        }
        registros.append(registro)

    return registros


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def inicio():
    """
    Endpoint inicial para verificar que la API está disponible.
    """

    return {
        "mensaje": "API Streaming funcionando correctamente",
        "tabla_origen": "dw_peliculas_analitica",
        "documentacion": "/docs"
    }


@app.get("/peliculas")
def obtener_peliculas():
    """
    Obtiene todas las películas desde la tabla analítica final.

    Fuente:
    - dw_peliculas_analitica
    """

    consulta = """
        SELECT
            id_pelicula,
            titulo,
            reproducciones_mensuales,
            fecha_estreno,
            popularidad_api,
            votos_promedio_api,
            clasificacion_edad_local,
            alerta_accion,
            fecha_actualizacion
        FROM dw_peliculas_analitica
        ORDER BY id_pelicula;
    """

    try:
        df = pd.read_sql(
            consulta,
            con=engine
        )

        return {
            "total_registros": len(df),
            "datos": convertir_dataframe_a_json(df)
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar películas: {str(error)}"
        )


@app.get("/peliculas/{id_pelicula}")
def obtener_pelicula_por_id(id_pelicula: int):
    """
    Obtiene una película específica según su ID.

    Parámetro:
    - id_pelicula: identificador de la película.
    """

    consulta = text("""
        SELECT
            id_pelicula,
            titulo,
            reproducciones_mensuales,
            fecha_estreno,
            popularidad_api,
            votos_promedio_api,
            clasificacion_edad_local,
            alerta_accion,
            fecha_actualizacion
        FROM dw_peliculas_analitica
        WHERE id_pelicula = :id_pelicula;
    """)

    try:
        df = pd.read_sql(
            consulta,
            con=engine,
            params={
                "id_pelicula": id_pelicula
            }
        )

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró película con id_pelicula={id_pelicula}"
            )

        resultado = convertir_dataframe_a_json(df)

        return resultado[0]

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar película por ID: {str(error)}"
        )