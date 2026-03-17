## bases.py

# ---------------------------------------------------------
# librerías necesarias
import pandas as pd
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
import folium
import numpy as np
from shapely.geometry import LineString
import contextily as ctx
import unicodedata
import re
import seaborn as sns
from matplotlib.patches import Patch
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones utilitarias
# ---------------------------------------------------------
def get_linewidth(weight):
    """Calcula grosor de línea proporcional al peso"""
    return np.log1p(weight) * 1.5

def limpiar_nombre(texto):
    """Pasa el texto a mayúsculas, quita acentos y símbolos"""
    if texto is None:
        return ""
    texto = texto.upper()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    texto = re.sub(r'[^A-Z0-9\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def coords_a_dict(hosp_coords):
    """Convierte un dataframe de coordenadas en diccionario {hospital: (lat, lon)}"""
    return dict(zip(
        hosp_coords["Nombre Hospital"],
        zip(hosp_coords["Latitud"], hosp_coords["Longitud"])
    ))

def draw_arrow(ax, line, lw=1, color="blue"):
    """Dibuja flecha sobre LineString en matplotlib"""
    x, y = line.xy
    ax.annotate(
        "",
        xy=(x[-1], y[-1]),
        xytext=(x[-2], y[-2]),
        arrowprops=dict(arrowstyle="->", color=color, lw=lw)
    )

def revisar_dias_negativos(df, max_pacientes=5):
    """
    Muestra los pacientes con dias_entre_hospitales negativos.
    Solo muestra los primeros `max_pacientes`, pero con todo su historial.
    """
    # filas con error
    errores = df[df["dias_entre_hospitales"] < 0]

    print("Cantidad de filas con dias negativos:", len(errores))

    # ids únicos de pacientes con error
    ids_problema = errores["Id"].unique()
    print("Pacientes afectados:", len(ids_problema))

    # limitar a los primeros max_pacientes
    ids_mostrar = ids_problema[:max_pacientes]

    for pid in ids_mostrar:
        print("\n" + "="*70)
        print("Paciente:", pid)

        # historial completo del paciente
        historial = df[df["Id"] == pid].sort_values("Fecha inicio")

        # filas con error
        print("\nFilas con dias negativos:")
        display(historial[historial["dias_entre_hospitales"] < 0][[
            "Nombre Hospital",
            "Fecha inicio",
            "Hospital siguiente",
            "Fecha ingreso siguiente",
            "dias_entre_hospitales"
        ]])

        # historial completo
        print("\nHistorial completo del paciente:")
        display(historial[[
            "Nombre Hospital",
            "Fecha inicio",
            "Fecha egreso",
            "Hospital siguiente",
            "Fecha ingreso siguiente",
            "dias_entre_hospitales"
        ]])
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de limpieza y carga de datos
# ---------------------------------------------------------
def limpiar_pacientes(df):
    df_clean = df[df["Id"].astype(str).str.match(r"[A-Za-z0-9]+")].copy()
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].apply(limpiar_nombre)
    date_cols = ["Fecha inicio", "Fecha egreso", "Última actualización"]
    for c in date_cols:
        if c in df_clean.columns:
            df_clean[c] = pd.to_datetime(df_clean[c], errors="coerce")
    if "Fecha inicio" in df_clean.columns and "Fecha egreso" in df_clean.columns:
        df_clean["Duracion días"] = (df_clean["Fecha egreso"] - df_clean["Fecha inicio"]).dt.days
    if "Motivo" in df_clean.columns:
        df_clean["murio"] = df_clean["Motivo"].astype(str).str.contains("fallec|muert", case=False, na=False)
    return df_clean

def cargar_datos_pacientes(path):
    return limpiar_pacientes(pd.read_excel(path))

def limpiar_coordenadas(hosp_coords):
    df_clean = hosp_coords.copy()
    if "Latitud" in df_clean.columns:
        df_clean["Latitud"] = df_clean["Latitud"].astype(str).str.replace(",", ".").astype(float)
    if "Longitud" in df_clean.columns:
        df_clean["Longitud"] = df_clean["Longitud"].astype(str).str.replace(",", ".").astype(float)
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].apply(limpiar_nombre)
    return df_clean

def cargar_coordenadas(path):
    return limpiar_coordenadas(pd.read_csv(path))

def cargar_municipios(path_shp):
    municipios = gpd.read_file(path_shp)
    municipios["nam_limpio"] = municipios["nam"].apply(limpiar_nombre)
    return municipios

