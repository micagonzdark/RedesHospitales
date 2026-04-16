import nbformat
import os

path = r'C:\Users\micag\Documents\RedesHospitales\JAIIO_notebooks\01_redes_basico.ipynb'
with open(path, 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

for cell in nb.cells:
    if cell.cell_type == 'code' and "df_base = df_base.rename(columns={" in cell.source:
        # Update Cell 7 with ID mapping
        source = cell.source
        if "mapear_ids_hospitales" not in source:
            # Find the end of rename or a good place to insert
            insertion_point = "df_base['hospital_origen'] = df_base['hospital_origen'].str.strip()"
            mapping_code = """
# --- NUEVO: Mapeo de IDs únicos de Hospital ---
df_base['Nombre Hospital'] = df_base['hospital_origen'] 
df_base = mapear_ids_hospitales(df_base, hospitales)
"""
            source = source.replace(insertion_point, insertion_point + mapping_code)
            
            # Update shifts to use IDs
            source = source.replace("df_base['hospital_destino'] = df_base.groupby('paciente_id')['hospital_origen'].shift(-1)", 
                                    "df_base['id_hospital_destino'] = df_base.groupby('paciente_id')['id_hospital'].shift(-1)\n    df_base['hospital_destino'] = df_base.groupby('paciente_id')['hospital_origen'].shift(-1)")
            
            cell.source = source
            print("Updated Cell 7 in 01_redes_basico.ipynb")

    # Update later cells that filter traslados
    if cell.cell_type == 'code' and "mask_validos = (df_base['hospital_origen'] != df_base['hospital_destino'])" in cell.source:
        cell.source = cell.source.replace("mask_validos = (df_base['hospital_origen'] != df_base['hospital_destino'])", 
                                          "mask_validos = (df_base['id_hospital'] != df_base['id_hospital_destino'])")
        print("Updated filtering in 01_redes_basico.ipynb")

with open(path, 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)
