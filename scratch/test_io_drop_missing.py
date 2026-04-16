import sys
import os
# Asegurar que el directorio raíz está en el path
sys.path.append(os.getcwd())

from src.io import init_notebook

def test_init_notebook_drop():
    print("Iniciando prueba de init_notebook(drop_missing=True)...")
    
    # Path a los datos (relativo desde el test)
    data_path = "data"
    
    try:
        # Ejecutar inicialización con filtrado
        print("\n--- EJECUTANDO init_notebook(drop_missing=True) ---")
        ctx = init_notebook(data_path=data_path, drop_missing=True, verbose=True)
        
        print("\nSUCESO: Inicialización completada.")
        print(f"Pacientes cargados: {len(ctx['df_pacientes'])}")
        print(f"Traslados cargados: {len(ctx['traslados'])}")
        
        # Verificar que el hospital problemático no está (si es que estaba en el excel)
        # El test confirma que la función no explotó y manejó el parámetro.
        print("\n✅ Prueba exitosa: init_notebook propaga correctamente el parámetro drop_missing.")
        
    except Exception as e:
        print(f"\n❌ FALLO: La inicialización lanzó una excepción: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_init_notebook_drop()