def cargar_provincias(path_shp):
    return gpd.read_file(path_shp)

def es_upa(nombre):
    """True si es UPA (el nombre comienza con 'UPA')"""
    return nombre.upper().startswith("UPA")

def ajustar_coordenadas_upa(coords_df):
    """Desplaza levemente UPA para evitar superposición en mapas"""
    coords_mod = coords_df.copy()
    mask_upa = coords_mod["Nombre Hospital"].str.upper().str.contains("UPA")
    coords_mod.loc[mask_upa, "Longitud"] -= 0.01
    return coords_mod
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de reconstrucción de traslados
# ---------------------------------------------------------
def reconstruir_traslados_mejor(df, max_horas_interno=24):
    """
    Reconstruye traslados y marca posibles errores.
    - max_horas_interno: diferencia máxima (en horas) que puede considerarse como traslado interno casi simultáneo
    """
    df = df.sort_values(["Id", "Fecha inicio"]).copy()
    
    # Hospital y fecha siguiente
    df["Hospital siguiente"] = df.groupby("Id")["Nombre Hospital"].shift(-1)
    df["Fecha ingreso siguiente"] = df.groupby("Id")["Fecha inicio"].shift(-1)
    
    # dias entre hospitales
    df["dias_entre_hospitales"] = (df["Fecha ingreso siguiente"] - df["Fecha egreso"]).dt.days
    
    # traslados
    df["es_traslado"] = df["Motivo"].str.contains("traslad", case=False, na=False)
    
    # filtrar traslados válidos
    traslados = df[
        (df["es_traslado"]) &
        (df["Hospital siguiente"].notna()) &
        (df["Hospital siguiente"] != df["Nombre Hospital"])
    ].copy()
    
    # marcar errores de fechas negativas
    traslados["error_fecha"] = traslados["dias_entre_hospitales"] < 0
    
    # marcar posibles internos o traslados casi simultáneos
    delta_horas = (traslados["Fecha ingreso siguiente"] - traslados["Fecha egreso"]).dt.total_seconds() / 3600
    traslados["posible_interno"] = (traslados["error_fecha"]) & (delta_horas.abs() <= max_horas_interno)
    
    return traslados
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de análisis individual del paciente
# ---------------------------------------------------------
def historial_paciente(df, paciente_id):
    df_p = df[df["Id"] == paciente_id].sort_values("Fecha inicio")
    return df_p[[
        "Nombre Hospital","Fecha inicio","Fecha egreso",
        "Estado al ingreso","Tipo al ingreso","Motivo","Duracion días"
    ]]

def historia_clinica(df, paciente_id):
    df_p = df[df["Id"] == paciente_id].sort_values("Fecha inicio")
    historia = {
        "paciente_id": paciente_id,
        "cantidad_internaciones": len(df_p),
        "hospitales_distintos": df_p["Nombre Hospital"].nunique(),
        "total_dias_internacion": df_p["Duracion días"].sum(),
        "eventos": []
    }
    for _, row in df_p.iterrows():
        historia["eventos"].append({
            "hospital": row["Nombre Hospital"],
            "fecha_inicio": row["Fecha inicio"],
            "fecha_egreso": row["Fecha egreso"],
            "estado_ingreso": row["Estado al ingreso"],
            "tipo_ingreso": row["Tipo al ingreso"],
            "motivo": row["Motivo"],
            "duracion_dias": row["Duracion días"]
        })
    return historia
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de analisis hospitalario / EDA
# ---------------------------------------------------------
def traslados_por_hospital(df, col_hospital="Nombre Hospital", hospitales=None, graficar=True):
    """Devuelve serie con cantidad de traslados por hospital"""    
    data = df.copy()
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    resultado = data.groupby(col_hospital).size().sort_values(ascending=False)
    if graficar:
        plt.figure(figsize=(12,5))
        resultado.plot(kind="bar")
        plt.title("Cantidad de traslados por hospital")
        plt.ylabel("Cantidad de traslados")
        plt.show()
    return resultado

def tiempo_promedio_por_hospital(df, col_hospital="Nombre Hospital", col_dias="Duracion días", hospitales=None, quantile_outlier=0.99, graficar=True):
    data = df.copy()
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    data = data[data[col_dias] >= 0]
    limite = data[col_dias].quantile(quantile_outlier)
    data = data[data[col_dias] <= limite]
    resultado = data.groupby(col_hospital)[col_dias].mean().sort_values(ascending=False)
    if graficar:
        plt.figure(figsize=(12,5))
        resultado.plot(kind="bar", color="orange")
        plt.title("Tiempo promedio en hospital por paciente")
        plt.ylabel("Días promedio")
        plt.show()
    return resultado

