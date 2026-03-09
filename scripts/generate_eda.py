import nbformat as nbf

nb = nbf.v4.new_notebook()

text = """\
# Análisis Exploratorio de Datos (EDA) - Medidas Agregadas
Este notebook contiene el análisis exploratorio agregado para comprender el funcionamiento general de la Red de Hospitales, de acuerdo a lo solicitado.
"""

code_setup = """\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import sys
sys.path.append("../scripts")
import bases

# Importación opcional de contextily para mapas base
try:
    import contextily as ctx
    HAS_CTX = True
except ImportError:
    HAS_CTX = False

# Configuración visual
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)

# Carga de datos
df_pacientes = pd.read_excel("../data/pacientes.xlsx")
hosp_coords = pd.read_csv("../data/hospitales_coordenadas.csv")

# Funciones de limpieza basadas en el código existente
df_pacientes = df_pacientes[df_pacientes["Id"].astype(str).str.match(r"[A-Za-z0-9]+")]
df_pacientes["Nombre Hospital"] = df_pacientes["Nombre Hospital"].str.strip().str.upper()
date_cols = ["Fecha inicio", "Fecha egreso", "Última actualización"]
for c in date_cols:
    df_pacientes[c] = pd.to_datetime(df_pacientes[c], errors="coerce")
df_pacientes["Duracion días"] = (df_pacientes["Fecha egreso"] - df_pacientes["Fecha inicio"]).dt.days

# Agregamos feature de fallecimiento
df_pacientes["murio"] = df_pacientes["Motivo"].astype(str).str.contains("fallec|muert", case=False, na=False)

# Reconstruir traslados
df_traslados = bases.reconstruir_traslados(df_pacientes)
print(f"Total registros limpios pacientes: {len(df_pacientes)}")
print(f"Total traslados reconstruidos: {len(df_traslados)}")
"""

text_mapa = "## Mapa con los hospitales y municipios alrededor\nUtilizando geopandas y las coordenadas provistas."

code_mapa = """\
# Limpiar y preparar coordenadas
hosp_coords["Latitud"] = hosp_coords["Latitud"].astype(str).str.replace(",", ".").astype(float)
hosp_coords["Longitud"] = hosp_coords["Longitud"].astype(str).str.replace(",", ".").astype(float)
hosp_coords["Nombre Hospital"] = hosp_coords["Nombre Hospital"].str.strip()

gdf_hosp = gpd.GeoDataFrame(
    hosp_coords,
    geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
    crs="EPSG:4326"
)

fig, ax = plt.subplots(figsize=(10, 10))

# Se proyecta al sistema pseudo-mercator exigido por contextily
gdf_hosp_m = gdf_hosp.to_crs(epsg=3857)
gdf_hosp_m.plot(ax=ax, color="red", markersize=100, edgecolor="black", label="Hospitales")

# Agregar basemap (municipios / entorno geográfico general)
if HAS_CTX:
    try:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    except:
        pass

# Anotaciones
for x, y, label in zip(gdf_hosp_m.geometry.x, gdf_hosp_m.geometry.y, gdf_hosp_m["Nombre Hospital"]):
    ax.text(x, y, label, fontsize=8, ha="right", va="bottom", bbox=dict(facecolor="white", alpha=0.5, edgecolor="none"))

plt.title("Mapa de la Red Sudeste de Hospitales", fontsize=14)
plt.axis("off")
plt.legend()
plt.show()
"""

text_tot_traslados = "## Total de traslados\nTotal histórico."

code_tot_traslados = """\
total_traslados = len(df_traslados)
print(f"El total de traslados procesados en la red fue: {total_traslados}")
"""

text_tiempo = "## Cantidad de traslados en función del tiempo"

code_tiempo = """\
# Agrupamos los traslados por mes/año utilizando la fecha del egreso (que genera el traslado)
traslados_tiempo = (
    df_traslados
    .set_index("Fecha egreso")
    .resample("M")
    .size()
)

plt.figure(figsize=(12, 5))
plt.plot(traslados_tiempo.index, traslados_tiempo.values, marker="o", linestyle="-", color="purple")
plt.title("Cantidad de traslados en función del tiempo (Mensual)", fontsize=14)
plt.xlabel("Fecha")
plt.ylabel("Cantidad de traslados")
plt.grid(True, alpha=0.4)
plt.tight_layout()
plt.show()
"""

text_persona_traslados = "## Cantidad de traslados para cada persona\nPromedio, desvío y distribución."

code_persona_traslados = """\
traslados_por_paciente = df_traslados.groupby("Id").size()

print("Métricas de traslados por paciente:")
print(f"  - Total de pacientes trasladados: {len(traslados_por_paciente)}")
print(f"  - Promedio de traslados: {traslados_por_paciente.mean():.2f}")
print(f"  - Desvío estándar: {traslados_por_paciente.std():.2f}")
print(f"  - Máximo de traslados de un paciente: {traslados_por_paciente.max()}")

plt.figure(figsize=(8, 4))
sns.histplot(traslados_por_paciente, bins=range(1, 10), discrete=True, color="teal")
plt.title("Distribución de traslados por persona")
plt.xlabel("Cantidad de traslados")
plt.ylabel("Frecuencia (personas)")
plt.xticks(range(1, 10))
plt.show()
"""

