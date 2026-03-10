# bases.py

# ---------------------------------------------------------
# ejemplos de uso en otro archivo
# from bases import *

# df = cargar_datos_pacientes("../data/pacientes.xlsx")
# traslados = reconstruir_traslados(df)
# hosp_coords = cargar_coordenadas("../data/hospitales_coordenadas.csv")
# G, edges = analizar_red_hospitalaria(traslados, hosp_coords, fecha_inicio="2020-06-01", fecha_fin="2020-10-31")
# ---------------------------------------------------------


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
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones utilitarias
# ---------------------------------------------------------
def get_linewidth(weight):
    return np.log1p(weight) * 1.5

def coords_a_dict(hosp_coords):

    return {
        row["Nombre Hospital"]: (row["Latitud"], row["Longitud"])
        for _, row in hosp_coords.iterrows()
    }
# ---------------------------------------------------------
# funciones de limpieza y reconstrucción de traslados
# ---------------------------------------------------------
def limpiar_pacientes(df):
    df_clean = df[df["Id"].astype(str).str.match(r"[A-Za-z0-9]+")].copy()
    
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].str.strip().str.upper()
        
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
    df = pd.read_excel(path)
    return limpiar_pacientes(df)

def reconstruir_traslados(df):
    df = df.sort_values(["Id", "Fecha inicio"]).copy()
    df["Hospital siguiente"] = df.groupby("Id")["Nombre Hospital"].shift(-1)
    df["Fecha ingreso siguiente"] = df.groupby("Id")["Fecha inicio"].shift(-1)
    df["dias_entre_hospitales"] = (df["Fecha ingreso siguiente"] - df["Fecha egreso"]).dt.days
    df["es_traslado"] = df["Motivo"].str.contains("traslad", case=False, na=False)
    traslados = df[
        (df["es_traslado"]) & 
        (df["Hospital siguiente"].notna()) & 
        (df["Hospital siguiente"] != df["Nombre Hospital"])
    ].copy()
    
    # normalizar nombres de hospitales
    traslados["Nombre Hospital"] = traslados["Nombre Hospital"].apply(limpiar_nombre)
    traslados["Hospital siguiente"] = traslados["Hospital siguiente"].apply(limpiar_nombre)
    
    return traslados

def normalizar_hospitales(df):
    df = df.copy()
    df["Nombre Hospital"] = df["Nombre Hospital"].apply(lambda x: limpiar_nombre(x))
    return df

def limpiar_nombre(texto):
    """Pasa el texto a mayúsculas, quita acentos y símbolos"""
    if texto is None:
        return ""
    texto = texto.upper()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    texto = re.sub(r'[^A-Z\s]', '', texto)
    return texto.strip()

def cargar_municipios(path_shp):
    """Carga un shapefile y crea columna limpia"""
    municipios = gpd.read_file(path_shp)
    municipios["nam_limpio"] = municipios["nam"].apply(limpiar_nombre)
    return municipios

# ---------------------------------------------------------
# funciones de creacion de la red hospitalaria
# ---------------------------------------------------------

# obsoleta. Es una funcion mas basica que analizar red. Por el momento usamos directo analizar red
# def generar_red(traslados, fecha_inicio="2020-06-01", fecha_fin="2020-10-31"):
#     fecha_inicio = pd.to_datetime(fecha_inicio)
#     fecha_fin = pd.to_datetime(fecha_fin)
#     traslados_periodo = traslados[
#         (traslados["Fecha egreso"] >= fecha_inicio) &
#         (traslados["Fecha egreso"] <= fecha_fin)
#     ].copy()
#     edges = (
#         traslados_periodo.groupby(["Nombre Hospital", "Hospital siguiente"])
#         .size().reset_index(name="weight")
#     )
#     G = nx.DiGraph()
#     for _, row in edges.iterrows():
#         G.add_edge(row["Nombre Hospital"], row["Hospital siguiente"], weight=row["weight"])
#     return G, edges