def muertes_por_hospital(df, col_hospital="Nombre Hospital", col_muerte="murio", hospitales=None, graficar=True):
    data = df.copy()
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    resultado = data[data[col_muerte]].groupby(col_hospital).size().sort_values(ascending=False)
    if graficar:
        plt.figure(figsize=(12,5))
        resultado.plot(kind="bar", color="red")
        plt.title("Cantidad de fallecidos por hospital")
        plt.ylabel("Cantidad de fallecidos")
        plt.show()
    return resultado

def distribucion_edades_por_hospital(df, col_hospital="Nombre Hospital", col_edad="Edad", hospitales=None, bins=20, graficar=True):
    data = df.copy()
    
    # convertir edades a numeric, los que no se puedan convertir se vuelven NaN
    data[col_edad] = pd.to_numeric(data[col_edad], errors="coerce")
    
    # filtrar hospitales si se pasa lista
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    
    # eliminar filas donde Edad es NaN
    data = data.dropna(subset=[col_edad])
    
    # calcular describe
    descr = data.groupby(col_hospital)[col_edad].describe()
    
    # calcular media y ordenar
    mean_orden = data.groupby(col_hospital)[col_edad].mean().sort_values(ascending=False)
    
    # reordenar describe por media
    resultado = descr.loc[mean_orden.index]
    
    # graficar
    if graficar:
        plt.figure(figsize=(12,5))
        data[col_edad].hist(bins=bins, edgecolor="white")
        plt.title("Distribución de edades")
        plt.xlabel("Edad")
        plt.ylabel("Frecuencia")
        plt.show()
    
    return resultado

def relacion_tiempo_riesgo_estado(df, col_riesgo="Nivel riesgo social", col_estado="Estado al ingreso", col_dias="Duracion días", graficar=True):
    data = df.copy()
    data = data[data[col_dias] >= 0]
    tabla = pd.pivot_table(data, values=col_dias, index=col_riesgo, columns=col_estado, aggfunc="mean")
    if graficar:
        plt.figure(figsize=(8,6))
        sns.heatmap(tabla, annot=True, fmt=".1f", cmap="coolwarm")
        plt.title("Tiempo promedio de internación\nRiesgo social vs Estado")
        plt.ylabel("Nivel de riesgo")
        plt.xlabel("Estado al ingreso")
        plt.show()
    return tabla
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de resúmenes de traslados
# ---------------------------------------------------------
def resumen_traslados(df, col_hospital="Nombre Hospital", imprimir=True):
    total_traslados = len(df)
    hospitales_unicos = df[col_hospital].nunique()
    if imprimir:
        print(f"Total de traslados: {total_traslados}")
        print(f"Cantidad de hospitales únicos: {hospitales_unicos}")
    return {"total_traslados": total_traslados, "hospitales_unicos": hospitales_unicos}

def traslados_por_mes(df, col_fecha="Fecha egreso", graficar=True, figsize=(12,5), marker="o"):
    df = df.copy()
    df[col_fecha] = pd.to_datetime(df[col_fecha])
    serie = df.groupby(df[col_fecha].dt.to_period("M")).size()
    serie.index = serie.index.astype(str)
    if graficar:
        sns.set_style("whitegrid")
        plt.figure(figsize=figsize)
        sns.lineplot(x=serie.index, y=serie.values, marker=marker)
        plt.xticks(rotation=45)
        plt.title("Traslados por mes")
        plt.ylabel("Cantidad de traslados")
        plt.xlabel("Mes")
        plt.tight_layout()
        plt.show()
    return serie

def traslados_en_el_tiempo(df, col_fecha="Fecha egreso", freq="M", graficar=True, figsize=(12,5)):
    data = df.copy()
    data[col_fecha] = pd.to_datetime(data[col_fecha])
    serie = data.groupby(data[col_fecha].dt.to_period(freq)).size()
    serie.index = serie.index.astype(str)
    if graficar:
        plt.figure(figsize=figsize)
        plt.plot(serie.index, serie.values, marker="o")
        plt.xticks(rotation=45)
        plt.title("Cantidad de traslados en el tiempo")
        plt.xlabel("Periodo")
        plt.ylabel("Cantidad de traslados")
        plt.tight_layout()
        plt.show()
    return serie

