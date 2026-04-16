import pandas as pd
import sys
import os

# Configuración de rutas
base_dir = r"c:\Users\micag\Documents\RedesHospitales"
csv_path = os.path.join(base_dir, "data", "hospitales_coordenadas.csv")
excel_path = os.path.join(base_dir, "data", "pacientes.xlsx")

# Cargar archivos
try:
    df_hosp = pd.read_csv(csv_path)
    df_pacientes = pd.read_excel(excel_path)
    
    # Normalizar nombres para comparación inicial
    df_pacientes['Nombre Hospital'] = df_pacientes['Nombre Hospital'].str.strip()
    df_hosp['Nombre Hospital'] = df_hosp['Nombre Hospital'].str.strip()
    
    # Identificar ID de Oñativia
    onativia_row = df_hosp[df_hosp['Nombre Hospital'].str.contains('Oñativia', na=False, case=False)]
    if not onativia_row.empty:
        onativia_id = onativia_row['id_hospital'].iloc[0]
        onativia_name = onativia_row['Nombre Hospital'].iloc[0]
        print(f"Hospital: {onativia_name} -> ID: {onativia_id}")
        
        # Conteo en el maestro
        count_maestro = len(df_hosp[df_hosp['id_hospital'] == onativia_id])
        print(f"Registros en maestro: {count_maestro}")
        
        # Mapeo de IDs (simular lógica de procesamiento.py)
        mapping = dict(zip(df_hosp['Nombre Hospital'], df_hosp['id_hospital']))
        df_pacientes['id_hospital'] = df_pacientes['Nombre Hospital'].map(mapping)
        
        # Conteo en pacientes
        count_pacientes = len(df_pacientes[df_pacientes['id_hospital'] == onativia_id])
        print(f"Pacientes asignados a {onativia_id}: {count_pacientes}")
        
        # Verificar hospital_destino
        df_pacientes['hospital_destino'] = df_pacientes['hospital_destino'].str.strip()
        df_pacientes['id_hospital_destino'] = df_pacientes['hospital_destino'].map(mapping)
        count_destinos = len(df_pacientes[df_pacientes['id_hospital_destino'] == onativia_id])
        print(f"Pacientes con DESTINO {onativia_id}: {count_destinos}")
        
        if count_destinos >= 4:
            print("\nSUCCESS: Se detectaron los 4 traslados hacia Oñativia.")
        else:
            print(f"\nWARNING: Aún se detectan solo {count_destinos} traslados hacia Oñativia.")
            # Diagnóstico: ver qué nombres hay en hospital_destino que contienen Oñativia
            raw_onativia_destinos = df_pacientes[df_pacientes['hospital_destino'].str.contains('Oñativia', na=False, case=False)]['hospital_destino'].unique()
            print(f"Nombres crudos en destino: {raw_onativia_destinos}")
    else:
        print("ERROR: No se encontró 'Oñativia' en el maestro de hospitales.")
        
except Exception as e:
    print(f"Error durante la auditoría: {e}")
