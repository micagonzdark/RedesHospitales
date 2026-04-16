import nbformat
import os

def update_notebook_init(filepath):
    print(f"Updating {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    
    modified = False
    for cell in nb.cells:
        if cell.cell_type == 'code':
            source = cell.source
            if 'ctx_datos = init_notebook(data_path="../data")' in source:
                new_source = source.replace(
                    'ctx_datos = init_notebook(data_path="../data")',
                    'ctx_datos = init_notebook(data_path="../data", drop_missing=True)'
                )
                cell.source = new_source
                modified = True
                print(f"  Updated init_notebook call in {filepath}")
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        return True
    return False

# Path to the notebook
base = r'c:\Users\micag\Documents\RedesHospitales'
nb_path = os.path.join(base, 'JAIIO_notebooks', '02_mapas.ipynb')

if os.path.exists(nb_path):
    update_notebook_init(nb_path)
else:
    print(f"File not found: {nb_path}")
