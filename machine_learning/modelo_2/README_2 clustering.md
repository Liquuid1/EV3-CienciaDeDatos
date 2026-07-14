# Modelo 2 - Clustering No Supervisado

## 1. Objetivo del modelo

Este módulo implementa el **Modelo 2 del proyecto**, correspondiente a un modelo de Machine Learning **no supervisado** utilizando el algoritmo **KMeans**.

El objetivo principal es segmentar las películas de la plataforma de streaming en grupos de comportamiento similares, utilizando variables analíticas generadas por el pipeline ETL.

Este modelo permite identificar patrones de negocio dentro del catálogo, tales como:

- Contenido consolidado de alto consumo local.
- Contenido globalmente popular y de alto rendimiento.
- Contenido de consumo moderado con oportunidad de impulso.
- Contenido con baja valoración crítica.

---

## 2. Fuente de datos

El modelo utiliza como fuente principal la tabla analítica final generada por el proceso ETL:

```sql
dw_peliculas_analitica
```

Esta tabla integra información proveniente de:

- Base de datos interna en TiDB Cloud.
- API externa TMDB.
- Archivo CSV local con restricciones de contenido.

La tabla ya contiene datos limpios, integrados y enriquecidos con reglas de negocio.

---

## 3. Variables utilizadas

Para el entrenamiento del clustering se utilizaron las siguientes variables:

| Variable | Tipo | Descripción |
|---|---|---|
| `reproducciones_mensuales` | Numérica | Nivel de consumo local de cada película en la plataforma. |
| `popularidad_api` | Numérica | Popularidad global obtenida desde la API TMDB. |
| `votos_promedio_api` | Numérica | Evaluación promedio de usuarios según TMDB. |
| `clasificacion_edad_local` | Categórica | Clasificación de edad local del contenido. |

No se utilizó la variable `alerta_accion` como entrada del modelo, ya que corresponde a una regla de negocio generada previamente por el ETL. El objetivo del clustering es encontrar patrones a partir de los datos base, no replicar directamente una regla ya calculada.

---

## 4. Preparación de datos

Antes de entrenar el modelo, se aplicaron las siguientes transformaciones:

### Variables numéricas

Para las variables numéricas se aplicó:

- Imputación de valores nulos usando la mediana.
- Escalamiento con `StandardScaler`.

Esto evita que variables con escalas mayores, como las reproducciones mensuales, dominen el comportamiento del algoritmo.

### Variable categórica

Para la variable `clasificacion_edad_local` se aplicó:

- Imputación usando el valor más frecuente.
- Codificación mediante `OneHotEncoder`.

Esto permite que el modelo incorpore la clasificación de edad sin imponer un orden numérico artificial entre categorías.

---

## 5. Algoritmo utilizado

El algoritmo utilizado fue:

```text
KMeans
```

Se eligió KMeans porque permite agrupar registros similares sin necesidad de una variable objetivo previamente etiquetada. Esto es adecuado para el problema, ya que se busca descubrir segmentos naturales dentro del catálogo de películas.

El modelo fue configurado con:

```python
random_state=42
n_init=10
```

Esto permite obtener resultados reproducibles y reducir la dependencia de una única inicialización aleatoria.

---

## 6. Selección del número de clusters

Se evaluaron distintos valores de `k`, desde 2 hasta 6 clusters.

La métrica utilizada para seleccionar el mejor valor fue:

```text
silhouette_score
```

Esta métrica evalúa qué tan bien separado y compacto está cada grupo. Un valor más alto indica una mejor separación entre clusters.

Resultados obtenidos:

| k | silhouette_score | inercia |
|---|---:|---:|
| 2 | 0.228007 | 878.640104 |
| 3 | 0.265101 | 675.196353 |
| 4 | 0.275533 | 516.145605 |
| 5 | 0.216885 | 463.278243 |
| 6 | 0.209741 | 417.636105 |

