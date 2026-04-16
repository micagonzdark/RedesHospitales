import pandas as pd
import numpy as np
import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib import cm, colors
import seaborn as sns
import geopandas as gpd
from shapely.geometry import LineString, Point
import contextily as ctx
from src.config import *
from src.procesamiento import *
from pathlib import Path




# Funciones de visualizacion
###########################################

def aplicar_escala_visual(valor, max_valor, v_min, v_max, tipo='sqrt', min_valor=0):
    if max_valor == min_valor or valor == 0: 
        return v_min if valor > 0 else 0
    
    # Respetamos tu normalización original Min-Max Lineal para la escala cuadrática
    if min_valor > 0 and tipo == 'cuadratica':
        x = (valor - min_valor) / (max_valor - min_valor)
    else:
        x = valor / max_valor
        
    escala = np.sqrt(x) if tipo == 'sqrt' else (x**2 if tipo == 'cuadratica' else x)
    return v_min + (escala * (v_max - v_min))
def dibujar_grafo_nx(ax, G, posiciones, max_traslados, max_ingresos, cfg):
    lista_nodos = list(G.nodes())
    tamanos_reales = [G.nodes[n]['size'] for n in lista_nodos]

    # 1. DIBUJAR NODOS
    for forma in set(nx.get_node_attributes(G, 'shape').values()):
        nodelist = [n for n in lista_nodos if G.nodes[n]['shape'] == forma]
        if not nodelist: continue
        
        # FIX: Pasamos zorder como un parámetro de dibujo de Matplotlib
        nx.draw_networkx_nodes(
            G, posiciones, nodelist=nodelist, ax=ax, node_shape=forma, 
            node_color=[G.nodes[n]['color'] for n in nodelist], 
            node_size=[G.nodes[n]['size'] for n in nodelist], 
            alpha=[G.nodes[n]['alpha'] for n in nodelist], 
            edgecolors='white', linewidths=cfg.get('lw_nodos', 0.5),
            label=None  # A veces ayuda a limpiar
        ).set_zorder(4) # <-- Esta es la forma segura de asignar zorder en NetworkX

    # 2. DIBUJAR ARISTAS
    for u, v, data in G.edges(data=True):
        peso = data['weight']
        grosor = aplicar_escala_visual(peso, max_traslados, cfg['min_grosor'], cfg['max_grosor'], cfg.get('escala_arista', 'sqrt'))
        
        if cfg.get('color_por_origen'):
            color_flecha = asignar_color_origen(u)
        elif cfg.get('aristas_negras'):
            color_flecha = 'black'
        else:
            intensidad = 0.8 - 0.6 * (peso / max_traslados) if max_traslados > 0 else 0.2
            color_flecha = (intensidad, intensidad, intensidad)
        
        rad_dinamico = ((sum(ord(c) for c in u + v) % 90 - 35) / 100.0)
        if abs(rad_dinamico) < 0.12: rad_dinamico = 0.25 if rad_dinamico >= 0 else -0.25

        # FIX: Asignamos zorder usando el objeto retornado
        lineas = nx.draw_networkx_edges(
            G, posiciones, edgelist=[(u, v)], ax=ax, width=grosor, edge_color=[color_flecha], 
            alpha=cfg.get('alpha_arista', 0.5), arrowstyle='-|>', arrowsize=cfg.get('arrow_size', 15), 
            connectionstyle=f"arc3,rad={rad_dinamico}", 
            nodelist=lista_nodos, node_size=tamanos_reales
        )
        if lineas:
            for l in lineas:
                l.set_zorder(3)

    # 3. DIBUJAR ETIQUETAS
    # Las claves k son IDs (H01, H02...), obtenemos el nombre desde los atributos del nodo
    labels = {
        k: str(G.nodes[k].get('label', k)).replace('Módulo Hospitalario', 'MÓDULO').replace('Modulo Hospitalario', 'MÓDULO') 
        for k in lista_nodos
    }
    pos_labels = {k: (v[0], v[1] + cfg.get('lbl_offset', 0.005)) for k, v in posiciones.items()} 
    
    bbox_cfg = dict(
        facecolor='white', 
        alpha=cfg.get('lbl_bbox_alpha', 0.7), 
        edgecolor='none', 
        boxstyle='round,pad=0.2'
    ) if cfg.get('lbl_bbox') else None

    # En etiquetas, zorder suele funcionar, pero lo aseguramos igual
    textos = nx.draw_networkx_labels(
        G, pos_labels, labels=labels, ax=ax, 
        font_size=cfg.get('lbl_size', 10), 
        font_color=cfg.get('lbl_color', '#333333'), 
        font_weight=cfg.get('lbl_weight', 'normal'),
        bbox=bbox_cfg
    )
    if textos:
        for t in textos.values():
            t.set_zorder(5)
    
    ax.axis('off')
    
