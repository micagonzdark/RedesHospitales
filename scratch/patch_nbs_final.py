import nbformat
import os

def patch_nb_01(filepath):
    print(f"Patching {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    
    modified = False
    for cell in nb.cells:
        if cell.cell_type == 'code':
            source = cell.source
            if 'plt.subplots(2, 2' in source:
                # 1. Ajustar grilla a 2x3
                source = source.replace('plt.subplots(2, 2', 'plt.subplots(2, 3')
                
                # 2. Agregar lógica para ocultar el eje sobrante (el 6to)
                if 'axes.flatten()[idx]' in source and 'ax.set_visible(False)' not in source:
                    # Encontrar el final del loop o el final de la celda
                    # Insertamos el borrado del último eje al final del loop por PERIODOS
                    # O más fácil: después del loop, ocultamos axes.flatten()[5]
                    source += "\n# Ocultar el último eje (sexto) que queda vacío\naxes.flatten()[-1].set_visible(False)"
                
                cell.source = source
                modified = True
                print("  Applied 2x3 grid and axes hide.")
                
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        return True
    return False

def patch_nb_02(filepath):
    print(f"Patching {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    
    modified = False
    for cell in nb.cells:
        if cell.cell_type == 'code':
            source = cell.source
            if 'ctx_datos = init_notebook(data_path="../data")' in source:
                source = source.replace(
                    'ctx_datos = init_notebook(data_path="../data")',
                    'ctx_datos = init_notebook(data_path="../data", drop_missing=True)'
                )
                cell.source = source
                modified = True
                print("  Applied drop_missing=True to init_notebook.")
                
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        return True
    return False

base = r'c:\Users\micag\Documents\RedesHospitales'
patch_nb_01(os.path.join(base, 'JAIIO_notebooks', '01_redes_basico.ipynb'))
patch_nb_02(os.path.join(base, 'JAIIO_notebooks', '02_mapas.ipynb'))