El mejor resultado se obtuvo con:

```text
k = 4
silhouette_score = 0.275533
```

Por este motivo, el modelo final fue entrenado con 4 clusters.

---

## 7. Resultados del clustering

El modelo agrupó 292 películas en 4 clusters.

Resumen obtenido:

| Cluster | Películas | Reproducciones promedio | Popularidad promedio | Votos promedio | Interpretación |
|---|---:|---:|---:|---:|---|
| 0 | 166 | 7.841 | 41,71 | 7,22 | Contenido consolidado de alto consumo local |
| 1 | 10 | 7.352 | 383,49 | 6,71 | Contenido globalmente popular y de alto rendimiento |
| 2 | 94 | 3.029 | 43,02 | 7,00 | Contenido de consumo moderado / oportunidad de impulso |
| 3 | 22 | 5.314 | 43,18 | 1,61 | Contenido con baja valoración crítica |

---

## 8. Interpretación de negocio

Los clusters permiten transformar un resultado técnico en segmentos útiles para la toma de decisiones.

### Cluster 0: Contenido consolidado de alto consumo local

Agrupa la mayor cantidad de películas. Presenta altas reproducciones locales, popularidad media y buena valoración promedio.

Este segmento representa contenido que ya funciona bien dentro de la plataforma y que debe mantenerse visible.

### Cluster 1: Contenido globalmente popular y de alto rendimiento

Agrupa pocas películas, pero con popularidad API extremadamente alta y alto consumo local.

Este segmento representa contenido con alto valor estratégico para destacar en banners, campañas o recomendaciones principales.

### Cluster 2: Contenido de consumo moderado / oportunidad de impulso

Tiene buena valoración promedio, pero menor consumo local en comparación con los clusters de mayor rendimiento.

Este segmento puede ser utilizado para campañas de recomendación, curaduría editorial o pruebas de promoción.

### Cluster 3: Contenido con baja valoración crítica

Presenta votos promedio muy bajos, aunque mantiene un nivel medio de reproducciones.

Este grupo debería revisarse antes de ser promocionado, ya que puede afectar la percepción de calidad del catálogo.

---

## 9. Archivos generados

La ejecución del script genera los siguientes artefactos:

| Archivo | Descripción |
|---|---|
| `modelo_clustering.pkl` | Modelo KMeans entrenado y guardado para reutilización. |
| `metricas_clustering.csv` | Comparación de valores de k usando silhouette score e inercia. |
| `resultados_clusters.csv` | Dataset completo con el cluster y segmento asignado a cada película. |
| `resumen_clusters.csv` | Resumen agregado por cluster con promedios principales. |

---

## 10. Ejecución del modelo

Desde la raíz del proyecto, ejecutar:

```bash
python machine_learning/modelo_2/modelo_2_clustering.py
```

Antes de ejecutar, se debe contar con el archivo `.env` en la raíz del proyecto con las variables de conexión a TiDB Cloud.

El archivo `.env` no debe subirse al repositorio, ya que contiene credenciales sensibles.

---

## 11. Dependencias principales

Este módulo utiliza las siguientes librerías:

```text
pandas
sqlalchemy
pymysql
python-dotenv
scikit-learn
joblib
```

Si es necesario instalarlas:

```bash
python -m pip install pandas sqlalchemy pymysql python-dotenv scikit-learn joblib
```

---

## 12. Valor para el proyecto EFT

Este modelo aporta al proyecto final porque incorpora una técnica de Machine Learning no supervisada para analizar el catálogo desde una perspectiva de negocio.

El clustering permite complementar las reglas del ETL con una segmentación basada en patrones de datos, facilitando decisiones sobre promoción, monitoreo, priorización y revisión de contenido.

Además, el modelo genera evidencia reproducible mediante archivos de métricas, resultados y modelo entrenado, cumpliendo con los requerimientos de evaluación asociados a Machine Learning, interpretación de resultados y aporte analítico.