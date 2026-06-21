# Configuración de conexión a PostgreSQL en RDS

1. Copia este ejemplo a un archivo `.env` real en la misma carpeta.
2. Completa `DB_HOST`, `DB_NAME`, `DB_USERNAME` y la región.
3. Si vas a usar IAM, deja `DB_USE_IAM=true` y usa `aws configure` o un perfil ya configurado.
4. Si no vas a usar IAM, define `DB_PASSWORD` en el `.env`.
5. Ejecuta el script `rds_postgres_connector.py` para consultar los IDs.
