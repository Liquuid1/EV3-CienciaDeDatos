# Especificación Técnica y Arquitectura del Proyecto

## 1. Resumen del Proyecto
El objetivo de este proyecto es construir una solución *end-to-end* para la gestión y análisis de un catálogo cinematográfico y de streaming, cruzando datos de inventario interno, tendencias globales del mercado y regulaciones locales de clasificación de edad. El sistema automatizará la extracción, transformación y carga (ETL) de los datos para disponibilizarlos en un dashboard interactivo enfocado en la toma de decisiones estratégicas de marketing y adquisición de licencias.

## 2. Fuentes de Datos (Heterogeneidad)
Para dar cumplimiento a los requisitos de heterogeneidad de fuentes, el proyecto integrará tres orígenes de datos distintos mediante una llave común (`id_pelicula` o `titulo`):

* **Base de Datos Central (SQL en la Nube):** Hospedada en **TiDB Cloud (MySQL compatible)**. Contendrá la tabla de *Staging* (`stg_catalogo_interno`) con información cruda e inconsistente de más de 1,000 registros para simular un entorno real que requiera limpieza.
* **API REST Externa:** Conexión en tiempo real con **The Movie Database (TMDB) API** (`/trending/movie/week`) para extraer métricas de popularidad global, votos promedio y tendencias de la semana.
* **Archivo Plano (CSV Local):** Documento estático controlado por el equipo de operaciones que contiene las **Restricciones y Regulaciones Locales de Edad** (Chile/Latam) por película o categoría (Ej: TE, TE+7, 14, 18), así como alertas de cumplimiento de horarios de exhibición.

## 3. Modelo y Arquitectura de Datos (TiDB Cloud)

### Tabla de Entrada (Información Sucia / Staging)
* **Nombre:** `stg_catalogo_interno`
* **Propósito:** Almacenar el volcado inicial de datos internos del negocio (+1000 registros auto-generados).
* **Estructura sugerida:**
    * `id_pelicula` (INT, Primary Key - Permite simular duplicados controlados).
    * `titulo_original` (VARCHAR).
    * `reproducciones_mensuales` (VARCHAR - Datos sucios con texto ej: "1.500 visitas" o nulos).
    * `fecha_estreno_plataforma` (VARCHAR - Fechas en formatos inconsistentes DD/MM/AAAA y AAAA-MM-DD).
    * `servidor_origen` (VARCHAR).

### Tabla de Destino (Data Warehouse / Analítica)
* **Nombre:** `dw_peliculas_analitica`
* **Propósito:** Almacenar los datos ya procesados, limpios y unificados tras el cruce de las 3 fuentes. Es la tabla que alimentará al Dashboard.
* **Estructura sugerida:**
    * `id_pelicula` (INT, Primary Key limpia).
    * `titulo` (VARCHAR).
    * `reproducciones_mensuales` (INT - Limpio y casteado).
    * `fecha_estreno` (DATE - Formato estandarizado ISO AAAA-MM-DD).
    * `popularidad_api` (FLOAT - Desde TMDB).
    * `votos_promedio_api` (FLOAT - Desde TMDB).
    * `clasificacion_edad_local` (VARCHAR - Desde el CSV).
    * `alerta_accion` (VARCHAR - Campo calculado por la regla de negocio del ETL).
    * `fecha_actualizacion` (Actualización del registro).

## 4. Regla de Negocio Principal (Gatillo del ETL)
Durante la etapa de **Transformación**, el script de Python evaluará la correlación entre la popularidad global (API) y el rendimiento interno (BBDD), contrastado con las restricciones del CSV. 
* *Ejemplo de Regla:* Si una película es altamente popular en la API (>80 pts) pero tiene bajas reproducciones internas, y su clasificación en el CSV es "18+", el ETL escribirá automáticamente en `alerta_accion`: *"Alerta: Mover a banner principal nocturno"*. Si infringe alguna norma, marcará *"Bloquear de portada infantil"*.

## 5. Stack de Herramientas Tecnológicas
* **Lenguaje de Programación:** Python 3.x
* **Control de Versiones:** Git & GitHub (Gestión mediante ramas de características `feature/` y Pull Requests).
* **Gestión de Proyecto:** GitHub Projects (Tablero Kanban para asignación de Issues).
* **Motor de Base de Datos:** TiDB Cloud (Instancia MySQL en la nube).
* **Librerías Python Core:** `pandas` (ETL), `requests` (API), `sqlalchemy` + `pymysql` (Conectores SQL), `dash` + `plotly` (Dashboard), `python-dotenv` (Seguridad de credenciales).