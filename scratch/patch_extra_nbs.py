import nbformat
import os

def patch_notebook(filepath):
    print(f"Patching {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    
    modified = False
    for cell in nb.cells:
        if cell.cell_type == 'code':
            source = cell.source
            # Logic: If it loads trayectorias but doesn't have df_hosp mapping
            if 'pd.read_excel(RUTA_EXCEL, sheet_name=2)' in source and 'df_hosp' not in source:
                new_source = source.replace(
                    'trayectorias = pd.read_excel(RUTA_EXCEL, sheet_name=2)',
                    "df_hosp = pd.read_csv('../data/hospitales_coordenadas.csv')\ntrayectorias = pd.read_excel(RUTA_EXCEL, sheet_name=2)"
                )
                if 'df_pacientes = pd.read_excel(RUTA_EXCEL, sheet_name=0)' in new_source:
                    new_source = new_source.replace(
                        'df_pacientes = pd.read_excel(RUTA_EXCEL, sheet_name=0)',
                        "df_pacientes = pd.read_excel(RUTA_EXCEL, sheet_name=0)\ndf_pacientes = mapear_ids_hospitales(df_pacientes, df_hosp)"
                    )
                cell.source = new_source
                modified = True
                print(f"  Applied mapping to {filepath}")
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        return True
    return False

# Base path
base = r'c:\Users\micag\Documents\RedesHospitales'
nbs = [
    os.path.join(base, 'JAIIO_notebooks', '03_ranking_trayectorias.ipynb'),
    os.path.join(base, 'JAIIO_notebooks', '04_trayectorias_especificas.ipynb'),
]

for nb_path in nbs:
    if os.path.exists(nb_path):
        patch_notebook(nb_path)
    else:
        print(f"File not found: {nb_path}")