def limpiar_coordenadas(hosp_coords):
    df_clean = hosp_coords.copy()
    if "Latitud" in df_clean.columns:
        df_clean["Latitud"] = df_clean["Latitud"].astype(str).str.replace(",", ".").astype(float)
    if "Longitud" in df_clean.columns:
        df_clean["Longitud"] = df_clean["Longitud"].astype(str).str.replace(",", ".").astype(float)
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].str.strip()
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].apply(limpiar_nombre)
    return df_clean

def cargar_coordenadas(path):
    hosp_coords = pd.read_csv(path)
    return limpiar_coordenadas(hosp_coords)



def gdf_red_hospitalaria(G, hosp_coords):
    """
    Convierte un DiGraph de hospitales y las coordenadas en un GeoDataFrame
    con aristas como LineStrings y nodos como puntos.
    
    Devuelve: gdf_edges, gdf_nodes
    """
    # nodo -> coordenadas
    geom_dict = {row["Nombre Hospital"]: (row["Longitud"], row["Latitud"])
                 for _, row in hosp_coords.iterrows()}

    # aristas
    edges_list = []
    missing_nodes = set()
    for u, v, d in G.edges(data=True):
        if u not in geom_dict:
            missing_nodes.add(u)
            continue
        if v not in geom_dict:
            missing_nodes.add(v)
            continue
        edges_list.append({
            "origen": u,
            "destino": v,
            "weight": d["weight"],
            "geometry": LineString([geom_dict[u], geom_dict[v]])
        })
    if missing_nodes:
        print("Ignorados (no encontrados en hosp_coords):", missing_nodes)

    gdf_edges = gpd.GeoDataFrame(edges_list, geometry="geometry", crs="EPSG:4326")
    gdf_edges = gdf_edges.to_crs(epsg=3857)

    # nodos
    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    return gdf_edges, gdf_nodes
# ---------------------------------------------------------
# funciones de visualización
# ---------------------------------------------------------

# estatico en eje de coordenadas
def plot_edges_geo(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    fig, ax = plt.subplots(figsize=(12,12))
    
    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"])
    )
    gdf_nodes.plot(marker="o", color="red", markersize=50, zorder=2, ax=ax)

    coords_dict = hosp_coords.set_index("Nombre Hospital")[["Latitud","Longitud"]].to_dict("index")
    for u, v, d in G.edges(data=True):
        if u not in coords_dict or v not in coords_dict:
            continue
        origen = coords_dict[u]
        destino = coords_dict[v]
        lw = get_linewidth(d["weight"]) if mostrar_peso else 1
        ax.plot([origen["Longitud"], destino["Longitud"]],
                [origen["Latitud"], destino["Latitud"]],
                linewidth=lw, alpha=0.5)
        if mostrar_peso:
            xm = (origen["Longitud"] + destino["Longitud"]) / 2
            ym = (origen["Latitud"] + destino["Latitud"]) / 2
            ax.text(xm, ym, str(d["weight"]), fontsize=8, color="blue")

    if mostrar_nombres:
        for _, row in gdf_nodes.iterrows():
            ax.text(row["Longitud"], row["Latitud"], row["Nombre Hospital"], fontsize=8, ha="right")
    
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Red hospitalaria")
    
    return fig, ax
# ejemplo de uso:
# fig, ax = plot_edges_geo(G_periodo, hosp_coords)
# ax.grid(True)
# plt.show()  # decidís cuándo mostrar


