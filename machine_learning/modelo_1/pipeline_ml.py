import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import numpy as np

ACCIONES_PRIORITARIAS = [
    "Revisar dato de reproducciones",
    "Mover a banner principal nocturno y bloquear de portada infantil",
    "Bloquear de portada infantil",
    "Potenciar en portada principal",
    "Revisar calidad antes de promocionar",
]

BASE_DIR = Path(__file__).resolve().parents[2]
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
    "DB_DATABASE": DB_NAME,
}

variables_faltantes = [nombre for nombre, valor in variables_requeridas.items() if not valor]
if variables_faltantes:
    raise ValueError(f"Faltan variables en el archivo .env: {variables_faltantes}")

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, pool_recycle=300)


def cargar_datos_dw():
    """Carga la tabla analítica final generada por el ETL."""
    consulta = """
        SELECT
            id_pelicula,
            titulo,
            reproducciones_mensuales,
            popularidad_api,
            votos_promedio_api,
            clasificacion_edad_local,
            alerta_accion,
            fecha_actualizacion
        FROM dw_peliculas_analitica;
    """

    try:
        df = pd.read_sql(consulta, con=engine)
        print("\n========================================")
        print("CARGA DE DATOS PARA MODELO 1")
        print("========================================")
        print("Datos cargados desde dw_peliculas_analitica.")
        print(f"Filas: {len(df)}")
        print(f"Columnas: {len(df.columns)}")
        print(df.head(10))
        print(df.isna().sum())
        return df
    except Exception as error:
        print(f"Error al cargar datos desde TiDB: {error}")
        return None


def preparar_variables(df):
    """Prepara las variables para clasificación supervisada."""
    if df is None:
        return None, None

    columnas_requeridas = [
        "popularidad_api",
        "votos_promedio_api",
        "reproducciones_mensuales",
        "clasificacion_edad_local",
        "alerta_accion",
    ]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {faltantes}")

    df_modelo = df.copy()
    df_modelo["objetivo"] = df_modelo["alerta_accion"].isin(ACCIONES_PRIORITARIAS).astype(int)

    X = df_modelo[
        [
            "popularidad_api",
            "votos_promedio_api",
            "reproducciones_mensuales",
            "clasificacion_edad_local",
        ]
    ].copy()

    X["popularidad_api"] = pd.to_numeric(X["popularidad_api"], errors="coerce")
    X["votos_promedio_api"] = pd.to_numeric(X["votos_promedio_api"], errors="coerce")
    X["reproducciones_mensuales"] = pd.to_numeric(X["reproducciones_mensuales"], errors="coerce")
    X["clasificacion_edad_local"] = X["clasificacion_edad_local"].fillna("desconocido").astype(str)
    X = pd.get_dummies(X, columns=["clasificacion_edad_local"], drop_first=True)
    X = X.fillna(0)

    y = df_modelo["objetivo"]
    return X, y


def entrenar_y_validar(X, y, df_original=None):
    """Entrena un Random Forest y valida su desempeño."""
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    modelo = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
    )
    modelo.fit(X_train, y_train)

    predicciones = modelo.predict(X_test)

    print("\n========================================")
    print("ENTRENAMIENTO Y VALIDACIÓN")
    print("========================================")
    print("Entrenamiento:", len(X_train))
    print("Prueba:", len(X_test))
    print()
    print("Accuracy:", accuracy_score(y_test, predicciones))
    print()
    print("Matriz de Confusión")
    print(confusion_matrix(y_test, predicciones))
    print()
    print("Classification Report")
    print(classification_report(y_test, predicciones))

    if df_original is not None:
        salida_dir = BASE_DIR / "machine_learning" / "modelo_1" / "salidas"
        salida_dir.mkdir(parents=True, exist_ok=True)

        resultados = pd.DataFrame({
            "y_real": y_test.reset_index(drop=True),
            "y_pred": pd.Series(predicciones, name="y_pred"),
        })

        resultados.to_csv(salida_dir / "resultados_modelo_1.csv", index=False, encoding="utf-8")

        print("\nArchivos generados:")
        print(f"- {salida_dir / 'resultados_modelo_1.csv'}")

        try:
            resultados.to_excel(salida_dir / "resultados_modelo_1.xlsx", index=False)
            print(f"- {salida_dir / 'resultados_modelo_1.xlsx'}")
        except ImportError:
            print("El archivo Excel no se generó porque falta la librería openpyxl.")

    return modelo


def main():
    """Ejecuta el pipeline completo del modelo 1."""
    print("\n========================================")
    print("MODELO 1 - CLASIFICACIÓN SUPERVISADA")
    print("========================================")

    df = cargar_datos_dw()
    if df is None:
        print("No se pudieron cargar los datos desde TiDB.")
        return

    X, y = preparar_variables(df)
    if X is None or y is None:
        print("No se pudieron preparar las variables del modelo.")
        return

    modelo = entrenar_y_validar(X, y, df_original=df)
    if modelo is None:
        print("No se pudo entrenar el modelo.")
        return

    print("\nModelo entrenado correctamente.")


if __name__ == "__main__":
    main()
