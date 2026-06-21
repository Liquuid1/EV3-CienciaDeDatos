from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote_plus

import boto3
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DB_USE_IAM = os.getenv("DB_USE_IAM", "false").lower() in {"1", "true", "yes", "on"}
DB_QUERY_CONDITION = os.getenv("DB_QUERY_CONDITION", "1=1")
OUTPUT_FILE = Path(__file__).with_name("ids_peliculas.json")


def get_auth_token() -> str:
    """Genera un token IAM para RDS si la configuración lo habilita."""
    if not DB_USE_IAM:
        if not DB_PASSWORD:
            raise RuntimeError(
                "Falta DB_PASSWORD. Define la variable de entorno o habilita DB_USE_IAM=true."
            )
        return DB_PASSWORD

    if not DB_HOST or not DB_USER:
        raise RuntimeError(
            "Para IAM debes definir DB_HOST, DB_USERNAME y AWS_REGION."
        )

    client = boto3.client("rds", region_name=AWS_REGION)
    token = client.generate_db_auth_token(
        DBHostname=DB_HOST,
        Port=DB_PORT,
        DBUsername=DB_USER,
        Region=AWS_REGION,
    )
    return token


def build_engine():
    password = get_auth_token()
    encoded_password = quote_plus(password)
    encoded_user = quote_plus(DB_USER or "")
    encoded_db = quote_plus(DB_NAME or "")

    database_url = (
        f"postgresql+psycopg2://{encoded_user}:{encoded_password}@"
        f"{DB_HOST}:{DB_PORT}/{encoded_db}"
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
    )


def fetch_ids() -> list[int]:
    if not DB_HOST or not DB_NAME or not DB_USER:
        raise RuntimeError(
            "Faltan variables de conexión: DB_HOST, DB_NAME, DB_USERNAME."
        )

    query = f"SELECT id FROM peliculas WHERE {DB_QUERY_CONDITION}"
    engine = build_engine()

    with engine.connect() as connection:
        result = connection.execute(text(query))
        ids = [row[0] for row in result.fetchall()]

    return ids


def save_ids(ids: list[int], output_path: Path = OUTPUT_FILE):
    output_path.write_text(json.dumps(ids, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"IDs guardados en: {output_path}")


if __name__ == "__main__":
    ids = fetch_ids()
    print(f"Se encontraron {len(ids)} IDs.")
    print(ids)
    save_ids(ids)
