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
sys.path.append("../scripts")  # carpeta donde está bases.py
import bases

# Cargar y limpiar datos centralizadamente vía bases.py
df_pacientes = bases.cargar_datos_pacientes("../data/pacientes.xlsx")
print("Cantidad de registros de pacientes válidos:", len(df_pacientes))

hosp_coord = bases.cargar_coordenadas("../data/hospitales_coordenadas.csv")
print("Cantidad de hospitales coordenadas válidos:", len(hosp_coord))

# Valores nulos
print(df_pacientes.isna().sum())

# reconstruir traslados usando la función de BASES
df_traslados = bases.reconstruir_traslados(df_pacientes)

# ver los primeros registros
# df_traslados.head()

# generar red para todo el período
G, edges = bases.generar_red(df_traslados, fecha_inicio="2020-06-01", fecha_fin="2020-10-31")

# ahora G es el grafo de networkx
fig, ax = bases.plot_red_con_mapa(G, hosp_coord)
plt.show()

# generar red para todo el período
G, edges = bases.generar_red(df_traslados, fecha_inicio="2020-06-01", fecha_fin="2020-10-31")

# ahora G es el grafo de networkx
fig, ax = bases.plot_red_con_mapa(G, hosp_coord)
plt.show()

gdf_hosp = gpd.GeoDataFrame(
    hosp_coord, # Usando hosp_coord que ya fue limpiada mediante bases.py
    geometry=gpd.points_from_xy(
        hosp_coord["Longitud"],
        hosp_coord["Latitud"]
    ),
    crs="EPSG:4326"
)

fig, ax = plt.subplots(figsize=(8,8))

gdf_hosp.to_crs(epsg=3857).plot(
    ax=ax,
    color="red",
    markersize=60
)

ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

plt.title("Hospitales y UPAs en la Red Sudeste")
plt.axis("off")
plt.show()
municipios = bases.cargar_municipios("../data/shapefiles/departamento/departamentoPolygon.shp")

amba_partidos = [
    "CIUDAD AUTONOMA DE BUENOS AIRES", "QUILMES", "ALMIRANTE BROWN",
    "FLORENCIO VARELA", "BERAZATEGUI", "LANUS", "LOMAS DE ZAMORA",
    "AVELLANEDA", "ESCOBAR", "MORON", "MARTINEZ", "HURLINGHAM",
    "ITUZAINGO", "LA MATANZA", "TIGRE", "SAN ISIDRO", "VICENTE LOPEZ"
]

municipios_amba = municipios[municipios["nam_limpio"].isin(amba_partidos)]

fig, ax = plt.subplots(figsize=(10,10))

municipios_amba.to_crs(epsg=3857).plot(
    ax=ax,
    alpha=0.3,
    edgecolor="black"
)

gdf_hosp.to_crs(epsg=3857).plot(
    ax=ax,
    color="red",
    markersize=60
)

ctx.add_basemap(ax)

plt.title("Red Sudeste y hospitales (AMBA)")
plt.axis("off")
plt.show()
gdf_hosp_m = gdf_hosp.to_crs(epsg=3857)
n = len(gdf_hosp_m)

dist_matrix = pd.DataFrame(
    np.zeros((n,n)),
    index=gdf_hosp_m["Nombre Hospital"],
    columns=gdf_hosp_m["Nombre Hospital"]
)

for i, row_i in gdf_hosp_m.iterrows():
    
    for j, row_j in gdf_hosp_m.iterrows():
        
        dist = row_i.geometry.distance(row_j.geometry) / 1000
        
        dist_matrix.loc[
            row_i["Nombre Hospital"],
            row_j["Nombre Hospital"]
        ] = dist
dist_matrix.round(2).head()
plt.figure(figsize=(10,8))

sns.heatmap(
    dist_matrix,
    cmap="viridis"
)

plt.title("Distancia entre hospitales (km)")
plt.show()
dias = traslados["dias_entre_hospitales"]

plt.figure(figsize=(8,5))

dias.hist(bins=20)

plt.title("Distribución de días entre hospitales")
plt.xlabel("Días")
plt.ylabel("Cantidad")

plt.show()
negativos = traslados[traslados["dias_entre_hospitales"] < 0]

print("Cantidad negativos:", len(negativos))
negativos[[
    "Id",
    "Nombre Hospital",
    "Hospital siguiente",
    "Fecha egreso",
    "Fecha ingreso siguiente",
    "dias_entre_hospitales"
]].head(10)
G_periodo, edges_periodo = bases.generar_red(
    traslados,
    "2020-06-01",
    "2020-10-31"
)
print("Nodos:", G_periodo.number_of_nodes())
print("Aristas:", G_periodo.number_of_edges())

print("Densidad:", nx.density(G_periodo))
print("Componentes débiles:", nx.number_weakly_connected_components(G_periodo))
in_strength = dict(G_periodo.in_degree(weight="weight"))

sorted(
    in_strength.items(),
    key=lambda x: x[1],
    reverse=True
)[:5]
out_strength = dict(G_periodo.out_degree(weight="weight"))

sorted(
    out_strength.items(),
    key=lambda x: x[1],
    reverse=True
)[:5]
bet = nx.betweenness_centrality(G_periodo, weight="weight")