# estatico sobre el mapa 
def plot_red_con_mapa(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    hosp_coords = hosp_coords.copy()
    hosp_coords["Nombre Hospital"] = hosp_coords["Nombre Hospital"].str.strip()

    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    geom_dict = dict(zip(gdf_nodes["Nombre Hospital"], gdf_nodes.geometry))

    edges_list = []
    missing_nodes = set()
    for u, v, d in G.edges(data=True):
        if u not in geom_dict:
            missing_nodes.add(u)
            continue
        if v not in geom_dict:
            missing_nodes.add(v)
            continue
        edges_list.append({
            "geometry": LineString([geom_dict[u], geom_dict[v]]),
            "weight": d["weight"]
        })

    if missing_nodes:
        print(f"Estos hospitales no están en hosp_coords y se ignoraron: {missing_nodes}")

    fig, ax = plt.subplots(figsize=(10,10))

    # plotear aristas solo si hay
    if edges_list:
        gdf_edges = gpd.GeoDataFrame(edges_list, geometry='geometry', crs="EPSG:3857")
        # definir ancho de línea
        if mostrar_peso:
            lw_series = gdf_edges["weight"].apply(get_linewidth)
        else:
            lw_series = 1
        gdf_edges.plot(ax=ax, linewidth=lw_series, alpha=0.6)

        # agregar texto con el peso
        if mostrar_peso:
            for _, row in gdf_edges.iterrows():
                x, y = row.geometry.interpolate(0.5, normalized=True).xy
                ax.text(x[0], y[0], str(row["weight"]), fontsize=8, color="blue",
                        ha="center", va="center")
    else:
        print("No hay aristas para mostrar")

    # plotear nodos
    gdf_nodes.plot(ax=ax, color="red", markersize=40, zorder=2)

    # nombres de hospitales
    if mostrar_nombres:
        for _, row in gdf_nodes.iterrows():
            ax.text(row.geometry.x, row.geometry.y, row["Nombre Hospital"], fontsize=8, ha="right")

    # agregar basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.axis("off")

    return fig, ax

# ejemplo de uso:
# fig, ax = plot_red_con_mapa(G_periodo, hosp_coords)
# plt.show()  # decidís cuándo mostrar
# interactivo en el mapa
def plot_red_interactiva(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    coord_dict = {row["Nombre Hospital"]: (row["Latitud"], row["Longitud"])
                  for _, row in hosp_coords.iterrows()}

    centro = [hosp_coords["Latitud"].mean(), hosp_coords["Longitud"].mean()]

    m = folium.Map(location=centro, zoom_start=9)

    # nodos
    for nombre, (lat, lon) in coord_dict.items():
        popup_text = nombre if mostrar_nombres else None
        folium.CircleMarker(location=[lat, lon], radius=6, popup=popup_text,
                            color="red", fill=True).add_to(m)

    # aristas
    for u, v, d in G.edges(data=True):
        if u not in coord_dict or v not in coord_dict:
            continue
        peso_linea = 1 + d["weight"]*0.5 if mostrar_peso else 1
        folium.PolyLine([coord_dict[u], coord_dict[v]], weight=peso_linea,
                        color="blue").add_to(m)

    return m
# ejemplo de uso:
# m = plot_red_interactiva(G_periodo, hosp_coords)
# m.save("red_interactiva.html")



def plot_red_gdf(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    """
    Convierte un DiGraph en GeoDataFrame y lo plotea.
    mostrar_nombres: si True, muestra nombres de hospitales
    mostrar_peso: si True, muestra grosor y número de arista
    """
    # nodos
    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    geom_dict = dict(zip(gdf_nodes["Nombre Hospital"], gdf_nodes.geometry))

    edges_list = []
    for u, v, d in G.edges(data=True):
        if u in geom_dict and v in geom_dict:
            edges_list.append({
                "geometry": LineString([geom_dict[u], geom_dict[v]]),
                "weight": float(d["weight"])
            })

    gdf_edges = gpd.GeoDataFrame(edges_list, geometry="geometry", crs="EPSG:3857")

    fig, ax = plt.subplots(figsize=(10,10))

    # plotear aristas
    if not gdf_edges.empty:
        lw_series = gdf_edges["weight"].apply(get_linewidth) if mostrar_peso else 1
        gdf_edges.plot(ax=ax, linewidth=lw_series, alpha=0.6, color="blue")

        if mostrar_peso:
            # mostrar el número de peso en el medio de cada arista
            for _, row in gdf_edges.iterrows():
                x, y = row.geometry.interpolate(0.5, normalized=True).xy
                ax.text(x[0], y[0], str(int(row["weight"])), fontsize=9, color="black",
                        ha="center", va="center", zorder=5, backgroundcolor="white", alpha=0.7)

    # plotear nodos
    gdf_nodes.plot(ax=ax, color="red", markersize=40, zorder=10)

    # nombres de hospitales
    if mostrar_nombres:
        for _, row in gdf_nodes.iterrows():
            ax.text(row.geometry.x, row.geometry.y, row["Nombre Hospital"], fontsize=8,
                    ha="right", zorder=20)

    # basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.axis("off")

    return fig, ax


def plot_red_sobre_amba(gdf_edges, gdf_nodes, municipios_amba, mostrar_nombres=True, mostrar_peso=True):
    """
    Plotea la red hospitalaria sobre los municipios del AMBA.
    gdf_edges: GeoDataFrame con aristas (LineString) y columna 'weight'
    gdf_nodes: GeoDataFrame con hospitales (Point) y columna 'Nombre Hospital'
    municipios_amba: GeoDataFrame de polígonos de AMBA
    """
    # Unificar CRS
    municipios = municipios_amba.to_crs(epsg=3857)
    hospitales = gdf_nodes.to_crs(epsg=3857)
    edges = gdf_edges.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(12,12))

    # 1. Plotear polígonos de municipios
    municipios.plot(ax=ax, alpha=0.3, edgecolor="black", color="lightgrey")

    # 2. Plotear aristas
    if not edges.empty:
        lw_series = edges["weight"].apply(lambda w: np.log1p(w)*1.5) if mostrar_peso else 1
        edges.plot(ax=ax, linewidth=lw_series, color="blue", alpha=0.6, zorder=1)
    
    # 3. Plotear nodos
    hospitales.plot(ax=ax, color="red", markersize=50, zorder=2)

    # 4. Nombres de hospitales
    if mostrar_nombres:
        for _, row in hospitales.iterrows():
            if row.geometry is not None and not row.geometry.is_empty:
                ax.annotate(
                    row["Nombre Hospital"],
                    xy=(row.geometry.x, row.geometry.y),
                    xytext=(5,5),
                    textcoords="offset points",
                    fontsize=8,
                    ha="left",
                    va="bottom"
                )

    ax.set_title("Red hospitalaria sobre AMBA", fontsize=16)
    ax.axis("off")
    plt.show()

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
# función generalizada para análisis de red
# ---------------------------------------------------------
def analizar_red_hospitalaria(
    traslados, hosp_coords,
    fecha_inicio=None, fecha_fin=None,
    filtrar_motivo=None,
    hospital_origen=None, hospital_destino=None,
    peso_minimo=1, modo="estatico", mostrar_resumen=True,
    graficar=True, mostrar_nombres=True, mostrar_peso=True
):
    # filtrar traslados según fechas y motivos
    df = traslados.copy()
    if fecha_inicio is not None:
        df = df[df["Fecha egreso"] >= pd.to_datetime(fecha_inicio)]
    if fecha_fin is not None:
        df = df[df["Fecha egreso"] <= pd.to_datetime(fecha_fin)]
    if filtrar_motivo is not None:
        df = df[df["Motivo"].isin(filtrar_motivo)]
    if hospital_origen is not None:
        df = df[df["Nombre Hospital"] == hospital_origen]
    if hospital_destino is not None:
        df = df[df["Hospital siguiente"] == hospital_destino]

    if mostrar_resumen:
        print("Registros luego de filtros:", len(df))
        print("Hospitales origen únicos:", df["Nombre Hospital"].nunique())
        print("Hospitales destino únicos:", df["Hospital siguiente"].nunique())

    # construir edges
    edges = df.groupby(["Nombre Hospital", "Hospital siguiente"]).size().reset_index(name="weight")
    edges = edges[edges["weight"] >= peso_minimo]

    # construir grafo
    G = nx.DiGraph()
    for _, row in edges.iterrows():
        G.add_edge(row["Nombre Hospital"], row["Hospital siguiente"], weight=row["weight"])

    if mostrar_resumen:
        print("Nodos en red:", G.number_of_nodes())
        print("Aristas en red:", G.number_of_edges())

    # graficar solo si graficar=True
    if graficar:
        if modo == "estatico":
            fig, ax = plot_edges_geo(
                G, hosp_coords,
                mostrar_nombres=mostrar_nombres,
                mostrar_peso=mostrar_peso
            )
        elif modo == "mapa":
            fig, ax = plot_red_con_mapa(
                G, hosp_coords,
                mostrar_nombres=mostrar_nombres,
                mostrar_peso=mostrar_peso
            )
        elif modo == "interactivo":
            return plot_red_interactiva(G, hosp_coords)

    return G, edges

# ---------------------------------------------------------
# funciones de resumen de traslados
# ---------------------------------------------------------

def resumen_traslados(
    df,
    col_hospital="Nombre Hospital",
    imprimir=True
):
    """
    imprime resumen básico del dataset de traslados
    """

    total_traslados = len(df)
    hospitales_unicos = df[col_hospital].nunique()

    if imprimir:
        print(f"Total de traslados: {total_traslados}")
        print(f"Cantidad de hospitales únicos: {hospitales_unicos}")

    return {
        "total_traslados": total_traslados,
        "hospitales_unicos": hospitales_unicos
    }

def traslados_por_mes(
    df,
    col_fecha="Fecha egreso",
    graficar=True,
    figsize=(12,5),
    marker="o"
):
    """
    cantidad de traslados por mes
    """

    df = df.copy()
    df[col_fecha] = pd.to_datetime(df[col_fecha])

    serie = (
        df.groupby(df[col_fecha].dt.to_period("M"))
        .size()
    )

    serie.index = serie.index.astype(str)

    if graficar:

        sns.set_style("whitegrid")

        plt.figure(figsize=figsize)

        sns.lineplot(
            x=serie.index,
            y=serie.values,
            marker=marker
        )

        plt.xticks(rotation=45)
        plt.title("Traslados por mes")
        plt.ylabel("Cantidad de traslados")
        plt.xlabel("Mes")

        plt.tight_layout()
        plt.show()

    return serie

def distribucion_traslados_paciente(
    df,
    col_id="Id",
    valores=[1,2,3],
    graficar=True,
    figsize=(8,5)
):
    """
    distribución de cantidad de traslados por paciente
    """

    traslados_por_paciente = df.groupby(col_id).size()

    conteo = traslados_por_paciente.value_counts().sort_index()
    conteo = conteo.loc[conteo.index.isin(valores)]

    if graficar:

        sns.set_style("whitegrid")

        plt.figure(figsize=figsize)

        ax = sns.barplot(
            x=conteo.index,
            y=conteo.values
        )

        plt.title("Cantidad de pacientes por número de traslados")
        plt.xlabel("Número de traslados")
        plt.ylabel("Número de pacientes")

        for i, v in enumerate(conteo.values):
            ax.text(i, v, str(v), ha="center", va="bottom")

        plt.show()

    stats = {
        "promedio": traslados_por_paciente.mean(),
        "desvio": traslados_por_paciente.std()
    }

    print("Promedio de traslados por paciente:", stats["promedio"])
    print("Desvío estándar:", stats["desvio"])

    return conteo, stats

def tiempo_total_paciente(
    df,
    col_id="Id",
    col_dias="Duracion días",
    max_dias=50,           # límite visual por defecto
    quantile_outlier=0.99,
    graficar=True,
    figsize=(10,5)         # tamaño fijo
):
    """
    Distribución del tiempo total en el sistema por paciente
    cada barra corresponde a un número entero de días
    muestra el valor arriba de cada barra
    """

    import seaborn as sns
    import matplotlib.pyplot as plt
    import numpy as np

    # tiempo total por paciente
    tiempo_sistema = df.groupby(col_id)[col_dias].sum()
    tiempo_sistema = tiempo_sistema[tiempo_sistema < max_dias]

    # límite para outliers
    limite = tiempo_sistema.quantile(quantile_outlier)
    limite = min(limite, max_dias)

    if graficar:
        sns.set_style("whitegrid")

        # bins enteros hasta el límite
        max_bin = int(np.ceil(limite))
        bins = np.arange(0, max_bin + 1)

        plt.figure(figsize=figsize)
        ax = sns.histplot(
            tiempo_sistema,
            bins=bins,
            discrete=True
        )

        plt.xlim(0, limite)
        plt.axvline(
            limite,
            color="red",
            linestyle="--",
            label=f"percentil {int(quantile_outlier*100)}"
        )

        # numeritos arriba de cada barra
        for p in ax.patches:
            height = p.get_height()
            if height > 0:
                ax.text(
                    p.get_x() + p.get_width()/2,
                    height,
                    str(int(height)),
                    ha="center",
                    va="bottom",
                    fontsize=8
                )

        plt.title("Tiempo total dentro del sistema por paciente")
        plt.xlabel("Días totales")
        plt.ylabel("Número de pacientes")
        plt.legend()
        plt.show()

    return tiempo_sistema, limite



# ---------------------------------------------------------
# funciones de analisis hospitalario / EDA
# ---------------------------------------------------------
def traslados_por_hospital(df, col_hospital="Nombre Hospital", hospitales=None, graficar=True):
    """
    cuenta traslados por hospital
    """

    data = df.copy()

    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]

    resultado = (
        data.groupby(col_hospital)
        .size()
        .sort_values(ascending=False)
    )

    if graficar:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12,5))
        resultado.plot(kind="bar")
        plt.title("Cantidad de traslados por hospital")
        plt.ylabel("Cantidad de traslados")
        plt.show()

    return resultado

