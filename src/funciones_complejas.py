import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import ast
import matplotlib.gridspec as gridspec
import networkx as nx

from shapely.geometry import LineString, Point
import geopandas as gpd

from src.config import *
from src.io import *
from src.procesamiento import *
from src.visualizacion import *


# from .procesamiento import *
# from .visualizacion import *

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

def traslados_por_hospital(df, col_hospital="Nombre Hospital", hospitales=None, graficar=True,
                           nombre_archivo=None, subcarpeta="general"):
    """Devuelve serie con cantidad de traslados por hospital."""
    data = df.copy()
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    resultado = data.groupby(col_hospital).size().sort_values(ascending=False)
    if graficar:
        plt.figure(figsize=(12, 5))
        resultado.plot(kind="bar", color=PALETA_GENERAL[0])
        plt.title("Cantidad de traslados por hospital")
        plt.ylabel("Cantidad de traslados")
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    return resultado

def tiempo_promedio_por_hospital(df, col_hospital="Nombre Hospital", col_dias="Duracion dias", hospitales=None,
                                  quantile_outlier=0.99, graficar=True,
                                  nombre_archivo=None, subcarpeta="tiempos"):
    data = df.copy()
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    data = data[data[col_dias] >= 0]
    limite = data[col_dias].quantile(quantile_outlier)
    data = data[data[col_dias] <= limite]
    resultado = data.groupby(col_hospital)[col_dias].mean().sort_values(ascending=False)
    if graficar:
        plt.figure(figsize=(12, 5))
        resultado.plot(kind="bar", color=PALETA_GENERAL[1])
        plt.title("Tiempo promedio en hospital por paciente")
        plt.ylabel("Dias promedio")
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    return resultado

def muertes_por_hospital(df, col_hospital="Nombre Hospital", col_muerte="murio", hospitales=None,
                         graficar=True, nombre_archivo=None, subcarpeta="desenlaces"):
    data = df.copy()
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    resultado = data[data[col_muerte]].groupby(col_hospital).size().sort_values(ascending=False)
    if graficar:
        plt.figure(figsize=(12, 5))
        resultado.plot(kind="bar", color=COLORES_MOTIVOS["muerte"])
        plt.title("Cantidad de fallecidos por hospital")
        plt.ylabel("Cantidad de fallecidos")
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    return resultado

def distribucion_edades_por_hospital(df, col_hospital="Nombre Hospital", col_edad="Edad", hospitales=None,
                                      bins=20, graficar=True, nombre_archivo=None, subcarpeta="general"):
    data = df.copy()
    data[col_edad] = pd.to_numeric(data[col_edad], errors="coerce")
    if hospitales is not None:
        data = data[data[col_hospital].isin(hospitales)]
    data = data.dropna(subset=[col_edad])
    descr = data.groupby(col_hospital)[col_edad].describe()
    mean_orden = data.groupby(col_hospital)[col_edad].mean().sort_values(ascending=False)
    resultado = descr.loc[mean_orden.index]
    if graficar:
        plt.figure(figsize=(12, 5))
        data[col_edad].hist(bins=bins, edgecolor="white", color=PALETA_GENERAL[0])
        plt.title("Distribucion de edades")
        plt.xlabel("Edad")
        plt.ylabel("Frecuencia")
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    return resultado

def relacion_tiempo_riesgo_estado(df, col_riesgo="Nivel riesgo social", col_estado="Estado al ingreso",
                                   col_dias="Duracion dias", graficar=True,
                                   nombre_archivo=None, subcarpeta="tiempos"):
    data = df.copy()
    data = data[data[col_dias] >= 0]
    tabla = pd.pivot_table(data, values=col_dias, index=col_riesgo, columns=col_estado, aggfunc="mean")
    if graficar:
        plt.figure(figsize=(8, 6))
        sns.heatmap(tabla, annot=True, fmt=".1f", cmap=CMAP_FRECUENCIA)
        plt.title("Tiempo promedio de internacion\nRiesgo social vs Estado")
        plt.ylabel("Nivel de riesgo")
        plt.xlabel("Estado al ingreso")
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    return tabla

def traslados_en_el_tiempo(df, col_fecha="Fecha egreso", freq="M", graficar=True, figsize=(12, 5), marker="o",
                           nombre_archivo=None, subcarpeta="general"):
    """
    Agrupa traslados por periodo de tiempo y opcionalmente los grafica.

    Parametros
    ----------
    freq : str
        Frecuencia de agrupacion: 'D' (dia), 'W' (semana), 'M' (mes), 'Q' (trimestre), 'Y' (anio).
    """
    data = df.copy()
    data[col_fecha] = pd.to_datetime(data[col_fecha])
    serie = data.groupby(data[col_fecha].dt.to_period(freq)).size()
    serie.index = serie.index.astype(str)
    if graficar:
        sns.set_style("whitegrid")
        plt.figure(figsize=figsize)
        sns.lineplot(x=serie.index, y=serie.values, marker=marker, color=PALETA_GENERAL[0])
        plt.xticks(rotation=45)
        plt.title(f"Cantidad de traslados en el tiempo (freq={freq})")
        plt.xlabel("Periodo")
        plt.ylabel("Cantidad de traslados")
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    return serie

