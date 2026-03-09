import nbformat as nbf
import os

# Refactorizar 01_EDA.ipynb
path_01 = '../notebooks/01_EDA.ipynb'
if os.path.exists(path_01):
    with open(path_01, 'r', encoding='utf-8') as f:
        nb01 = nbf.read(f, as_version=4)
        
    code_01_setup = """\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import geopandas as gpd
import folium
from scipy import stats
from shapely.geometry import LineString
import contextily as ctx

import sys
sys.path.append("../scripts")
import bases

# Carga y limpieza estandarizada de datos
df_pacientes = bases.cargar_datos_pacientes("../data/pacientes.xlsx")
print("Cantidad de pacientes válidos:", len(df_pacientes))

hosp_coord = bases.cargar_coordenadas("../data/hospitales_coordenadas.csv")
print("Cantidad de hospitales coordenadas:", len(hosp_coord))

# Reconstruir traslados
df_traslados = bases.reconstruir_traslados(df_pacientes)
"""
    # Find the setup cell and replace it. Let's assume it's the first code cell.
    for cell in nb01.cells:
        if cell.cell_type == 'code':
            if 'df_pacientes = pd.read_excel("..\data\pacientes.xlsx")' in cell.source or 'date_cols' in cell.source:
                cell.source = code_01_setup
                break

    with open(path_01, 'w', encoding='utf-8') as f:
        nbf.write(nb01, f)
    print("01_EDA.ipynb refactorizado.")


# Refactorizar 02_EDA_agregadas.ipynb
path_02 = '../notebooks/02_EDA_agregadas.ipynb'
if os.path.exists(path_02):
    with open(path_02, 'r', encoding='utf-8') as f:
        nb02 = nbf.read(f, as_version=4)
        
    code_02_setup = """\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import sys
sys.path.append("../scripts")
import bases

try:
    import contextily as ctx
    HAS_CTX = True
except ImportError:
    HAS_CTX = False

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)

# Cargar y limpiar datos centralizadamente vía bases.py
df_pacientes = bases.cargar_datos_pacientes("../data/pacientes.xlsx")
hosp_coords = bases.cargar_coordenadas("../data/hospitales_coordenadas.csv")

# Reconstruir traslados
df_traslados = bases.reconstruir_traslados(df_pacientes)
print(f"Total pacientes limpios: {len(df_pacientes)}")
print(f"Total traslados reconstruidos: {len(df_traslados)}")
"""
    # Replace the setup cell (the second cell, index 1 usually)
    for i, cell in enumerate(nb02.cells):
        if cell.cell_type == 'code' and "df_pacientes['murio'] = df_pacientes['Motivo']" in cell.source:
            nb02.cells[i].source = code_02_setup
            break

    # We also need to fix code_mapa cell in 02_EDA as well
    # because previously coordinates were cleaned in map cell there
    code_02_mapa = """\
# Geopandas directamente desde coordenadas procesadas
gdf_hosp = gpd.GeoDataFrame(
    hosp_coords,
    geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
    crs="EPSG:4326"
)

fig, ax = plt.subplots(figsize=(10, 10))
gdf_hosp_m = gdf_hosp.to_crs(epsg=3857)
gdf_hosp_m.plot(ax=ax, color="red", markersize=100, edgecolor="black", label="Hospitales")

if HAS_CTX:
    try:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    except:
        pass

for x, y, label in zip(gdf_hosp_m.geometry.x, gdf_hosp_m.geometry.y, gdf_hosp_m["Nombre Hospital"]):
    ax.text(x, y, label, fontsize=8, ha="right", va="bottom", bbox=dict(facecolor="white", alpha=0.5, edgecolor="none"))

plt.title("Mapa de la Red Sudeste de Hospitales", fontsize=14)
plt.axis("off")
plt.legend()
plt.show()
"""
    for i, cell in enumerate(nb02.cells):
        if cell.cell_type == 'code' and 'hosp_coords["Latitud"].astype(str).str.replace' in cell.source:
            nb02.cells[i].source = code_02_mapa
            break

    with open(path_02, 'w', encoding='utf-8') as f:
        nbf.write(nb02, f)
    print("02_EDA_agregadas.ipynb refactorizado.")

