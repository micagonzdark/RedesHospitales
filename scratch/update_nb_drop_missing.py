import nbformat
import os

def update_notebook_call(filepath):
    print(f"Updating {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    
    modified = False
    for cell in nb.cells:
        if cell.cell_type == 'code':
            source = cell.source
            if 'df_base = mapear_ids_hospitales(df_base, hospitales)' in source:
                new_source = source.replace(
                    'df_base = mapear_ids_hospitales(df_base, hospitales)',
                    'df_base = mapear_ids_hospitales(df_base, hospitales, drop_missing=True)'
                )
                cell.source = new_source
                modified = True
                print(f"  Updated call in {filepath}")
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        return True
    return False

# Path to the notebook
base = r'c:\Users\micag\Documents\RedesHospitales'
nb_path = os.path.join(base, 'JAIIO_notebooks', '01_redes_basico.ipynb')

if os.path.exists(nb_path):
    update_notebook_call(nb_path)
else:
    print(f"File not found: {nb_path}")