def distribucion_traslados_paciente(df, col_id="Id", valores=[1, 2, 3], graficar=True, figsize=(8, 5),
                                    nombre_archivo=None, subcarpeta="general"):
    traslados_por_paciente = df.groupby(col_id).size()
    conteo = traslados_por_paciente.value_counts().sort_index()
    conteo = conteo.loc[conteo.index.isin(valores)]
    if graficar:
        sns.set_style("whitegrid")
        plt.figure(figsize=figsize)
        ax = sns.barplot(x=conteo.index, y=conteo.values, color=PALETA_GENERAL[0])
        plt.title("Cantidad de pacientes por numero de traslados")
        plt.xlabel("Numero de traslados")
        plt.ylabel("Numero de pacientes")
        for i, v in enumerate(conteo.values):
            ax.text(i, v, str(v), ha="center", va="bottom")
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    stats = {"promedio": traslados_por_paciente.mean(), "desvio": traslados_por_paciente.std()}
    print("Promedio de traslados por paciente:", stats["promedio"])
    print("Desvio estandar:", stats["desvio"])
    return conteo, stats

def tiempo_total_paciente(df, col_id="Id", col_dias="Duracion dias", max_dias=50, quantile_outlier=0.99,
                          graficar=True, figsize=(10, 5), nombre_archivo=None, subcarpeta="tiempos"):
    tiempo_sistema = df.groupby(col_id)[col_dias].sum()
    tiempo_sistema = tiempo_sistema[tiempo_sistema.between(0, max_dias)]
    limite = min(tiempo_sistema.quantile(quantile_outlier), max_dias)
    if graficar:
        conteo = tiempo_sistema.value_counts().sort_index()
        conteo = conteo[conteo.index <= limite]
        x, y = conteo.index, conteo.values
        plt.figure(figsize=figsize)
        bars = plt.bar(x, y, color=PALETA_GENERAL[0])
        plt.axvline(limite, color=COLORES_MOTIVOS["muerte"], linestyle="--",
                    label=f"percentil {int(quantile_outlier * 100)}")
        for xi, yi in zip(x, y):
            plt.text(xi, yi, str(int(yi)), ha="center", va="bottom", fontsize=8)
        plt.title("Tiempo total dentro del sistema por paciente")
        plt.xlabel("Dias totales")
        plt.ylabel("Numero de pacientes")
        plt.legend()
        plt.tight_layout()
        if nombre_archivo:
            guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
        plt.show()
    return tiempo_sistema, limite

