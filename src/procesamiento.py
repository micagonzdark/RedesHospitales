# Imports y configuraciones basicas
import os
import ast
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import seaborn as sns
from shapely.geometry import LineString, Point

import unicodedata  
import re           

from src.config import *


# ==========================================
# FUNCIONES AUXILIARES (DRY)
# ==========================================
def clasificar_hospital(nombre):
    n = str(nombre).upper()
    if 'MODULO' in n or 'MÓDULO' in n: return 'Desde MÓDULO'
    elif 'UPA' in n: return 'Desde UPA'
    return 'Desde HOSPITAL'

def asignar_color_origen(nombre):
    return COLORES_ORIGEN[clasificar_hospital(nombre)]

def redondear_estetico(valor):
    if valor <= 10: return 10
    if valor <= 100: return int(np.ceil(valor / 10) * 10)
    if valor <= 500: return int(np.ceil(valor / 50) * 50)
    return int(np.ceil(valor / 100) * 100)

def guardar_grafico_alta_calidad(nombre_archivo, bbox="tight"):
    ruta_salida = "results/outputs/red"
    os.makedirs(ruta_salida, exist_ok=True)
    ruta_completa = f"{ruta_salida}/{nombre_archivo}"
    
    plt.savefig(f"{ruta_completa}.png", dpi=300, bbox_inches=bbox, facecolor="white")
    plt.savefig(f"{ruta_completa}.svg", format="svg", bbox_inches=bbox)
    plt.savefig(f"{ruta_completa}.pdf", format="pdf", bbox_inches=bbox)
    print(f"Gráficos exportados en: {ruta_salida}")




def armar_trayectoria(group, dict_complejidad=None):
    if dict_complejidad is None:
        dict_complejidad = {}
        
    ruta_hosp = group['hospital_ingreso'].tolist() + [group['hospital_destino'].iloc[-1]]
    ruta_tipo = group['tipo_ingreso'].tolist() + [group['tipo_destino'].iloc[-1]]
    
    ruta_comp_num = [dict_complejidad.get(h, 0) for h in ruta_hosp] 
    ruta_tipo_num = [MAPA_ESTADOS.get(str(e).lower().strip(), 0) for e in ruta_tipo]

    str_hosp = " -> ".join(ruta_hosp)
    str_tipo = " -> ".join([str(e) for e in ruta_tipo])
    str_comp = " -> ".join([str(c) for c in ruta_comp_num])
    str_tipo_num = " -> ".join([str(e) for e in ruta_tipo_num])

    alertas_array = [dias for dias in group['dias_alerta'].tolist() if dias > 0]
    fecha_inicial = group['fecha_ingreso'].iloc[0]
    
    # --- ACÁ CAPTURAMOS EL MOTIVO FIN DE CASO ---
    # Como es el mismo para todas las filas del paciente, sacamos el primero
    motivo_final = group['motivo_fin_caso'].iloc[0] 
    
    return pd.Series({
        'ruta_hospitales_str': str_hosp,
        'ruta_tipos_str': str_tipo,
        'ruta_tipos_num_str': str_tipo_num,
        'ruta_complejidad_str': str_comp,
        
        'ruta_hospitales_array': ruta_hosp,
        'ruta_tipos_array': ruta_tipo,
        'ruta_tipos_num_array': ruta_tipo_num,
        'ruta_complejidad_array': ruta_comp_num,
        
        'hospital_final': ruta_hosp[-1],
        'tipo_final_txt': ruta_tipo[-1], 
        'tipo_final_num': ruta_tipo_num[-1],
        'complejidad_final': ruta_comp_num[-1],
        
        'motivo_fin_caso': motivo_final, # <-- ¡Y ACÁ LO AGREGAMOS A LAS COLUMNAS!
        
        'cantidad_traslados': len(group),
        'hubo_alerta': len(alertas_array) > 0,
        'dias_alerta_array': alertas_array,
        'fecha_ingreso_trayectoria': fecha_inicial
    })



    
def requiere_ambulancia(row):
    return {row['hospital_ingreso'], row['hospital_destino']} not in PAREJAS_MISMO_PREDIO

def es_upa_o_modulo(nombre):
    n = str(nombre).upper()
    return 'UPA' in n or 'MÓDULO' in n or 'MODULO' in n