text_tiempo_sistema = "## Tiempo dentro del sistema por persona"

code_tiempo_sistema = """\
# Consideramos el tiempo total que estuvo una persona en el sistema (de su primera fecha inicio a su última fecha egreso)
tiempo_sistema = df_pacientes.groupby("Id").agg(
    ingreso_inicial=("Fecha inicio", "min"),
    egreso_final=("Fecha egreso", "max")
)
tiempo_sistema["dias_en_sistema"] = (tiempo_sistema["egreso_final"] - tiempo_sistema["ingreso_inicial"]).dt.days

# Filtramos outliers o datos erróneos (días negativos)
tiempo_sistema = tiempo_sistema[tiempo_sistema["dias_en_sistema"] >= 0]

print(f"Promedio de tiempo en el sistema por persona: {tiempo_sistema['dias_en_sistema'].mean():.2f} días")
print(f"Desvío estándar de tiempo en el sistema: {tiempo_sistema['dias_en_sistema'].std():.2f} días")

plt.figure(figsize=(10, 5))
sns.histplot(tiempo_sistema["dias_en_sistema"], bins=50, color="darkorange", kde=True)
plt.title("Distribución del tiempo dentro del sistema por persona")
plt.xlabel("Días en el sistema")
plt.ylabel("Pacientes")
plt.xlim(0, 100) # recorta un poco la cola para mejor visibilidad
plt.show()
"""

text_hospital = "## Descriptivos por hospital\nTraslados (ingresos/egresos), tiempo promedio y muertes por hospital."

code_hospital = """\
# Traslados generados (origen del traslado)
traslados_out = df_traslados.groupby("Nombre Hospital").size()
# Traslados recibidos (destino del traslado)  
traslados_in = df_traslados.groupby("Hospital siguiente").size()

# Estancia promedio por evento
estadia_promedio = df_pacientes.groupby("Nombre Hospital")["Duracion días"].mean()

# Cantidad de muertos
muertes = df_pacientes.groupby("Nombre Hospital")["murio"].sum()

# Consolidamos
desc_hospitales = pd.DataFrame({
    "Traslados (Egresados)": traslados_out,
    "Traslados (Recibidos)": traslados_in,
    "Tiempo Promedio (Días)": estadia_promedio,
    "Muertes Totales": muertes
}).fillna(0)

desc_hospitales = desc_hospitales.round(2).sort_values(by="Traslados (Egresados)", ascending=False)
display(desc_hospitales)
"""

text_riesgo = "## Cantidad de personas con distintos niveles de riesgo social y estados (crítico, intermedio, general)"

code_riesgo = """\
# Verificamos los campos disponibles en df_pacientes. Si los nombres varían ajustamos.
# Intentaremos encontrar los equivalentes a Riesgo Social y Estado al ingreso
cols = [c for c in df_pacientes.columns if 'riesgo social' in c.lower() or 'riesgo_social' in c.lower()]
col_riesgo_social = cols[0] if cols else "Nivel de riesgo"

cols_estado = [c for c in df_pacientes.columns if 'estado al ingreso' in c.lower() or 'tipo al ingreso' in c.lower()]
col_estado = cols_estado[0] if cols_estado else "Estado al ingreso"

if col_riesgo_social in df_pacientes.columns and col_estado in df_pacientes.columns:
    # Agrupamos por Id para no duplicar pacientes (tomamos su último registro)
    df_unicos = df_pacientes.sort_values("Fecha inicio").drop_duplicates("Id", keep="last")
    
    tabla_riesgo_estado = pd.crosstab(
        df_unicos[col_riesgo_social],
        df_unicos[col_estado]
    )
    display(tabla_riesgo_estado)
    
    tabla_riesgo_estado.plot(kind="bar", figsize=(8, 6), colormap="Set2")
    plt.title("Personas por Nivel de Riesgo y Estado Clínico", fontsize=14)
    plt.xlabel(col_riesgo_social)
    plt.ylabel("Cantidad de pacientes")
    plt.xticks(rotation=0)
    plt.legend(title=col_estado)
    plt.show()
else:
    print(f"Columnas no encontradas con precisión. Estructura disponible: {df_pacientes.columns.tolist()}")
"""

nb['cells'] = [
    nbf.v4.new_markdown_cell(text),
    nbf.v4.new_code_cell(code_setup),
    nbf.v4.new_markdown_cell(text_mapa),
    nbf.v4.new_code_cell(code_mapa),
    nbf.v4.new_markdown_cell(text_tot_traslados),
    nbf.v4.new_code_cell(code_tot_traslados),
    nbf.v4.new_markdown_cell(text_tiempo),
    nbf.v4.new_code_cell(code_tiempo),
    nbf.v4.new_markdown_cell(text_persona_traslados),
    nbf.v4.new_code_cell(code_persona_traslados),
    nbf.v4.new_markdown_cell(text_tiempo_sistema),
    nbf.v4.new_code_cell(code_tiempo_sistema),
    nbf.v4.new_markdown_cell(text_hospital),
    nbf.v4.new_code_cell(code_hospital),
    nbf.v4.new_markdown_cell(text_riesgo),
    nbf.v4.new_code_cell(code_riesgo)
]

with open('../notebooks/02_EDA_agregadas.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook 02_EDA_agregadas.ipynb generado exitosamente en notebooks/")