def analizar_red_hospitalaria(traslados, hosp_coords, fecha_inicio=None, fecha_fin=None, filtrar_motivo=None,
                              hospital_origen=None, hospital_destino=None, peso_minimo=UMBRAL_MIN_TRASLADOS_GRAFICO, modo="estatico",
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


import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import ast

def generar_matrices_traslados(traslados_df, pacientes_df, hospitales_df, fecha_inicio, fecha_fin,
                               tipo_matriz='probabilidad', nombre_archivo=None, subcarpeta="general"):
    df_meta = hospitales_df[['id_hospital', 'Nombre Hospital', 'municipioAbreviado', 'complejidad', 'color']].copy()
    df_meta['color'] = df_meta['color'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
    df_meta_red = df_meta[df_meta['id_hospital'].isin(set(hospitales_df['id_hospital']))].sort_values(['municipioAbreviado', 'complejidad'])

    orden_ids = df_meta_red['id_hospital'].tolist()
    nombres_hospitales = df_meta_red['Nombre Hospital'].tolist()
    municipios_ordenados = df_meta_red['municipioAbreviado'].tolist()

    mask_tras = (traslados_df['fecha_egreso'].between(fecha_inicio, fecha_fin))
    df_t_periodo = traslados_df[mask_tras].copy()
    
    # Usar IDs para la lógica de la matriz
    mask_validos = (df_t_periodo['id_hospital'].isin(orden_ids)) & (df_t_periodo['id_hospital_destino'].isin(orden_ids)) & (df_t_periodo['id_hospital'] != df_t_periodo['id_hospital_destino'])
    df_t_limpio = df_t_periodo[mask_validos].copy()

    df_p_periodo = pacientes_df[pacientes_df['fecha_ingreso'].between(fecha_inicio, fecha_fin)]

    # Totales (usando IDs para indexar)
    total_admisiones = df_p_periodo.groupby('id_hospital').size().reindex(orden_ids, fill_value=0)
    total_derivaciones_hechas = df_t_limpio.groupby('id_hospital').size().reindex(orden_ids, fill_value=0)

    # Matriz (usando IDs como índices y columnas)
    matriz_frecuencias = pd.crosstab(df_t_limpio['id_hospital'], df_t_limpio['id_hospital_destino']).reindex(index=orden_ids, columns=orden_ids, fill_value=0)
    
    # Para el gráfico, renombramos los índices/columnas de la matriz de IDs a Nombres
    id_to_name = dict(zip(orden_ids, nombres_hospitales))
    matriz_frecuencias.index = [id_to_name[i] for i in matriz_frecuencias.index]
    matriz_frecuencias.columns = [id_to_name[i] for i in matriz_frecuencias.columns]

    if tipo_matriz == 'probabilidad':
        matriz_dibujo = matriz_frecuencias.div(matriz_frecuencias.sum(axis=1), axis=0).fillna(0)
        fmt_matriz, label_colorbar, titulo_base = ".2f", 'Probabilidad de Transicion', "Matriz de Transicion (Probabilidades)"
        cmap_matriz = 'Reds' 
        mostrar_cbar = True
    else:
        matriz_dibujo = matriz_frecuencias
        fmt_matriz, label_colorbar, titulo_base = "d", 'Cantidad de Traslados', "Matriz de Frecuencia (Cantidad de Traslados)"
        cmap_matriz = 'Blues'
        mostrar_cbar = False  

    fig = plt.figure(figsize=(16, 12))
    fig.patch.set_facecolor('white')

    # NUEVO: Calculamos la proporción exacta en base a las columnas
    columnas_matriz = len(nombres_hospitales)
    columnas_totales = 2 # 'Admisiones Totales' y 'Derivaciones Hechas'
    
    # Configuramos el ancho para que respete esa proporción exacta
    gs = gridspec.GridSpec(1, 2, width_ratios=[columnas_matriz, columnas_totales], wspace=0.05)

    ax_matriz = plt.subplot(gs[0])
    ax_totales = plt.subplot(gs[1])

    # Matriz principal con square=True para evitar rectángulos
    sns.heatmap(matriz_dibujo, annot=True, cmap=cmap_matriz, fmt=fmt_matriz,
                linewidths=0.5, linecolor='lightgray', 
                cbar=mostrar_cbar, cbar_kws={'label': label_colorbar} if mostrar_cbar else None, 
                square=True,  # <-- NUEVO: Obliga a que cada celda sea un cuadrado perfecto
                ax=ax_matriz)
                
    # Panel lateral de totales
    # Panel lateral de totales
    df_totales_plot = pd.DataFrame(
        {'Admisiones': total_admisiones.values, 'Derivaciones': total_derivaciones_hechas.values},
        index=nombres_hospitales
    )
    
    # Agregamos square=True aquí también
    sns.heatmap(df_totales_plot, annot=True, cmap='Blues', fmt="d",
                linewidths=0.5, linecolor='lightgray', cbar=False, 
                square=True,  # <-- NUEVO: Obliga a ser cuadrados
                ax=ax_totales)

    # Modificación dinámica de los textos (ceros a rayitas y tamaño de fuente)
    if tipo_matriz != 'probabilidad':
        for ax in [ax_matriz, ax_totales]:
            for text in ax.texts:
                if text.get_text() == '0':
                    text.set_text('-')
                    text.set_color('gray')
                    text.set_fontsize(10)
                else:
                    text.set_fontsize(13)
                    text.set_fontweight('bold')

    # Estetica ejes
    ax_matriz.xaxis.tick_top(); ax_matriz.xaxis.set_label_position('top')
    # ax_matriz.set_title(titulo_base, fontsize=18, fontweight='bold', pad=40)
    ax_matriz.set_xlabel("Hospital de Destino", fontsize=18, fontweight='bold', labelpad=15)
    ax_matriz.set_ylabel("Hospital de Origen", fontsize=18, fontweight='bold', labelpad=15)

    ax_totales.xaxis.tick_top(); ax_totales.xaxis.set_label_position('top'); ax_totales.set_ylabel("")

    dict_colores = dict(zip(df_meta_red['Nombre Hospital'], df_meta_red['color']))
    for ax in [ax_matriz, ax_totales]:
        for tick_label in ax.get_xticklabels():
            hosp_name = tick_label.get_text()
            if ax == ax_matriz: tick_label.set_color(dict_colores.get(hosp_name, 'black'))
            tick_label.set_fontweight('bold'); tick_label.set_rotation(45); tick_label.set_ha('left')
            tick_label.set_fontsize(13)

    for tick_label in ax_matriz.get_yticklabels():
        tick_label.set_color(dict_colores.get(tick_label.get_text(), 'black'))
        tick_label.set_fontweight('bold')
        tick_label.set_fontsize(13)

    ax_totales.set_yticklabels([]); ax_totales.tick_params(axis='y', which='both', length=0)

    cambios_municipio = [i for i in range(1, len(municipios_ordenados)) if municipios_ordenados[i] != municipios_ordenados[i - 1]]
    for c in cambios_municipio:
        ax_matriz.axhline(c, color='#333333', lw=2, linestyle='--'); ax_totales.axhline(c, color='#333333', lw=2, linestyle='--')
        ax_matriz.axvline(c, color='#333333', lw=2, linestyle='--')

    plt.tight_layout()
    # plt.figtext(0.99, 0.01, f"Periodo: {fecha_inicio} al {fecha_fin}",
    #             horizontalalignment='right', verticalalignment='bottom',
    #             fontsize=10, color='gray', style='italic')
                
    if nombre_archivo:
        guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
    plt.show()