def generar_tabla_resumen(pacientes_df, traslados_df, periodos, hospitales_conocidos):
    columnas_tabla = {}
    
    for titulo, inicio, fin in periodos:
        fecha_ini, fecha_fin = pd.to_datetime(inicio), pd.to_datetime(fin)
        total_days = (fecha_fin - fecha_ini).days + 1
        
        # Admisiones
        df_p_per = pacientes_df[pacientes_df['fecha_ingreso'].between(inicio, fin)]
        admissions = len(df_p_per)
        pacientes_admitidos_unicos = df_p_per['paciente_id'].nunique()
        
        # Traslados Válidos (filtrando self-loops y no conocidos, igual que el mapa)
        df_t_bruto = traslados_df[traslados_df['fecha_egreso'].between(inicio, fin)]
        mask_validos = (df_t_bruto['hospital_ingreso'].isin(hospitales_conocidos)) & (df_t_bruto['hospital_destino'].isin(hospitales_conocidos)) & (df_t_bruto['hospital_ingreso'] != df_t_bruto['hospital_destino'])
        df_t_limpio = df_t_bruto[mask_validos]
        
        pesos_rutas = df_t_limpio.groupby(['hospital_ingreso', 'hospital_destino']).size().reset_index(name='peso')
        rutas_dibujables = pesos_rutas[pesos_rutas['peso'] > 2]
        df_t_periodo = df_t_limpio.merge(rutas_dibujables[['hospital_ingreso', 'hospital_destino']], on=['hospital_ingreso', 'hospital_destino'])
        
        total_transfers = len(df_t_periodo)
        df_amb_periodo = df_t_periodo[df_t_periodo['es_ambulancia']]
        amb_transfers = len(df_amb_periodo)
        
        edges_totales = df_t_periodo[['hospital_ingreso', 'hospital_destino']].drop_duplicates().shape[0]
        edges_amb = df_amb_periodo[['hospital_ingreso', 'hospital_destino']].drop_duplicates().shape[0]
        
        df_refuerzo = df_t_periodo[df_t_periodo['hospital_ingreso'].apply(es_upa_o_modulo)]
        
        columnas_tabla[titulo] = {
            'Días totales': f"{total_days}",
            'Admisiones (Prom. diario)': f"{admissions} ({admissions/total_days if total_days>0 else 0:.1f})",
            'Pacientes admitidos': f"{pacientes_admitidos_unicos}",
            'Traslados totales (% admisiones)': f"{total_transfers} ({(total_transfers/admissions*100) if admissions>0 else 0:.1f}%)",
            'Pacientes trasladados': f"{df_t_periodo['paciente_id'].nunique()}",
            'Promedio diario de traslados': f"{total_transfers/total_days if total_days>0 else 0:.1f}",
            'Traslados en ambulancia (% total)': f"{amb_transfers} ({(amb_transfers/total_transfers*100) if total_transfers>0 else 0:.1f}%)",
            'Traslados UPA-Módulos': f"{len(df_refuerzo)}",
            'Rutas UPA-Módulos': f"{df_refuerzo[['hospital_ingreso', 'hospital_destino']].drop_duplicates().shape[0]}",
            'Rutas totales | Ambulancia': f"{edges_totales} | {edges_amb}",
            'Promedio traslados por ruta | Ambulancia': f"{total_transfers/edges_totales if edges_totales>0 else 0:.1f} | {amb_transfers/edges_amb if edges_amb>0 else 0:.1f}"
        }

    orden_filas = ['Días totales', 'Admisiones (Prom. diario)', 'Pacientes admitidos', 'Traslados totales (% admisiones)', 'Pacientes trasladados', 'Promedio diario de traslados', 'Traslados en ambulancia (% total)', 'Traslados UPA-Módulos', 'Rutas UPA-Módulos', 'Rutas totales | Ambulancia', 'Promedio traslados por ruta | Ambulancia']
    return pd.DataFrame(columnas_tabla).loc[orden_filas]

