import os
from pathlib import Path

import joblib
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

# Este archivo está en:
# machine_learning/modelo_2/modelo_2_clustering.py
# parents[2] permite llegar a la raíz del proyecto.
BASE_DIR = Path(__file__).resolve().parents[2]

# Carpeta donde se guardarán los resultados del modelo 2.
OUTPUT_DIR = Path(__file__).resolve().parent

RUTA_MODELO = OUTPUT_DIR / "modelo_clustering.pkl"
RUTA_METRICAS = OUTPUT_DIR / "metricas_clustering.csv"
RUTA_RESULTADOS = OUTPUT_DIR / "resultados_clusters.csv"

load_dotenv(BASE_DIR / ".env")


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
# 3. CONEXIÓN A TIDB CLOUD
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
# 4. EXTRACCIÓN DE DATOS
# ============================================================

def cargar_datos_dw():
    """
    Carga la tabla analítica final generada por el ETL.

    Fuente:
    - dw_peliculas_analitica

    Esta tabla contiene datos limpios, integrados y con reglas
    de negocio aplicadas.
    """

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
        df = pd.read_sql(
            consulta,
            con=engine
        )

        print("\n========================================")
        print("CARGA DE DATOS PARA MODELO 2")
        print("========================================")
        print("Datos cargados desde dw_peliculas_analitica.")
        print(f"Filas: {len(df)}")
        print(f"Columnas: {len(df.columns)}")

        print("\nPrimeros registros:")
        print(df.head(10))

        print("\nValores nulos:")
        print(df.isna().sum())

        return df

    except Exception as error:
        print(f"Error al cargar datos desde TiDB: {error}")
        return None


# ============================================================
# 5. PREPARACIÓN DE VARIABLES
# ============================================================

def preparar_variables_clustering(df):
    """
    Prepara las variables que se usarán en el modelo KMeans.

    Variables numéricas:
    - reproducciones_mensuales
    - popularidad_api
    - votos_promedio_api

    Variable categórica:
    - clasificacion_edad_local

    Se excluye alerta_accion como variable de entrada porque es
    una regla de negocio ya calculada por el ETL. El objetivo del
    clustering es encontrar patrones en los datos base, no agrupar
    copiando directamente la alerta.
    """

    try:
        df_modelo = df.copy()

        columnas_necesarias = [
            "reproducciones_mensuales",
            "popularidad_api",
            "votos_promedio_api",
            "clasificacion_edad_local"
        ]

        columnas_faltantes = [
            columna
            for columna in columnas_necesarias
            if columna not in df_modelo.columns
        ]

        if columnas_faltantes:
            raise ValueError(
                f"Faltan columnas para clustering: {columnas_faltantes}"
            )

        X = df_modelo[columnas_necesarias]

        columnas_numericas = [
            "reproducciones_mensuales",
            "popularidad_api",
            "votos_promedio_api"
        ]

        columnas_categoricas = [
            "clasificacion_edad_local"
        ]

        preprocesador = ColumnTransformer(
            transformers=[
                (
                    "numericas",
                    Pipeline(
                        steps=[
                            (
                                "imputador",
                                SimpleImputer(strategy="median")
                            ),
                            (
                                "escalador",
                                StandardScaler()
                            )
                        ]
                    ),
                    columnas_numericas
                ),
                (
                    "categoricas",
                    Pipeline(
                        steps=[
                            (
                                "imputador",
                                SimpleImputer(strategy="most_frequent")
                            ),
                            (
                                "onehot",
                                OneHotEncoder(
                                    handle_unknown="ignore"
                                )
                            )
                        ]
                    ),
                    columnas_categoricas
                )
            ]
        )

        print("\n========================================")
        print("PREPARACIÓN DE VARIABLES")
        print("========================================")

        print("Variables utilizadas para clustering:")
        for columna in columnas_necesarias:
            print(f"- {columna}")

        print(
            "\nTratamiento aplicado:"
            "\n- Numéricas: imputación por mediana + escalamiento."
            "\n- Categóricas: imputación por moda + One Hot Encoding."
        )

        return X, preprocesador

    except Exception as error:
        print(f"Error al preparar variables: {error}")
        return None, None


# ============================================================
# 6. COMPARACIÓN DE VALORES DE K
# ============================================================

