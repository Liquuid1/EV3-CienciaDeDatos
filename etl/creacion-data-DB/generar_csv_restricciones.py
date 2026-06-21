import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ============================================================
# Este script NO modifica insert-staging.py.
# Objetivo:
#   1) Leer IDs desde la base de datos (AWS/TiDB).
#   2) Consultar la API TMDB usando esos IDs.
#   3) Generar un CSV con reglas locales de Chile.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE)

API_KEY = os.getenv("API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "catalogo_restricciones_chile.csv"

TMDB_BASE_URL = "https://api.themoviedb.org/3/movie"
SESSION = requests.Session()


def get_engine():
    if not all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
        raise RuntimeError(
            "Faltan variables de entorno para la base de datos."
        )

    database_url = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
    return create_engine(database_url, connect_args=connect_args)


def fetch_ids_from_db(engine):
    query = "SELECT id_pelicula FROM stg_catalogo_interno"
    with engine.connect() as connection:
        result = connection.execute(text(query))
        ids = []
        for row in result:
            value = row[0]
            if value is None:
                continue
            ids.append(int(str(value).strip()))
    return ids


def fetch_movie_details(movie_id):
    if not API_KEY:
        raise RuntimeError("API_KEY no configurada en el .env")

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    params = {
        "language": "es-ES",
        "append_to_response": "release_dates,credits"
    }

    url = f"{TMDB_BASE_URL}/{movie_id}"
    response = SESSION.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_chile_certification(data):
    release_dates = data.get("release_dates", {}).get("results", [])

    for item in release_dates:
        if item.get("iso_3166_1") == "CL":
            for release in item.get("release_dates", []):
                cert = release.get("certification", "")
                if cert:
                    return cert

    if data.get("adult") is True:
        return "18+"

    return "Sin certificación"


def map_rules(certification, adult_flag=False):
    cert = str(certification).strip().upper()

    # Reglas base para Chile (formato visual / negocio)
    if cert in {"18", "18+", "NC-17", "R", "X"} or adult_flag:
        return {
            "clasificacion_chile": "18+",
            "restriccion_horaria": "Solo horario nocturno / no promoción infantil",
            "promocion_permitida": "No permitida para público infantil",
        }

    if cert in {"14", "14+", "15", "15+", "PG-13"}:
        return {
            "clasificacion_chile": "14+",
            "restriccion_horaria": "Promoción restringida después de las 22:00",
            "promocion_permitida": "Permitida solo con contenido para mayores",
        }

    if cert in {"7", "7+", "TE", "TE+7", "PG", "G"}:
        return {
            "clasificacion_chile": cert if cert != "TE+7" else "TE+7",
            "restriccion_horaria": "Permitida en horario familiar",
            "promocion_permitida": "Permitida para campañas familiares",
        }

    return {
        "clasificacion_chile": "Sin clasificación",
        "restriccion_horaria": "Revisar manualmente",
        "promocion_permitida": "Revisar manualmente",
    }


def build_rows(ids):
    rows = []
    total = len(ids)
    for index, movie_id in enumerate(ids, start=1):
        print(
            f"[{index}/{total}] Procesando id={movie_id}...",
            flush=True,
        )
        start = time.time()
        try:
            data = fetch_movie_details(movie_id)
            certification = get_chile_certification(data)
            rules = map_rules(certification, adult_flag=data.get("adult", False))

            rows.append(
                {
                    "id_pelicula": movie_id,
                    "titulo": data.get("title", ""),
                    "popularidad": data.get("popularity", ""),
                    "votos_promedio": data.get("vote_average", ""),
                    "clasificacion_chile": rules["clasificacion_chile"],
                    "restriccion_horaria": rules["restriccion_horaria"],
                    "promocion_permitida": rules["promocion_permitida"],
                    "fuente": "TMDB + reglas Chile",
                }
            )
            elapsed = round(time.time() - start, 2)
            print(f"  OK ({elapsed}s)", flush=True)
        except Exception as e:
            elapsed = round(time.time() - start, 2)
            print(f"  ERROR ({elapsed}s): {e}", flush=True)
            rows.append(
                {
                    "id_pelicula": movie_id,
                    "titulo": "",
                    "popularidad": "",
                    "votos_promedio": "",
                    "clasificacion_chile": "Error",
                    "restriccion_horaria": str(e),
                    "promocion_permitida": "No disponible",
                    "fuente": "TMDB + reglas Chile",
                }
            )

    return rows


def main():
    engine = get_engine()
    ids = fetch_ids_from_db(engine)

    if not ids:
        print("No se encontraron IDs en stg_catalogo_interno.")
        return

    rows = build_rows(ids)
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Se generaron {len(df)} registros en: {OUTPUT_FILE}")
    print("Columnas del CSV:")
    print(df.columns.tolist())


if __name__ == "__main__":
    main()
