import pandas as pd
import numpy as np
import sys
import os
# Asegurar que el directorio raíz está en el path
sys.path.append(os.getcwd())

from src.funciones_complejas import generar_matrices_traslados

def test_generar_matrices():
    print("Iniciando prueba de generar_matrices_traslados...")
    
    # 1. Mock Data
    hosp_data = {
        'id_hospital': ['H01', 'H02'],
        'Nombre Hospital': ['Hospital A', 'Hospital B'],
        'municipioAbreviado': ['MUN1', 'MUN2'],
        'complejidad': [1, 2],
        'color': ["(1,0,0)", "(0,1,0)"]
    }
    df_hosp = pd.DataFrame(hosp_data)
    
    pacientes_data = {
        'paciente_id': [1, 2, 3],
        'id_hospital': ['H01', 'H01', 'H02'],
        'fecha_ingreso': pd.to_datetime(['2023-01-01', '2023-01-05', '2023-01-10'])
    }
    df_pacientes = pd.DataFrame(pacientes_data)
    
    traslados_data = {
        'fecha_egreso': pd.to_datetime(['2023-01-02', '2023-01-06']),
        'id_hospital': ['H01', 'H01'],
        'id_hospital_destino': ['H02', 'H02'],
        'motivo_egreso': ['traslado', 'traslado'],
        'estado_egreso': ['egreso', 'egreso']
    }
    df_traslados = pd.DataFrame(traslados_data)
    
    # Mock PERIODOS
    fecha_ini = pd.to_datetime('2023-01-01')
    fecha_fin = pd.to_datetime('2023-01-31')
    
    try:
        # 2. Ejecutar función
        # Usamos plt.ion() para que no bloquee si se abre una ventana, 
        # aunque en este entorno no debería abrirse.
        import matplotlib.pyplot as plt
        plt.ion()
        
        generar_matrices_traslados(
            df_traslados, 
            df_pacientes, 
            df_hosp, 
            fecha_ini, 
            fecha_fin, 
            tipo_matriz='probabilidad'
        )
        
        print("\nSUCESO: La función se ejecutó correctamente sin NameError.")
        print("✅ Prueba exitosa.")
        
    except Exception as e:
        print(f"\n❌ FALLO: La función lanzó una excepción: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generar_matrices()
