# Script simple para consultar las columnas de una tabla en PostgreSQL.

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_TABLE = os.getenv("DB_TABLE", "peliculas")

if not all([DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD]):
    raise RuntimeError(
        "Faltan variables de entorno: DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD"
    )

DATABASE_URL = (
    f"postgresql+psycopg2://{quote_plus(DB_USERNAME)}:{quote_plus(DB_PASSWORD)}@"
    f"{DB_HOST}:{DB_PORT}/{quote_plus(DB_NAME)}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"sslmode": "require"})

query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = :table_name
ORDER BY ordinal_position
"""

with engine.connect() as connection:
    result = connection.execute(text(query), {"table_name": DB_TABLE}).fetchall()

    print(f"Columnas de la tabla '{DB_TABLE}':")
    for row in result:
        print(f"- {row[0]} ({row[1]})")