def evaluar_valores_k(X, preprocesador):
    """
    Evalúa distintos valores de k para KMeans.

    Se utiliza silhouette_score como métrica principal.
    Un valor más alto indica clusters más separados y coherentes.
    """

    try:
        X_transformado = preprocesador.fit_transform(X)

        resultados = []

        # Con 292 registros, probar de 2 a 6 clusters es razonable
        # y fácil de explicar en la presentación.
        for k in range(2, 7):

            modelo = KMeans(
                n_clusters=k,
                random_state=42,
                n_init=10
            )

            etiquetas = modelo.fit_predict(X_transformado)

            silueta = silhouette_score(
                X_transformado,
                etiquetas
            )

            resultados.append({
                "k": k,
                "silhouette_score": silueta,
                "inercia": modelo.inertia_
            })

        df_metricas = pd.DataFrame(resultados)

        mejor_fila = df_metricas.sort_values(
            "silhouette_score",
            ascending=False
        ).iloc[0]

        mejor_k = int(mejor_fila["k"])

        print("\n========================================")
        print("EVALUACIÓN DE VALORES DE K")
        print("========================================")

        print(df_metricas)

        print(
            f"\nMejor valor de k según silhouette_score: {mejor_k}"
        )

        return mejor_k, df_metricas

    except Exception as error:
        print(f"Error al evaluar valores de k: {error}")
        return None, None


# ============================================================
# 7. ENTRENAMIENTO DEL MODELO FINAL
# ============================================================

def entrenar_modelo_final(X, preprocesador, mejor_k):
    """
    Entrena el modelo KMeans final utilizando el mejor k detectado.
    """

    try:
        pipeline_clustering = Pipeline(
            steps=[
                (
                    "preprocesador",
                    preprocesador
                ),
                (
                    "modelo",
                    KMeans(
                        n_clusters=mejor_k,
                        random_state=42,
                        n_init=10
                    )
                )
            ]
        )

        pipeline_clustering.fit(X)

        print("\n========================================")
        print("ENTRENAMIENTO DEL MODELO FINAL")
        print("========================================")

        print(
            f"Modelo KMeans entrenado correctamente con k={mejor_k}."
        )

        return pipeline_clustering

    except Exception as error:
        print(f"Error al entrenar modelo final: {error}")
        return None


# ============================================================
# 8. INTERPRETACIÓN DE CLUSTERS
# ============================================================

def asignar_segmentos(df_resultados):
    """
    Asigna una etiqueta interpretativa a cada cluster según
    el comportamiento promedio observado.

    Esta interpretación se construye a partir de:
    - reproducciones promedio
    - popularidad promedio
    - votos promedio

    KMeans solo entrega números de cluster; la interpretación
    de negocio debe realizarse posteriormente.
    """

    try:
        resumen_clusters = (
            df_resultados
            .groupby("cluster")
            .agg(
                peliculas=("id_pelicula", "count"),
                promedio_reproducciones=(
                    "reproducciones_mensuales",
                    "mean"
                ),
                promedio_popularidad=(
                    "popularidad_api",
                    "mean"
                ),
                promedio_votos=(
                    "votos_promedio_api",
                    "mean"
                )
            )
            .reset_index()
        )

        segmentos = {}

        for _, fila in resumen_clusters.iterrows():

            cluster = int(fila["cluster"])
            reproducciones = fila["promedio_reproducciones"]
            popularidad = fila["promedio_popularidad"]
            votos = fila["promedio_votos"]

            if votos < 5:
                segmento = "Contenido con baja valoración crítica"

            elif popularidad >= 100 and reproducciones >= 5000:
                segmento = "Contenido globalmente popular y de alto rendimiento"

            elif reproducciones >= 6000 and votos >= 6:
                segmento = "Contenido consolidado de alto consumo local"

            elif reproducciones < 5000 and votos >= 6:
                segmento = "Contenido de consumo moderado / oportunidad de impulso"

            else:
                segmento = "Contenido estable / monitoreo"

            segmentos[cluster] = segmento

        df_resultados["segmento_cluster"] = (
            df_resultados["cluster"]
            .map(segmentos)
        )

        print("\n========================================")
        print("INTERPRETACIÓN DE CLUSTERS")
        print("========================================")

        print("Resumen por cluster:")
        print(resumen_clusters)

        print("\nEtiquetas asignadas:")
        for cluster, segmento in segmentos.items():
            print(f"Cluster {cluster}: {segmento}")

        return df_resultados, resumen_clusters

    except Exception as error:
        print(f"Error al interpretar clusters: {error}")
        return None, None


# ============================================================
# 9. GENERACIÓN DE RESULTADOS
# ============================================================