def generar_leyendas(ax, v_max_raw, i_min_raw, i_max_raw, max_traslados, max_ingresos, cfg, posiciones_bbox):
    """ Creador maestro de leyendas con redondeo estricto e igualación visual """
    
    # REDONDEO OBLIGATORIO para que la leyenda siempre sea limpia
    v_max_g = redondear_estetico(v_max_raw)
    v_min_g = UMBRAL_MIN_TRASLADOS_GRAFICO
    v_med_g = redondear_estetico(v_max_g / 2)
    
    i_max_g = redondear_estetico(i_max_raw)
    # Respetamos el comportamiento duro del mapa global (min = 50) si la config lo pide
    i_min_g = 50 if cfg.get('forzar_i_min_50') else redondear_estetico(i_min_raw)
    i_med_g = redondear_estetico(i_max_g / 2) if cfg.get('forzar_i_min_50') else redondear_estetico((i_max_g + i_min_g) / 2)
    
    # Helpers: calculan el tamaño usando el valor REDONDEADO contra el MÁXIMO REAL
    f_grosor = lambda p: aplicar_escala_visual(p, max_traslados, cfg['min_grosor'], cfg['max_grosor'], cfg.get('escala_arista', 'sqrt'))
    f_nodo = lambda i: np.sqrt(aplicar_escala_visual(i, max_ingresos, cfg['min_tamano'], cfg['max_tamano'], cfg.get('escala_nodo', 'sqrt'), cfg.get('min_ingresos_real', 0)))

    # === EL ARREGLO DE COLOR ===
    # Atamos el color y la transparencia de la leyenda a lo que diga la configuración del grafo
    color_linea = 'black' if cfg.get('aristas_negras') else 'grey'
    alpha_linea = cfg.get('alpha_arista', 0.5)

    # === CORRECCIÓN EN generar_leyendas ===

    # 1. Definimos los valores que queremos mostrar en la leyenda
    v_min_leg = UMBRAL_MIN_TRASLADOS_GRAFICO 
    v_med_leg = 75
    v_max_leg = v_max_g

    proxies_vol = [
        mlines.Line2D([], [], color=color_linea, alpha=alpha_linea, 
                    linewidth=f_grosor(v_min_leg), label=f'{int(v_min_leg)}'),
        
        mlines.Line2D([], [], color=color_linea, alpha=alpha_linea, 
                    linewidth=f_grosor(v_med_leg), label=f'{int(v_med_leg)}'),
        
        mlines.Line2D([], [], color=color_linea, alpha=alpha_linea, 
                    linewidth=f_grosor(v_max_leg), label=f'{int(v_max_leg)}')
    ]
    
    proxies_col = [mlines.Line2D([], [], color=v, lw=3, label=k) for k, v in COLORES_ORIGEN.items()] if cfg.get('color_por_origen') else []
    
    # Los nodos los dejamos en gris oscuro (#444444) que es el estándar neutro para leyendas de tamaño
    proxies_nod = [
        mlines.Line2D([], [], color='white', marker='o', markerfacecolor='#444444', markersize=f_nodo(val), label=f'{int(val)}') 
        for val in [i_min_g, i_med_g, i_max_g]
    ]

    # 1. Calculamos el tamaño del círculo más grande para empujar los márgenes
    tamano_max_marcador = f_nodo(i_max_g)
    
    # 2. Espaciados dinámicos
    lbl_spc = max(1.5, tamano_max_marcador / 20) if cfg.get('leg_dynamic_spc') else 2.0
    h_height = max(2.0, tamano_max_marcador / 15) if cfg.get('leg_dynamic_spc') else 2.0

    # 3. DICCIONARIO MAESTRO DE ESTILO: Obliga a todas las leyendas a verse igual
    estilo_base = {
        'frameon': True,
        'title_fontsize': cfg.get('leg_title_sz', 14),
        'fontsize': cfg.get('leg_lbl_sz', 12),
        'borderpad': 1.8,             
        'labelspacing': lbl_spc,      
        'handletextpad': 1.5,         
        'handleheight': h_height      
    }

    # 4. Renderizamos (SIN duplicados y CON validación None)
    if posiciones_bbox[0] is not None:
        leg1 = ax.legend(handles=proxies_vol, title="Traslados", loc='upper left', 
                         bbox_to_anchor=posiciones_bbox[0], **estilo_base)
        ax.add_artist(leg1)
    
    if proxies_col and len(posiciones_bbox) > 1 and posiciones_bbox[1] is not None:
        leg2 = ax.legend(handles=proxies_col, title="Origen", loc='upper left', 
                         bbox_to_anchor=posiciones_bbox[1], **estilo_base)
        ax.add_artist(leg2)
    
    if posiciones_bbox[-1] is not None:
        ax.legend(handles=proxies_nod, title="Ingresos", loc='upper left', 
                  bbox_to_anchor=posiciones_bbox[-1], **estilo_base)


