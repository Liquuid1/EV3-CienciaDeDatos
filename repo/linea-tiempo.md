# Linea de tiempo y planificación del proyecto

Este documento funcionara como una bitacora oficial de cambios a lo largo del proyecto

## FASE 0 - PLANIFICACIÓN

Como equipo decidimos elegir como tema para este proyecto una plataforma de streaming nacional que se dedica a transmitir peliculas en internet. Consumiremos datos de la api publica **https://themoviedb.org** para tener mas información de las peliculas, simularemos un catalogo interno en una base de datos en la nube en **https://tidbcloud.com/** y tambien guardaremos restricciones legales regionales en un archivo csv local. Todo esto llevara a una tabla en la base de datos con los datos limpios y listos para hacer dashboards interactivos.

### Organización

Para organizar el proyecto generamos issues en Github y creamos un github proyects para mantener el trackeo de las tareas en las que esta trabajando cada uno. Cada issue tiene su propia rama definida y estas ramas deberan pasar por un pull request para pasar a main. Los issues creados son los siguientes:

1) Inicialización del Repositorio y Entorno Seguro
2) Script de Carga de Datos Sucios (+1000 registros)
3) Script de Extracción Base de la API de TMDB
4) Archivo CSV con restricción por edad de las peliculas en el repositorio interno
5) Creación del Script Central etl_proyecto.py
6) Construcción de la Interfaz y Vistas para Audiencias
7) Pruebas Unitarias y Documentación Final

En el estado actual el tablero del proyecto se ve así:

![alt text](tablero-00.png)