def exportar_tabla_estetica(tabla_df):
    """ Dibuja la tabla con Matplotlib y exporta a LaTeX """
    # 1. LaTeX
    latex_code = tabla_df.reset_index().style.format(escape="latex").hide(axis="index").to_latex(
        buf="results/outputs/red/tabla_resumen.tex", column_format='l' + 'c' * len(tabla_df.columns), hrules=True
    )
    
    # 2. Matplotlib
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.axis('tight'); ax.axis('off')
    tabla_mpl = ax.table(cellText=tabla_df.values, rowLabels=tabla_df.index, colLabels=tabla_df.columns, loc='center', cellLoc='center')
    
    tabla_mpl.auto_set_font_size(False)
    tabla_mpl.set_fontsize(12)
    tabla_mpl.scale(1.2, 2.2)

    for (row, col), cell in tabla_mpl.get_celld().items():
        cell.set_edgecolor('#cccccc')
        if row == 0: cell.set_facecolor('#4c72b0'); cell.set_text_props(weight='bold', color='white')
        elif col == -1: cell.set_facecolor('#e8e8e8'); cell.set_text_props(weight='bold', color='#333333'); cell._loc = 'left'
        else: cell.set_facecolor('#f5f5f5' if row % 2 == 0 else '#ffffff')

    plt.title("Resumen de Admisiones y Traslados por Periodo", fontsize=18, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.show()

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

def limpiar_pacientes(df):
    """
    Pipeline completo de limpieza sobre el dataset de pacientes.
    Mantiene los nombres de columnas originales.
    """
    df_clean = df[df["Id"].astype(str).str.match(r"[A-Za-z0-9]+")].copy()

    # normalizar nombre de hospital
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].apply(limpiar_nombre)

    # convertir fechas
    date_cols = ["Fecha inicio", "Fecha egreso", "Última actualización"]
    for c in date_cols:
        if c in df_clean.columns:
            df_clean[c] = pd.to_datetime(df_clean[c], errors="coerce")

    # duración de internación
    if "Fecha inicio" in df_clean.columns and "Fecha egreso" in df_clean.columns:
        df_clean["Duracion días"] = (df_clean["Fecha egreso"] - df_clean["Fecha inicio"]).dt.days

    # normalizar columnas categóricas (minúsculas, sin espacios extras, nan → NA)
    cols_cat = ["Estado al ingreso", "Último estado", "Tipo al ingreso", "Último tipo", "Sexo", "Motivo"]
    for col in cols_cat:
        if col in df_clean.columns:
            df_clean[col] = (
                df_clean[col]
                .astype(str)
                .str.lower()
                .str.strip()
                .replace("nan", pd.NA)
            )

    # estandarizar tipo de cama: uti-pediatrica → criticas
    for col in ["Tipo al ingreso", "Último tipo"]:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].replace({"uti-pediatrica": "criticas"})

    # clasificar tipo de egreso
    if "Motivo" in df_clean.columns:
        df_clean["tipo_egreso"] = df_clean["Motivo"].apply(clasificar_egreso)
        df_clean["murio"] = df_clean["tipo_egreso"] == "muerte"

    # evolución de complejidad dentro de la internación
    if "Tipo al ingreso" in df_clean.columns and "Último tipo" in df_clean.columns:
        df_clean = clasificar_evolucion(df_clean,
                                        col_ingreso="Tipo al ingreso",
                                        col_final="Último tipo")

    # edad numérica
    if "Edad" in df_clean.columns:
        df_clean["Edad"] = pd.to_numeric(df_clean["Edad"], errors="coerce")

    return df_clean

def clasificar_egreso(x):
    """
    Clasifica el motivo de egreso en categorías simples.
    Retorna: 'muerte', 'alta', 'traslado', 'otro', 'desconocido'
    """
    if pd.isna(x):
        return "desconocido"
    x = str(x).lower().strip()
    if "muert" in x or "fallec" in x:
        return "muerte"
    if "alta" in x:
        return "alta"
    if "traslad" in x:
        return "traslado"
    if x in ["otro", "anulado"]:
        return "otro"
    return "otro"

def clasificar_evolucion(df, col_ingreso="Tipo al ingreso", col_final="Último tipo"):
    """
    Agrega columnas de nivel numérico de complejidad y evolución del paciente.
    evolucion > 0 → empeoró | evolucion < 0 → mejoró | evolucion = 0 → igual
    """
    orden = {"generales": 1, "intermedias": 2, "criticas": 3}
    df["nivel_ingreso"] = df[col_ingreso].map(orden)
    df["nivel_final"] = df[col_final].map(orden)
    df["evolucion"] = df["nivel_final"] - df["nivel_ingreso"]
    return df

def check_post_limpieza(df):
    """
    Imprime un resumen rápido del dataset después de limpiar.
    Útil para correr al final de la celda de carga en los notebooks.
    """
    print("--- CHEQUEO POST-LIMPIEZA ---")
    print(f"Filas:              {len(df)}")
    print(f"Pacientes únicos:   {df['Id'].nunique()}")
    print(f"Hospitales únicos:  {df['Nombre Hospital'].nunique()}")
    print(f"Valores nulos (Fecha inicio): {df['Fecha inicio'].isna().sum()}")
    print(f"Valores nulos (Fecha egreso): {df['Fecha egreso'].isna().sum()}")
    if "tipo_egreso" in df.columns:
        print("\nDistribución tipo_egreso:")
        print(df["tipo_egreso"].value_counts())
    if "evolucion" in df.columns:
        print("\nDistribución evolución:")
        print(df["evolucion"].value_counts())

