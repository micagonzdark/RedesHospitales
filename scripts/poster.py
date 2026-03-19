"""
poster.py
---------
Funciones específicas para generar las figuras del poster académico.
Trabaja sobre datos ya cargados por init_notebook.py.

Requiere: geopandas, contextily, osmnx (para rutas de calles), networkx.
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import networkx as nx

from scripts import bases


# ---------------------------------------------------------
# A: Mapa de ubicación de Buenos Aires en Argentina
# ---------------------------------------------------------
def plot_pba_en_argentina(argentina_shp, provincias_shp):
    """Resalta la Provincia de Buenos Aires dentro del mapa de Argentina."""
    argentina = gpd.read_file(argentina_shp).to_crs(epsg=3857)
    provincias = gpd.read_file(provincias_shp).to_crs(epsg=3857)
    pba = provincias[provincias["name"].str.contains("Buenos Aires", case=False)]

    fig, ax = plt.subplots(figsize=(6, 6))
    argentina.plot(ax=ax, color="lightgrey", edgecolor="black")
    pba.plot(ax=ax, color="red")
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.set_title("Ubicación de la Provincia de Buenos Aires en Argentina")
    ax.axis("off")
    return fig, ax


# ---------------------------------------------------------
# B: Mapa de la Red Sudeste dentro de la Provincia de Buenos Aires
# ---------------------------------------------------------
def plot_red_sudeste(municipios_shp, municipios_red):
    """Resalta los municipios de la Red Sudeste en el mapa de PBA."""
    municipios = gpd.read_file(municipios_shp)
    municipios["nam_limpio"] = municipios["nam"].apply(bases.limpiar_nombre)
    red = municipios[municipios["nam_limpio"].isin(municipios_red)]

    municipios = municipios.to_crs(epsg=3857)
    red = red.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(6, 6))
    municipios.plot(ax=ax, color="lightgrey", edgecolor="black")
    red.plot(ax=ax, color="red")
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.set_title("Red Sudeste en la Provincia de Buenos Aires")
    ax.axis("off")
    return fig, ax


# ---------------------------------------------------------
# C: Mapa de villas/asentamientos cercanos a los hospitales
# ---------------------------------------------------------
def plot_slums_hospitales(slums_shp, hosp_coords):
    """Superpone villas y asentamientos con la ubicación de los hospitales."""
    slums = gpd.read_file(slums_shp).to_crs(epsg=3857)
    hospitales = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(8, 8))
    slums.plot(ax=ax, color="orange", alpha=0.5, label="Villas/Asentamientos")
    hospitales.plot(ax=ax, color="red", markersize=50, label="Hospitales")
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
    ax.set_title("Villas y asentamientos cercanos a hospitales")
    ax.legend()
    ax.axis("off")
    return fig, ax


# ---------------------------------------------------------
# D: Red hospitalaria (delegar a bases.analizar_red_hospitalaria)
# ---------------------------------------------------------
# Usar directamente: bases.analizar_red_hospitalaria(traslados, hosp_coords, modo="mapa")


# ---------------------------------------------------------
# E: Caminos más cortos entre hospitales usando red vial (requiere osmnx)
# ---------------------------------------------------------
def plot_shortest_paths(hosp_coords):
    """
    Grafica los caminos más cortos por red vial entre todos los pares de hospitales.
    Requiere osmnx instalado: pip install osmnx
    """
    try:
        import osmnx as ox
    except ImportError:
        raise ImportError("Esta función requiere osmnx. Instalalo con: pip install osmnx")

    G = ox.graph_from_place("Buenos Aires Province, Argentina", network_type="drive")
    fig, ax = ox.plot_graph(G, show=False, close=False, bgcolor="white")

    for i, row1 in hosp_coords.iterrows():
        for j, row2 in hosp_coords.iterrows():
            if i >= j:
                continue
            orig = ox.distance.nearest_nodes(G, row1["Longitud"], row1["Latitud"])
            dest = ox.distance.nearest_nodes(G, row2["Longitud"], row2["Latitud"])
            paths = list(nx.shortest_simple_paths(G, orig, dest, weight="length"))
            for p in paths[:2]:
                xs = [G.nodes[n]["x"] for n in p]
                ys = [G.nodes[n]["y"] for n in p]
                ax.plot(xs, ys, linewidth=2, alpha=0.6)

    return fig, ax