def distribucion_traslados_paciente(df, col_id="Id", valores=[1,2,3], graficar=True, figsize=(8,5)):
    traslados_por_paciente = df.groupby(col_id).size()
    conteo = traslados_por_paciente.value_counts().sort_index()
    conteo = conteo.loc[conteo.index.isin(valores)]
    if graficar:
        sns.set_style("whitegrid")
        plt.figure(figsize=figsize)
        ax = sns.barplot(x=conteo.index, y=conteo.values)
        plt.title("Cantidad de pacientes por número de traslados")
        plt.xlabel("Número de traslados")
        plt.ylabel("Número de pacientes")
        for i, v in enumerate(conteo.values):
            ax.text(i, v, str(v), ha="center", va="bottom")
        plt.show()
    stats = {"promedio": traslados_por_paciente.mean(), "desvio": traslados_por_paciente.std()}
    print("Promedio de traslados por paciente:", stats["promedio"])
    print("Desvío estándar:", stats["desvio"])
    return conteo, stats

def tiempo_total_paciente(df, col_id="Id", col_dias="Duracion días", max_dias=50, quantile_outlier=0.99, graficar=True, figsize=(10,5)):
    tiempo_sistema = df.groupby(col_id)[col_dias].sum()
    tiempo_sistema = tiempo_sistema[tiempo_sistema.between(0, max_dias)]
    limite = min(tiempo_sistema.quantile(quantile_outlier), max_dias)
    if graficar:
        conteo = tiempo_sistema.value_counts().sort_index()
        conteo = conteo[conteo.index <= limite]
        x, y = conteo.index, conteo.values
        plt.figure(figsize=figsize)
        bars = plt.bar(x, y)
        plt.axvline(limite, color="red", linestyle="--", label=f"percentil {int(quantile_outlier*100)}")
        for xi, yi in zip(x, y):
            plt.text(xi, yi, str(int(yi)), ha="center", va="bottom", fontsize=8)
        plt.title("Tiempo total dentro del sistema por paciente")
        plt.xlabel("Días totales")
        plt.ylabel("Número de pacientes")
        plt.legend()
        plt.show()
    return tiempo_sistema, limite


def pacientes_con_muchos_traslados(df, col_id="Id", minimo=3):
    traslados_por_paciente = df.groupby(col_id).size()
    ids = traslados_por_paciente[traslados_por_paciente >= minimo].index
    return df[df[col_id].isin(ids)]

def imprimir_recorridos_pacientes(df, col_id="Id",
                                  col_origen="Hospital Origen",
                                  col_destino="Hospital Destino",
                                  col_fecha=None):

    for paciente_id, grupo in df.groupby(col_id):

        if col_fecha is not None and col_fecha in df.columns:
            grupo = grupo.sort_values(col_fecha)

        print("\n" + "="*50)
        print(f"Paciente {paciente_id} - {len(grupo)} traslados")

        recorrido = [grupo.iloc[0][col_origen]]

        for _, row in grupo.iterrows():
            recorrido.append(row[col_destino])

        print(" -> ".join(recorrido))

def mostrar_recorridos_estado(df, col_id="Id"):
    columnas = [
        "Nombre Hospital", "Fecha inicio", "Estado al ingreso", 
        "Tipo al ingreso", "Último estado", "Último tipo",
        "Pasó por Críticas", "Pasó por Intermedias", "Pasó por Generales",
        "dias_entre_hospitales"
    ]
    for paciente_id, grupo in df.groupby(col_id):
        grupo = grupo.sort_values("Fecha inicio")
        print("\n" + "="*60)
        print(f"Paciente {paciente_id} - {len(grupo)} traslados")
        display(grupo[columnas])

def graficar_estado_paciente(df, col_id="Id"):

    tipo_map = {
        "criticas": 3,
        "intermedias": 2,
        "generales": 1
    }

    for paciente_id, grupo in df.groupby(col_id):

        grupo = grupo.sort_values("Fecha inicio")

        niveles = grupo["Tipo al ingreso"].map(tipo_map)

        if niveles.isna().all():
            continue

        hospitales = grupo["Nombre Hospital"]

        plt.figure(figsize=(8,3))

        plt.plot(
            range(1, len(niveles)+1),
            niveles,
            marker="o"
        )

        plt.xticks(
            range(1, len(niveles)+1),
            hospitales,
            rotation=45,
            ha="right"
        )

        plt.yticks(
            [1,2,3],
            ["Generales","Intermedias","Críticas"]
        )

        plt.title(f"Paciente {paciente_id}")
        plt.xlabel("Traslado")
        plt.ylabel("Nivel de cama")

        plt.tight_layout()
        plt.show()