def agregar_etiquetas_grafico(ax, tipo='bar'):
    """ Agrega los números encima de las barras o los puntos """
    max_y = ax.get_ylim()[1]
    
    if tipo == 'bar' or tipo == 'stack':
        max_y_per_x = {}
        for p in ax.patches:
            h = p.get_height()
            if h > 0:
                x_c = p.get_x() + p.get_width() / 2.
                y_t = p.get_y() + h
                max_y_per_x[x_c] = max(max_y_per_x.get(x_c, 0), y_t)
        
        for x, top in max_y_per_x.items():
            if top >= (max_y * 0.02):
                ax.text(x, top * 1.1, f'{int(top)}', ha="center", va="bottom", fontsize=10, fontweight='bold', color='#333333')
    
    elif tipo == 'scatter':
        for c in ax.collections:
            for x, y in c.get_offsets():
                if y > 0: ax.text(x, y * 1.25, f'{int(y)}', ha="center", va="bottom", fontsize=10, fontweight='bold')
    
    ax.set_ylim(0.5 if ax.get_yscale() == 'log' else 0, max_y * 5 if ax.get_yscale() == 'log' else max_y * 1.1)







# Funciones de Anotación Originales (Intactas)
def agregar_valores_scatter(ax, x_vals, y_vals):
    for x, y in zip(x_vals, y_vals):
        if y > 0: ax.text(x, y * 1.25, f'{int(y)}', ha="center", va="bottom", fontsize=10, fontweight='bold', color='#2b2b2b')
    ax.set_ylim(0.5, (max(y_vals) if len(y_vals) > 0 else 1) * 5)

def agregar_valores_barras(ax):
    for p in ax.patches:
        h = p.get_height()
        if h > 0: ax.text(p.get_x() + p.get_width() / 2., (p.get_y() + h) * 1.2, f'{int(h)}', ha="center", va="bottom", fontsize=10, fontweight='bold', color='#2b2b2b')
    ax.set_ylim(0.5, ax.get_ylim()[1] * 5)

def agregar_valores_totales(ax):
    max_y_per_x = {}
    for p in ax.patches:
        h = p.get_height()
        if h > 0:
            x_c, y_t = p.get_x() + p.get_width() / 2., p.get_y() + h
            if x_c not in max_y_per_x or y_t > max_y_per_x[x_c]: max_y_per_x[x_c] = y_t
    
    max_y_axis = ax.get_ylim()[1]
    for x_c, total_height in max_y_per_x.items():
        if total_height >= (max_y_axis * 0.02):
            ax.text(x_c, total_height + (max_y_axis * 0.01), f'{int(total_height)}', ha="center", va="bottom", fontsize=9, fontweight='bold', color='#333333')
    ax.set_ylim(0, max_y_axis * 1.1)