def limpiar_coordenadas(hosp_coords):
    df_clean = hosp_coords.copy()
    if "Latitud" in df_clean.columns:
        df_clean["Latitud"] = df_clean["Latitud"].astype(str).str.replace(",", ".").astype(float)
    if "Longitud" in df_clean.columns:
        df_clean["Longitud"] = df_clean["Longitud"].astype(str).str.replace(",", ".").astype(float)
    if "Nombre Hospital" in df_clean.columns:
        df_clean["Nombre Hospital"] = df_clean["Nombre Hospital"].apply(limpiar_nombre)
    return df_clean

def es_upa(nombre):
    """True si es UPA (el nombre comienza con 'UPA')"""
    return nombre.upper().startswith("UPA")

def ajustar_coordenadas_upa(coords_df):
    """Desplaza levemente UPA para evitar superposición en mapas"""
    coords_mod = coords_df.copy()
    mask_upa = coords_mod["Nombre Hospital"].str.upper().str.contains("UPA")
    coords_mod.loc[mask_upa, "Longitud"] -= 0.01
    return coords_mod

def reconstruir_traslados(df, max_horas_interno=24, filtrar_errores=True):
    """
    Reconstruye traslados entre hospitales a partir del dataset de pacientes.

    Parámetros
    ----------
    max_horas_interno : int
        Diferencia máxima en horas para considerar un traslado casi simultáneo
        (posible traslado interno). Default: 24.
    filtrar_errores : bool
        Si True (default), descarta traslados con errores graves de fechas
        (gravedad_error == 2). Los posibles internos (gravedad 1) se mantienen.

    Gravedad del error:
        0 → todo ok
        1 → posible traslado interno / casi simultáneo (diferencia < max_horas_interno)
        2 → error grave de fechas (fechas negativas graves)
    """
    df = df.sort_values(["Id", "Fecha inicio"]).copy()

    # hospital y fecha del siguiente registro del mismo paciente
    df["Hospital siguiente"] = df.groupby("Id")["Nombre Hospital"].shift(-1)
    df["Fecha ingreso siguiente"] = df.groupby("Id")["Fecha inicio"].shift(-1)

    # días entre egreso del hospital actual e ingreso al siguiente
    df["dias_entre_hospitales"] = (df["Fecha ingreso siguiente"] - df["Fecha egreso"]).dt.days

    # usar tipo_egreso si está disponible, sino buscar en Motivo directamente
    if "tipo_egreso" in df.columns:
        df["es_traslado"] = df["tipo_egreso"] == "traslado"
    else:
        df["es_traslado"] = df["Motivo"].str.contains("traslad", case=False, na=False)

    # filtrar traslados válidos: marcados como traslado, con destino distinto al origen
    traslados = df[
        (df["es_traslado"]) &
        (df["Hospital siguiente"].notna()) &
        (df["Hospital siguiente"] != df["Nombre Hospital"])
    ].copy()

    # detectar errores de fechas
    traslados["error_fecha"] = traslados["dias_entre_hospitales"] < 0

    delta_horas = (
        traslados["Fecha ingreso siguiente"] - traslados["Fecha egreso"]
    ).dt.total_seconds() / 3600
    traslados["posible_interno"] = (
        traslados["error_fecha"]
    ) & (
        delta_horas.abs() <= max_horas_interno
    )

    def calcular_gravedad(row):
        if row["error_fecha"]:
            return 1 if row["posible_interno"] else 2
        return 0

    traslados["gravedad_error"] = traslados.apply(calcular_gravedad, axis=1)

    # descartar errores graves por defecto
    if filtrar_errores:
        n_antes = len(traslados)
        traslados = traslados[traslados["gravedad_error"] < 2].copy()
        n_descartados = n_antes - len(traslados)
        if n_descartados > 0:
            print(f"[reconstruir_traslados] Se descartaron {n_descartados} traslados con error grave de fechas.")

    return traslados

