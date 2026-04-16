import pandas as pd
import sys
import os

# Configuración de rutas
base_dir = r"c:\Users\micag\Documents\RedesHospitales"
csv_path = os.path.join(base_dir, "data", "hospitales_coordenadas.csv")
excel_path = os.path.join(base_dir, "data", "revision_dfs.xlsx")

# Cargar archivos
try:
    df_hosp = pd.read_csv(csv_path)
    # Cargar la hoja de episodios cronológicos
    df_episodios = pd.read_excel(excel_path, sheet_name='2_Episodios_Cronologicos')
    
    # Normalizar nombres 
    df_hosp['Nombre Hospital'] = df_hosp['Nombre Hospital'].str.strip()
    df_episodios['Nombre Hospital'] = df_episodios['Nombre Hospital'].str.strip()
    df_episodios['hospital_destino'] = df_episodios['hospital_destino'].str.strip()
    
    # Identificar ID de Oñativia
    onativia_row = df_hosp[df_hosp['Nombre Hospital'].str.contains('Oñativia', na=False, case=False)]
    if not onativia_row.empty:
        onativia_id = onativia_row['id_hospital'].iloc[0]
        onativia_name = onativia_row['Nombre Hospital'].iloc[0]
        print(f"Hospital: {onativia_name} -> ID: {onativia_id}")
        
        # Mapeo de IDs
        mapping = dict(zip(df_hosp['Nombre Hospital'], df_hosp['id_hospital']))
        
        # Mapear destino
        df_episodios['id_hospital_destino'] = df_episodios['hospital_destino'].map(mapping)
        
        # Conteo de destinos Oñativia
        count_destinos = len(df_episodios[df_episodios['id_hospital_destino'] == onativia_id])
        print(f"Traslados con DESTINO {onativia_name} ({onativia_id}) en revision_dfs.xlsx: {count_destinos}")
        
        if count_destinos >= 4:
            print("\nSUCCESS: Se detectaron los 4 traslados hacia Oñativia en la fuente original.")
            print("Esto confirma que la lógica de IDs ahora permite capturar todos los datos.")
        else:
            print(f"\nWARNING: Aún se detectan solo {count_destinos} traslados hacia Oñativia.")
            # Diagnóstico
            matches = df_episodios[df_episodios['hospital_destino'].str.contains('Oñativia', na=False, case=False)]
            print(f"Nombres encontrados en Excel: {matches['hospital_destino'].unique()}")

    else:
        print("ERROR: No se encontró 'Oñativia' en el maestro de hospitales.")
        
except Exception as e:
    print(f"Error durante la auditoría: {e}")
