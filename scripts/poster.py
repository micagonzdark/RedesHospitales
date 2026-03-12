# ---------------------------------------------------------
# funciones geograficas
# ---------------------------------------------------------

#A
def plot_pba_en_argentina(argentina_shp, provincias_shp):

    argentina = gpd.read_file(argentina_shp)
    provincias = gpd.read_file(provincias_shp)

    pba = provincias[provincias["name"].str.contains("Buenos Aires", case=False)]

    argentina = argentina.to_crs(epsg=3857)
    provincias = provincias.to_crs(epsg=3857)
    pba = pba.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(6,6))

    argentina.plot(ax=ax, color="lightgrey", edgecolor="black")
    pba.plot(ax=ax, color="red")

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

    ax.set_title("Location of Buenos Aires Province in Argentina")
    ax.axis("off")

    return fig, ax

#B
def plot_red_sudeste(municipios_shp, municipios_red):

    municipios = gpd.read_file(municipios_shp)

    municipios["nam_limpio"] = municipios["nam"].apply(bases.limpiar_nombre)

    red = municipios[municipios["nam_limpio"].isin(municipios_red)]

    municipios = municipios.to_crs(epsg=3857)
    red = red.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(6,6))

    municipios.plot(ax=ax, color="lightgrey", edgecolor="black")
    red.plot(ax=ax, color="red")

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

    ax.set_title("Red Sudeste in Buenos Aires Province")
    ax.axis("off")

    return fig, ax


#C
def plot_slums_hospitales(slums_shp, hosp_coords):

    slums = gpd.read_file(slums_shp)

    hospitales = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    )

    slums = slums.to_crs(epsg=3857)
    hospitales = hospitales.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(8,8))

    slums.plot(ax=ax, color="orange", alpha=0.5)
    hospitales.plot(ax=ax, color="red", markersize=50)

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

    ax.set_title("Slums close to hospitals")
    ax.axis("off")

    return fig, ax


#D
# analizar_red_hospitalaria


#E
def plot_shortest_paths(hosp_coords):

    # descargar red de calles
    G = ox.graph_from_place(
        "Buenos Aires Province, Argentina",
        network_type="drive"
    )

    hosp_coords = hosp_coords.copy()

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