def identificar_episodios(df, col_id="Id", col_fecha="Fecha inicio", col_motivo="Motivo", umbral_alerta_dias=2):
    """
    Identifica episodios de internación basados en el motivo de egreso.
    Un nuevo episodio comienza si el registro previo terminó en alta domiciliaria o muerte.
    
    Agrega:
        - episodio_id: ID incremental por paciente
        - alerta_gap: True si pasaron más de `umbral_alerta_dias` desde el egreso previo
    """
    df = df.sort_values([col_id, col_fecha]).copy()
    
    # 1. Delta de tiempo con el registro anterior
    df["_delta"] = df.groupby(col_id)[col_fecha].diff()
    
    # 2. Motivo del egreso anterior
    df["_motivo_previo"] = df.groupby(col_id)[col_motivo].shift(1)
    
    # 3. Identificar fin de episodio (Alta o Muerte)
    # Valores típicos configurados en limpiar_pacientes: 'alta-domiciliaria', 'muerte'
    fin_episodio = df["_motivo_previo"].isin(["alta-domiciliaria", "muerte", "alta", "muerte"])
    
    # 4. Iniciar nuevo episodio si el anterior finalizó o si es el primer registro (delta NaT)
    df["nuevo_episodio"] = fin_episodio | df["_delta"].isna()
    
    # 5. Numerar episodios
    df["episodio_id"] = df.groupby(col_id)["nuevo_episodio"].cumsum()
    
    # 6. Alerta de gap temporal (sin romper el episodio)
    df["alerta_gap"] = df["_delta"].dt.days > umbral_alerta_dias
    
    # Limpiar columnas auxiliares
    df = df.drop(columns=["_delta", "_motivo_previo"])
    
    return df

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

def resumen_traslados(df, col_hospital="Nombre Hospital", imprimir=True):
    total_traslados = len(df)
    hospitales_unicos = df[col_hospital].nunique()
    if imprimir:
        print(f"Total de traslados: {total_traslados}")
        print(f"Cantidad de hospitales únicos: {hospitales_unicos}")
    return {"total_traslados": total_traslados, "hospitales_unicos": hospitales_unicos}

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

def agrupar_trayectorias_largas(ruta):
    """
    Acorta o agrupa rutas largas a 'Más de 3 hospitales (4+)',
    útil para análisis y top_n de trayectorias.
    """
    import pandas as pd
    if pd.isna(ruta):
        return ruta
    # Contamos cuántos nodos (hospitales) tiene separando por la flecha
    nodos = str(ruta).split('->')
    if len(nodos) >= 4:
        return 'Más de 3 hospitales (4+)'
    return str(ruta).strip()




def obtener_nivel_inicial(row):
    """
    Identificar nivel de complejidad inicial (para el punto 12)
    Si es trasladado, tomamos el primer elemento del array. Si es estacionario, su nivel único.
    """
    if row['es_trasladado']:
        # Buscamos en trayectorias el array original
        val = trayectorias.loc[trayectorias['paciente_id'] == row['paciente_id'], 'ruta_complejidad_array'].values
        if len(val) > 0 and isinstance(val[0], list) and len(val[0]) > 0:
            return val[0][0]
    # Si no es trasladado o no hay array, intentamos usar el dato de hospital_origen cruzado antes
    return row.get('complejidad', np.nan)



# COLORES_MOTIVOS se define en src/config.py y se importa via 'from src.config import *'.
# La definicion canonica esta en config.py para garantizar coherencia en todo el proyecto.



def calcular_matrices_transicion(rutas):
    from collections import Counter
    import pandas as pd
    transiciones = Counter()
    niveles_unicos = set()
    for ruta in rutas.dropna():
        nodos = [n.strip() for n in str(ruta).split('->')]
        niveles_unicos.update(nodos)
        for i in range(len(nodos)-1):
            transiciones[(nodos[i], nodos[i+1])] += 1
    niveles = sorted(list(niveles_unicos))
    df_cantidades = pd.DataFrame(0, index=niveles, columns=niveles)
    for (origen, destino), cantidad in transiciones.items():
        df_cantidades.at[origen, destino] = cantidad
    df_probabilidades = df_cantidades.div(df_cantidades.sum(axis=1), axis=0).fillna(0)
    return df_cantidades, df_probabilidades, transiciones

def extraer_origen_destino_final(valor):
    import ast
    if isinstance(valor, str) and valor.startswith('['):
        try:
            lista = ast.literal_eval(valor)
        except:
            return None
    elif isinstance(valor, list):
        lista = valor
    else:
        return None
    if len(lista) > 0:
        return f"{lista[0]} → {lista[-1]}"
    return None

def asignar_periodo(fecha, periodos):
    import pandas as pd
    if pd.isna(fecha):
        return 'Sin Dato/Otro'
    fecha_str = str(fecha)[:10] 
    for nombre, inicio, fin in periodos:
        if inicio <= fecha_str <= fin:
            return nombre
    return 'Fuera de rango'