sorted(
    bet.items(),
    key=lambda x: x[1],
    reverse=True
)[:5]
fig, ax = bases.plot_red_con_mapa(G_periodo, hosp_coords)

m = bases.plot_red_interactiva(G_periodo, hosp_coords)

m
traslados = bases.reconstruir_traslados(df_pacientes)

print("Traslados confirmados:", len(traslados))
# total de admisiones
total_admisiones = len(df_pacientes)

# total de traslados detectados
total_traslados = len(traslados)

porcentaje_traslados = total_traslados / total_admisiones * 100

print("Total admisiones:", total_admisiones)
print("Total traslados:", total_traslados)
print("Porcentaje de admisiones que terminan en traslado:", round(porcentaje_traslados,2), "%")
# admisiones por semana
adm_semana = (
    df_pacientes
    .set_index("Fecha inicio")
    .resample("W")
    .size()
)

# traslados por semana
tras_semana = (
    traslados
    .set_index("Fecha egreso")
    .resample("W")
    .size()
)

plt.figure(figsize=(10,5))

plt.plot(adm_semana.index, adm_semana.values, label="Admisiones")
plt.plot(tras_semana.index, tras_semana.values, label="Traslados")

plt.title("Admisiones vs Traslados en el tiempo")
plt.xlabel("Fecha")
plt.ylabel("Cantidad de pacientes")

plt.legend()
plt.grid(alpha=0.3)

plt.show()
traslados_por_persona = traslados.groupby("Id").size()

print("Pacientes con al menos un traslado:", len(traslados_por_persona))
print("Media:", traslados_por_persona.mean())
print("Desvío estándar:", traslados_por_persona.std())
print("Mediana:", traslados_por_persona.median())
print("Máximo:", traslados_por_persona.max())
plt.figure(figsize=(8,5))

traslados_por_persona.hist(bins=15)

plt.title("Distribución de traslados por paciente")
plt.xlabel("Cantidad de traslados")
plt.ylabel("Número de pacientes")

plt.grid(alpha=0.3)
plt.show()
plt.figure(figsize=(6,4))

plt.boxplot(traslados_por_persona)

plt.title("Boxplot traslados por paciente")
plt.ylabel("Cantidad de traslados")

plt.show()
tiempo_sistema = df_pacientes.groupby("Id").agg(
    ingreso_inicial=("Fecha inicio", "min"),
    egreso_final=("Fecha egreso", "max")
)

tiempo_sistema["dias_sistema"] = (
    tiempo_sistema["egreso_final"] -
    tiempo_sistema["ingreso_inicial"]
).dt.days
plt.figure(figsize=(8,5))

tiempo_sistema["dias_sistema"].hist(bins=30)

plt.title("Tiempo total en el sistema hospitalario")
plt.xlabel("Días")
plt.ylabel("Cantidad de pacientes")

plt.grid(alpha=0.3)
plt.show()
print(df_pacientes["Estado al ingreso"].value_counts())
print(df_pacientes["Nivel de riesgo"].value_counts())
tabla_riesgo_estado = pd.crosstab(
    df_pacientes["Nivel de riesgo"],
    df_pacientes["Estado al ingreso"]
)

print(tabla_riesgo_estado)
tabla_riesgo_estado.plot(
    kind="bar",
    figsize=(8,5)
)

plt.title("Nivel de riesgo vs estado clínico al ingreso")
plt.xlabel("Nivel de riesgo")
plt.ylabel("Cantidad de pacientes")

plt.xticks(rotation=0)
plt.legend(title="Estado clínico")

plt.show()
df_pacientes["murio"] = df_pacientes["Motivo"].str.contains("falle", case=False, na=False)
mortalidad_riesgo = df_pacientes.groupby("Nivel de riesgo")["murio"].mean()

print(mortalidad_riesgo)
mortalidad_riesgo.plot(kind="bar", figsize=(6,4))

plt.title("Tasa de mortalidad por nivel de riesgo")
plt.ylabel("Probabilidad de muerte")

plt.xticks(rotation=0)
plt.show()
traslados_out = traslados.groupby("Nombre Hospital").size()
traslados_in = traslados.groupby("Hospital siguiente").size()
estadia_promedio = df_pacientes.groupby("Nombre Hospital")["Duracion días"].mean()
mortalidad_hospital = df_pacientes.groupby("Nombre Hospital")["murio"].mean()
pacientes_por_hospital = df_pacientes.groupby("Nombre Hospital")["Id"].nunique()
tabla_hospitales = pd.DataFrame({
    "traslados_out": traslados_out,
    "traslados_in": traslados_in,
    "estadia_promedio_dias": estadia_promedio,
    "tasa_mortalidad": mortalidad_hospital,
    "pacientes_distintos": pacientes_por_hospital
}).fillna(0)

tabla_hospitales = tabla_hospitales.sort_values(
    "traslados_in",
    ascending=False
)

tabla_hospitales.head(10)
tabla_hospitales["traslados_in"].sort_values(ascending=False).head(10).plot(
    kind="bar",
    figsize=(8,5)
)

plt.title("Hospitales que más reciben traslados")
plt.ylabel("Cantidad de pacientes")

plt.show()