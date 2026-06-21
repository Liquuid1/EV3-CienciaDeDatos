import argparse
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")

ALLOWED_TABLES = {
    "stg_catalogo_interno",
    "dw_peliculas_analitica",
}


def get_engine():
    if not all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
        raise RuntimeError("Faltan variables de entorno para la base de datos.")

    database_url = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
    return create_engine(database_url, connect_args=connect_args)


def is_safe_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value))


def fetch_row_by_value(table_name: str, column_name: str, value: str):
    if table_name not in ALLOWED_TABLES:
        raise ValueError(
            f"Tabla no permitida: {table_name}. Tablas válidas: {sorted(ALLOWED_TABLES)}"
        )

    if not is_safe_identifier(table_name) or not is_safe_identifier(column_name):
        raise ValueError("Nombre de tabla o columna inválido.")

    engine = get_engine()
    with engine.connect() as connection:
        query = text(
            f"SELECT * FROM {table_name} WHERE {column_name} = :value"
        )
        result = connection.execute(query, {"value": value}).fetchone()

    if result is None:
        return None

    return dict(result._mapping)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Consulta una sola fila de la base de datos por columna y valor."
        )
    )
    parser.add_argument(
        "--table",
        default="stg_catalogo_interno",
        help="Tabla a consultar (por defecto: stg_catalogo_interno)",
    )
    parser.add_argument(
        "--column",
        required=True,
        help="Nombre de la columna por la que se va a filtrar",
    )
    parser.add_argument(
        "--value",
        required=True,
        help="Valor exacto a buscar en esa columna",
    )
    args = parser.parse_args()

    row = fetch_row_by_value(args.table, args.column, args.value)

    if row is None:
        print(f"No se encontraron resultados en {args.table} para {args.column}={args.value}")
        return

    print(f"Tabla: {args.table}")
    print(f"Filtro: {args.column}={args.value}")
    print("Resultado:")
    for key, val in row.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