from IPython.display import display

def graficar_estado_paciente_debug(df, col_id="Id"):

    tipo_map = {
        "criticas": 3,
        "intermedias": 2,
        "generales": 1
    }

    for paciente_id, grupo in df.groupby(col_id):

        grupo = grupo.sort_values("Fecha inicio")

        niveles = grupo["Tipo al ingreso"].map(tipo_map)

        if niveles.isna().all():
            continue

        hospitales = grupo["Nombre Hospital"]

        fig, ax = plt.subplots(figsize=(8,3))

        ax.plot(
            range(1, len(niveles)+1),
            niveles,
            marker="o"
        )

        ax.set_xticks(range(1,len(niveles)+1))
        ax.set_xticklabels(hospitales, rotation=45, ha="right")

        ax.set_yticks([2,3])
        ax.set_yticklabels(["Intermedias","Críticas"])

        ax.set_title(f"Paciente {paciente_id}")

        plt.tight_layout()

        display(fig)

import plotly.graph_objects as go
from IPython.display import display

def sankey_pacientes(df):
    df_pairs = df[df["Hospital siguiente"].notna()][["Nombre Hospital", "Hospital siguiente"]]
    df_pairs = df_pairs.groupby(["Nombre Hospital", "Hospital siguiente"]).size().reset_index(name="count")
    
    labels = list(pd.concat([df_pairs["Nombre Hospital"], df_pairs["Hospital siguiente"]]).unique())
    label_map = {label:i for i,label in enumerate(labels)}
    
    source = df_pairs["Nombre Hospital"].map(label_map)
    target = df_pairs["Hospital siguiente"].map(label_map)
    value = df_pairs["count"]
    
    fig = go.Figure(data=[go.Sankey(
        node = {"label": labels},
        link = {"source": source, "target": target, "value": value}
    )])
    fig.update_layout(title_text="Flujo de pacientes con ≥3 traslados", font_size=10)
    fig.show()
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de análisis de redes
# ---------------------------------------------------------
def top_flujos_hospitales(traslados, top_n=10, graficar=True, figsize=(10,5)):
    flujos = traslados.groupby(["Nombre Hospital","Hospital siguiente"]).size().reset_index(name="cantidad").sort_values("cantidad", ascending=False)
    top = flujos.head(top_n)
    if graficar:
        labels = top["Nombre Hospital"] + " → " + top["Hospital siguiente"]
        plt.figure(figsize=figsize)
        plt.barh(labels[::-1], top["cantidad"][::-1])
        plt.title("Flujos más frecuentes entre hospitales")
        plt.xlabel("Cantidad de traslados")
        plt.tight_layout()
        plt.show()
    return top

def metricas_red(G, top_n=10):
    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, weight="weight")
    in_degree = dict(G.in_degree(weight="weight"))
    out_degree = dict(G.out_degree(weight="weight"))
    df_metricas = pd.DataFrame({
        "hospital": list(G.nodes()),
        "degree_centrality": [degree[n] for n in G.nodes()],
        "betweenness": [betweenness[n] for n in G.nodes()],
        "in_degree": [in_degree[n] for n in G.nodes()],
        "out_degree": [out_degree[n] for n in G.nodes()]
    }).sort_values("betweenness", ascending=False)
    print("Top hospitales por betweenness:")
    print(df_metricas.head(top_n))
    return df_metricas
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de creación y visualización de red hospitalaria
# ---------------------------------------------------------
def gdf_red_hospitalaria(G, hosp_coords):
    geom_dict = {row["Nombre Hospital"]: (row["Longitud"], row["Latitud"])
                 for _, row in hosp_coords.iterrows()}
    edges_list = []
    missing_nodes = set()
    for u, v, d in G.edges(data=True):
        if u not in geom_dict or v not in geom_dict:
            missing_nodes.add(u if u not in geom_dict else v)
            continue
        edges_list.append({"origen": u, "destino": v, "weight": d["weight"], "geometry": LineString([geom_dict[u], geom_dict[v]])})
    if missing_nodes: print("Ignorados (no encontrados en hosp_coords):", missing_nodes)
    gdf_edges = gpd.GeoDataFrame(edges_list, geometry="geometry", crs="EPSG:4326").to_crs(epsg=3857)
    gdf_nodes = gpd.GeoDataFrame(hosp_coords, geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]), crs="EPSG:4326").to_crs(epsg=3857)
    return gdf_edges, gdf_nodes

