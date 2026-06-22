# 🎬 Streaming EV3 - Panel de Analítica e Integración de Datos

Este repositorio contiene la solución empaquetada para el proyecto final de **Programación para la Ciencia de Datos**. El sistema implementa un flujo automatizado de extremo a extremo (End-to-End Pipeline) que extrae, procesa y unifica datos heterogéneos de una plataforma de streaming nacional, enriqueciéndolos con metadatos globales mediante una API REST y cruzándolos con reglas de negocio locales a través de un archivo plano. El resultado final se despliega en un dashboard analítico interactivo multi-audiencia.

---

## 👥 1. Estructura del Equipo y Roles

* **David Zúñiga** — *Coordinador & Product Owner* (Modelamiento de arquitectura, orquestación central y control de calidad en Git).
* **Betsabe Spring** — *Desarrolladora* (Diseño y optimización del motor central ETL y lógica de negocio).
* **Rodrigo Toro** — *Idearador/Desarrollador* (Ingesta en staging, generación de datos heterogéneos y construcción de interfaz).

---

## 🏗️ 2. Arquitectura del Sistema y Componentes

El proyecto integra tres fuentes de datos con tecnologías modernas en la nube y metodologías ágiles:

1. **Base de Datos Staging (`TiDB Cloud`):** Simulación del catálogo de consumo interno de la plataforma con más de 1,000 registros sucios (ID con espacios, fechas desordenadas, duplicados y ruido string).
2. **API REST Externa (`The Movie Database - TMDB`):** Extracción de metadatos globales en tiempo real (Popularidad, títulos oficiales y votación de la crítica) a través de peticiones HTTP parametrizadas por ID único.
3. **Archivo Plano Local (`CSV`):** Matriz estática de operaciones comerciales que define las restricciones de edad para Chile (`TE`, `14`, `18`), advertencias de contenido y banderas de bloqueo horario.

---

## 📁 3. Estructura del Repositorio

El árbol de directorios refleja una separación limpia de responsabilidades (SoC):

```text
EV3/
├── api/
│   ├── extract_api.py       # Módulo de consulta en bruto a TMDB API
│   └── test-api.py          # Scripts de pruebas unitarias/conexión de la API
├── dashboards/
│   └── dashboard.py         # Aplicación interactiva en Dash y Plotly
├── data/
│   ├── creacion-csv.py      # Generador del archivo estático de restricciones
│   └── restricciones_locales.csv # Archivo plano de negocio (CSV)
├── docs/
│   └── especificaciones_proyecto.md # Documentación y requerimientos iniciales
├── etl/
│   ├── conexion_DB/
│   │   └── test-db.py       # Script de testeo para certificados SSL con TiDB
│   ├── creacion-data-DB/
│   │   └── insert-staging.py # Script de ingesta masiva y ensuciamiento de datos
│   └── etl_proyecto.py      # Motor ETL central (Limpieza, Merge y Carga a DW)
├── repo/
│   ├── linea-tiempo.md      # Bitácora viva y control de fases del proyecto
│   ├── tablero-00.png       # Evidencia visual Kanban - Estado inicial
│   └── tablero-01.png       # Evidencia visual Kanban - Avances
├── .env                     # Variables de entorno seguras (Ignorado en Git)
├── .gitignore               # Configuración de exclusiones de Git
├── README.MD                # Documentación principal del sistema
└── run_pipeline.py          # Orquestador maestro del proyecto
```

## 🛠️ 4. Tecnologías y Librerías Utilizadas

El entorno se ejecuta bajo Python y utiliza las siguientes dependencias del ecosistema de datos:

* **Manipulación de Datos:** `pandas`
* **Conexión a Bases de Datos:** `sqlalchemy`, `pymysql`
* **Consumo de APIs REST:** `requests`
* **Visualización e Interactividad:** `dash`, `plotly`
* **Seguridad y Entorno:** `python-dotenv`
* **Soporte y Sistema:** `subprocess`, `sys`, `os`, `time`, `datetime`, `random`, `re`

---

## 🚀 5. Instrucciones de Despliegue y Ejecución

Para levantar todo el ecosistema de datos, desde la base cruda hasta la visualización en el navegador con un solo clic, sigue estos pasos:

### Paso 1: Configurar las variables de entorno
Crea un archivo llamado `.env` en la raíz del proyecto y agrega tus credenciales de acceso seguro siguiendo esta estructura (reemplaza con tus datos reales):

```env
TMDB_KEY=tu_api_key_de_the_moviedb
DB_HOST=tu_host_de_tidb_cloud
DB_PORT=3306
DB_USER=tu_usuario
DB_PASSWORD=tu_password
DB_NAME=tu_base_de_datos
```

### Paso 2: Ejecutar el Orquestador Maestro
Abre tu terminal en la raíz del proyecto (`EV3/`) y ejecuta el script centralizador utilizando el siguiente comando en la consola:

`python run_pipeline.py`

Este script ejecutará de forma secuencial y automática:
1. Población de `stg_catalogo_interno` en TiDB Cloud.
2. Generación del CSV local en `/data/`.
3. Limpieza, cruce de datos y carga final en la tabla destino analítica del Data Warehouse.
4. Inicialización del servidor web del dashboard.

### Paso 3: Visualizar el Dashboard
Una vez completado el pipeline, abre tu navegador web e ingresa a la dirección local por defecto:
👉 **http://127.0.0.1:8050/**

*Nota: Para detener la ejecución por completo en cualquier momento, presiona `Ctrl + C` en la terminal.*

---

## 📝 6. Conclusiones y Aprendizajes del Proyecto

* **Integración de Datos Heterogéneos:** El desarrollo de este proyecto demostró la complejidad real de unificar fuentes de datos de naturaleza distinta (Relacional en la nube, NoRelacional estructurado vía API REST y planos locales CSV). La correcta alineación de claves primarias limpias (`id_pelicula`) fue la piedra angular para lograr merges sin pérdida de integridad de la información.
* **Gobierno y Seguridad del Dato:** El uso de herramientas de protección como archivos `.gitignore` y variables de entorno `.env` reforzó la importancia del manejo seguro de credenciales críticas en infraestructura Cloud (TiDB). Evitar el traspaso de API Keys y claves de producción en el historial público de Git es una competencia indispensable para cualquier científico o ingeniero de datos.
* **Valor Metodológico del Rol de Coordinador:** La implementación de una estrategia clara de ramas (`feature/`, `bugfix/`, `docs/`) vinculadas a los *Issues* del tablero Kanban redujo a cero los conflictos de código complejos y permitió un desarrollo paralelo armónico. La figura del orquestador automatizado (`run_pipeline.py`) unificó el esfuerzo individual de los desarrolladores en un producto de software robusto, escalable y reproducible.