def tiempo_promedio_por_hospital(
    df,
    col_hospital="Nombre Hospital",
    col_dias="Duracion días",
    hospitales=None,
    quantile_outlier=0.99,
    graficar=True
):
    """
    calcula tiempo promedio por hospital eliminando outliers
    """

    data = df.copy()

    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]

    limite = data[col_dias].quantile(quantile_outlier)
    data = data[data[col_dias] <= limite]

    resultado = (
        data.groupby(col_hospital)[col_dias]
        .mean()
        .sort_values(ascending=False)
    )

    if graficar:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12,5))
        resultado.plot(kind="bar", color="orange")
        plt.title("Tiempo promedio en hospital por paciente")
        plt.ylabel("Días promedio")
        plt.show()

    return resultado


def muertes_por_hospital(
    df,
    col_hospital="Nombre Hospital",
    col_muerte="murio",
    hospitales=None,
    graficar=True
):
    """
    cuenta fallecidos por hospital
    """

    data = df.copy()

    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]

    resultado = (
        data[data[col_muerte]]
        .groupby(col_hospital)
        .size()
        .sort_values(ascending=False)
    )

    if graficar:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12,5))
        resultado.plot(kind="bar", color="red")
        plt.title("Cantidad de fallecidos por hospital")
        plt.ylabel("Cantidad de fallecidos")
        plt.show()

    return resultado

def distribucion_edades_por_hospital(
    df,
    col_hospital="Nombre Hospital",
    col_edad="Edad",
    hospitales=None,
    bins=20,
    graficar=True
):
    """
    calcula distribución de edades por hospital
    """

    data = df.copy()

    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]

    resultado = (
        data.groupby(col_hospital)[col_edad]
        .describe()
        .sort_values("mean", ascending=False)
    )

    if graficar:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12,5))
        data[col_edad].hist(bins=bins, edgecolor="white")
        plt.title("Distribución de edades")
        plt.xlabel("Edad")
        plt.ylabel("Frecuencia")
        plt.show()

    return resultado

### ejemplos de uso:
#bases.traslados_por_hospital(df_traslados)
#bases.tiempo_promedio_por_hospital(df_traslados)
#bases.muertes_por_hospital(df_pacientes)

# hosp = [
#     "HOSPITAL POSADAS",
#     "HOSPITAL ITALIANO",
#     "HOSPITAL GARRAHAN"
# ]

# bases.traslados_por_hospital(df_traslados, hospitales=hosp)

# bases.tiempo_promedio_por_hospital(df_traslados, hospitales=hosp)

# bases.muertes_por_hospital(df_pacientes, hospitales=hosp)