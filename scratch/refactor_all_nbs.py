import nbformat
import os
import re

def refactor_notebook(path):
    print(f"Processing {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    modified = False
    for cell in nb.cells:
        if cell.cell_type == 'code':
            source = cell.source
            original_source = source
            
            # Pattern 1: Inject ID mapping in manual cleaning blocks
            if 'df_base = df_base.rename(columns={' in source and 'hospitales' in source:
                if 'mapear_ids_hospitales' not in source:
                    # Insert after the common normalization line
                    insert_after = "df_base['hospital_origen'] = df_base['hospital_origen'].str.strip()"
                    if insert_after in source:
                        mapping_code = """
# --- NUEVO: Mapeo de IDs únicos de Hospital ---
df_base['Nombre Hospital'] = df_base['hospital_origen'] 
df_base = mapear_ids_hospitales(df_base, hospitales)
"""
                        source = source.replace(insert_after, insert_after + mapping_code)
                    
            # Pattern 2: Update destination shifts to include IDs
            source = source.replace(
                "df_base['hospital_destino'] = df_base.groupby('paciente_id')['hospital_origen'].shift(-1)",
                "df_base['id_hospital_destino'] = df_base.groupby('paciente_id')['id_hospital'].shift(-1)\n    df_base['hospital_destino'] = df_base.groupby('paciente_id')['hospital_origen'].shift(-1)"
            )
            
            # Pattern 3: Update validity masks (names -> IDs)
            source = source.replace(
                "(df_base['hospital_origen'] != df_base['hospital_destino'])",
                "(df_base['id_hospital'] != df_base['id_hospital_destino'])"
            )
            
            # Pattern 4: Merges and joins (updating left_on/right_on to IDs if it makes sense)
            # This is riskier, but 'Nombre Hospital' in merge is usually joining coords.
            # No changes here yet to avoid breaking name-based complexity dictionaries.

            if source != original_source:
                cell.source = source
                modified = True

    if modified:
        with open(path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        print(f"Refactored {path}")
    else:
        print(f"No changes made to {path}")

# List of all relevant notebooks
notebooks = [
    'JAIIO_notebooks/02_mapas.ipynb',
    'JAIIO_notebooks/03_ranking_trayectorias.ipynb',
    'JAIIO_notebooks/04_trayectorias_especificas.ipynb',
    'JAIIO_notebooks/05_1er_informe.ipynb'
]

base_dir = r'C:\Users\micag\Documents\RedesHospitales'

for nb_path in notebooks:
    abs_path = os.path.join(base_dir, nb_path)
    if os.path.exists(abs_path):
        refactor_notebook(abs_path)
    else:
        print(f"Warning: {abs_path} not found")