# Fíjate que agregamos promedios_traslados=None al final de los paréntesis
def graficar_traslados_paciente(df_stats, df_pacientes, es_global=False, promedios_traslados=None):
    
    # Acá le decimos que si no le pasamos nada, cree un diccionario vacío
    if promedios_traslados is None:
        promedios_traslados = {}
        
    if es_global:
        fig, axes = plt.subplots(figsize=(14, 8)); axes = [axes]
        iteracion = [("Global", None, None)]
    else:
        # REQ 7: sharex=True y sharey=True para mantener todos en la misma escala
        fig, axes = plt.subplots(2, 2, figsize=(18, 12), sharex=True, sharey=True)
        fig.suptitle("Número de traslados por paciente por Periodo", fontsize=22, fontweight='bold', y=0.98)
        axes = axes.flatten()
        iteracion = PERIODOS

    fig.patch.set_facecolor('white')

    for ax, (titulo, inicio, fin) in zip(axes, iteracion):
        mask_p = df_pacientes['fecha_ingreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_pacientes.index)
        mask_t = df_stats['fecha_egreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_stats.index)
        
        df_t_per, df_p_per = df_stats[mask_t], df_pacientes[mask_p]
        cero_traslados = len(set(df_p_per['paciente_id']) - set(df_t_per['paciente_id']))
        
        # REQ 5: Calcular promedio total de traslados por paciente (incluyendo ceros)
        total_pacientes = df_p_per['paciente_id'].nunique()
        total_traslados = len(df_t_per)
        promedio = total_traslados / total_pacientes if total_pacientes > 0 else 0
        promedios_traslados["Global" if es_global else titulo] = promedio
        
        if not df_p_per.empty: # Evaluamos df_p_per para que grafique incluso si solo hay pacientes con 0
            conteo = df_t_per.groupby('paciente_id').size().value_counts()
            
            # REQ 1: Agregar pacientes con 0 traslados a la serie de datos
            if cero_traslados > 0:
                conteo.loc[0] = cero_traslados
            
            # Ordenamos el índice (0, 1, 2, 3...) para que la línea se dibuje bien
            conteo = conteo.sort_index()

            # REQ 2: Curva uniendo los puntos (se sacó el ax.vlines de las barras)
            ax.plot(conteo.index, conteo.values, color='#4c72b0', linestyle='-', linewidth=2.5, alpha=0.6, zorder=2)
            # Mantenemos el scatter de los puntos
            sns.scatterplot(x=conteo.index, y=conteo.values, color='#4c72b0', s=150 if not es_global else 250, edgecolor='black', linewidth=1.5, ax=ax, zorder=3)
            
            ax.set_yscale('log')
            agregar_valores_scatter(ax, conteo.index, conteo.values)
        
        # REQ 3 y REQ 6: Sin "(Log)" y con valores de ejes más grandes
        ax.set_title(titulo, fontsize=16)
        ax.set_xlabel("Cantidad de traslados", fontsize=14)
        ax.set_ylabel("Cantidad de pacientes", fontsize=14)
        ax.tick_params(axis='both', which='major', labelsize=12)
        
        # REQ 4: Sacar la cuadrícula
        ax.grid(False)
        
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        # REQ 1: Se eliminó la leyenda `ax.legend(...)` que mostraba los 0 traslados apartados

    plt.tight_layout(rect=[0, 0, 1, 0.96 if not es_global else 1], pad=3.0)
    plt.show()

def graficar_tiempo_sistema(df_todas, df_traslados, es_global=False):
    if es_global:
        # REQ 3: sharey=True y sharex=True para asegurar la misma escala en ambos gráficos
        fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=True, sharex=True)
        fig.suptitle("Tiempo total en el sistema: Global vs Trasladados", fontsize=22, fontweight='bold', y=1.02)
        iteraciones = [("Global", None, None, axes)]
    else:
        # REQ 4: Versión por periodo (Cuadrícula dinámica de N filas x 2 columnas)
        filas = len(PERIODOS)
        fig, axes = plt.subplots(filas, 2, figsize=(16, 5 * filas), sharey=True, sharex=True)
        fig.suptitle("Tiempo total en el sistema por Periodo", fontsize=22, fontweight='bold', y=0.98)
        iteraciones = [(titulo, inicio, fin, axes[i]) for i, (titulo, inicio, fin) in enumerate(PERIODOS)]

    fig.patch.set_facecolor('white')

    for titulo_per, inicio, fin, axes_row in iteraciones:
        # Filtrar datos por periodo usando la fecha de ingreso
        mask_per = df_todas['ingreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_todas.index)
        df_todas_per = df_todas[mask_per]
        # Nos quedamos con los trasladados que corresponden a ese subset temporal
        df_traslados_per = df_traslados[df_traslados.index.isin(df_todas_per.index)]

        for ax, subtitulo, df_subset, color in zip(axes_row, ["Todos los pacientes", "Solo Trasladados"], [df_todas_per, df_traslados_per], ['#4c72b0', '#1a9850']):
            if not df_subset.empty:
                sns.histplot(df_subset['dias_en_sistema'], bins=bins_5dias, color=color, ax=ax, edgecolor='black', alpha=0.8)
                
                # REQ 2: Se mantiene explícitamente la escala logarítmica
                ax.set_yscale('log')
                agregar_valores_barras(ax)
                
                mediana = df_subset['dias_en_sistema'].median()
                if not pd.isna(mediana):
                    ax.axvline(mediana, color='red', linestyle='dashed', linewidth=2)
                    # REQ 1: Se eliminó la palabra "Mediana:", quedando solo "X días"
                    ax.text(mediana + 1, ax.get_ylim()[1]*0.5, f'{int(mediana)} días', color='red', fontweight='bold', fontsize=12)
            
            # Formato general de ejes y títulos estandarizado
            titulo_final = f"{titulo_per} - {subtitulo}" if not es_global else subtitulo
            ax.set_title(titulo_final, fontsize=16)
            ax.set_xlabel("Días totales", fontsize=14)
            ax.set_ylabel("Cantidad de personas", fontsize=14) # Eliminado "(Log)" del texto
            ax.set_xlim(0, max_plot)
            ax.set_xticks(np.arange(0, max_plot + 5, 10))
            ax.tick_params(axis='both', which='major', labelsize=12)
            ax.grid(False)

    plt.tight_layout(rect=[0, 0, 1, 0.96 if not es_global else 1], pad=3.0)
    plt.show()

def graficar_tiempo_traslado(df_mov, es_global=False):
    if es_global:
        fig, axes = plt.subplots(figsize=(14, 8)); axes = [axes]
        iteracion = [("Tiempo hasta traslado (Estadía en nodo origen) - Global", None, None)]
    else:
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle("Tiempo hasta traslado (Estadía en nodo origen) por Periodo", fontsize=22, fontweight='bold', y=0.98)
        axes = axes.flatten()
        iteracion = PERIODOS

    fig.patch.set_facecolor('white')

    for ax, (titulo, inicio, fin) in zip(axes, iteracion):
        mask_m = df_mov['fecha_egreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_mov.index)
        df_m_per = df_mov[mask_m]
        
        if not df_m_per.empty:
            sns.histplot(data=df_m_per, x='dias_antes_traslado', hue='tipo_hospital', palette=COLORES_ORIGEN, multiple='stack', bins=bins_mov_5, ax=ax, edgecolor='white')
            agregar_valores_totales(ax)
            
        ax.set(title=titulo, xlabel="Días de estadía antes de ser trasladado", ylabel="Cantidad de traslados", xlim=(0, max_plot_nodo))

    plt.tight_layout(rect=[0, 0, 1, 0.95], pad=3.0)
    plt.show()


def get_linewidth(weight):
    """Calcula grosor de línea proporcional al peso"""
    return np.log1p(weight) * 1.5

def draw_arrow(ax, line, lw=1, color="blue"):
    """Dibuja flecha sobre LineString en matplotlib"""
    x, y = line.xy
    ax.annotate(
        "",
        xy=(x[-1], y[-1]),
        xytext=(x[-2], y[-2]),
        arrowprops=dict(arrowstyle="->", color=color, lw=lw)
    )

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

def sankey_pacientes(df):
    df_pairs = df[df["id_hospital_destino"].notna()][["id_hospital", "id_hospital_destino", "Nombre Hospital", "Nombre Hospital siguiente"]]
    df_pairs = df_pairs.groupby(["id_hospital", "id_hospital_destino", "Nombre Hospital", "Nombre Hospital siguiente"]).size().reset_index(name="count")
    
    # Usar nombres para los labels de los nodos del Sankey
    labels = list(pd.concat([df_pairs["Nombre Hospital"], df_pairs["Nombre Hospital siguiente"]]).unique())
    label_map = {label:i for i,label in enumerate(labels)}
    
    source = df_pairs["Nombre Hospital"].map(label_map)
    target = df_pairs["Nombre Hospital siguiente"].map(label_map)
    value = df_pairs["count"]
    
    fig = go.Figure(data=[go.Sankey(
        node = {"label": labels},
        link = {"source": source, "target": target, "value": value}
    )])
    fig.update_layout(title_text="Flujo de pacientes con ≥3 traslados", font_size=10)
    fig.show()

def top_flujos_hospitales(traslados, top_n=10, graficar=True, figsize=(10,5)):
    flujos = traslados.groupby(["id_hospital", "id_hospital_destino", "Nombre Hospital","Nombre Hospital siguiente"]).size().reset_index(name="cantidad").sort_values("cantidad", ascending=False)
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

def get_curvature(G, u, v, base_curva=0.2):
    if G.has_edge(v, u):
        return base_curva if str(u) < str(v) else -base_curva
    return base_curva

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

def colapsar_grafo(G):
    import networkx as nx

    if isinstance(G, nx.MultiDiGraph) or isinstance(G, nx.MultiGraph):
        H = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            w = data.get("weight", 1)
            if H.has_edge(u, v):
                H[u][v]["weight"] += w
            else:
                H.add_edge(u, v, weight=w)
        return H
    return G

def get_edge_style(weights):
    weights = [max(w, 1) for w in weights]

    norm = colors.LogNorm(vmin=min(weights), vmax=max(weights))
    cmap = cm.get_cmap("plasma")

    def get_color(w):
        return cmap(norm(max(w, 1)))

    def get_width(w):
        return 1 + np.log1p(max(w, 1))

    return get_color, get_width, norm, cmap

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

def plot_edges_geo(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    G = colapsar_grafo(G)

    fig, ax = plt.subplots(figsize=(12,12))

    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"])
    )

    gdf_nodes.plot(ax=ax, color="red", markersize=50, zorder=2)

    geom_dict = {row["id_hospital"]: row.geometry for _, row in gdf_nodes.iterrows()}
    edges, _ = construir_gdf_edges(G, geom_dict, 0.15)

    weights = [e["weight"] for e in edges]
    get_color, get_width, norm, cmap = get_edge_style(weights)

    for e in edges:
        line = e["geometry"]
        w = e["weight"]

        x, y = line.xy
        ax.plot(x, y,
                linewidth=get_width(w),
                color=get_color(w),
                alpha=0.7)

        draw_arrow(ax, line, get_width(w))

        if mostrar_peso:
            xm, ym = line.interpolate(0.5, normalized=True).coords[0]
            ax.text(xm, ym, str(w), fontsize=8, color=get_color(w))

    if mostrar_nombres:
        for _, row in gdf_nodes.iterrows():
            ax.text(row.geometry.x, row.geometry.y, row["Nombre Hospital"], fontsize=8)

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    plt.colorbar(sm, ax=ax)

    return fig, ax

def plot_red_con_mapa(G, hosp_coords, mostrar_nombres=True, mostrar_peso=True):
    G = colapsar_grafo(G)

    gdf_nodes = gpd.GeoDataFrame(
        hosp_coords,
        geometry=gpd.points_from_xy(hosp_coords["Longitud"], hosp_coords["Latitud"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    geom_dict = dict(zip(gdf_nodes["id_hospital"], gdf_nodes.geometry))
    edges, _ = construir_gdf_edges(G, geom_dict, 100)  # 👈 más chico

    weights = [e["weight"] for e in edges]
    get_color, get_width, norm, cmap = get_edge_style(weights)

    fig, ax = plt.subplots(figsize=(10,10))

    # -----------------------
    # dibujar aristas
    # -----------------------
    for e in edges:
        line = e["geometry"]
        w = e["weight"]

        x, y = line.xy
        ax.plot(x, y,
                linewidth=get_width(w),
                color=get_color(w),
                alpha=0.7)

        draw_arrow(ax, line, get_width(w))

        if mostrar_peso:
            xm, ym = line.interpolate(0.5, normalized=True).coords[0]
            ax.text(xm, ym, str(w), fontsize=8, color=get_color(w))

    # -----------------------
    # nodos
    # -----------------------
    gdf_nodes.plot(ax=ax, color="red", markersize=40, zorder=2)

    if mostrar_nombres:
        for _, row in gdf_nodes.iterrows():
            ax.text(row.geometry.x, row.geometry.y, row["Nombre Hospital"], fontsize=8)

    # -----------------------
    # 🔥 LIMITES BIEN HECHOS
    # -----------------------
    xs = gdf_nodes.geometry.x
    ys = gdf_nodes.geometry.y

    xmin, xmax = np.percentile(xs, [1, 99])
    ymin, ymax = np.percentile(ys, [1, 99])

    # padding (clave para que no quede apretado)
    pad_x = (xmax - xmin) * 0.05
    pad_y = (ymax - ymin) * 0.05

    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)

    # -----------------------
    # basemap
    # -----------------------
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

    ax.axis("off")

    # -----------------------
    # colorbar
    # -----------------------
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    plt.colorbar(sm, ax=ax)

    return fig, ax

def plot_red_sobre_amba(gdf_edges, gdf_nodes, municipios_amba, mostrar_nombres=True, mostrar_peso=True):
    municipios = municipios_amba.to_crs(epsg=3857)
    hospitales = gdf_nodes.to_crs(epsg=3857)
    edges = gdf_edges.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(12,12))
    municipios.plot(ax=ax, alpha=0.3, edgecolor="black", color="lightgrey")

    if not edges.empty:
        norm = colors.LogNorm(vmin=max(edges["weight"].min(), 1), vmax=edges["weight"].max())
        cmap = cm.get_cmap("plasma")

        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        for _, row in edges.iterrows():
            line = row.geometry
            w = max(row["weight"], 1)

            lw = np.log1p(w) * 1.5 if mostrar_peso else 1
            color = cmap(norm(w))

            x, y = line.xy
            ax.plot(x, y, linewidth=lw, alpha=0.7, color=color)
            draw_arrow(ax, line, lw)

            if mostrar_peso:
                xm, ym = line.interpolate(0.5, normalized=True).coords[0]
                ax.text(xm, ym, str(row["weight"]), fontsize=8, color=color)

        cbar = plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
        cbar.set_label("Cantidad de traslados (log scale)")

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

    ax.set_title("Red hospitalaria sobre AMBA")
    ax.axis("off")

    return fig, ax

def plot_red_interactiva(G, hosp_coords):
    import folium
    import branca.colormap as bcm

    G = colapsar_grafo(G)

    coord_dict = {
        row["id_hospital"]: (row["Latitud"], row["Longitud"])
        for _, row in hosp_coords.iterrows()
    }

    weights = [d["weight"] for _,_,d in G.edges(data=True)]
    weights = [max(w,1) for w in weights]

    colormap = bcm.linear.plasma.scale(min(weights), max(weights))

    m = folium.Map(tiles="cartodbpositron")

    # nodos
    for name, (lat, lon) in coord_dict.items():
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color="black",
            fill=True,
            popup=name
        ).add_to(m)

    # edges con curva
    for u, v, d in G.edges(data=True):
        if u not in coord_dict or v not in coord_dict:
            continue

        p1 = coord_dict[u][::-1]  # lon, lat
        p2 = coord_dict[v][::-1]

        curva = get_curvature(G, u, v, 0.2)
        line = curved_line(p1, p2, curva, n=20)

        coords = [(y, x) for x, y in line.coords]  # volver a lat,lon

        w = max(d["weight"], 1)

        folium.PolyLine(
            coords,
            weight=1 + np.log1p(w),
            color=colormap(w),
            opacity=0.8,
            tooltip=f"{u} → {v}: {w}"
        ).add_to(m)

    colormap.caption = "Cantidad de traslados"
    colormap.add_to(m)

    return m


def graficar_heatmaps(df_probabilidades, df_cantidades, nombre_archivo=None, subcarpeta="general"):
    import matplotlib.pyplot as plt
    import seaborn as sns
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.patch.set_facecolor('white')
    # Probabilidades → CMAP_PROBABILIDAD (Purples)
    sns.heatmap(df_probabilidades, annot=True, fmt=".2f", cmap=CMAP_PROBABILIDAD,
                linewidths=0.5, linecolor='lightgray', vmin=0, vmax=1, ax=axes[0],
                cbar_kws={'label': 'Probabilidad de Transicion'})
    axes[0].set_title("Matriz de Transicion (Probabilidades)", fontsize=16, fontweight='bold', pad=15)
    axes[0].set_ylabel("Nivel de Origen", fontsize=12, fontweight='bold')
    axes[0].set_xlabel("Nivel de Destino", fontsize=12, fontweight='bold')
    # Cantidades → CMAP_FRECUENCIA (YlGnBu)
    sns.heatmap(df_cantidades, annot=True, fmt="d", cmap=CMAP_FRECUENCIA,
                linewidths=0.5, linecolor='lightgray', ax=axes[1],
                cbar_kws={'label': 'Cantidad de Traslados'})
    axes[1].set_title("Matriz de Frecuencia (Cantidades Absolutas)", fontsize=16, fontweight='bold', pad=15)
    axes[1].set_ylabel("Nivel de Origen", fontsize=12, fontweight='bold')
    axes[1].set_xlabel("Nivel de Destino", fontsize=12, fontweight='bold')
    for ax in axes:
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        plt.setp(ax.get_xticklabels(), rotation=45, ha='left', fontweight='bold')
        plt.setp(ax.get_yticklabels(), fontweight='bold')
    plt.tight_layout()
    if nombre_archivo is not None:
        guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
    plt.show()

def graficar_top_10(df, x_col, y_col, titulo, xlabel, ylabel, sufijo="pac.", palette=None, subtitulo=None, nombre_archivo=None, subcarpeta="general"):
    import matplotlib.pyplot as plt
    import seaborn as sns
    # Usa la paleta categórica académica si no se especifica otra
    if palette is None:
        palette = PALETA_GENERAL[:len(df)]
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('white')
    sns.barplot(data=df, x=x_col, y=y_col, palette=palette, hue=y_col, legend=False, ax=ax)
    margen = df[x_col].max() * 0.015
    for index, row in df.iterrows():
        texto_etiqueta = f"{int(row[x_col])} {sufijo} ({row['Porcentaje']:.1f}%)"
        ax.text(row[x_col] + margen, index, texto_etiqueta, color='#333333', va="center", fontweight='bold', fontsize=11)
    ax.set_title(titulo, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    if subtitulo:
        plt.figtext(0.5, 0.92, subtitulo, ha="center", fontsize=11, color='dimgray')
        plt.tight_layout(rect=[0, 0, 1, 0.95])
    else:
        plt.tight_layout()
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.tick_params(axis='y', labelsize=12)
    if nombre_archivo is not None:
        guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
    plt.show()

    
def graficar_top_10_apilado(df_pivot, titulo, xlabel, ylabel, total_general, sufijo="pac.", nombre_archivo=None, subcarpeta="desenlaces"):
    """Grafica barras horizontales apiladas por motivo de egreso usando la paleta semantica COLORES_MOTIVOS."""
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('white')

    # Estandarizar nombre de columnas para compatibilidad perfecta con COLORES_MOTIVOS
    df_pivot.columns = df_pivot.columns.astype(str).str.lower().str.strip()
    
    # 1. Orden estandarizado segun directriz (lo que quede fuera se pega al final)
    orden_apilado = ['alta', 'muerte', 'hospital externo', 'alta hotel', 'otro/desconocido']
    columnas_presentes = [c for c in orden_apilado if c in df_pivot.columns]
    columnas_extra = [c for c in df_pivot.columns if c not in orden_apilado]
    df_pivot = df_pivot[columnas_presentes + columnas_extra]

    # 2. Asignacion estricta de color
    colores_barras = [COLORES_MOTIVOS.get(col, '#9E9E9E') for col in df_pivot.columns]

    df_pivot.plot(kind='barh', stacked=True, color=colores_barras, ax=ax, width=0.7)

    totales = df_pivot.sum(axis=1)
    margen = totales.max() * 0.015
    ax.set_xlim(0, totales.max() * 1.25)

    for i, (idx, total) in enumerate(totales.items()):
        if total > 0:
            porcentaje = (total / total_general) * 100
            texto_etiqueta = f"{int(total)} {sufijo} ({porcentaje:.1f}%)"
            ax.text(total + margen, i, texto_etiqueta,
                    color='#333333', va="center", fontweight='bold', fontsize=11)

    ax.set_title(titulo, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.tick_params(axis='y', labelsize=12)

    plt.legend(title='Motivo Fin de Caso', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False)
    plt.tight_layout()
    if nombre_archivo is not None:
        guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
    plt.show()
    
def graficar_grilla_periodos(pivot_periodos, orden_columnas, nombre_archivo=None, subcarpeta="evolucion"):
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor('white')
    axes = axes.flatten()
    # Usa la paleta de períodos académica (una barra por panel)
    max_x = pivot_periodos.max().max() * 1.15
    for idx, periodo in enumerate(orden_columnas):
        ax = axes[idx]
        color = PALETA_PERIODOS[idx % len(PALETA_PERIODOS)]
        valores = pivot_periodos[periodo]
        y_pos = np.arange(len(valores))
        ax.barh(y_pos, valores, color=color, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(valores.index, fontweight='bold', fontsize=11)
        ax.set_xlim(0, max_x)
        ax.set_title(f"{periodo}", fontsize=15, fontweight='bold', pad=10)
        ax.set_xlabel("Traslados", fontsize=11, color='dimgray')
        for i, v in enumerate(valores):
            if v > 0:
                ax.text(v + (max_x * 0.015), i, str(int(v)), va='center', fontweight='bold', color='#333333', fontsize=10)
        sns.despine(ax=ax)
    plt.suptitle("Evolucion del Top 10 Global de Traslados por Ola", fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    if nombre_archivo is not None:
        guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
    plt.show()

def graficar_grilla_trayectorias_periodos(pivot_periodos, orden_columnas, nombre_archivo=None, subcarpeta="evolucion"):
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor('white')
    axes = axes.flatten()
    max_x = pivot_periodos.max().max() * 1.15
    for idx, periodo in enumerate(orden_columnas):
        ax = axes[idx]
        color = PALETA_PERIODOS[idx % len(PALETA_PERIODOS)]
        valores = pivot_periodos[periodo]
        y_pos = np.arange(len(valores))
        ax.barh(y_pos, valores, color=color, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(valores.index, fontweight='bold', fontsize=11)
        ax.set_xlim(0, max_x)
        ax.set_title(f"{periodo}", fontsize=15, fontweight='bold', pad=10)
        ax.set_xlabel("Pacientes", fontsize=11, color='dimgray')
        for i, v in enumerate(valores):
            if v > 0:
                ax.text(v + (max_x * 0.015), i, str(int(v)), va='center', fontweight='bold', color='#333333', fontsize=10)
        sns.despine(ax=ax)
    plt.suptitle("Evolucion del Top 10 de Trayectorias Completas por Ola", fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    if nombre_archivo is not None:
        guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
    plt.show()

def graficar_grilla_trayectorias_dinamico(df_cantidades, df_rankings, orden_columnas, n_top=8, nombre_archivo=None, subcarpeta="evolucion"):
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    fig.patch.set_facecolor('white')
    axes = axes.flatten()
    max_x = df_cantidades.max().max() * 1.2
    for idx, periodo in enumerate(orden_columnas):
        ax = axes[idx]
        color_periodo = PALETA_PERIODOS[idx % len(PALETA_PERIODOS)]
        valores = df_cantidades[periodo]
        rankings = df_rankings[periodo]
        y_pos = np.arange(len(valores))
        colores_barras = [
            color_periodo if not pd.isna(rankings[ruta]) else '#e0e0e0'
            for ruta in valores.index
        ]
        ax.barh(y_pos, valores, color=colores_barras, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(valores.index, fontweight='bold', fontsize=10)
        ax.set_xlim(0, max_x)
        ax.set_title(f"{periodo}", fontsize=15, fontweight='bold', pad=10)
        ax.set_xlabel("Pacientes", fontsize=11, color='dimgray')
        for i, (ruta, v) in enumerate(valores.items()):
            if v > 0:
                rank = rankings[ruta]
                if not pd.isna(rank):
                    texto = f"[#{int(rank)}]  {int(v)} pac."
                    font_weight = 'bold'
                    color_texto = '#c21807' if rank <= 3 else '#333333'
                else:
                    texto = f"{int(v)}"
                    font_weight = 'normal'
                    color_texto = 'gray'
                ax.text(v + (max_x * 0.015), i, texto, va='center', fontweight=font_weight, color=color_texto, fontsize=10)
        sns.despine(ax=ax)
    plt.suptitle(f"Evolucion Dinamica: Union de las Top {n_top} Trayectorias por Ola", fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    if nombre_archivo is not None:
        guardar_pdf(nombre_archivo, subcarpeta=subcarpeta)
    plt.show()

