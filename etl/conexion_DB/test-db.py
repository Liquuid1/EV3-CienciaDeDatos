#ESTE ARCHIVO NO ES PARTE DE LA EVALUACION, ES SOLO PARA PROBAR LA CONEXION A TIDB CLOUD Y VER SI FUNCIONA CORRECTAMENTE

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Cargar las variables de entorno desde el archivo .env
load_dotenv()

# 2. Construir la URL de conexión de MySQL utilizando pymysql
# Formato: mysql+pymysql://usuario:contraseña@host:puerto/base_de_datos
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_DATABASE')}"

try:
    # 3. Crear el motor de conexión (Engine)
    # Agregamos ssl_verify_cert=False si TiDB Cloud requiere SSL pero tu entorno local no tiene los certificados configurados
    connect_args = {"ssl": {"fake_user_to_enable_ssl": True}} 
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    
    print("🔄 Intentando conectar a TiDB Cloud...")
    
    # 4. Abrir una conexión y ejecutar comandos SQL
    with engine.connect() as connection:
        print("✅ ¡Conexión exitosa a TiDB Cloud!")
        
        # --- PRUEBA 2: Insertar un dato sucio de prueba ---
        print("\n📥 Insertando registro de prueba...")
        insert_query = """
        INSERT INTO stg_catalogo_interno (id_pelicula, titulo_original, reproducciones_mensuales, fecha_estreno_plataforma, servidor_origen)
        VALUES ('MV-9999', '  Inception (ORIGINAL) ', '1.250 views', '25/12/2010', 'Servidor_Test')
        ON DUPLICATE KEY UPDATE titulo_original=VALUES(titulo_original);
        """
        connection.execute(text(insert_query))
        connection.commit()
        print("✅ Registro insertado con éxito.")
        
        # --- PRUEBA 3: Consultar el dato para verificar ---
        print("\n🔍 Consultando la base de datos...")
        select_query = "SELECT * FROM stg_catalogo_interno WHERE id_pelicula = 'MV-9999';"
        result = connection.execute(text(select_query)).fetchone()
        
        if result:
            print(f"🎉 ¡Dato recuperado con éxito de la nube!")
            print(f"ID: {result[0]} | Título: '{result[1]}' | Reproducciones: {result[2]}")
        else:
            print("⚠️ No se encontró el registro.")

except Exception as e:
    print("Error crítico en la conexión o manipulación de la base de datos:")
    print(e)