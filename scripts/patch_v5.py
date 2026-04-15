import json
import re

RENAMES = {
    # 01_redes_basico
    "01_grilla_redes_periodos": "evo_panel2x2_redes_por_periodo",
    "02_mapa_geopandas_red": "gen_mapa_redsudeste_global",
    "03_matriz_roles": "gen_heatmap_roles_global",
    "04_evolucion_asimetria": "evo_lineas_asimetria_por_periodo",
    "05_roles_red_intrapredio": "gen_burbujas_roles_red_global",
    "06_mortalidad_saltos": "des_barras_mortalidad_n_saltos",
    "07_mortalidad_trayectoria": "des_barras_mortalidad_tipo_trayectoria",
    "08_evolucion_mortalidad_lineas": "evo_lineas_mortalidad_tipo_trayectoria_por_periodo",
    "09_pingpong_mortalidad": "des_barras_mortalidad_pingpong_global",

    # 02_mapas
    "mapa_adicional": "gen_mapa_barrios_populares_global",
    "01_mapa_buenos_aires": "gen_mapa_buenos_aires_global",
    "02_mapa_red_sudeste_opt1": "gen_mapa_redsudeste_opt1_global",
    "02_mapa_red_sudeste_opt2": "gen_mapa_redsudeste_opt2_global",

    # 03_ranking_trayectorias
    "01_heatmaps_matrices": "gen_heatmap_transicion_global",
    "02_top10_trayectorias_con_traslados": "gen_barras_top10_trayectorias_global",
    "03_top10_trayectorias_global": "gen_barras_top10_trayectorias_total",
    "04_top10_saltos_individuales": "gen_barras_top10_saltos1paso_global",
    "05_top10_saltos_apilados": "des_barras100_saltos2pasos_global",

    # 04_trayectorias_especificas
    "01_desenlaces_por_trayectoria": "des_barras100_desenlaces_top10trayectorias",
    "02_evolucion_desenlaces_nivel0": "evo_lineas_desenlaces_nivel0_por_periodo",
    "03_boxplot_tiempos_traslado": "tmp_boxplot_tiempos_traslado_2pasos"
}

def patch_cell_source(src):
    # 1. Renombrar strings de archivos
    for old, new in RENAMES.items():
        src = src.replace(f"'{old}'", f"'{new}'")
        src = src.replace(f'"{old}"', f'"{new}"')
    
    # 2. Renombrar prefijos en f-strings de evolucion
    src = src.replace("nombre_archivo=f'06_evolucion", "nombre_archivo=f'evo_panel2x2_barras")
    src = src.replace("nombre_archivo=f'07_evolucion", "nombre_archivo=f'evo_panel2x2_barras_toptrayectorias")
    src = src.replace("nombre_archivo=f'08_evolucion", "nombre_archivo=f'evo_panel2x2_dinamico")

    # 3. Logica de colores en notebooks
    if "crosstab_desenlaces.plot(kind='barh', stacked=True, colormap='Set2'" in src:
        old_block = """# Ordenamos por la tasa de mortalidad o alta para darle sentido de lectura
if 'muerte' in crosstab_desenlaces.columns:
    crosstab_desenlaces = crosstab_desenlaces.sort_values('muerte', ascending=False)

# Gráfico
plt.figure(figsize=(12, 6))
crosstab_desenlaces.plot(kind='barh', stacked=True, colormap='Set2', ax=plt.gca())"""
        new_block = """# 1. Estandarizamos texto de columnas para la paleta
crosstab_desenlaces.columns = crosstab_desenlaces.columns.astype(str).str.lower().str.strip()

# 2. Orden estricto de apilado
orden_apilado = ['alta', 'muerte', 'hospital externo', 'alta hotel', 'otro/desconocido']
cols_presentes = [c for c in orden_apilado if c in crosstab_desenlaces.columns]
cols_extra = [c for c in crosstab_desenlaces.columns if c not in orden_apilado]
crosstab_desenlaces = crosstab_desenlaces[cols_presentes + cols_extra]

# 3. Orden contextual para lectura (ordenamos el índice Y por mortalidad o alta)
if 'muerte' in crosstab_desenlaces.columns:
    crosstab_desenlaces = crosstab_desenlaces.sort_values('muerte', ascending=False)

# 4. Asignar colores estrictos
colores_barras = [COLORES_MOTIVOS.get(col, '#9E9E9E') for col in crosstab_desenlaces.columns]

# Grafico
plt.figure(figsize=(12, 6))
crosstab_desenlaces.plot(kind='barh', stacked=True, color=colores_barras, ax=plt.gca())"""
        src = src.replace(old_block, new_block)
        
    # Parchear iteradores directos usando COLORES_MOTIVOS
    
    # pivot_100 (03_ranking_trayectorias)
    if "colores_barras = [COLORES_MOTIVOS.get(col, '#333333') for col in pivot_100.columns]" in src:
        src = re.sub(
            r"colores_barras = \[COLORES_MOTIVOS\.get\(col, '#333333'\) for col in pivot_100\.columns\]",
            r"""pivot_100.columns = pivot_100.columns.astype(str).str.lower().str.strip()
    _ord = ['alta', 'muerte', 'hospital externo', 'alta hotel', 'otro/desconocido']
    _pres = [c for c in _ord if c in pivot_100.columns]
    _ext = [c for c in pivot_100.columns if c not in _ord]
    pivot_100 = pivot_100[_pres + _ext]
    colores_barras = [COLORES_MOTIVOS.get(col, '#9E9E9E') for col in pivot_100.columns]""",
            src
        )
    
    # pivot (03_ranking_trayectorias)
    if "colores = [COLORES_MOTIVOS.get(c, '#333333') for c in pivot.columns]" in src:
        src = re.sub(
            r"colores = \[COLORES_MOTIVOS\.get\(c, '#333333'\) for c in pivot\.columns\]",
            r"""pivot.columns = pivot.columns.astype(str).str.lower().str.strip()
        _ord = ['alta', 'muerte', 'hospital externo', 'alta hotel', 'otro/desconocido']
        _pres = [c for c in _ord if c in pivot.columns]
        _ext = [c for c in pivot.columns if c not in _ord]
        pivot = pivot[_pres + _ext]
        colores = [COLORES_MOTIVOS.get(c, '#9E9E9E') for c in pivot.columns]""",
            src
        )
        
    return src

notebooks = [
    "JAIIO_notebooks/01_redes_basico.ipynb",
    "JAIIO_notebooks/02_mapas.ipynb",
    "JAIIO_notebooks/03_ranking_trayectorias.ipynb",
    "JAIIO_notebooks/04_trayectorias_especificas.ipynb"
]

for nb_path in notebooks:
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    
    changed = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            new_src = patch_cell_source(src)
            if new_src != src:
                # We need to maintain the list of lines with newlines style
                lines = new_src.splitlines(True)
                if len(lines) > 0 and lines[-1].endswith("\n"):
                    lines[-1] = lines[-1][:-1] # remove trailing newline
                cell["source"] = lines
                changed = True
                
    if changed:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
            f.write('\n')
        print(f"[OK] Patched correctly: {nb_path}")
