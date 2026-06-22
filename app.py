import subprocess
import sys
import os
import time

def ejecutar_script(ruta_script):
    """Ejecuta un script de Python en un subproceso y espera a que termine."""
    nombre_script = os.path.basename(ruta_script)
    print(f"\n==================================================")
    print(f"🚀 [ORQUESTADOR] Iniciando: {nombre_script}")
    print(f"==================================================")
    
    # Ejecutamos usando el mismo intérprete de Python actual
    resultado = subprocess.run([sys.executable, ruta_script])
    
    if resultado.returncode == 0:
        print(f"✅ [ORQUESTADOR] {nombre_script} finalizó con éxito.")
        return True
    else:
        print(f"❌ [ORQUESTADOR] ERROR crítico en {nombre_script}. Pipeline detenido.")
        return False

def main():
    print("🤖 --- INICIANDO PIPELINE CENTRALIZADO AUTOMÁTICO --- 🤖")
    inicio_total = time.time()

    # 1. PASO 1: Carga de datos sucios a Staging
    # Ruta según tu árbol: etl/creacion-data-DB/insert-staging.py
    script_staging = os.path.join("etl", "creacion-data-DB", "insert-staging.py")
    if not ejecutar_script(script_staging):
        sys.exit(1)

    # 2. PASO 2: Creación del archivo CSV de restricciones locales
    # Ruta según tu árbol: data/creacion-csv (Asegúrate de renombrarlo a .py si corresponde)
    script_csv = os.path.join("data", "creacion-csv.py") # <--- Cambiar extensión/nombre si es necesario
    if not ejecutar_script(script_csv):
        sys.exit(1)

    # 3. PASO 3: Ejecución del proceso ETL core (Cruce, Limpieza y Carga a DW)
    # Ruta según tu árbol: etl/etl_proyecto.py
    script_etl = os.path.join("etl", "etl_proyecto.py")
    if not ejecutar_script(script_etl):
        sys.exit(1)

    # Fin de la carga de datos
    tiempo_datos = time.time() - inicio_total
    print(f"\n✨ ¡Flujo de datos completado con éxito en {tiempo_datos:.2f} segundos! ✨")
    
    # 4. PASO 4: Levantar el Dashboard interactivo
    # Ruta según tu árbol: dashboards/dashboard.py
    script_dashboard = os.path.join("dashboards", "dashboard.py")
    
    print(f"\n==================================================")
    print(f"📊 [ORQUESTADOR] Levantando Dashboard: {os.path.basename(script_dashboard)}")
    print(f"📌 Nota: Este proceso mantendrá la terminal ocupada.")
    print(f"🛑 Para apagar todo, presiona Ctrl + C.")
    print(f"==================================================")
    
    try:
        # Usamos Popen en vez de run para el dashboard, porque este script NO termina (se queda escuchando)
        subprocess.run([sys.executable, script_dashboard])
    except KeyboardInterrupt:
        print("\n🛑 [ORQUESTADOR] Servidor del dashboard detenido por el usuario.")
    print("\n🤖 --- PIPELINE FINALIZADO --- 🤖")

if __name__ == "__main__":
    main()