def analizar_red_hospitalaria(traslados, hosp_coords, fecha_inicio=None, fecha_fin=None, filtrar_motivo=None,
                              hospital_origen=None, hospital_destino=None, peso_minimo=1, modo="estatico",
                              mostrar_resumen=True, graficar=True, mostrar_nombres=True, mostrar_peso=True):
    """
    Construye la red de traslados entre hospitales a partir de un DataFrame
    y devuelve el grafo, las aristas y la figura si se grafica.
    """
    df = traslados.copy()
    if fecha_inicio: df = df[df["Fecha egreso"] >= pd.to_datetime(fecha_inicio)]
    if fecha_fin: df = df[df["Fecha egreso"] <= pd.to_datetime(fecha_fin)]
    if filtrar_motivo: df = df[df["Motivo"].isin(filtrar_motivo)]
    if hospital_origen: df = df[df["Nombre Hospital"] == hospital_origen]
    if hospital_destino: df = df[df["Hospital siguiente"] == hospital_destino]

    if mostrar_resumen:
        print("Registros luego de filtros:", len(df))
        print("Hospitales origen únicos:", df["Nombre Hospital"].nunique())
        print("Hospitales destino únicos:", df["Hospital siguiente"].nunique())

    edges = df.groupby(["Nombre Hospital", "Hospital siguiente"]).size().reset_index(name="weight")
    edges = edges[edges["weight"] >= peso_minimo]

    G = nx.DiGraph()
    for _, row in edges.iterrows():
        G.add_edge(row["Nombre Hospital"], row["Hospital siguiente"], weight=row["weight"])

    if mostrar_resumen:
        print("Nodos en red:", G.number_of_nodes())
        print("Aristas en red:", G.number_of_edges())

    fig = None
    if graficar:
        if modo == "estatico":
            fig = plot_edges_geo(G, hosp_coords, mostrar_nombres, mostrar_peso)
        elif modo == "mapa":
            fig = plot_red_con_mapa(G, hosp_coords, mostrar_nombres, mostrar_peso)
        elif modo == "interactivo":
            fig = plot_red_interactiva(G, hosp_coords)

    return G, edges, fig
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones de visualización
# ---------------------------------------------------------

# -------------------------------------------------------
# construir gdf de aristas (reutilizable)
# -------------------------------------------------------