def generar_resultados(df, modelo):
    """
    Aplica el modelo entrenado a todas las películas y agrega
    la columna cluster.
    """

    try:
        df_resultados = df.copy()

        columnas_modelo = [
            "reproducciones_mensuales",
            "popularidad_api",
            "votos_promedio_api",
            "clasificacion_edad_local"
        ]

        X = df_resultados[columnas_modelo]

        df_resultados["cluster"] = modelo.predict(X)

        df_resultados, resumen_clusters = asignar_segmentos(
            df_resultados
        )

        if df_resultados is None:
            raise ValueError(
                "No fue posible asignar segmentos a los clusters."
            )

        print("\n========================================")
        print("RESULTADOS DEL CLUSTERING")
        print("========================================")

        print("Distribución de películas por cluster:")
        print(
            df_resultados["cluster"]
            .value_counts()
            .sort_index()
        )

        print("\nDistribución por segmento:")
        print(
            df_resultados["segmento_cluster"]
            .value_counts()
        )

        print("\nPrimeros resultados:")
        print(
            df_resultados[
                [
                    "id_pelicula",
                    "titulo",
                    "reproducciones_mensuales",
                    "popularidad_api",
                    "votos_promedio_api",
                    "clasificacion_edad_local",
                    "alerta_accion",
                    "cluster",
                    "segmento_cluster"
                ]
            ].head(15)
        )

        return df_resultados, resumen_clusters

    except Exception as error:
        print(f"Error al generar resultados: {error}")
        return None, None


# ============================================================
# 10. GUARDADO DE ARTEFACTOS
# ============================================================

def guardar_artefactos(
    modelo,
    df_metricas,
    df_resultados,
    resumen_clusters
):
    """
    Guarda los artefactos generados por el modelo:

    - modelo_clustering.pkl
    - metricas_clustering.csv
    - resultados_clusters.csv
    - resumen_clusters.csv
    """

    try:
        RUTA_RESUMEN = OUTPUT_DIR / "resumen_clusters.csv"

        joblib.dump(
            modelo,
            RUTA_MODELO
        )

        df_metricas.to_csv(
            RUTA_METRICAS,
            index=False,
            encoding="utf-8"
        )

        df_resultados.to_csv(
            RUTA_RESULTADOS,
            index=False,
            encoding="utf-8"
        )

        resumen_clusters.to_csv(
            RUTA_RESUMEN,
            index=False,
            encoding="utf-8"
        )

        print("\n========================================")
        print("GUARDADO DE ARTEFACTOS")
        print("========================================")

        print(f"Modelo guardado en: {RUTA_MODELO}")
        print(f"Métricas guardadas en: {RUTA_METRICAS}")
        print(f"Resultados guardados en: {RUTA_RESULTADOS}")
        print(f"Resumen de clusters guardado en: {RUTA_RESUMEN}")

        return True

    except Exception as error:
        print(f"Error al guardar artefactos: {error}")
        return False


# ============================================================
# 11. EJECUCIÓN PRINCIPAL
# ============================================================

def main():
    """
    Ejecuta el flujo completo del Modelo 2:
    clustering no supervisado de películas.
    """

    print("\n========================================")
    print("MODELO 2 - CLUSTERING NO SUPERVISADO")
    print("========================================")

    df = cargar_datos_dw()

    if df is None:
        print("\nEl proceso terminó porque no se pudieron cargar datos.")
        return

    X, preprocesador = preparar_variables_clustering(df)

    if X is None or preprocesador is None:
        print("\nEl proceso terminó porque falló la preparación.")
        return

    mejor_k, df_metricas = evaluar_valores_k(
        X,
        preprocesador
    )

    if mejor_k is None or df_metricas is None:
        print("\nEl proceso terminó porque falló la evaluación de k.")
        return

    modelo = entrenar_modelo_final(
        X,
        preprocesador,
        mejor_k
    )

    if modelo is None:
        print("\nEl proceso terminó porque falló el entrenamiento.")
        return

    df_resultados, resumen_clusters = generar_resultados(
        df,
        modelo
    )

    if df_resultados is None or resumen_clusters is None:
        print("\nEl proceso terminó porque falló la generación de resultados.")
        return

    guardado_correcto = guardar_artefactos(
        modelo,
        df_metricas,
        df_resultados,
        resumen_clusters
    )

    if not guardado_correcto:
        print("\nEl proceso terminó con errores al guardar archivos.")
        return

    print("\n========================================")
    print("MODELO 2 COMPLETADO CORRECTAMENTE")
    print("========================================")

    print(
        "El modelo no supervisado fue entrenado, evaluado "
        "y guardado correctamente."
    )


if __name__ == "__main__":
    main()