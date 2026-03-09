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
# ---------------------------------------------------------

# ---------------------------------------------------------
# funciones utilitarias
# ---------------------------------------------------------
def get_linewidth(weight):
    return np.log1p(weight) * 1.5
# ---------------------------------------------------------

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
    return traslados

# ---------------------------------------------------------
# funciones de red hospitalaria
# ---------------------------------------------------------
def generar_red(traslados, fecha_inicio="2020-06-01", fecha_fin="2020-10-31"):
    fecha_inicio = pd.to_datetime(fecha_inicio)
    fecha_fin = pd.to_datetime(fecha_fin)
    traslados_periodo = traslados[
        (traslados["Fecha egreso"] >= fecha_inicio) &
        (traslados["Fecha egreso"] <= fecha_fin)
    ].copy()
    edges = (
        traslados_periodo.groupby(["Nombre Hospital", "Hospital siguiente"])
        .size().reset_index(name="weight")
    )
    G = nx.DiGraph()
    for _, row in edges.iterrows():
        G.add_edge(row["Nombre Hospital"], row["Hospital siguiente"], weight=row["weight"])
    return G, edges

def limpiar_coordenadas(hosp_coords):
    df_clean = hosp_coords.copy()
    if "Latitud" in df_clean.columns:
        df_clean["Latitud"] = df_clean["Latitud"].astype(str).str.replace(",", ".").astype(float)
    if "Longitud" in df_clean.columns:
        df_clean["Longitud"] = df_clean["Longitud"].astype(str).str.replace(",", ".").astype(float)
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].str.strip()
    return df_clean

def cargar_coordenadas(path):
    hosp_coords = pd.read_csv(path)
    return limpiar_coordenadas(hosp_coords)

# ---------------------------------------------------------
# funciones de visualización
# ---------------------------------------------------------

# estatico en eje de coordenadas
def plot_edges_geo(G, hosp_coords):
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
        ax.plot([origen["Longitud"], destino["Longitud"]],
                [origen["Latitud"], destino["Latitud"]],
                linewidth=get_linewidth(d["weight"]), alpha=0.5)
    
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
def plot_red_con_mapa(G, hosp_coords):
    # limpiar nombres de hospitales
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
        gdf_edges.plot(ax=ax, linewidth=gdf_edges["weight"].apply(get_linewidth), alpha=0.6)
    else:
        print("No hay aristas para mostrar")

    # plotear nodos
    gdf_nodes.plot(ax=ax, color="red", markersize=40, zorder=2)

    # agregar basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.axis("off")

    return fig, ax

# ejemplo de uso:
# fig, ax = plot_red_con_mapa(G_periodo, hosp_coords)
# plt.show()  # decidís cuándo mostrar

# interactivo en el mapa
def plot_red_interactiva(G, hosp_coords):
    coord_dict = {row["Nombre Hospital"]: (row["Latitud"], row["Longitud"])
                  for _, row in hosp_coords.iterrows()}

    centro = [hosp_coords["Latitud"].mean(), hosp_coords["Longitud"].mean()]

    m = folium.Map(location=centro, zoom_start=9)

    for nombre, (lat, lon) in coord_dict.items():
        folium.CircleMarker(location=[lat, lon], radius=6, popup=nombre,
                            color="red", fill=True).add_to(m)

    for u, v, d in G.edges(data=True):
        if u not in coord_dict or v not in coord_dict:
            continue
        folium.PolyLine([coord_dict[u], coord_dict[v]], weight=1 + d["weight"]*0.5,
                        color="blue").add_to(m)

    return m  # ahora solo devuelve el mapa, vos decidís cuándo guardar o mostrar

# ejemplo de uso:
# m = plot_red_interactiva(G_periodo, hosp_coords)
# m.save("red_interactiva.html")



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
    peso_minimo=1, modo="estatico", mostrar_resumen=True):
    
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
    edges = df.groupby(["Nombre Hospital", "Hospital siguiente"]).size().reset_index(name="weight")
    edges = edges[edges["weight"] >= peso_minimo]
    G = nx.DiGraph()
    for _, row in edges.iterrows():
        G.add_edge(row["Nombre Hospital"], row["Hospital siguiente"], weight=row["weight"])
    if mostrar_resumen:
        print("Nodos en red:", G.number_of_nodes())
        print("Aristas en red:", G.number_of_edges())
    if modo == "estatico":
        plot_edges_geo(G, hosp_coords)
    elif modo == "mapa":
        pass # plot_red_con_mapa(G, hosp_coords)
    elif modo == "interactivo":
        pass # return plot_red_interactiva(G, hosp_coords)
    return G, edges