def curved_line(p1, p2, curva_factor=0.2, n=40):
    """
    Genera una curva cuadrática entre p1 y p2.
    - curva_factor: porcentaje de la longitud de la línea para el desplazamiento
    - garantiza que incluso líneas cortas se curven
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    if length == 0:
        return LineString([p1, p2])

    # punto medio
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2

    # vector perpendicular normalizado
    nx = -dy / length
    ny = dx / length

    # desplazamiento proporcional a la longitud
    displacement = max(curva_factor * length, 0.0001)

    # punto de control
    cx = mx + displacement * nx
    cy = my + displacement * ny

    # generar puntos de la parábola
    t = np.linspace(0, 1, n)
    xs = (1 - t)**2 * x1 + 2*(1 - t)*t*cx + t**2*x2
    ys = (1 - t)**2 * y1 + 2*(1 - t)*t*cy + t**2*y2

    return LineString(list(zip(xs, ys)))

def get_curvature(G, u, v, base_curva=0.8):
    """
    Determina la curvatura de la arista.
    - base_curva >0
    - alterna sentido si existe ida y vuelta
    """
    if G.has_edge(v, u):
        return base_curva if hash(u) < hash(v) else -base_curva
    return base_curva

def construir_gdf_edges(G, geom_dict, curva_base):
    edges = []
    missing_nodes = set()
    for u, v, d in G.edges(data=True):
        if u not in geom_dict or v not in geom_dict:
            missing_nodes.add(u if u not in geom_dict else v)
            continue
        p1 = (geom_dict[u].x, geom_dict[u].y)
        p2 = (geom_dict[v].x, geom_dict[v].y)
        curva = get_curvature(G, u, v, curva_base)
        line = curved_line(p1, p2, curva)
        edges.append({
            "geometry": line,
            "weight": d["weight"],
            "u": u,
            "v": v
        })
    return edges, missing_nodes

# -------------------------------------------------------
# plot simple (sin mapa)
# -------------------------------------------------------

def plot_edges_geo(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    fig, ax = plt.subplots(figsize=(12,12))

    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"])
    )

    gdf_nodes.plot(ax=ax, marker="o", color="red", markersize=50, zorder=2)

    geom_dict = {row["Nombre Hospital"]: row.geometry for _, row in gdf_nodes.iterrows()}

    edges, _ = construir_gdf_edges(G, geom_dict, 0.15)

    for e in edges:
        line = e["geometry"]
        lw = get_linewidth(e["weight"]) if mostrar_peso else 1
        x, y = line.xy
        ax.plot(x, y, linewidth=lw, alpha=0.6, color="blue")
        draw_arrow(ax, line, lw)
        if mostrar_peso:
            xm, ym = line.interpolate(0.5, normalized=True).coords[0]
            ax.text(xm, ym, str(e["weight"]), fontsize=8, color="blue")

    if mostrar_nombres:
        for _, row in gdf_nodes.iterrows():
            ax.text(row.geometry.x, row.geometry.y, row["Nombre Hospital"], fontsize=8, ha="right")

    ax.set_title("Red hospitalaria")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")

    return fig, ax

# -------------------------------------------------------
# plot con mapa base
# -------------------------------------------------------

def plot_red_con_mapa(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    hosp_coords = hosp_coords.copy()
    hosp_coords["Nombre Hospital"] = hosp_coords["Nombre Hospital"].str.strip()

    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    geom_dict = dict(zip(gdf_nodes["Nombre Hospital"], gdf_nodes.geometry))

    edges_list, missing_nodes = construir_gdf_edges(G, geom_dict, 2000)
    if missing_nodes:
        print("Hospitales ignorados:", missing_nodes)

    fig, ax = plt.subplots(figsize=(10,10))
    for e in edges_list:
        line = e["geometry"]
        lw = get_linewidth(e["weight"]) if mostrar_peso else 1
        x, y = line.xy
        ax.plot(x, y, linewidth=lw, alpha=0.6, color="blue")
        draw_arrow(ax, line, lw)
        if mostrar_peso:
            xm, ym = line.interpolate(0.5, normalized=True).coords[0]
            ax.text(xm, ym, str(e["weight"]), fontsize=8, color="blue")

    gdf_nodes.plot(ax=ax, color="red", markersize=40, zorder=2)

    if mostrar_nombres:
        for _, row in gdf_nodes.iterrows():
            ax.text(row.geometry.x, row.geometry.y, row["Nombre Hospital"], fontsize=8, ha="right")

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.axis("off")

    return fig, ax

# -------------------------------------------------------
# plot sobre AMBA
# -------------------------------------------------------
def plot_red_sobre_amba(gdf_edges, gdf_nodes, municipios_amba, mostrar_nombres=True, mostrar_peso=True):
    municipios = municipios_amba.to_crs(epsg=3857)
    hospitales = gdf_nodes.to_crs(epsg=3857)
    edges = gdf_edges.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(12,12))
    municipios.plot(ax=ax, alpha=0.3, edgecolor="black", color="lightgrey")

    if not edges.empty:
        # normalizar pesos en escala logarítmica
        norm = colors.LogNorm(vmin=max(edges["weight"].min(), 1), vmax=edges["weight"].max())
        cmap = cm.get_cmap("plasma")
        
        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])  # necesario para colorbar


        for _, row in edges.iterrows():
            line = row.geometry
            lw = np.log1p(row["weight"]) * 1.5 if mostrar_peso else 1
            color = cmap(norm(max(row["weight"], 1)))  # color según peso log
            x, y = line.xy
            ax.plot(x, y, linewidth=lw, alpha=0.7, color=color)
            draw_arrow(ax, line, lw)
            if mostrar_peso:
                xm, ym = line.interpolate(0.5, normalized=True).coords[0]
                ax.text(xm, ym, str(row["weight"]), fontsize=8, color=color)
        cbar = plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
        cbar.set_label("Cantidad de traslados (log scale)")

    # -------------------------
    # Plot nodos por tipo
    # -------------------------
    def get_node_color(name):
        if "UPA" in name.upper():
            return "green"
        elif "MODULO HOSPITALARIO" in name.upper():
            return "orange"
        else:
            return "blue"

    node_colors = [get_node_color(n) for n in hospitales["Nombre Hospital"]]
    hospitales.plot(ax=ax, color=node_colors, markersize=50, zorder=2)

    # -------------------------
    # Leyenda de nodos
    # -------------------------
    legend_elements = [
        Patch(facecolor="green", edgecolor="black", label="UPA"),
        Patch(facecolor="orange", edgecolor="black", label="Módulo Hospitalario"),
        Patch(facecolor="blue", edgecolor="black", label="Otros")
    ]
    ax.legend(handles=legend_elements, loc="upper right")

    if mostrar_nombres:
        for _, row in hospitales.iterrows():
            if row.geometry is not None:
                ax.annotate(
                    row["Nombre Hospital"],
                    xy=(row.geometry.x, row.geometry.y),
                    xytext=(5,5),
                    textcoords="offset points",
                    fontsize=8
                )
    ax.set_title("Red hospitalaria sobre AMBA (colores por traslados y tipo de hospital)")
    ax.axis("off")
    plt.show()

def gdf_red_hospitalaria_curva(G, hosp_coords, curva_base=0.3):
    """
    Genera GeoDataFrames de nodos y aristas con curvas visibles
    """
    geom_dict = {
        row["Nombre Hospital"]: row.geometry
        for _, row in gpd.GeoDataFrame(
            hosp_coords,
            geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"])
        ).iterrows()
    }

    edges_list, missing_nodes = construir_gdf_edges(G, geom_dict, curva_base)

    gdf_edges = gpd.GeoDataFrame(edges_list, geometry="geometry", crs="EPSG:4326").to_crs(3857)
    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    ).to_crs(3857)

    if missing_nodes:
        print("Ignorados (no encontrados en hosp_coords):", missing_nodes)

    return gdf_edges, gdf_nodes


import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
from shapely.geometry import LineString
import contextily as ctx
from matplotlib import cm, colors

# -------------------------------------------------------
# generar curva uniforme
# -------------------------------------------------------
def curved_line(p1, p2, curva_factor=0.2, n=40):
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    if length == 0:
        return LineString([p1, p2])

    mx, my = (x1 + x2)/2, (y1 + y2)/2
    nx, ny = -dy/length, dx/length
    displacement = max(curva_factor*length, 0.0001)
    cx, cy = mx + displacement*nx, my + displacement*ny

    t = np.linspace(0, 1, n)
    xs = (1 - t)**2 * x1 + 2*(1 - t)*t*cx + t**2*x2
    ys = (1 - t)**2 * y1 + 2*(1 - t)*t*cy + t**2*y2
    return LineString(list(zip(xs, ys)))

# -------------------------------------------------------
# construir gdf de aristas
# -------------------------------------------------------
def construir_gdf_edges(G, geom_dict, curva_base=0.2):
    edges = []
    missing_nodes = set()
    for u, v, d in G.edges(data=True):
        if u not in geom_dict or v not in geom_dict:
            missing_nodes.add(u if u not in geom_dict else v)
            continue
        p1, p2 = (geom_dict[u].x, geom_dict[u].y), (geom_dict[v].x, geom_dict[v].y)
        line = curved_line(p1, p2, curva_base)
        edges.append({
            "geometry": line,
            "weight": d["weight"],
            "u": u,
            "v": v
        })
    return edges, missing_nodes

# -------------------------------------------------------
# plot sobre AMBA con color por peso
# -------------------------------------------------------
def plot_red_sobre_amba_colores(gdf_edges, gdf_nodes, municipios_amba, mostrar_nombres=True, mostrar_peso=True):
    municipios = municipios_amba.to_crs(epsg=3857)
    hospitales = gdf_nodes.to_crs(epsg=3857)
    edges = gdf_edges.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(12,12))
    municipios.plot(ax=ax, alpha=0.3, edgecolor="black", color="lightgrey")

    if not edges.empty:
        # normalizar pesos a colormap
        norm = colors.Normalize(vmin=edges["weight"].min(), vmax=edges["weight"].max())
        cmap = cm.get_cmap("plasma")

        for _, row in edges.iterrows():
            line = row.geometry
            lw = np.log1p(row["weight"]) * 1.5 if mostrar_peso else 1
            color = cmap(norm(row["weight"]))
            x, y = line.xy
            ax.plot(x, y, linewidth=lw, alpha=0.7, color=color)

    hospitales.plot(ax=ax, color="red", markersize=50, zorder=2)
    if mostrar_nombres:
        for _, row in hospitales.iterrows():
            if row.geometry is not None:
                ax.annotate(
                    row["Nombre Hospital"],
                    xy=(row.geometry.x, row.geometry.y),
                    xytext=(5,5),
                    textcoords="offset points",
                    fontsize=8
                )

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.set_title("Red hospitalaria sobre AMBA (colores por traslados)")
    ax.axis("off")
    plt.show()
# ---------------------------------------------------------