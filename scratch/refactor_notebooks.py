import nbformat
import os
import re

def refactor_notebook(path):
    with open(path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    modified = False
    for cell in nb.cells:
        if cell.cell_type == 'code':
            source = cell.source
            original_source = source
            
            # 1. Update manual mapping/renaming logic in 01
            # If it renames 'Nombre Hospital' to 'hospital_origen' AND loads 'hospitales_coordenadas.csv'
            if ('hospital_origen' in source or 'Nombre Hospital' in source) and 'hospitales_coordenadas.csv' in source:
                # Inyectar mapeo de IDs después de la limpieza
                if 'limpiar_pacientes' in source and 'mapear_ids_hospitales' not in source:
                    source = source.replace('df_base = limpiar_pacientes(df_base)', 'df_base = limpiar_pacientes(df_base)\ndf_base = mapear_ids_hospitales(df_base, hospitales)')
                    modified = True
            
            # 2. General logical replacements (careful with labels)
            # Replace grouping by names with IDs where it makes sense for network logic
            source = source.replace("['hospital_origen', 'hospital_destino']", "['id_hospital', 'id_hospital_destino']")
            source = source.replace("groupby('hospital_origen')", "groupby('id_hospital')")
            source = source.replace("groupby(['hospital_origen',", "groupby(['id_hospital',")
            
            # Update 'Nombre Hospital' calls in network logic to 'id_hospital'
            # But keep them for plotting where appropriate. This is tricky.
            # Most notebooks use 'hospital_origen' after renaming in Cell 7.
            
            if source != original_source:
                cell.source = source
                modified = True

    if modified:
        with open(path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        print(f"Refactored {path}")
    else:
        print(f"No changes needed for {path}")

# Note: many notebooks use init_notebook, which is already fixed.
# This script targets those that do manual loading or specific aggregations.

notebooks = [
    'JAIIO_notebooks/01_redes_basico.ipynb',
    'JAIIO_notebooks/02_mapas.ipynb',
    'JAIIO_notebooks/03_atractores_emisores.ipynb',
    'JAIIO_notebooks/04_trayectorias.ipynb',
    'JAIIO_notebooks/05_grafos_interactivos.ipynb'
]

for nb_path in notebooks:
    abs_nb_path = os.path.join(r'C:\Users\micag\Documents\RedesHospitales', nb_path)
    if os.path.exists(abs_nb_path):
        refactor_notebook(abs_nb_path)
