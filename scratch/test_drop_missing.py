import pandas as pd
import sys
import os
# Asegurar que el directorio raíz está en el path
sys.path.append(os.getcwd())

from src.procesamiento import mapear_ids_hospitales, limpiar_nombre

def test_drop_missing():
    print("Iniciando prueba de filtrado (drop_missing=True)...")
    
    # 1. Simular datos con el hospital problemático
    data = {
        'Nombre Hospital': ['UPA 11 - FV', 'Oñativia', 'MODULO HOSPITALARIO 8 LZ', 'MODULO HOSPITALARIO 8 LZ'],
        'paciente_id': [1, 2, 3, 4]
    }
    df_test = pd.DataFrame(data)
    
    # 2. Cargar maestro de coordenadas actual
    csv_path = "data/hospitales_coordenadas.csv"
    if not os.path.exists(csv_path):
        print(f"ERROR: No se encuentra {csv_path}")
        return
        
    df_hosp = pd.read_csv(csv_path)
    
    try:
        # 3. Intentar mapeo con drop_missing=True
        print("\n--- EJECUTANDO mapear_ids_hospitales(drop_missing=True) ---")
        df_result = mapear_ids_hospitales(df_test, df_hosp, drop_missing=True)
        
        print("\nSUCESO: Mapeo completado.")
        print("Resultados finales (sin hospitales faltantes):")
        print(df_result[['Nombre Hospital', 'id_hospital']])
        
        # Verificar que se eliminaron 2 registros
        original_count = len(df_test)
        final_count = len(df_result)
        dropped = original_count - final_count
        print(f"\nRegistros originales: {original_count}")
        print(f"Registros finales: {final_count}")
        print(f"Registros eliminados: {dropped}")
        
        assert dropped == 2, f"Se esperaba eliminar 2 registros, se eliminaron {dropped}"
        assert 'MODULO HOSPITALARIO 8 LZ' not in df_result['Nombre Hospital'].values, "Hospital no filtrado"
        
        print("\n✅ Prueba exitosa: Filtrado y reporte funcionan correctamente.")
        
    except Exception as e:
        print(f"\n❌ FALLO: La validación falló inesperadamente: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_drop_missing()
