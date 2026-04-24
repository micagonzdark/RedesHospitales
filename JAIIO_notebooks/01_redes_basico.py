#!/usr/bin/env python
# coding: utf-8

# In[1]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')

import sys
import os
sys.path.append(os.path.abspath(".."))
from src.config import *
from src.io import *
from src.procesamiento import *
from src.visualizacion import *
from src.funciones_complejas import *

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

# ==========================================
# CONFIGURACIONES GLOBALES
# ==========================================
sns.set_style("whitegrid") 
# from src.config import crear_directorios_overleaf
# crear_directorios_overleaf()  # Crea subcarpetas en graficos_overleaf/


# In[2]:


# CARGA Y LIMPIEZA DE DATOS (Nomenclatura completa)
# ==========================================
df_base = pd.read_excel("../data/pacientes.xlsx")
hospitales = pd.read_csv("../data/hospitales_coordenadas.csv")

# Diccionarios de referencia para hospitales
dict_complejidad = dict(zip(hospitales['Nombre Hospital'], hospitales['complejidad']))
hospitales['color_rgb'] = hospitales['color'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

# --- RECUPERADO: El renombre COMPLETO de columnas ---
df_base = df_base.rename(columns={
    'Id Hospital': 'hospital_id',
    'Nombre Hospital': 'hospital_origen',
    'Id': 'paciente_id',
    'Fecha inicio': 'fecha_ingreso',
    'Estado al ingreso': 'estado_ingreso',
    'Tipo al ingreso': 'tipo_ingreso',
    'Último estado': 'estado_ultimo',
    'Último tipo': 'tipo_ultimo',
    'Sexo': 'sexo',
    'Edad': 'edad',
    'Nivel riesgo clínico': 'riesgo_clinico',
    'Nivel riesgo social': 'riesgo_social',
    'Enfermedades preexistentes Covid-19': 'comorbilidades_covid',
    'Enfermedades preexistentes pediatría': 'comorbilidades_pediatria',
    'Vacuna': 'vacuna',
    'Cant. dosis': 'cantidad_dosis',
    '1º dosis': 'fecha_dosis_1',
    '2º dosis': 'fecha_dosis_2',
    'Buscado en el ministerio': 'validado_ministerio',
    'Obra social': 'obra_social',
    'Asistencia Respiratoria Mecánica': 'requiere_arm',
    'Motivo': 'motivo_egreso',
    'Operación': 'operacion',
    'Fecha egreso': 'fecha_egreso',
    'Última actualización': 'fecha_ultima_actualizacion',
    'Pasó por Críticas': 'paso_criticas',
    'Pasó por Intermedias': 'paso_intermedias',
    'Pasó por Generales': 'paso_generales'
}).copy()

df_base['hospital_origen'] = df_base['hospital_origen'].replace({
    'Módulo Hospitalario 11- FV': 'Módulo Hospitalario 11 - FV',
    'Módulo Hospitalario  9 - AB': 'Módulo Hospitalario 9 - AB'
})

df_base['fecha_ingreso'] = pd.to_datetime(df_base['fecha_ingreso'], errors='coerce')
df_base['fecha_egreso'] = pd.to_datetime(df_base['fecha_egreso'], errors='coerce')
    # Normalización proactiva de nombres de hospitales
df_base['hospital_origen'] = df_base['hospital_origen'].str.strip()
# --- NUEVO: Mapeo de IDs únicos de Hospital ---
df_base['Nombre Hospital'] = df_base['hospital_origen'] 
df_base = mapear_ids_hospitales(df_base, hospitales, drop_missing=True)


    # Ordenamiento crítico para el cálculo de traslados funcionales
df_base = df_base.sort_values(['paciente_id', 'fecha_ingreso']).reset_index(drop=True)

# Cálculo de estancia por segmento (hospital) con redondeo ceil
df_base['dias_en_nodo'] = np.ceil((df_base['fecha_egreso'] - df_base['fecha_ingreso']).dt.total_seconds() / 86400).fillna(0).astype('Int64')


# ==========================================
# 2. MÉTRICAS DE TRAYECTORIA DEL PACIENTE (RED)
# ==========================================
# Agrupamos por paciente para extraer el inicio, fin y los motivos
df_metricas_globales = df_base.groupby('paciente_id').agg(
    fecha_ingreso_red=('fecha_ingreso', 'first'),  
    fecha_egreso_red=('fecha_egreso', 'last'),     
    dias_estadia_total=('dias_en_nodo', 'sum'),
    motivos_historial=('motivo_egreso', list),     
    motivo_fin_caso=('motivo_egreso', 'last')      
).reset_index()

# Validamos que el motivo de fin de caso
condiciones = [
    df_metricas_globales['motivo_fin_caso'] == 'alta-domiciliaria',
    df_metricas_globales['motivo_fin_caso'] == 'muerte',
    df_metricas_globales['motivo_fin_caso'] == 'traslado-otro',
    df_metricas_globales['motivo_fin_caso'] == 'traslado-extra-sanitario'
]
resultados = ['alta', 'muerte', 'hospital externo', 'alta hotel']

df_metricas_globales['motivo_fin_caso'] = np.select(condiciones, resultados, default='otro/desconocido')
df_base = df_base.merge(df_metricas_globales, on='paciente_id', how='left')


# ==========================================
# 3. CORE DEL MODELO: CONSTRUCCIÓN DE TRASLADOS (PARA MAPAS)
# ==========================================
df_base['id_hospital_destino'] = df_base.groupby('paciente_id')['id_hospital'].shift(-1)
df_base['hospital_destino'] = df_base.groupby('paciente_id')['hospital_origen'].shift(-1)
df_base['fecha_ingreso_destino'] = df_base.groupby('paciente_id')['fecha_ingreso'].shift(-1)
df_base['estado_destino'] = df_base.groupby('paciente_id')['estado_ingreso'].shift(-1)
df_base['tipo_destino'] = df_base.groupby('paciente_id')['tipo_ingreso'].shift(-1) 

df_base['dias_traslado'] = (df_base['fecha_ingreso_destino'] - df_base['fecha_egreso']).dt.days
df_base.loc[df_base['dias_traslado'] == -1, 'dias_traslado'] = 0

    # CRITERIO DE TRASLADO: 
    # 1. El hospital de origen es distinto al de destino.
    # 2. El motivo de egreso contiene la palabra 'traslado'.
mask_traslados = (
    df_base['hospital_destino'].notna() & 
    df_base['motivo_egreso'].str.contains('traslado', na=False, case=False) & 
    (df_base['hospital_origen'] != df_base['hospital_destino'])
)

df_potenciales = df_base[mask_traslados].copy() 
df_aristas_traslados = df_potenciales[df_potenciales['dias_traslado'] <= 100].copy()
df_aristas_traslados = df_aristas_traslados.rename(columns={'hospital_origen': 'hospital_ingreso'})

df_aristas_traslados['alerta_demora'] = df_aristas_traslados['dias_traslado'] > 3
df_aristas_traslados['dias_alerta'] = df_aristas_traslados.apply(lambda row: row['dias_traslado'] if row['alerta_demora'] else 0, axis=1)


# ==========================================
# 4. TABLAS RELACIONALES: ESTANCIAS Y TRAYECTORIAS
# ==========================================
# A. Armamos las Estancias (Episodios) sin perder el último destino
df_estancias_episodios = df_base.sort_values(['paciente_id', 'fecha_ingreso']).copy()
df_estancias_episodios['orden_episodio'] = df_estancias_episodios.groupby('paciente_id').cumcount() + 1
df_estancias_episodios['dias_en_nodo'] = np.ceil((df_estancias_episodios['fecha_egreso'] - df_estancias_episodios['fecha_ingreso']).dt.total_seconds() / 86400).astype('Int64')

# Pegamos la complejidad a cada internación
df_estancias_episodios = df_estancias_episodios.merge(
    hospitales[['Nombre Hospital', 'complejidad']], 
    left_on='hospital_origen', right_on='Nombre Hospital', how='left'
)
df_estancias_episodios['nivel_complejidad'] = df_estancias_episodios['complejidad'].fillna('Desc').astype(str).str.replace('.0', '', regex=False)

# B. Armamos las rutas (Trayectorias)
df_rutas = df_estancias_episodios.groupby('paciente_id').agg(
    ruta_hospitales_str=('hospital_origen', lambda x: ' -> '.join(x.astype(str))),
    ruta_complejidad_str=('nivel_complejidad', lambda x: ' -> '.join(x.astype(str))),
    cantidad_traslados=('hospital_origen', lambda x: len(x) - 1)
).reset_index()

# Unimos con las métricas para tener 1 fila por paciente con su resumen total
df_pacientes_trayectorias = df_metricas_globales.merge(df_rutas, on='paciente_id', how='left')
# Métrica calculada por suma de episodios
# df_pacientes_trayectorias['dias_estadia_total'] = np.ceil((df_pacientes_trayectorias['fecha_egreso_red'] - df_pacientes_trayectorias['fecha_ingreso_red']).dt.total_seconds() / 86400).astype('Int64')
df_pacientes_trayectorias['motivo_fin_caso'] = df_pacientes_trayectorias['motivo_fin_caso'].replace('otro/desconocido', 'alta')


# ==========================================
# 5. EL PEDIDO DE LOS MENTORES: TRAYECTORIAS DE 1 TRASLADO
# ==========================================
# Filtramos solo pacientes con 1 traslado (exactamente 2 pasos/nodos)
df_analisis_rutas = df_pacientes_trayectorias[df_pacientes_trayectorias['cantidad_traslados'] == 1].copy()

# Rescatamos la cantidad de días que pasaron en el "orden_episodio == 1"
tiempo_primer_salto = df_estancias_episodios[df_estancias_episodios['orden_episodio'] == 1][['paciente_id', 'dias_en_nodo']]
tiempo_primer_salto = tiempo_primer_salto.rename(columns={'dias_en_nodo': 'tiempo_hasta_traslado'})

# Unimos la info y armamos el DataFrame final con los nombres declarativos que pidieron
df_tiempos_1_traslado = df_analisis_rutas.merge(tiempo_primer_salto, on='paciente_id', how='left')
df_tiempos_1_traslado = df_tiempos_1_traslado[[
    'ruta_complejidad_str', 
    'motivo_fin_caso', 
    'tiempo_hasta_traslado', 
    'dias_estadia_total'
]].rename(columns={
    'ruta_complejidad_str': 'Tipo de trayectoria',
    'motivo_fin_caso': 'Motivo de egreso',
    'dias_estadia_total': 'Tiempo hasta el egreso (total)'
})


# ==========================================
# 6. PREPARACIÓN DE COORDENADAS (Unificado)
# ==========================================
df_coordenadas = hospitales.rename(columns={'Nombre Hospital': 'hospital', 'Latitud': 'lat', 'Longitud': 'lon'})

# Ajustes manuales unificados
df_coordenadas.loc[df_coordenadas['hospital'] == 'Módulo Hospitalario 8 - LZ', 'lon'] += 0.06
df_coordenadas.loc[df_coordenadas['hospital'] == 'UPA 10 - BE', 'lon'] -= 0.06
df_coordenadas.loc[df_coordenadas['hospital'] == 'Evita Pueblo', 'lon'] -= 0.03

# Desplazar duplicados
nuevas_filas = []
for (lat, lon), group in df_coordenadas.groupby(['lat', 'lon']):
    for i, (_, row) in enumerate(group.iterrows()):
        row_mod = row.copy()
        if i > 0:
            row_mod['lon'] = lon + 0.01   
            row_mod['lat'] = lat + (i * 0.015)  
        nuevas_filas.append(row_mod)

df_coordenadas = pd.DataFrame(nuevas_filas)
hospitales_conocidos = set(df_coordenadas['hospital'])


# In[3]:


# PRE-CÁLCULOS GLOBALES (DRY - Don't Repeat Yourself)
# ==========================================
# 1. Filtramos aristas válidas una sola vez para todos los gráficos
mask_val_g = (
    (df_aristas_traslados['hospital_ingreso'].isin(hospitales_conocidos)) & 
    (df_aristas_traslados['hospital_destino'].isin(hospitales_conocidos)) & 
    (df_aristas_traslados['hospital_ingreso'] != df_aristas_traslados['hospital_destino'])
)

# APLICACIÓN DE UMBRALES GLOBALES:
# df_aristas_validas se usará EXCLUSIVAMENTE para visualización de grafos/mapas
df_aristas_validas = df_aristas_traslados[mask_val_g].copy()
conteo_aristas = df_aristas_validas.groupby(['hospital_ingreso', 'hospital_destino']).size()
aristas_a_dibujar = conteo_aristas[conteo_aristas >= UMBRAL_MIN_TRASLADOS_GRAFICO].index

# Solo filtramos para la visualización
df_aristas_visualizacion = df_aristas_validas.set_index(['hospital_ingreso', 'hospital_destino']).loc[aristas_a_dibujar].reset_index()

# 2. Agrupamientos globales compartidos (Basados en el universo descriptivo completo)
traslados_globales_grp = df_aristas_validas.groupby(['hospital_ingreso', 'hospital_destino']).size()
ingresos_globales_ser = df_base[df_base['hospital_origen'].isin(hospitales_conocidos)]['hospital_origen'].value_counts()

max_tras_glob = traslados_globales_grp.max() if not traslados_globales_grp.empty else 1
max_ing_glob = ingresos_globales_ser.max() if not ingresos_globales_ser.empty else 1


# In[4]:


import matplotlib.pyplot as plt
import networkx as nx

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 14,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

# ==========================================
# GRÁFICO 1: GRILLA 2x2 PERIODOS
# ==========================================
# Volvemos a la creación clásica para tener control manual de los espacios
fig, axes = plt.subplots(2, 2, figsize=(16, 14))
fig.patch.set_facecolor('white')
axes = axes.flatten()

cfg_grilla = {
    'min_grosor': 0.05, 'max_grosor': 10.0, 'min_tamano': 50, 'max_tamano': 1500, 
    'escala_nodo': 'cuadratica', 'color_por_origen': False, 'alpha_arista': 0.9, 'aristas_negras': True,
    'forzar_i_min_50': True, 'arrow_size': 20, 'node_size_edge': 600,
    'leg_title_sz': 14, 'leg_lbl_sz': 11, 'leg_dynamic_spc': True, 'lbl_size': 13,
    'lbl_weight': 'bold', 'lbl_offset': 0.008, 'lbl_bbox': True, 'lbl_bbox_alpha': 0.6, 'lbl_color': '#333333'
}

v_max_enc, i_max_enc = 0, 0

for idx, (titulo, inicio, fin) in enumerate(PERIODOS):
    ax = axes[idx]
    
    # Título con un 'pad' amplio para que respire respecto a la red
    ax.set_title(titulo, fontsize=15, fontweight='bold', pad=15)
    ax.margins(0.1)
    ax.axis('off')
    
    # Filtros temporales
    df_p_per = df_base[df_base['fecha_ingreso'].between(inicio, fin)]
    df_t_per = df_aristas_validas[df_aristas_validas['fecha_egreso'].between(inicio, fin)]
    
    ingresos_ser = df_p_per['hospital_origen'].value_counts()
    traslados_ser = df_t_per.groupby(['hospital_ingreso', 'hospital_destino']).size()
    traslados_dib = traslados_ser[traslados_ser >= UMBRAL_MIN_TRASLADOS_GRAFICO].reset_index(name='peso')
    
    if not traslados_dib.empty:
        v_max_enc = max(v_max_enc, traslados_dib['peso'].max())
    if not ingresos_ser.empty:
        i_max_enc = max(i_max_enc, ingresos_ser.max())


    # Construcción del grafo
    G = nx.DiGraph()
    for _, row in df_coordenadas.iterrows():
        n_ing = ingresos_ser.get(row['hospital'], 0)
        
        # Si tiene ingresos, escalamos; si no, forzamos el tamaño mínimo para que sea visible
        if n_ing > 0:
            sz = aplicar_escala_visual(
                n_ing, max_ing_glob,
                cfg_grilla['min_tamano'], cfg_grilla['max_tamano'],
                cfg_grilla['escala_nodo']
            )
            node_alpha = 0.9
        else:
            sz = cfg_grilla['min_tamano']
            node_alpha = 0.3  # Muy tenue si no tiene actividad
            
        G.add_node(
            row['hospital'],
            pos=(row['lon'], row['lat']),
            color=row.get('color_rgb', 'grey'),
            size=sz,
            shape=MAPA_FORMAS.get(row['shape'], 'o'),
            alpha=node_alpha
        )

    
    for _, row_t in traslados_dib.iterrows():
        G.add_edge(
            row_t['hospital_ingreso'],
            row_t['hospital_destino'],
            weight=row_t['peso']
        )

    dibujar_grafo_nx(
        ax, G,
        nx.get_node_attributes(G, 'pos'),
        max_tras_glob, max_ing_glob,
        cfg_grilla
    )

# Generación de leyendas
generar_leyendas(
    axes[-1],
    v_max_enc, 50, i_max_enc,
    max_tras_glob, max_ing_glob,
    cfg_grilla,
    [(0.55, 0.36), None, (0.75, 0.36)]
)

# ==========================================
# AJUSTE DE ESPACIOS Y LÍNEAS SEPARADORAS
# ==========================================
# 1. Aplicamos tight_layout con un margen vertical (h_pad) grande para proteger los títulos
plt.tight_layout(pad=2.0, h_pad=4.0, w_pad=2.0)

# 2. TRUCO CLAVE: Forzamos el renderizado para que las posiciones de los ejes se actualicen
fig.canvas.draw()

# 3. Obtenemos las cajas delimitadoras exactas de los gráficos
pos_top_left = axes[0].get_position()
pos_top_right = axes[1].get_position()
pos_bottom_left = axes[2].get_position()

# 4. Calculamos los puntos medios geométricos entre los paneles
x_vert = (pos_top_left.x1 + pos_top_right.x0) / 2
y_horiz = (pos_top_left.y0 + pos_bottom_left.y1) / 2

# 5. Dibujamos las líneas relativas a esas posiciones seguras
trans = fig.transFigure

# Línea vertical central
fig.add_artist(plt.Line2D(
    [x_vert, x_vert], [pos_bottom_left.y0, pos_top_left.y1], 
    transform=trans, color='#d3d3d3', linewidth=1.5, linestyle='--'
))

# Línea horizontal central
fig.add_artist(plt.Line2D(
    [pos_top_left.x0, pos_top_right.x1], [y_horiz, y_horiz], 
    transform=trans, color='#d3d3d3', linewidth=1.5, linestyle='--'
))

# Guardado
guardar_pdf('evo_panel2x2_redes_por_periodo', subcarpeta='evolucion')
plt.show()


# In[5]:


# GRAFICO 4X1 para comparar
# ==========================================
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 14,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

# ==========================================
# GRÁFICO 1: GRILLA 1x4 PERIODOS
# ==========================================
# Cambiamos a 1 fila, 4 columnas. El ancho sube drásticamente (ej: 28) y el alto baja (ej: 7 o 8)
fig, axes = plt.subplots(1, 4, figsize=(28, 7))
fig.patch.set_facecolor('white')
axes = axes.flatten()

cfg_grilla = {
    'min_grosor': 0.05, 'max_grosor': 10.0, 'min_tamano': 50, 'max_tamano': 1500, 
    'escala_nodo': 'cuadratica', 'color_por_origen': False, 'alpha_arista': 0.9, 'aristas_negras': True,
    'forzar_i_min_50': True, 'arrow_size': 20, 'node_size_edge': 600,
    'leg_title_sz': 14, 'leg_lbl_sz': 11, 'leg_dynamic_spc': True, 'lbl_size': 13.5,
    'lbl_weight': 'bold', 'lbl_offset': 0.008, 'lbl_bbox': True, 'lbl_bbox_alpha': 0.6, 'lbl_color': '#333333'
}

v_max_enc, i_max_enc = 0, 0

for idx, (titulo, inicio, fin) in enumerate(PERIODOS):
    ax = axes[idx]
    
    # Título con un 'pad' amplio para que respire respecto a la red
    ax.set_title(titulo, fontsize=15, fontweight='bold', pad=15)
    ax.margins(0.1)
    ax.axis('off')
    
    # Filtros temporales
    df_p_per = df_base[df_base['fecha_ingreso'].between(inicio, fin)]
    df_t_per = df_aristas_validas[df_aristas_validas['fecha_egreso'].between(inicio, fin)]
    
    
    ingresos_ser = df_p_per['hospital_origen'].value_counts()
    traslados_ser = df_t_per.groupby(['hospital_ingreso', 'hospital_destino']).size()
    traslados_dib = traslados_ser[traslados_ser >= UMBRAL_MIN_TRASLADOS_GRAFICO].reset_index(name='peso')
    


    if not traslados_dib.empty:
        v_max_enc = max(v_max_enc, traslados_dib['peso'].max())
    if not ingresos_ser.empty:
        i_max_enc = max(i_max_enc, ingresos_ser.max())


    # Construcción del grafo
    G = nx.DiGraph()
    for _, row in df_coordenadas.iterrows():
        n_ing = ingresos_ser.get(row['hospital'], 0)
        
        if n_ing > 0:
            sz = aplicar_escala_visual(
                n_ing, max_ing_glob,
                cfg_grilla['min_tamano'], cfg_grilla['max_tamano'],
                cfg_grilla['escala_nodo']
            )
            node_alpha = 0.9
        else:
            sz = cfg_grilla['min_tamano']
            node_alpha = 0.3
            
        G.add_node(
            row['hospital'],
            pos=(row['lon'], row['lat']),
            color=row.get('color_rgb', 'grey'),
            size=sz,
            shape=MAPA_FORMAS.get(row['shape'], 'o'),
            alpha=node_alpha
        )


    
    for _, row_t in traslados_dib.iterrows():
        G.add_edge(
            row_t['hospital_ingreso'],
            row_t['hospital_destino'],
            weight=row_t['peso']
        )

    dibujar_grafo_nx(
        ax, G,
        nx.get_node_attributes(G, 'pos'),
        max_tras_glob, max_ing_glob,
        cfg_grilla
    )

# Generación de leyendas (mantenemos las mismas posiciones por ahora)
generar_leyendas(
    axes[-1],
    v_max_enc, 50, i_max_enc,
    max_tras_glob, max_ing_glob,
    cfg_grilla,
    [(0.55, 0.36), None, (0.75, 0.36)]
)

# ==========================================
# AJUSTE DE ESPACIOS Y LÍNEAS SEPARADORAS
# ==========================================
# 1. tight_layout adaptado a una sola fila (h_pad ya no importa, pero w_pad sí)
plt.tight_layout(pad=2.0, w_pad=3.0)

# 2. Forzamos el renderizado
fig.canvas.draw()

# 3. Obtenemos las cajas delimitadoras exactas de los 4 gráficos
pos0 = axes[0].get_position()
pos1 = axes[1].get_position()
pos2 = axes[2].get_position()
pos3 = axes[3].get_position()

# 4. Calculamos las posiciones en X para las tres líneas divisorias verticales
x_vert_1 = (pos0.x1 + pos1.x0) / 2
x_vert_2 = (pos1.x1 + pos2.x0) / 2
x_vert_3 = (pos2.x1 + pos3.x0) / 2

# Obtenemos los límites verticales para que las líneas vayan de arriba a abajo de los ejes
y_bottom = pos0.y0
y_top = pos0.y1

# 5. Dibujamos las tres líneas verticales
trans = fig.transFigure
line_kwargs = {'transform': trans, 'color': '#d3d3d3', 'linewidth': 1.5, 'linestyle': '--'}

fig.add_artist(plt.Line2D([x_vert_1, x_vert_1], [y_bottom, y_top], **line_kwargs))
fig.add_artist(plt.Line2D([x_vert_2, x_vert_2], [y_bottom, y_top], **line_kwargs))
fig.add_artist(plt.Line2D([x_vert_3, x_vert_3], [y_bottom, y_top], **line_kwargs))

# Guardado (le cambié el nombre a evo_panel1x4 para no pisar tu archivo anterior)
guardar_pdf('evo_panel1x4_redes_por_periodo', subcarpeta='evolucion')
plt.show()


# In[6]:


# UNIFICACIÓN DE UPA + MÓDULO   PARA EL GLOBAL
# ==========================================

# 1. Definir el diccionario de mapeo
mapeo_unificacion = {
    'UPA 17 - QU': 'UPA 17 / Módulo Hospitalario 10',
    'Módulo Hospitalario 10 - QU': 'UPA 17 / Módulo Hospitalario 10',
    'UPA 11 - FV': 'UPA 11 / Módulo Hospitalario 11',
    'Módulo Hospitalario 11 - FV': 'UPA 11 / Módulo Hospitalario 11',
    'UPA 5 - AB': 'UPA 5 / Módulo Hospitalario 9',
    'Módulo Hospitalario 9 - AB': 'UPA 5 / Módulo Hospitalario 9'
}

# 2. Aplicar el mapeo a los DataFrames base para el mapa
# Trabajamos sobre copias para no alterar el análisis previo si es necesario
df_base_mapa = df_base.copy()
df_base_mapa['hospital_origen'] = df_base_mapa['hospital_origen'].replace(mapeo_unificacion)

df_aristas_mapa = df_aristas_validas.copy()
df_aristas_mapa['hospital_ingreso'] = df_aristas_mapa['hospital_ingreso'].replace(mapeo_unificacion)
df_aristas_mapa['hospital_destino'] = df_aristas_mapa['hospital_destino'].replace(mapeo_unificacion)

# 3. Eliminar "autodirigidas" (traslados entre UPA y su Módulo que ahora son el mismo nodo)
df_aristas_mapa = df_aristas_mapa[df_aristas_mapa['hospital_ingreso'] != df_aristas_mapa['hospital_destino']]

# 4. Actualizar Coordenadas: Crear una nueva tabla de coordenadas unificada

# Función rápida para rescatar el color original de la UPA
def obtener_color_original(nombre_hospital):
    try:
        return df_coordenadas.loc[df_coordenadas['hospital'] == nombre_hospital, 'color_rgb'].values[0]
    except IndexError:
        return 'grey' # Por si acaso no lo encuentra

# Tomamos las coordenadas y el color original de la UPA
coordenadas_fusion = {
    'UPA 17 / Módulo Hospitalario 10': (-34.73689, -58.32961, 'hospital', obtener_color_original('UPA 17 - QU')),
    'UPA 11 / Módulo Hospitalario 11': (-34.80694, -58.29605, 'hospital', obtener_color_original('UPA 11 - FV')),
    'UPA 5 / Módulo Hospitalario 9':   (-34.87250, -58.38618, 'hospital', obtener_color_original('UPA 5 - AB'))
}

# Filtramos df_coordenadas para quitar los hospitales individuales que se van a fusionar
nombres_individuales = list(mapeo_unificacion.keys())
df_coordenadas_mapa = df_coordenadas[~df_coordenadas['hospital'].isin(nombres_individuales)].copy()

# Agregamos las 3 nuevas filas fusionadas con su color histórico
for nombre, (lat, lon, shape, color) in coordenadas_fusion.items():
    nueva_fila = pd.DataFrame([{
        'hospital': nombre, 'lat': lat, 'lon': lon, 
        'shape': shape, 'color_rgb': color
    }])
    df_coordenadas_mapa = pd.concat([df_coordenadas_mapa, nueva_fila], ignore_index=True)
    
# 5. Recalcular métricas para el gráfico con los nombres nuevos
ingresos_mapa_ser = df_base_mapa['hospital_origen'].value_counts()
traslados_mapa_grp = df_aristas_mapa.groupby(['hospital_ingreso', 'hospital_destino']).size()

# Actualizar el set de hospitales conocidos para el mapa
hospitales_conocidos_mapa = set(df_coordenadas_mapa['hospital'])
max_ing_mapa = ingresos_mapa_ser.max()


# In[7]:


# GRÁFICO 2: MAPA GEOPANDAS
# ==========================================
fig, ax = plt.subplots(figsize=(16, 12))
fig.patch.set_facecolor('white')

min_i_g = ingresos_globales_ser.min() if not ingresos_globales_ser.empty else 0

cfg_geo = {
    'min_grosor': 0.05, 'max_grosor': 10.0, 'min_tamano': 50, 'max_tamano': 1500,
    'escala_nodo': 'cuadratica', 'color_por_origen': False, 'alpha_arista': 0.9, 'aristas_negras': True,
    'arrow_size': 20, 'node_size_edge': 600, 'lbl_offset': 0.008, 'lbl_size': 13,
    'lbl_weight': 'bold', 'lbl_color': '#333333', 'lbl_bbox': True, 'zorder_nodos': 5, 
    'zorder_aristas': 6, 'lw_nodos': 1.0, 'forzar_i_min_50': True, 'min_ingresos_real': min_i_g,
    'leg_title_sz': 14, 'leg_lbl_sz': 12, 'leg_dynamic_spc': True, 'lbl_bbox_alpha': 0.7,
}

deptos = gpd.read_file("../data/shapefiles/departamento/departamentoPolygon.shp")
pba = deptos[deptos["in1"].astype(str).str.startswith("06")].to_crs(epsg=4326)
sudeste = pba[pba["nam"].astype(str).str.upper().isin(["QUILMES", "ALMIRANTE BROWN", "FLORENCIO VARELA", "BERAZATEGUI", "LANUS", "LOMAS DE ZAMORA", "AVELLANEDA", "MORON", "ITUZAINGO"])]

pba.plot(ax=ax, color="#FFFFFF", edgecolor="#ced4da", linewidth=0.5, zorder=0)
sudeste.plot(ax=ax, color="#FFFFFF", edgecolor="#ced4da", linewidth=0.8, zorder=1)

# Filtro de peso de aristas
tras_dib_geo = traslados_mapa_grp[traslados_mapa_grp > 3]
max_t_g_geo = tras_dib_geo.max() if not tras_dib_geo.empty else 1

G_geo = nx.DiGraph()
for _, row in df_coordenadas_mapa.iterrows():
    cant = ingresos_mapa_ser.get(row['hospital'], 0)
    # El tamaño ahora será la suma de ingresos de UPA + Módulo
    sz = aplicar_escala_visual(cant, max_ing_mapa, cfg_geo['min_tamano'], cfg_geo['max_tamano'], 'cuadratica')
    G_geo.add_node(row['hospital'], pos=(row['lon'], row['lat']), 
                   color=row.get('color_rgb', 'grey'), size=sz, 
                   shape=MAPA_FORMAS.get(row['shape'], 'o'), 
                   alpha=0.9 if cant > 0 else 0.4)

for (u, v), peso in tras_dib_geo.items():
    G_geo.add_edge(u, v, weight=peso)

# Dibujar
dibujar_grafo_nx(ax, G_geo, nx.get_node_attributes(G_geo, 'pos'), max_t_g_geo, max_ing_mapa, cfg_geo)

# Ajustar límites del mapa con los nuevos nombres
ax.set_xlim(df_coordenadas_mapa['lon'].min() - 0.05, df_coordenadas_mapa['lon'].max() + 0.08)
ax.set_ylim(df_coordenadas_mapa['lat'].min() - 0.05, df_coordenadas_mapa['lat'].max() + 0.05)

generar_leyendas(ax, max_t_g_geo, min_i_g, max_ing_glob, max_t_g_geo, max_ing_glob, cfg_geo, [(0.46, 0.35), None, (0.60, 0.35)])

plt.tight_layout()
guardar_pdf('gen_mapa_redsudeste_global', subcarpeta='general')

plt.savefig('mapa_global_unificado.svg', format='svg', bbox_inches='tight', transparent=True, dpi=300)

plt.show()


# In[8]:


# 7. GENERACIÓN DE TABLA RESUMEN (MÉTRICAS)
# ==========================================

df_aristas_traslados['es_ambulancia'] = df_aristas_traslados.apply(requiere_ambulancia, axis=1)


# EJECUCIÓN SECCIÓN 7
tabla_resumen = generar_tabla_resumen(df_base, df_aristas_traslados, PERIODOS, hospitales_conocidos)
display(tabla_resumen)
exportar_tabla_estetica(tabla_resumen)


# - PICO DE ESTRES SEGUNDA OLA: admisiones y traslados: en segunda ola aumentan mucho , y tmb el porcentaje de traslados respecto a ingresos
# - BAJA DE AMBULANCIAS: o se optimizaron otros medios, o la red UPA-MODULOS empezo a absorber pacientes que antes requerian ser trasladados
# - CONSOLIDACION DE RUTAS: bajaron mucho las rutas pero aumentaron los traslados por ruta , es decir que el sistema aprendió y se institucionalizaron ciertos caminos. Ya no se mandaban pacientes "a donde hubiera lugar", sino que se establecieron corredores sanitarios claros.

# In[9]:


# 8. GENERACIÓN DE MATRICES
# ==============================================================================

# EJECUCIÓN SECCIÓN 8
ini_estudio, fin_estudio = PERIODOS[0][1], PERIODOS[3][2]
generar_matrices_traslados(df_aristas_traslados, df_base, hospitales, ini_estudio, fin_estudio, 'probabilidad')
generar_matrices_traslados(df_aristas_traslados, df_base, hospitales, ini_estudio, fin_estudio, 'cantidad', nombre_archivo='matriz_frecuencias_global', subcarpeta='general')


# In[10]:


# ANÁLISIS DE IMPACTO DEL UMBRAL DE CORTE
# ==========================================
# Agrupamos los traslados válidos para obtener el peso (frecuencia) de cada arista
pesos_aristas = df_aristas_validas.groupby(['hospital_ingreso', 'hospital_destino']).size().reset_index(name='peso')

# Definimos el umbral que justificamos en el texto
umbral = 3

# 1. Análisis Topológico (Reducción de "ruido" visual)
aristas_totales = len(pesos_aristas)
aristas_retenidas = len(pesos_aristas[pesos_aristas['peso'] > umbral])
aristas_eliminadas = aristas_totales - aristas_retenidas
porcentaje_aristas_retenidas = (aristas_retenidas / aristas_totales) * 100

# 2. Análisis de Flujo (Retención de datos reales de pacientes)
volumen_total = pesos_aristas['peso'].sum()
volumen_retenido = pesos_aristas[pesos_aristas['peso'] > umbral]['peso'].sum()
porcentaje_volumen_retenido = (volumen_retenido / volumen_total) * 100

# 3. Reporte por consola para trasladar al documento/anexo
print(f"--- IMPACTO DEL UMBRAL > {umbral} ---")
print(f"1. REDUCCIÓN VISUAL (Aristas/Flechas):")
print(f"   - Conexiones originales: {aristas_totales}")
print(f"   - Conexiones retenidas:  {aristas_retenidas}")
print(f"   - Conexiones eliminadas: {aristas_eliminadas} (ruido)")
print(f"   -> % de red visual conservada: {porcentaje_aristas_retenidas:.1f}%\n")

print(f"2. CONSERVACIÓN DE DATOS (Pacientes/Traslados):")
print(f"   - Traslados totales originales: {volumen_total}")
print(f"   - Traslados retenidos (flujo):  {volumen_retenido}")
print(f"   -> % de flujo real conservado:  {porcentaje_volumen_retenido:.1f}%")


# In[11]:


# 9. DISTRIBUCIONES DE TIEMPO (CORREGIDO)
# ==========================================

# # 9. ANÁLISIS ESTADÍSTICO Y TEMPORAL (DRY)
# # ==========================================
mask_validos_stats = (
    (df_aristas_traslados['hospital_ingreso'].isin(hospitales_conocidos)) & 
    (df_aristas_traslados['hospital_destino'].isin(hospitales_conocidos)) & 
    (df_aristas_traslados['hospital_ingreso'] != df_aristas_traslados['hospital_destino'])
)
df_aristas_traslados_stats = df_aristas_traslados[mask_validos_stats].copy()

# --- 9.1 Gráfico de Puntos Conectados (Ex Lollipop) ---
promedios_traslados = {}

graficar_traslados_paciente(df_aristas_traslados_stats, df_base, es_global=False, promedios_traslados=promedios_traslados)
graficar_traslados_paciente(df_aristas_traslados_stats, df_base, es_global=True, promedios_traslados=promedios_traslados)

print("-" * 50)
print("PROMEDIO DE TRASLADOS POR PACIENTE (INCLUYE 0s):")
for periodo, prom in promedios_traslados.items():
    print(f"{periodo}: {prom:.4f}")
print("-" * 50)




# 1. Definición robusta de los universos de análisis
# ------------------------------------------------
# Universo A: Global (Todos los pacientes únicos con su estadía total)
df_global_dist = df_pacientes_trayectorias.copy()

# Universo B: Solo los que tuvieron al menos 1 traslado
df_trasladados = df_pacientes_trayectorias[df_pacientes_trayectorias['cantidad_traslados'] > 0].copy()

# Universo C: Solo los que NO tuvieron traslados (quedaron en el hospital de origen)
df_sin_traslado = df_pacientes_trayectorias[df_pacientes_trayectorias['cantidad_traslados'] == 0].copy()

# 2. Configuración de visualización Estilo Paper
# ------------------------------------------------
COLOR_PRINCIPAL = '#4a7abc'  # Azul (Global)
COLOR_ACENTO = '#5cb85c'     # Verde (Trasladados)
COLOR_NEUTRO = '#95a5a6'     # Gris (Sin Traslado)

# Definimos los bins explícitamente para que los 3 gráficos sean comparables
max_plot_dias = 80
bins_5dias = np.arange(0, max_plot_dias + 5, 5)

config_paper_final = [
    (df_global_dist, "A. Distribución Global", COLOR_PRINCIPAL),
    (df_trasladados, "B. Pacientes Trasladados", COLOR_ACENTO),
    (df_sin_traslado, "C. Pacientes Sin Traslado", COLOR_NEUTRO)
]

# --- 9.2.bis Histograma de Conteo Lineal con Medianas ---
# --------------------------------------------------------
fig_bis, axes_bis = plt.subplots(1, 3, figsize=(18, 5.5), sharey=True)
fig_bis.patch.set_facecolor('white')

for i, (ax, (df_plot, titulo, color)) in enumerate(zip(axes_bis, config_paper_final)):
    # Histograma de conteo real (Escala Lineal)
    sns.histplot(data=df_plot, x='dias_estadia_total', bins=bins_5dias, 
                 color=color, stat='count', alpha=0.7, ax=ax, edgecolor='white', linewidth=0.5)
    
    # Cálculo de la mediana real del subgrupo
    mediana_actual = df_plot['dias_estadia_total'].median()
    
    # Línea vertical de la mediana
    ax.axvline(mediana_actual, color='#e67e22', linestyle='--', linewidth=2.5, 
               label=f'Mediana: {mediana_actual:.1f} días')
    
    # Configuración estética
    ax.set_xlim(0, max_plot_dias)
    ax.set_xlabel("Días en el sistema (Total)")
    ax.set_ylabel("Cantidad de Pacientes" if i == 0 else "")
    ax.set_title(titulo, fontweight='bold', fontsize=14)
    ax.grid(axis='y', linestyle=':', alpha=0.6)
    
    # Leyenda para mostrar el valor de la mediana en cada panel
    ax.legend(frameon=True, facecolor='white', framealpha=0.9, loc='upper right')

    # Auditoría rápida por consola para que verifiques los valores mientras corre
    print(f"Subgrupo {titulo[0]}: N={len(df_plot)} | Mediana={mediana_actual:.1f}")

plt.tight_layout()
# guardar_pdf(nombre_archivo="09_2_bis_histograma_mediana_final", subcarpeta="stats")
plt.show()


# In[12]:


# # 9. ANÁLISIS ESTADÍSTICO Y TEMPORAL (DRY)
# # ==========================================
import matplotlib.ticker as ticker
# Paleta distintiva pero profesional (Tipo ColorBrewer/D3)
# 1: Rojo quemado, 2: Azul acero, 3: Verde bosque, 4: Dorado viejo
PALETA_DISTINTIVA = ["#2C4A6E", "#9E6B3B", "#3A6351", "#6B5B7B"]

# Definición de marcadores para los distintos periodos
MARKERS = ['o', 's', '^', 'D', 'v', '*', 'p'] # Círculo, Cuadrado, Triángulo, Diamante, etc.

# Paleta distintiva pero profesional (Tipo ColorBrewer/D3)
# 1: Rojo quemado, 2: Azul acero, 3: Verde bosque, 4: Dorado viejo
PALETA_DISTINTIVA = ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3"]

def generar_grafico_final_distintivo(df_edges, df_base):
    # Aumentamos el tamaño de la figura para soportar fuentes más grandes
    plt.figure(figsize=(12, 8))
    col_id = 'paciente_id' if 'paciente_id' in df_base.columns else 'run_encriptado'
    
    promedios = {}

    for i, (nombre, inicio, fin) in enumerate(PERIODOS):
        inicio_dt, fin_dt = pd.to_datetime(inicio), pd.to_datetime(fin)

        # 1. Población total y traslados
        mask_base = (df_base['fecha_ingreso'] >= inicio_dt) & (df_base['fecha_ingreso'] <= fin_dt)
        pacientes_periodo = df_base[mask_base][col_id].unique()
        n_total = len(pacientes_periodo)
        
        mask_edges = (df_edges['fecha_ingreso_destino'] >= inicio_dt) & (df_edges['fecha_ingreso_destino'] <= fin_dt)
        edges_p = df_edges[mask_edges & df_edges[col_id].isin(pacientes_periodo)]
        
        # 2. Distribución y Media
        counts = edges_p.groupby(col_id).size()
        dist = counts.value_counts().sort_index()
        n_cero = n_total - len(counts)
        promedios[nombre] = counts.sum() / n_total

        # 3. Datos
        eje_x = np.concatenate([[0], dist.index.values])
        eje_y = np.concatenate([[n_cero], dist.values])
        
        # 4. Graficar
        plt.plot(eje_x, eje_y, 
                 label=f"{nombre} (n={n_total})", 
                 color=PALETA_DISTINTIVA[i], 
                 marker=MARKERS[i], 
                 markersize=10, 
                 linewidth=2.5, 
                 alpha=0.65) # Alpha para ver solapamientos

    # --- CONFIGURACIÓN DE EJES (FUENTES GRANDES) ---
    plt.yscale('log')
    
    # Eje Vertical
    plt.gca().yaxis.set_major_formatter(ticker.LogFormatterMathtext())
    plt.gca().yaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=np.arange(2, 10) * 0.1, numticks=12))
    plt.tick_params(axis='both', which='major', labelsize=16) # Tamaño de números en ejes

    # Eje Horizontal
    max_x = int(df_edges.groupby(col_id).size().max()) if not df_edges.empty else 5
    plt.xticks(range(0, max_x + 1))
    plt.gca().xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

    # Etiquetas (Tamaño 18-20)
    plt.xlabel('Número de Traslados por Paciente', fontsize=22, labelpad=15)
    plt.ylabel('Cantidad de Pacientes', fontsize=22, labelpad=15) 
    
    # Leyenda grande
    plt.legend(frameon=True, fontsize=18, loc='upper right')
    
    # Grillas muy sutiles para no ensuciar
    plt.grid(True, which="major", ls="-", alpha=0.1, color='black')
    
    # Quitar marcos superior y derecho
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    plt.tight_layout()

    guardar_pdf(nombre_archivo="09_scatter_periodos", subcarpeta="stats")

    plt.show()

    # --- PROMEDIOS ---
    print("\nPROMEDIOS POR PERIODO:")
    for per, val in promedios.items():
        print(f"{per}: {val:.6f}")


# Ejecutar
generar_grafico_final_distintivo(df_aristas_traslados_stats, df_base)

# ==============================================================================
# PREPARACIÓN DE DATOS PARA 9.2 Y 9.2.bis
# ==============================================================================
# Usamos df_pacientes_trayectorias que YA TIENE todo calculado
tiempo_trayectorias_todas = df_pacientes_trayectorias.set_index('paciente_id').rename(columns={
    'fecha_ingreso_red': 'ingreso',
    'fecha_egreso_red': 'egreso',
    'dias_estadia_total': 'dias_en_sistema'
})[['ingreso', 'egreso', 'dias_en_sistema']].copy()

tiempo_trayectorias_todas = tiempo_trayectorias_todas[tiempo_trayectorias_todas['dias_en_sistema'] >= 0]

# Filtros para separar los grupos
mask_trasladados = df_pacientes_trayectorias.set_index('paciente_id')['cantidad_traslados'] > 0
df_trasladados = tiempo_trayectorias_todas[mask_trasladados]
df_sin_traslado = tiempo_trayectorias_todas[~mask_trasladados]

# Cálculos de límites para el eje X
limite_p99 = tiempo_trayectorias_todas['dias_en_sistema'].quantile(0.99)
max_plot = int(limite_p99) if not pd.isna(limite_p99) else int(tiempo_trayectorias_todas['dias_en_sistema'].max())
bins_5dias = np.arange(0, max_plot + 5, 5)




# ==============================================================================
# 9.2 PREPARACIÓN DE CONFIGURACIÓN Y ORDEN (PAPER STYLE)
# ==============================================================================

# Definimos los bins de 5 días (asegurando que lleguen hasta el máximo plot)
bins_5dias = np.arange(0, max_plot + 5, 5)

# REORDENAMIENTO SOLICITADO: A (Global), B (Sin Traslado), C (Trasladados)
config_paper = [
    (tiempo_trayectorias_todas, "A. Pacientes totales", COLOR_PRINCIPAL),
    (df_sin_traslado, "B. Pacientes sin traslados", COLOR_NEUTRO),
    (df_trasladados, "C. Pacientes con traslados", COLOR_ACENTO)
]

# --- 9.2 Tiempo en el Sistema: Vista de Distribución (1x3) ---
fig2, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=False)
fig2.patch.set_facecolor('white')

for i, (ax, (df_plot, titulo, color)) in enumerate(zip(axes, config_paper)):
    # Histograma de Densidad con bins de 5 días
    sns.histplot(data=df_plot, x='dias_en_sistema', bins=bins_5dias, 
                 color=color, stat='density', alpha=0.3, ax=ax, edgecolor=color)
    
    sns.kdeplot(data=df_plot, x='dias_en_sistema', color=color, linewidth=2, ax=ax)
    
    ax_twin = ax.twinx()
    sns.kdeplot(data=df_plot, x='dias_en_sistema', cumulative=True, 
                color=color, linewidth=1.5, linestyle='--', ax=ax_twin)
    
    ax.set_xlim(0, max_plot)
    ax.set_xlabel("Días en el sistema")
    ax.set_ylabel("Densidad" if i == 0 else "")
    ax.set_title(titulo, fontweight='bold')
    ax.grid(axis='y', linestyle=':', alpha=0.5)
    
    ax_twin.set_ylim(0, 1.05)
    ax_twin.set_ylabel("Prob. Acumulada" if i == 2 else "")
    ax_twin.spines['right'].set_visible(True)
    ax_twin.spines['right'].set_color(color)
    ax_twin.tick_params(axis='y', colors=color)

plt.tight_layout()
plt.show()
# --- 9.2.bis Histograma de Conteo Lineal (Escala Mixta y Eje X Centrado) ---

fig_bis, axes_bis = plt.subplots(1, 3, figsize=(18, 6)) # Aumentamos un poco el alto para el título inferior
fig_bis.patch.set_facecolor('white')

# Vinculamos el eje Y del segundo gráfico con el primero
axes_bis[1].sharey(axes_bis[0])

for i, (ax, (df_plot, titulo, color)) in enumerate(zip(axes_bis, config_paper)):
    # Histograma de conteo con bins de 5 días
    sns.histplot(data=df_plot, x='dias_en_sistema', bins=bins_5dias, 
                 color=color, stat='count', alpha=0.7, ax=ax, edgecolor='white', linewidth=0.5)
    
    # Configuración de límites
    ax.set_xlim(0, max_plot)
    
    # ELIMINAMOS los labels individuales de los ejes
    ax.set_xlabel("") 
    
    # Etiqueta del eje Y: Solo en el primero
    if i == 0:
        ax.set_ylabel("Cantidad de pacientes", fontsize=20, fontweight='bold')
    else:
        ax.set_ylabel("")
    
    ax.set_title(titulo, fontweight='bold', pad=10)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Mediana
    mediana = df_plot['dias_en_sistema'].median()
    ax.axvline(mediana, color='#e67e22', linestyle='--', linewidth=2.5, label=f'Mediana: {mediana:.1f}')
    ax.legend(frameon=False, loc='upper right')

# --- TOQUES FINALES DE FORMATO ---

# Agregamos el eje X global, centrado y más grande
fig_bis.text(0.5, 0.02, 'Días en el sistema', ha='center', va='center', fontsize=20, fontweight='bold')

# Ajustamos los márgenes para que el texto de abajo no se corte
plt.tight_layout(rect=[0, 0.05, 1, 1]) 

guardar_pdf(nombre_archivo="09_2_bis_histograma_final_limpio", subcarpeta="stats")
plt.show()



# ==============================================================================
# AJUSTE DE LÍMITE Y BINS (Para ver más allá de 70 días)
# ==============================================================================
# Opción A: Forzar un número fijo (ej. 100)
# Opción B: Tomar el máximo real de los datos
max_plot_extendido = 100  # <--- Cambia este número al valor que desees
bins_5dias_ext = np.arange(0, max_plot_extendido + 5, 5)

# --- 9.2.bisbis RE-EJECUCIÓN CON ESCALA AMPLIADA ---

fig_bbis, axes_bbis = plt.subplots(1, 3, figsize=(18, 6), sharey=True) 
fig_bbis.patch.set_facecolor('white')

for i, (ax, (df_plot, titulo, color)) in enumerate(zip(axes_bbis, config_paper)):
    sns.histplot(data=df_plot, x='dias_en_sistema', bins=bins_5dias_ext, 
                 color=color, stat='count', alpha=0.7, ax=ax, edgecolor='white', linewidth=0.5)
    
    ax.set_yscale('log')
    
    # Ajustamos el límite al nuevo valor extendido
    ax.set_xlim(0, max_plot_extendido)
    ax.set_xlabel("") 
    
    if i == 0:
        ax.set_ylabel("Cantidad de pacientes (Log)", fontsize=20, fontweight='bold')
    else:
        ax.set_ylabel("")
    
    ax.set_title(titulo, fontweight='bold', pad=10)
    ax.grid(axis='y', which='major', linestyle='--', alpha=0.4)
    ax.grid(axis='y', which='minor', linestyle=':', alpha=0.2)
    
    mediana = df_plot['dias_en_sistema'].median()
    ax.axvline(mediana, color='#e67e22', linestyle='--', linewidth=2.5, label=f'Mediana: {mediana:.1f}')
    ax.legend(frameon=False, loc='upper right')

fig_bbis.text(0.5, 0.02, 'Días en el sistema', ha='center', va='center', fontsize=20, fontweight='bold')
plt.tight_layout(rect=[0, 0.05, 1, 1]) 

guardar_pdf(nombre_archivo="09_2_bisbis_histograma_log_ampliado", subcarpeta="stats")
plt.show()


# ### ⚠️ OPCIÓN D (Clúster 3): Filtrado Manual de Trayectorias
# *Nota: Este bloque es un clon de la lógica de copiado y filtrado de pacientes. Podría ser reemplazado por la versión centralizada.*

# In[13]:


# --- 9.3 Scatter de Traslados vs Tiempo (< 4) (SÚPER OPTIMIZADO) ---
# Chau pd.merge! Ya tenemos 'cantidad_traslados' y 'dias_estadia_total' juntos.
# Filtramos entre 1 y 3 traslados (tu inner join original excluía los de 0 traslados)
df_plot = df_pacientes_trayectorias[
    (df_pacientes_trayectorias['cantidad_traslados'] > 0) & 
    (df_pacientes_trayectorias['cantidad_traslados'] < 4)
].copy()

df_plot['dias_plot'] = df_plot['dias_estadia_total'].astype(float).replace(0, 0.5)

fig3, ax3 = plt.subplots(figsize=(12, 8))
fig3.patch.set_facecolor('white')
sns.stripplot(data=df_plot, x='cantidad_traslados', y='dias_plot', color='#4c72b0', alpha=0.4, jitter=0.2, size=5, ax=ax3, zorder=1)
sns.pointplot(data=df_plot, x='cantidad_traslados', y='dias_plot', estimator=np.mean, errorbar='sd', color='#d62728', markers='D', capsize=0.1, err_kws={'linewidth': 2}, ax=ax3, zorder=3)

ax3.set_yscale('log')
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:g}'.format(y)))
ax3.set(title="Relación entre Cantidad de Traslados y Días en el Sistema\n(Solo pacientes con 1 a 3 traslados)", xlabel="Cantidad de Traslados", ylabel="Días totales en el sistema (Escala Log)")
ax3.legend(handles=[mlines.Line2D([], [], color='#d62728', marker='D', markersize=8, label='Promedio ± Desvío Estándar')], loc='upper left', frameon=True, fontsize=12)
plt.tight_layout()
plt.show()


# --- 9.4 Tiempo hasta Traslado (Barras Apiladas) ---
df_movimientos = df_aristas_traslados_stats.copy()
df_movimientos['dias_antes_traslado'] = (df_movimientos['fecha_egreso'] - df_movimientos['fecha_ingreso']).dt.days
df_movimientos = df_movimientos[df_movimientos['dias_antes_traslado'] >= 0]
df_movimientos['tipo_hospital'] = df_movimientos['hospital_ingreso'].apply(clasificar_hospital)

limite_p99_nodo = df_movimientos['dias_antes_traslado'].quantile(0.99) if not df_movimientos.empty else 30
max_plot_nodo = int(limite_p99_nodo) if not pd.isna(limite_p99_nodo) else 30
bins_mov_5 = np.arange(0, max_plot_nodo + 5, 5)

graficar_tiempo_traslado(df_movimientos, es_global=False)
graficar_tiempo_traslado(df_movimientos, es_global=True)


# --- 9.5 Evolución Temporal (Escalas Duales + Meses en Español + Paleta Azul) ---
# Aplicamos un estilo base limpio
plt.style.use('seaborn-v0_8-whitegrid')
fig4, ax4 = plt.subplots(figsize=(18, 9), dpi=300)
fig4.patch.set_facecolor('#ffffff')

# Resampleo semanal
df_ts = pd.concat([
    df_base.set_index('fecha_ingreso').resample('W').size().rename('Ingresos Totales'),
    df_aristas_traslados_stats.set_index('fecha_egreso').resample('W').size().rename('Traslados')
], axis=1).fillna(0)

# Volvemos a la Paleta Azulada
color_ingresos = '#1a5276'  # Azul oscuro / SteelBlue
color_traslados = '#5499c7'  # Azul claro brillante

# --- EJE IZQUIERDO: INGRESOS ---
lns1 = ax4.plot(df_ts.index, df_ts['Ingresos Totales'], label='Ingresos Totales', 
                color=color_ingresos, linewidth=3, marker='o', markersize=6)
ax4.fill_between(df_ts.index, df_ts['Ingresos Totales'], color=color_ingresos, alpha=0.05)
ax4.set_ylabel("Ingresos", fontsize=20, fontweight='bold', color=color_ingresos)
ax4.tick_params(axis='y', labelcolor=color_ingresos, labelsize=13)

# --- EJE DERECHO: TRASLADOS (twinx) ---
ax4_twin = ax4.twinx()
lns2 = ax4_twin.plot(df_ts.index, df_ts['Traslados'], label='Traslados Efectuados', 
                     color=color_traslados, linewidth=3, marker='s', markersize=6, linestyle='--')
ax4_twin.set_ylabel("Traslados Efectuados", fontsize=20, fontweight='bold', color=color_traslados)
ax4_twin.tick_params(axis='y', labelcolor=color_traslados, labelsize=13)
ax4_twin.grid(False) # Evitamos que las grillas se superpongan

# Ajuste de límites para que las etiquetas de período no choquen
ax4.set_ylim(top=df_ts['Ingresos Totales'].max() * 1.15)
ax4_twin.set_ylim(top=df_ts['Traslados'].max() * 1.15)

# Períodos (Solo líneas separadoras y texto, sin fondo de color)
for i, (titulo, inicio, fin) in enumerate(PERIODOS):
    f_ini, f_fin = pd.to_datetime(inicio), pd.to_datetime(fin)
    
    # Línea divisoria gruesa
    ax4.axvline(f_ini, color='#7f8c8d', linestyle='-', linewidth=2.5, alpha=0.6)
    
    # Etiqueta del período más alta y grande
    ax4.text(f_ini + (f_fin - f_ini)/2, ax4.get_ylim()[1]*0.98, titulo.upper(), 
             ha='center', va='top', fontsize=14, fontweight='bold', color='#2c3e50',
             bbox=dict(facecolor='white', alpha=0.9, edgecolor='#bdc3c7', boxstyle='round,pad=0.5'))

# --- TRUCO PARA MESES EN ESPAÑOL ---
meses_es = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}

def formato_fecha_es(x, pos):
    fecha = mdates.num2date(x)
    return f"{meses_es[fecha.month]}\n{fecha.year}"

ax4.xaxis.set_major_formatter(plt.FuncFormatter(formato_fecha_es))
# -----------------------------------

# Configuración de Eje X y Títulos
ax4.set_xlabel("Fecha", fontsize=19, fontweight='bold', color='#2c3e50')
ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax4.tick_params(axis='x', labelsize=15)

# plt.title("Evolución Temporal: Ingresos vs Traslados", 
#           fontsize=20, fontweight='bold', pad=30, color='#2c3e50')

# Combinar leyendas de ambos ejes en una sola
lns = lns1 + lns2
labs = [l.get_label() for l in lns]
ax4.legend(lns, labs, loc='upper left', fontsize=16, frameon=True, shadow=True)

plt.tight_layout()

# --- Guardado usando tu función personalizada ---
guardar_pdf(nombre_archivo="09_evolucion_temporal_ingresos_traslados", subcarpeta="evolucion")

# Mostramos el gráfico
plt.show()


# In[14]:


# CONSULTAS, FILTROS, RESULTADOS Y EXPORTACIÓN
# ==========================================

# ---------------------------------------------------------
# 1. PARÁMETROS PARA LOS CÁLCULOS
# ---------------------------------------------------------
# Definimos un periodo, un hospital y un ID de interés para hacer las pruebas
fecha_inicio_filtro = '2020-06-01'
fecha_fin_filtro = '2022-12-31'
hospital_interes = 'Evita Pueblo'
id_buscado = 'WN04' # Reemplazar por el ID real

# ---------------------------------------------------------
# 2. BÚSQUEDAS ESPECÍFICAS (OPCIONALES PARA TESTING)
# ---------------------------------------------------------
# Buscar un paciente en particular en la base
historia_paciente = df_base[df_base['paciente_id'] == id_buscado]

# Detectar traslados lentos (> 2 días de demora logística)
traslados_lentos = df_aristas_traslados[df_aristas_traslados['dias_traslado'] > 2]

# ---------------------------------------------------------
# 3. CONTADORES (INGRESOS Y TRASLADOS EN EL PERIODO)
# ---------------------------------------------------------
# A. Contar Ingresos (Totales vs Un Hospital)
mask_periodo_ingresos = df_base['fecha_ingreso'].between(fecha_inicio_filtro, fecha_fin_filtro)
ingresos_totales_periodo = df_base[mask_periodo_ingresos].shape[0]

mask_hospital_ingreso = mask_periodo_ingresos & (df_base['hospital_origen'] == hospital_interes)
ingresos_hospital_periodo = df_base[mask_hospital_ingreso].shape[0]

# B. Contar Traslados Efectuados (Enviados por el hospital de interés)
mask_traslados_enviados = (
    df_aristas_traslados['fecha_egreso'].between(fecha_inicio_filtro, fecha_fin_filtro) & 
    (df_aristas_traslados['hospital_ingreso'] == hospital_interes)
)
traslados_enviados_count = df_aristas_traslados[mask_traslados_enviados].shape[0]

# C. Contar Traslados Recibidos (Por el hospital de interés)
mask_traslados_recibidos = (
    df_aristas_traslados['fecha_egreso'].between(fecha_inicio_filtro, fecha_fin_filtro) & 
    (df_aristas_traslados['hospital_destino'] == hospital_interes)
)
traslados_recibidos_count = df_aristas_traslados[mask_traslados_recibidos].shape[0]

# D. Contar cantidad de pacientes únicos (Corregido para la nueva arquitectura)
pacientes_unicos_absolutos = len(df_pacientes_trayectorias) 
pacientes_unicos_trasladados = len(df_pacientes_trayectorias[df_pacientes_trayectorias['cantidad_traslados'] > 0])

# ---------------------------------------------------------
# 4. IMPRESIÓN DE RESULTADOS
# ---------------------------------------------------------
print("="*60)
print(f"📊 RESULTADOS PARA EL PERIODO: {fecha_inicio_filtro} al {fecha_fin_filtro}")
print("="*60)
print(f"🏥 Hospital analizado: {hospital_interes}\n")
print(f"INGRESOS:")
print(f"  - Totales en la red: {ingresos_totales_periodo}")
print(f"  - Solo en {hospital_interes}: {ingresos_hospital_periodo}\n")
print(f"TRASLADOS DE {hospital_interes}:")
print(f"  - Efectuados (Derivados a otros): {traslados_enviados_count}")
print(f"  - Recibidos (Desde otros): {traslados_recibidos_count}\n")
print(f"MÉTRICAS GLOBALES DE PACIENTES:")
print(f"  - Total de personas registradas (históricas): {pacientes_unicos_absolutos}")
print(f"  - Total de personas con al menos 1 traslado: {pacientes_unicos_trasladados}")
print("="*60)

# ---------------------------------------------------------
# 5. EXPORTACIÓN A EXCEL (LA BASE DE DATOS FINAL)
# ---------------------------------------------------------
ruta_exportacion = "../data/revision_dfs.xlsx"

print(f"\n💾 Exportando base de datos relacional a: {ruta_exportacion} ...")
with pd.ExcelWriter(ruta_exportacion, engine='xlsxwriter') as writer:
    # 1. Base demográfica y de eventos sueltos
    df_base.to_excel(writer, sheet_name='1_Pacientes_Crudos', index=False)
    
    # 2. El historial clínico ordenado cama por cama (¡La joya de la corona!)
    df_estancias_episodios.to_excel(writer, sheet_name='2_Episodios_Cronologicos', index=False)
    
    # 3. Resumen de 1 fila por paciente con su viaje total
    df_pacientes_trayectorias.to_excel(writer, sheet_name='3_Trayectorias_Pacientes', index=False)
    
    # 4. Tabla analítica pedida por los mentores
    df_tiempos_1_traslado.to_excel(writer, sheet_name='4_Tiempos_1_Traslado', index=False)
    
    # 5. Solo aristas (viajes de ambulancia) para mapas
    df_aristas_traslados.to_excel(writer, sheet_name='5_Aristas_Mapas', index=False)
    
    # Si tabla_resumen está definida en celdas anteriores, también la exporta
    if 'tabla_resumen' in locals() or 'tabla_resumen' in globals():
        tabla_resumen.to_excel(writer, sheet_name='6_Tabla_Resumen', index=True)

print("✅ ¡Exportación completada exitosamente!")


# RED: Detectar Hospitales "Sumidero" (Destino Final) vs "Distribuidores" (Triaje)

# In[15]:


# 10. ANÁLISIS DE RED: ROLES DE LOS HOSPITALES (Sumideros vs Distribuidores)
# =============================================================================

# 0. Calculamos si el traslado requirió ambulancia (si tenés tu función requiere_ambulancia definida)
# Si ya la tenías calculada en celdas anteriores, esta línea no hace daño:
if 'es_ambulancia' not in df_aristas_traslados.columns:
    df_aristas_traslados['es_ambulancia'] = df_aristas_traslados.apply(requiere_ambulancia, axis=1)

# 1. Nos quedamos SOLAMENTE con los traslados reales por la red (fuera del predio)
# USAMOS EL NUEVO NOMBRE: df_aristas_traslados
df_red_real = df_aristas_traslados[df_aristas_traslados['es_ambulancia'] == 'ambulancia'].copy()

# 2. Limpieza de nodos basura (eliminamos el hospital '0' o vacíos)
nodos_basura = [0, '0', 'nan', 'NaN']
df_red_real = df_red_real[~df_red_real['hospital_ingreso'].isin(nodos_basura)]
df_red_real = df_red_real[~df_red_real['hospital_destino'].isin(nodos_basura)]

# 3. Calculamos cuánto recibe y cuánto envía cada hospital
ingresos_red = df_red_real.groupby('hospital_destino').size().reset_index(name='recibidos')
egresos_red = df_red_real.groupby('hospital_ingreso').size().reset_index(name='enviados')

# 4. Unificamos
roles_red = pd.merge(ingresos_red, egresos_red, left_on='hospital_destino', right_on='hospital_ingreso', how='outer').fillna(0)
roles_red['hospital'] = roles_red['hospital_destino'].combine_first(roles_red['hospital_ingreso'])

# 5. NUEVAS MÉTRICAS: Volumen y Asimetría
roles_red['volumen_total'] = roles_red['recibidos'] + roles_red['enviados']

# Índice de Asimetría: Rango de -1 (Puro Distribuidor) a +1 (Puro Sumidero)
roles_red['indice_asimetria'] = (roles_red['recibidos'] - roles_red['enviados']) / roles_red['volumen_total']

# 6. FILTRO DE CONFIABILIDAD
# Exigimos un mínimo de 15 traslados totales para ser considerados en el ranking
UMBRAL_VOLUMEN = 15 
roles_filtrado = roles_red[roles_red['volumen_total'] >= UMBRAL_VOLUMEN].copy()

# Ordenamos
roles_filtrado = roles_filtrado[['hospital', 'recibidos', 'enviados', 'volumen_total', 'indice_asimetria']].sort_values('indice_asimetria', ascending=False)

print(f"➤ TOP HOSPITALES 'SUMIDERO' (Retienen pacientes - Índice cercano a +1):")
display(roles_filtrado.head(5))

print(f"\n➤ TOP HOSPITALES 'DISTRIBUIDORES' (Derivan rápido - Índice cercano a -1):")
display(roles_filtrado.tail(5))


# In[16]:


# GRÁFICO: LA MATRIZ DE ROLES (Volumen vs Asimetría)
# =======================================================
fig, ax = plt.subplots(figsize=(12, 8))

# Usamos los roles calculados previamente (filtrando los de muy bajo volumen)
df_plot = roles_red[roles_red['volumen_total'] >= 10].copy()

# Scatterplot: Tamaño del punto según el volumen, color según el índice
scatter = sns.scatterplot(
    data=df_plot, 
    x='indice_asimetria', 
    y='volumen_total', 
    hue='indice_asimetria',
    palette='coolwarm', # Rojo para sumideros, azul para distribuidores
    size='volumen_total', sizes=(100, 1000), 
    legend=False, ax=ax, alpha=0.8, edgecolor='black'
)

# Líneas divisorias de los cuadrantes (Cruz central)
ax.axvline(0, color='grey', linestyle='--', zorder=0) # Asimetría 0
mediana_volumen = df_plot['volumen_total'].median()
ax.axhline(mediana_volumen, color='grey', linestyle='--', zorder=0)

# Etiquetamos los hospitales más extremos (Para saber quién es quién)
for _, row in df_plot.iterrows():
    if row['volumen_total'] > mediana_volumen * 1.5 or abs(row['indice_asimetria']) > 0.6:
        ax.text(row['indice_asimetria'], row['volumen_total'] + (row['volumen_total']*0.05), 
                str(row['hospital']), ha='center', fontsize=9, fontweight='bold')

# Textos de los cuadrantes
ax.text(0.5, df_plot['volumen_total'].max() * 0.9, 'LOS TITANES\n(Reciben y Retienen)', color='darkred', ha='center', alpha=0.6, fontweight='bold', fontsize=12)
ax.text(-0.5, df_plot['volumen_total'].max() * 0.9, 'LOS ENRUTADORES\n(Derivación Masiva)', color='darkblue', ha='center', alpha=0.6, fontweight='bold', fontsize=12)

ax.set_title("Matriz Logística: Volumen de Pacientes vs. Rol en la Red", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("Índice de Asimetría ⟵ (Distribuidor) --- (Sumidero) ⟶", fontsize=12)
ax.set_ylabel("Volumen Total de Pacientes Movilizados (Tráfico)", fontsize=12)
plt.tight_layout()
guardar_pdf('gen_heatmap_roles_global', subcarpeta='general')
plt.show()


# In[17]:


# 10bis. ANÁLISIS DE RED: EVOLUCIÓN DEL ÍNDICE DE ASIMETRÍA POR PERÍODO
# =============================================================================

# Asegurarnos de que existe la columna es_ambulancia
if 'es_ambulancia' not in df_aristas_traslados.columns:
    df_aristas_traslados['es_ambulancia'] = df_aristas_traslados.apply(requiere_ambulancia, axis=1)

# USAMOS EL NUEVO NOMBRE: df_aristas_traslados
df_red_real = df_aristas_traslados[df_aristas_traslados['es_ambulancia'] == 'ambulancia'].copy()
nodos_basura = [0, '0', 'nan', 'NaN']
df_red_real = df_red_real[~df_red_real['hospital_ingreso'].isin(nodos_basura)]
df_red_real = df_red_real[~df_red_real['hospital_destino'].isin(nodos_basura)]

resultados_periodos = []

# Calculamos el índice para cada período
for titulo, inicio, fin in PERIODOS:
    mask_per = df_red_real['fecha_egreso'].between(inicio, fin)
    df_per = df_red_real[mask_per]
    
    ing = df_per.groupby('hospital_destino').size().reset_index(name='recibidos')
    egr = df_per.groupby('hospital_ingreso').size().reset_index(name='enviados')
    
    roles = pd.merge(ing, egr, left_on='hospital_destino', right_on='hospital_ingreso', how='outer').fillna(0)
    roles['hospital'] = roles['hospital_destino'].combine_first(roles['hospital_ingreso'])
    roles['volumen'] = roles['recibidos'] + roles['enviados']
    roles['indice_asimetria'] = (roles['recibidos'] - roles['enviados']) / roles['volumen']
    roles['periodo'] = titulo
    
    # Solo guardamos los que tuvieron movimiento real en ese periodo (> 5 traslados)
    resultados_periodos.append(roles[roles['volumen'] > 5])

df_evolucion_red = pd.concat(resultados_periodos)

# Elegimos los 5 hospitales con MÁS VOLUMEN histórico para graficar
top_hospitales = df_evolucion_red.groupby('hospital')['volumen'].sum().nlargest(6).index
df_plot_red = df_evolucion_red[df_evolucion_red['hospital'].isin(top_hospitales)]

# Graficamos
fig, ax = plt.subplots(figsize=(14, 7))
sns.lineplot(data=df_plot_red, x='periodo', y='indice_asimetria', hue='hospital', 
             marker='o', linewidth=2.5, markersize=8, ax=ax)

# Línea del cero (equilibrio)
ax.axhline(0, color='black', linestyle='--', alpha=0.5, zorder=1)
ax.text(0, 0.05, 'Equilibrio (Pasan y Siguen)', color='black', alpha=0.7)
ax.text(0, 0.9, 'Zona SUMIDERO (Retienen)', color='red', alpha=0.7)
ax.text(0, -0.9, 'Zona DISTRIBUIDOR (Derivan)', color='blue', alpha=0.7)

ax.set_ylim(-1.1, 1.1)
ax.set_title("Evolución del Rol de los Hospitales Principales (Índice de Asimetría)", fontsize=16, fontweight='bold')
ax.set_ylabel("Índice de Asimetría (-1 a +1)")
ax.set_xlabel("Período de la Pandemia")
ax.legend(title="Hospitales (Top Volumen)", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()
guardar_pdf('evo_lineas_asimetria_por_periodo', subcarpeta='evolucion')
plt.show()


# In[18]:


#  10. ANÁLISIS AVANZADO: ROLES DE RED Y GESTIÓN INTRA-PREDIO (BLOQUE INTEGRADO)
# =============================================================================

print("Iniciando análisis integrado de trayectorias...")

# 0. Asegurarnos de que existe la columna es_ambulancia
if 'es_ambulancia' not in df_aristas_traslados.columns:
    df_aristas_traslados['es_ambulancia'] = df_aristas_traslados.apply(requiere_ambulancia, axis=1)

# ---------------------------------------------------------
# A. PREPARACIÓN DE DATOS: Separar Macro (Ambulancia) de Micro (Camilla)
# ---------------------------------------------------------
nodos_basura = [0, '0', 'nan', 'NaN']
df_limpio = df_aristas_traslados[
    (~df_aristas_traslados['hospital_ingreso'].isin(nodos_basura)) & 
    (~df_aristas_traslados['hospital_destino'].isin(nodos_basura))
].copy()

df_red_real = df_limpio[df_limpio['es_ambulancia'] == 'ambulancia'].copy()
df_camilla = df_limpio[df_limpio['es_ambulancia'] == False].copy()

# ---------------------------------------------------------
# B. MACRO-RED: Índice de Asimetría (Sumideros vs Distribuidores)
# ---------------------------------------------------------
ing = df_red_real.groupby('hospital_destino').size().reset_index(name='recibidos')
egr = df_red_real.groupby('hospital_ingreso').size().reset_index(name='enviados')

roles_red = pd.merge(ing, egr, left_on='hospital_destino', right_on='hospital_ingreso', how='outer').fillna(0)
roles_red['hospital'] = roles_red['hospital_destino'].combine_first(roles_red['hospital_ingreso'])
roles_red['volumen_total'] = roles_red['recibidos'] + roles_red['enviados']
roles_red['indice_asimetria'] = (roles_red['recibidos'] - roles_red['enviados']) / roles_red['volumen_total']

roles_filtrado = roles_red[roles_red['volumen_total'] >= 15].sort_values('indice_asimetria', ascending=False)
print("\n➤ TOP 3 HOSPITALES SUMIDERO (Retienen):")
display(roles_filtrado[['hospital', 'volumen_total', 'indice_asimetria']].head(3))
print("\n➤ TOP 3 HOSPITALES DISTRIBUIDORES (Derivan):")
display(roles_filtrado[['hospital', 'volumen_total', 'indice_asimetria']].tail(3))

# ---------------------------------------------------------
# C. MICRO-RED: El Fenómeno "Ping-Pong" Intra-predio
# ---------------------------------------------------------
# 1. Rescatamos los datos clínicos crudos desde df_base (1 por paciente)
df_clinico = df_base.groupby('paciente_id').agg({
    'riesgo_clinico': 'first',
    'paso_criticas': 'last'
}).reset_index()

# 2. Le pegamos estos datos clínicos a nuestra tabla de 1 fila por paciente
df_analisis_base = df_pacientes_trayectorias.merge(df_clinico, on='paciente_id', how='left')

# 3. Calcular saltos
saltos_red = df_red_real.groupby('paciente_id').size().reset_index(name='saltos_externos')
rebotes_int = df_camilla.groupby('paciente_id').size().reset_index(name='rebotes_internos')

# 4. Consolidar TODO en el paciente
df_analisis = df_analisis_base.merge(saltos_red, on='paciente_id', how='left').merge(rebotes_int, on='paciente_id', how='left')
df_analisis['saltos_externos'] = df_analisis['saltos_externos'].fillna(0).astype(int)
df_analisis['rebotes_internos'] = df_analisis['rebotes_internos'].fillna(0).astype(int)

# Categorizar
df_analisis['dinamica_interna'] = df_analisis['rebotes_internos'].apply(
    lambda x: 'Sin rebotes' if x == 0 else ('1 Traslado Normal' if x == 1 else 'Ping-Pong (2+ rebotes)')
)

# Calcular estadía TOTAL en el sistema (Ya la teníamos, pero la aseguramos acá)
df_analisis['dias_estadia'] = (pd.to_datetime(df_analisis['fecha_egreso_red']) - pd.to_datetime(df_analisis['fecha_ingreso_red'])).dt.days
df_analisis['dias_estadia'] = df_analisis['dias_estadia'].clip(lower=0)

# Resultados del Ping-Pong
pingpong_stats = df_analisis.groupby('dinamica_interna').agg(
    total_pacientes=('paciente_id', 'count'), # Corregido el nombre "df_base" por el Find&Replace
    mortalidad_pct=('motivo_fin_caso', lambda x: (x == 'muerte').mean() * 100),
    riesgo_grave_pct=('riesgo_clinico', lambda x: (x.astype(str).str.lower() == 'grave').mean() * 100),
    paso_criticas_pct=('paso_criticas', lambda x: (x.astype(str).str.lower() == 'si').mean() * 100),
    mediana_dias=('dias_estadia', 'median')
).round(1).sort_values('mediana_dias')

print("\n➤ IMPACTO DEL REBOTE INTRA-PREDIO (Perfil Clínico y Logístico):")
display(pingpong_stats)

# ---------------------------------------------------------
# D. VISUALIZACIÓN FINAL COMPUESTA (1x2 Gráficos)
# ---------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(18, 6))

# Gráfico 1: Riesgo vs Mortalidad en el Ping Pong
sns.barplot(data=pingpong_stats.reset_index(), x='dinamica_interna', y='mortalidad_pct', 
            color='lightcoral', ax=axes[0], label='Mortalidad (%)')
sns.lineplot(data=pingpong_stats.reset_index(), x='dinamica_interna', y='riesgo_grave_pct', 
             color='darkred', marker='o', linewidth=2, markersize=8, ax=axes[0], label='Ingreso Grave (%)')
axes[0].set_title("Paradoja de Supervivencia: Mayor Riesgo, Menor Mortalidad", fontweight='bold')
axes[0].set_ylabel("Porcentaje (%)")
axes[0].set_xlabel("Dinámica Interna (Mismo Predio)")
axes[0].legend()

# Gráfico 2: Días de Estadía
sns.boxplot(data=df_analisis[df_analisis['dias_estadia'] < 40], 
            x='dinamica_interna', y='dias_estadia', palette='Blues', ax=axes[1])
axes[1].set_title("Días de Internación ('El Paciente Crónico')", fontweight='bold')
axes[1].set_ylabel("Días Totales en el Sistema")
axes[1].set_xlabel("Dinámica Interna (Mismo Predio)")

plt.tight_layout()
guardar_pdf('gen_burbujas_roles_red_global', subcarpeta='general')
plt.show()


# ### Adaptación Logística y el Fenómeno del "Tetris de Camas" durante la Crisis
# 
# Al analizar las trayectorias de los df_base en la red hospitalaria, el enfoque debió escindirse en dos niveles de resolución: la Macro-Red (traslados inter-hospitalarios en ambulancia) y la Micro-Red (movimientos intra-predio en camilla).
# 
# A nivel Macro, se identificó un comportamiento asimétrico severo en la red, donde ciertos nodos funcionaron puramente como "distribuidores" de triaje rápido, mientras otros actuaron como "sumideros" absolutos.
# 
# Sin embargo, el hallazgo más contraintuitivo se dio en la Micro-Red al analizar las trayectorias de alta frecuencia. Se detectó un subgrupo de df_base (N=183) que rebotó repetidamente (2 o más veces) entre unidades de distinta complejidad dentro del mismo predio. La hipótesis inicial sugería que estos múltiples traslados generarían una mayor tasa de mortalidad por inestabilidad clínica. Los datos demostraron exactamente lo contrario.
# 
# Este grupo ("Ping-Pong") presentó la mortalidad más baja de la red (2.7%), a pesar de tener el mayor porcentaje de riesgo clínico grave al ingreso (32.2%) y la mayor tasa de derivación a camas críticas (17.5%).
# 
# Explicación Logística (El Paciente Crónico y el Sesgo de Sobrevivencia):
# Lejos de ser un error de gestión fatal, este patrón revela un mecanismo de supervivencia del sistema durante el colapso. Para que un paciente sufra múltiples reubicaciones internas, debe sobrevivir a la fase aguda inicial. Estos df_base se convirtieron en sobrevivientes prolongados ("Long-Haulers"), reflejando una mediana de internación casi un 100% mayor que el resto. Durante el pico de saturación, la red utilizó a estos df_base estables pero aún internados como "comodines logísticos", desplazándolos constantemente hacia camas de menor complejidad (Nivel 0) para liberar espacio crítico (Nivel 3) a nuevos ingresos urgentes, y retornándolos cuando sufrían leves descompensaciones.
# 
# En conclusión, la alta movilidad intra-predio no fue una causa de agravamiento, sino el rastro logístico de una red colapsada ejecutando estrategias de descompresión extrema ("tetris de camas") con sus sobrevivientes de larga estadía.

# ## --- ZONA DE PRUEBAS Y EXPLORACIÓN ---
# 

# PACIENTE: El "Costo" de los Saltos en la Mortalidad

# In[19]:


# 11. ANÁLISIS DEL PACIENTE: IMPACTO DE LOS "SALTOS" EN LA MORTALIDAD
# =============================================================================

# 1. Contamos cuántos traslados EN AMBULANCIA tuvo cada paciente
# (Agregamos un chequeo de seguridad por si corrés esta celda suelta)
if 'df_red_real' not in locals():
    df_red_real = df_aristas_traslados[df_aristas_traslados['es_ambulancia'] == 'ambulancia'].copy()

saltos_por_paciente = df_red_real.groupby('paciente_id').size().reset_index(name='cantidad_saltos')

# 2. Lo pegamos al DataFrame maestro (AHORA USAMOS df_pacientes_trayectorias)
df_pacientes_analisis = df_pacientes_trayectorias.merge(saltos_por_paciente, on='paciente_id', how='left')
df_pacientes_analisis['cantidad_saltos'] = df_pacientes_analisis['cantidad_saltos'].fillna(0).astype(int)

# 3. Agrupamos por cantidad de saltos y vemos cómo afecta al destino final
mortalidad_por_saltos = df_pacientes_analisis.groupby('cantidad_saltos').agg(
    total_pacientes=('paciente_id', 'count'),
    muertes=('motivo_fin_caso', lambda x: (x == 'muerte').sum())
).reset_index()

mortalidad_por_saltos['probabilidad_muerte_%'] = (mortalidad_por_saltos['muertes'] / mortalidad_por_saltos['total_pacientes']) * 100

# 4. Graficamos la conclusión
fig, ax = plt.subplots(figsize=(10, 6))

# Filtramos outliers raros (ej: alguien con 8 saltos) para no romper el gráfico
df_plot = mortalidad_por_saltos[mortalidad_por_saltos['total_pacientes'] > 10].copy()

sns.barplot(data=df_plot, x='cantidad_saltos', y='probabilidad_muerte_%', palette='Reds', ax=ax)

ax.set_title("Probabilidad de Muerte según la Cantidad de Traslados en Ambulancia", fontsize=14, fontweight='bold')
ax.set_xlabel("Cantidad de Traslados Externos (Saltos)")
ax.set_ylabel("Tasa de Mortalidad (%)")

# Ponemos el % arriba de la barra y el 'n=' adentro de la barra (VERSIÓN SEGURA)
for i, (_, row) in enumerate(df_plot.iterrows()):
    probabilidad = row['probabilidad_muerte_%']
    pacientes_totales = row['total_pacientes']
    
    # Porcentaje arriba de la barra
    ax.text(i, probabilidad + 0.5, f"{probabilidad:.1f}%", ha='center', fontweight='bold')
    
    # N de pacientes adentro de la barra (a la mitad de su altura)
    ax.text(i, probabilidad / 2, f"n={int(pacientes_totales)}", ha='center', color='white', fontweight='bold', fontsize=10)

plt.tight_layout()
guardar_pdf('des_barras_mortalidad_n_saltos', subcarpeta='desenlaces')
plt.show()


# TRAYECTORIA: La "Puerta de Entrada" marca el Destino

# In[20]:


# 12. TRAYECTORIAS: IMPACTO DE LA CONDICIÓN DE ENTRADA Y COMORBILIDADES
# =============================================================================

# 1. Rescatamos las variables clínicas desde el historial crudo (df_base)
# Para el riesgo, tomamos el del primer ingreso ('first')
# Para el respirador, buscamos si en ALGUN momento de toda su historia requirió ARM
df_clinico_extra = df_base.groupby('paciente_id').agg({
    'riesgo_clinico': 'first',
    'requiere_arm': lambda x: 1 if any(str(v).lower() in ['si', 'sí', 'true', '1'] for v in x) else 0
}).reset_index()

# Renombramos para que coincida con tu lógica
df_clinico_extra = df_clinico_extra.rename(columns={'requiere_arm': 'necesito_respirador'})

# 2. Se las pegamos a nuestro DataFrame de análisis (que ya tiene los saltos del paso 11)
df_pacientes_analisis = df_pacientes_analisis.merge(df_clinico_extra, on='paciente_id', how='left')

# 3. Analizamos por Riesgo Clínico Inicial
riesgo_trayectoria = df_pacientes_analisis.groupby('riesgo_clinico').agg(
    total=('paciente_id', 'count'),
    promedio_saltos_red=('cantidad_saltos', 'mean'),
    tasa_requiere_arm_=('necesito_respirador', 'mean') # mean() de 0s y 1s da la proporción exacta
)

# Pasamos a porcentaje
riesgo_trayectoria['tasa_requiere_arm_%'] = riesgo_trayectoria['tasa_requiere_arm_'] * 100

print("➤ COMPLEJIDAD DE LA TRAYECTORIA SEGÚN EL RIESGO CLÍNICO AL INGRESAR:")
display(riesgo_trayectoria[['total', 'promedio_saltos_red', 'tasa_requiere_arm_%']].sort_values('tasa_requiere_arm_%', ascending=False))


# ### ⚠️ OPCIÓN D (Clúster 3): Filtrado Manual de Trayectorias
# *Nota: Este bloque es un clon de la lógica de copiado y filtrado de pacientes. Podría ser reemplazado por la versión centralizada.*

# In[21]:


# 14. ANÁLISIS DEL PACIENTE: EVOLUCIÓN DE MORTALIDAD SEGÚN TRAYECTORIA (Corregido)
# =============================================================================

# 1. Partimos de nuestra tabla maestra de pacientes (1 fila por persona)
df_pacientes_analisis = df_pacientes_trayectorias.copy()

# Asignar cada paciente al período correspondiente según su fecha de ingreso a la red
def asignar_periodo(fecha):
    if pd.isna(fecha): return 'Sin Dato'
    for titulo, inicio, fin in PERIODOS:
        if pd.to_datetime(inicio) <= fecha <= pd.to_datetime(fin):
            return titulo
    return 'Fuera de Rango'

df_pacientes_analisis['periodo_ingreso'] = df_pacientes_analisis['fecha_ingreso_red'].apply(asignar_periodo)

# 2. Traemos la cantidad de saltos EN AMBULANCIA
# (Chequeo por si no corriste la celda anterior recién)
if 'df_red_real' not in locals():
    df_red_real = df_aristas_traslados[df_aristas_traslados['es_ambulancia'] == 'ambulancia'].copy()

saltos_por_paciente = df_red_real.groupby('paciente_id').size().reset_index(name='cantidad_saltos')
df_pacientes_analisis = df_pacientes_analisis.merge(saltos_por_paciente, on='paciente_id', how='left')
df_pacientes_analisis['cantidad_saltos'] = df_pacientes_analisis['cantidad_saltos'].fillna(0).astype(int)

# 3. Agrupamos saltos largos
df_pacientes_analisis['categoria_saltos'] = df_pacientes_analisis['cantidad_saltos'].apply(
    lambda x: '0 Traslados' if x == 0 else ('1 Traslado' if x == 1 else '2 o más Traslados')
)

# Filtramos los datos válidos y agrupamos
df_validos = df_pacientes_analisis[df_pacientes_analisis['periodo_ingreso'].isin([p[0] for p in PERIODOS])]

mortalidad_periodo = df_validos.groupby(['periodo_ingreso', 'categoria_saltos']).agg(
    total_pacientes=('paciente_id', 'count'),
    muertes=('motivo_fin_caso', lambda x: (x == 'muerte').sum())
).reset_index()

mortalidad_periodo['tasa_mortalidad_%'] = (mortalidad_periodo['muertes'] / mortalidad_periodo['total_pacientes']) * 100

# Ordenar los períodos cronológicamente
orden_periodos = [p[0] for p in PERIODOS]
mortalidad_periodo['periodo_ingreso'] = pd.Categorical(mortalidad_periodo['periodo_ingreso'], categories=orden_periodos, ordered=True)
mortalidad_periodo = mortalidad_periodo.sort_values('periodo_ingreso')

# ---------------------------------------------------------
# MOSTRAMOS LA TABLA PARA CONTROL DE VOLUMEN (N)
# ---------------------------------------------------------
print("➤ DETALLE DE MORTALIDAD Y VOLUMEN DE PACIENTES (N) POR PERÍODO:")
# Mostramos solo las filas donde hubo al menos 1 paciente
display(mortalidad_periodo[mortalidad_periodo['total_pacientes'] > 0])
print("\n" + "="*80 + "\n")

# ---------------------------------------------------------
# GRAFICAMOS
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(14, 7))

# Filtramos donde haya más de 6 pacientes para que el % no sea engañoso (ej: 1 muerto de 1 paciente = 100%)
sns.barplot(data=mortalidad_periodo[mortalidad_periodo['total_pacientes'] > 6], 
            x='periodo_ingreso', y='tasa_mortalidad_%', hue='categoria_saltos', 
            palette=['#a1dab4', '#41b6c4', '#225ea8'], ax=ax)

ax.set_title("Evolución de la Mortalidad según Cantidad de Traslados por Período", fontsize=16, fontweight='bold')
ax.set_xlabel("Período de la Pandemia")
ax.set_ylabel("Tasa de Mortalidad (%)")
ax.legend(title="Trayectoria del Paciente")

# Agregamos los porcentajes arriba de las barras
for container in ax.containers:
    ax.bar_label(container, fmt='%.1f%%', padding=3, fontsize=10)

plt.tight_layout()
guardar_pdf('des_barras_mortalidad_tipo_trayectoria', subcarpeta='desenlaces')
plt.show()


# In[22]:


# 14.A INVESTIGACIÓN DE ANOMALÍAS: Los sobrevivientes con múltiples traslados
# =============================================================================
# Filtramos exactamente ese grupo
casos_raros = df_pacientes_analisis[
    (df_pacientes_analisis['periodo_ingreso'] == 'Intermedia') &
    (df_pacientes_analisis['categoria_saltos'] == '2 o más Traslados')
].copy()

print(f"➤ Analizando {len(casos_raros)} pacientes anómalos...")

# 1. Rescatamos la "historia clínica" de df_base SOLO para estos pacientes raros
ids_raros = casos_raros['paciente_id']
info_clinica_extra = df_base[df_base['paciente_id'].isin(ids_raros)].groupby('paciente_id').agg(
    edad=('edad', 'first'),
    estado_ingreso=('estado_ingreso', 'first'),
    estado_ultimo=('estado_ultimo', 'last'),
    ultimo_hospital=('hospital_origen', 'last') # Buscamos la última cama que pisaron
).reset_index()

# 2. Le pegamos esa info a nuestra tablita de casos raros
casos_raros = casos_raros.merge(info_clinica_extra, on='paciente_id', how='left')

# 3. Definimos las columnas clave (usamos motivo_fin_caso que es la correcta ahora)
cols_interes = ['paciente_id', 'edad', 'estado_ingreso', 'estado_ultimo', 
                'motivo_fin_caso', 'cantidad_saltos', 'ultimo_hospital']

display(casos_raros[cols_interes])

# 4. Veamos también a qué hospitales fueron destinados finalmente
print("\n➤ Últimos hospitales donde estuvieron registrados:")
resumen_hospitales = casos_raros.groupby('ultimo_hospital').size().reset_index(name='cantidad_pacientes')
display(resumen_hospitales.sort_values('cantidad_pacientes', ascending=False))


# In[23]:


# 14.B GRÁFICO DE EVOLUCIÓN (VERSIÓN LÍNEAS / POINTPLOT)
# =============================================================================
fig, ax = plt.subplots(figsize=(14, 7))

# Usamos pointplot en lugar de barplot
# ACÁ ESTABA EL ERROR: Cambiamos 'total' por 'total_pacientes'
sns.pointplot(data=mortalidad_periodo[mortalidad_periodo['total_pacientes'] > 0], 
              x='periodo_ingreso', 
              y='tasa_mortalidad_%', 
              hue='categoria_saltos', 
              palette=['#2ca02c', '#ff7f0e', '#d62728'], # Verde, Naranja, Rojo
              markers=['o', 's', 'D'], # Círculo, Cuadrado, Diamante
              linestyles=['-', '--', '-.'],
              linewidth=2.5,
              ax=ax)

ax.set_title("Evolución de la Mortalidad según Cantidad de Traslados por Período", fontsize=16, fontweight='bold')
ax.set_xlabel("Período de la Pandemia", fontsize=12)
ax.set_ylabel("Tasa de Mortalidad (%)", fontsize=12)
ax.legend(title="Trayectoria del Paciente", fontsize=11)
ax.grid(True, axis='y', alpha=0.3)

# Opcional: Anotar la anomalía de N=14 directamente en el gráfico
ax.annotate('Posible subregistro\n(N=14, 0 muertes)', 
            xy=(1, 0), # Coordenada (Indice 1=Intermedia, Y=0%)
            xytext=(1.2, 5), # Posición del texto
            arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6),
            fontsize=10, bbox=dict(boxstyle="round", alpha=0.1))

plt.tight_layout()
guardar_pdf('evo_lineas_mortalidad_tipo_trayectoria_por_periodo', subcarpeta='evolucion')
plt.show()


# In[24]:


# 15. ANÁLISIS DEL PACIENTE: EL FENÓMENO DEL "PING-PONG" INTRA-PREDIO
# =============================================================================

# 0. Asegurarnos de que existe la columna es_ambulancia (por seguridad)
if 'es_ambulancia' not in df_aristas_traslados.columns:
    df_aristas_traslados['es_ambulancia'] = df_aristas_traslados.apply(requiere_ambulancia, axis=1)

# 1. Filtramos SOLAMENTE los traslados que NO fueron en ambulancia (Intra-predio / Camilla)
# USAMOS EL NOMBRE NUEVO: df_aristas_traslados
df_camilla = df_aristas_traslados[df_aristas_traslados['es_ambulancia'] == False].copy()

# 2. Contamos cuántos rebotes internos tuvo cada paciente
rebotes_internos = df_camilla.groupby('paciente_id').size().reset_index(name='cantidad_rebotes_internos')

# 3. Lo unimos a nuestro DF maestro de pacientes (USAMOS df_pacientes_trayectorias)
df_pacientes_pingpong = df_pacientes_trayectorias.merge(rebotes_internos, on='paciente_id', how='left')
df_pacientes_pingpong['cantidad_rebotes_internos'] = df_pacientes_pingpong['cantidad_rebotes_internos'].fillna(0).astype(int)

# 4. Creamos la categoría de análisis
def categorizar_rebote(cant):
    if cant == 0:
        return 'Sin rebotes internos'
    elif cant == 1:
        return '1 Traslado a Módulo (Normal)'
    else:
        return '2 o más (Ping-Pong)'

df_pacientes_pingpong['tipo_pingpong'] = df_pacientes_pingpong['cantidad_rebotes_internos'].apply(categorizar_rebote)

# 5. Calculamos la mortalidad agrupada por este nuevo fenómeno
mortalidad_pingpong = df_pacientes_pingpong.groupby('tipo_pingpong').agg(
    total_pacientes=('paciente_id', 'count'),
    muertes=('motivo_fin_caso', lambda x: (x == 'muerte').sum())
).reset_index()

mortalidad_pingpong['tasa_mortalidad_%'] = (mortalidad_pingpong['muertes'] / mortalidad_pingpong['total_pacientes']) * 100

# Ordenamos para visualizar mejor
mortalidad_pingpong = mortalidad_pingpong.sort_values('tasa_mortalidad_%')

print("➤ IMPACTO DEL REBOTE INTRA-PREDIO (CAMILLA) EN LA MORTALIDAD GLOBAL:")
display(mortalidad_pingpong)

# Graficamos
fig, ax = plt.subplots(figsize=(10, 6))
# Usamos un degradado de colores para enfatizar el aumento de riesgo
sns.barplot(data=mortalidad_pingpong, x='tipo_pingpong', y='tasa_mortalidad_%', 
            palette='YlOrRd', ax=ax)

ax.set_title("Efecto del 'Ping-Pong' Intra-Predio en la Mortalidad del Paciente", fontsize=14, fontweight='bold')
ax.set_xlabel("Dinámica Interna (Mismo Predio)")
ax.set_ylabel("Tasa de Mortalidad (%)")

for container in ax.containers:
    ax.bar_label(container, fmt='%.1f%%', padding=3, fontsize=12, fontweight='bold')

plt.tight_layout()
guardar_pdf('des_barras_mortalidad_pingpong_global', subcarpeta='general')
plt.show()


# In[25]:


# 16. DESARMANDO EL MISTERIO: Anatomía del paciente "Ping-Pong" (Sin usar ARM)
# =============================================================================

# 1. Rescatamos los datos clínicos desde la historia en bruto (df_base)
# Buscamos si pasó por críticas en algún momento y su riesgo clínico inicial
df_clinico_pingpong = df_base.groupby('paciente_id').agg({
    'paso_criticas': lambda x: 'Si' if any(str(v).lower() in ['si', 'sí', 'true'] for v in x) else 'No',
    'riesgo_clinico': 'first'
}).reset_index()

# Cruzamos estos datos clínicos con nuestra tabla de análisis
df_pacientes_pingpong = df_pacientes_pingpong.merge(df_clinico_pingpong, on='paciente_id', how='left')

# (Nota: Omitimos recalcular 'dias_estadia_total' porque ya existe en este DataFrame 
# gracias a nuestra nueva arquitectura relacional).

# 2. Analizamos el paso por Terapia Intensiva (Críticas) y Riesgo Clínico
columnas_analisis = ['paso_criticas', 'riesgo_clinico']

print("➤ PERFIL CLÍNICO DEL PACIENTE SEGÚN SU DINÁMICA DE TRASLADOS:")
for col in columnas_analisis:
    print(f"\n--- Distribución de '{col.upper()}' ---")
    cruce = pd.crosstab(
        df_pacientes_pingpong['tipo_pingpong'], 
        df_pacientes_pingpong[col], 
        normalize='index' # Porcentaje por fila
    ) * 100
    display(cruce.round(1).style.format("{:.1f}%"))

# 3. Analizamos el Tiempo y Destino
print("\n➤ RESULTADO LOGÍSTICO (Días de internación y Destino final):")
metricas_logisticas = df_pacientes_pingpong.groupby('tipo_pingpong').agg(
    total_pacientes=('paciente_id', 'count'),
    promedio_dias_estadia=('dias_estadia_total', 'mean'),
    mediana_dias_estadia=('dias_estadia_total', 'median'),
    # ACÁ CORREGIDO: Buscamos 'alta' porque unificamos los nombres antes
    alta_domiciliaria_pct=('motivo_fin_caso', lambda x: (x == 'alta').mean() * 100)
).round(1)

display(metricas_logisticas)

# 4. Gráfico para hacerlo visual en tu presentación
fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(data=df_pacientes_pingpong[df_pacientes_pingpong['dias_estadia_total'] < 60], # Cortamos outliers de más de 2 meses para el dibujo
            x='tipo_pingpong', y='dias_estadia_total', 
            palette=['#cccccc', '#ffc107', '#dc3545'], ax=ax)

ax.set_title("Días de Internación según la Dinámica Intra-Predio", fontsize=14, fontweight='bold')
ax.set_xlabel("Dinámica Interna")
ax.set_ylabel("Días de Estadía Totales")
plt.tight_layout()
plt.show()


# In[26]:


# NUEVA CELDA: RESUMEN DE INGRESOS Y TRASLADOS POR ETAPA Y GLOBAL
# =============================================================================

resultados_resumen = []

# 1. Calcular por cada etapa definida en PERIODOS
for titulo, inicio, fin in PERIODOS:
    # Contar ingresos en el periodo
    mask_ingresos = df_base['fecha_ingreso'].between(inicio, fin)
    ingresos_etapa = df_base[mask_ingresos].shape[0]
    
    # Contar traslados en el periodo (usamos fecha_egreso que es cuando ocurre el salto)
    mask_traslados = df_aristas_traslados['fecha_egreso'].between(inicio, fin)
    traslados_etapa = df_aristas_traslados[mask_traslados].shape[0]
    
    resultados_resumen.append({
        'Etapa / Periodo': titulo,
        'Ingresos': ingresos_etapa,
        'Traslados': traslados_etapa
    })

df_resumen = pd.DataFrame(resultados_resumen)

# 2. Calcular los totales Globales de toda la base (sin filtro de fecha)
ingresos_globales = df_base.shape[0]
traslados_globales = df_aristas_traslados.shape[0]

# 3. Anexar la fila de Totales Globales al DataFrame
fila_total = pd.DataFrame([{
    'Etapa / Periodo': 'GLOBAL (Histórico Total)',
    'Ingresos': ingresos_globales,
    'Traslados': traslados_globales
}])

df_resumen_final = pd.concat([df_resumen, fila_total], ignore_index=True)

# 4. Calcular el Porcentaje de Derivación (Opcional pero muy útil para el análisis)
df_resumen_final['% de Traslado'] = (df_resumen_final['Traslados'] / df_resumen_final['Ingresos'] * 100).round(1).astype(str) + '%'

# Imprimir resultados
print("="*70)
print("📊 CONTEO DIRECTO: INGRESOS Y TRASLADOS POR ETAPA")
print("="*70)
display(df_resumen_final)


# In[27]:


# CÁLCULO DE TRAYECTORIAS PARA EL PAPER/INFORME
# ==========================================

# 1. Total de trayectorias únicas (pacientes distintos)
total_trayectorias = len(df_pacientes_trayectorias)

# 2. Asignar el periodo a cada trayectoria basándonos en su ingreso a la red
def asignar_periodo_texto(fecha):
    if pd.isna(fecha): return 'Sin Dato'
    for titulo, inicio, fin in PERIODOS:
        if pd.to_datetime(inicio) <= fecha <= pd.to_datetime(fin):
            return titulo
    return 'Fuera de Rango'

df_temp_trayectorias = df_pacientes_trayectorias.copy()
df_temp_trayectorias['periodo_ingreso'] = df_temp_trayectorias['fecha_ingreso_red'].apply(asignar_periodo_texto)

# 3. Contar los casos por periodo
conteo_periodos = df_temp_trayectorias['periodo_ingreso'].value_counts()

# 4. Imprimir los resultados sueltos
print("="*60)
print(f"📊 TOTAL DE TRAYECTORIAS: {total_trayectorias}")
print("="*60)
for titulo, _, _ in PERIODOS:
    cantidad = conteo_periodos.get(titulo, 0)
    print(f" - {titulo}: {cantidad}")

# 5. Generar el texto formateado
print("\n📝 TEXTO GENERADO PARA EL DOCUMENTO:")
print("-" * 60)

partes_texto = []
for titulo, _, _ in PERIODOS:
    cantidad = conteo_periodos.get(titulo, 0)
    partes_texto.append(f"{cantidad} ({titulo})")

# Unimos los elementos con comas y el último con "y"
if len(partes_texto) > 1:
    distribucion_str = ", ".join(partes_texto[:-1]) + f" y {partes_texto[-1]}"
else:
    distribucion_str = partes_texto[0]

texto_final = f"Identificando entradas con un mismo ID y organizándolas temporalmente, reconstruimos la trayectoria de cada paciente en el sistema hospitalario. El resultado son {total_trayectorias} trayectorias distintas, distribuidas en {distribucion_str}. La Fig."

print(texto_final)
print("-" * 60)


# In[28]:


# 16. TABLA ESTRUCTURAL PARA PAPER (DETALLE POR HOSPITAL)
# =============================================================================

# A. Preparación: Cruzar metadatos (Municipio y Complejidad)
# -----------------------------------------------------------------------------
df_base_mapped = df_base.merge(
    hospitales[['Nombre Hospital', 'municipioAbreviado', 'complejidad']], 
    on='Nombre Hospital', 
    how='inner'
)

# B. Métricas por Nodo (Hospital) - Admitidos y Estancia
# -----------------------------------------------------------------------------
hospital_metrics = df_base_mapped.groupby(['municipioAbreviado', 'complejidad', 'Nombre Hospital']).agg(
    admisiones=('paciente_id', 'count'),
    estancia=('dias_en_nodo', 'mean')
).reset_index()

# C. Métricas por Arista (Traslados) - Recibidos y Realizados
# -----------------------------------------------------------------------------
# 1. Realizados (Outgoing) + Desglose Ambulancia
outgoing_metrics = df_aristas_traslados.groupby('hospital_ingreso').agg(
    t_realizados=('paciente_id', 'count'),
    con_amb=('es_ambulancia', lambda x: (x == 'ambulancia').sum()),
    sin_amb=('es_ambulancia', lambda x: (x == 'upa_modulo').sum())
).reset_index()

# 2. Recibidos (Incoming)
incoming_metrics = df_aristas_traslados.groupby('hospital_destino').agg(
    t_recibidos=('paciente_id', 'count')
).reset_index()

# D. Consolidación de Tabla
# -----------------------------------------------------------------------------
detailed_table = hospital_metrics.merge(
    incoming_metrics, left_on='Nombre Hospital', right_on='hospital_destino', how='left'
).merge(
    outgoing_metrics, left_on='Nombre Hospital', right_on='hospital_ingreso', how='left'
).fillna(0)

# E. Totales y Formateo Final
# -----------------------------------------------------------------------------
detailed_table = detailed_table.sort_values(['municipioAbreviado', 'complejidad', 'Nombre Hospital'])
total_global = pd.Series({
    'municipioAbreviado': 'TOTAL GLOBAL',
    'complejidad': '-',
    'Nombre Hospital': '-',
    'admisiones': detailed_table['admisiones'].sum(),
    't_recibidos': detailed_table['t_recibidos'].sum(),
    't_realizados': detailed_table['t_realizados'].sum(),
    'con_amb': detailed_table['con_amb'].sum(),
    'sin_amb': detailed_table['sin_amb'].sum(),
    'estancia': df_base['dias_en_nodo'].mean()
})

# F. Generación de Bloque LaTeX (Doble Multirow)
# -----------------------------------------------------------------------------
def generar_latex_detallado(df):
    output = []
    output.append("\\begin{table}[htbp]")
    output.append("  \\centering")
    output.append("  \\caption{Detalle de Actividad por Hospital y Jerarquía Territorial}")
    output.append("  \\label{tab:actividad_hospitalaria}")
    output.append("  \\begin{tabular}{lllc|cc|cc|c}")
    output.append("    \\toprule")
    output.append("    & & & & \\multicolumn{2}{c}{Traslados} & \\multicolumn{2}{c}{Logistica (Amb)} & \\\\")
    output.append("    Municipio & Nivel & Hospital & Adm. & Recib. & Realiz. & Con & Sin & Estancia \\\\")
    output.append("    \\midrule")
    
    df_data = df[df['municipioAbreviado'] != 'TOTAL GLOBAL']
    mun_counts = df_data['municipioAbreviado'].value_counts().to_dict()
    comp_counts = df_data.groupby(['municipioAbreviado', 'complejidad']).size().to_dict()
    
    current_mun, current_comp = "", None
    
    for _, row in df.iterrows():
        mun, comp = row['municipioAbreviado'], row['complejidad']
        
        if mun == 'TOTAL GLOBAL':
            output.append("    \\midrule")
            line = "    \\textbf{{{}}} & - & - & \\textbf{{{}}} & \\textbf{{{}}} & \\textbf{{{}}} & \\textbf{{{}}} & \\textbf{{{}}} & \\textbf{{{{:.1f}}}} \\\\".format(
                mun, int(row['admisiones']), int(row['t_recibidos']), int(row['t_realizados']), 
                int(row['con_amb']), int(row['sin_amb']), row['estancia']
            )
            output.append(line)
        else:
            mun_cell = ""
            if mun != current_mun:
                mun_cell = "\\multirow{{{}}}{{*}}{{{}}}".format(int(mun_counts[mun]), mun)
                if len(output) > 10: output.append("    \\addlinespace[0.5em]")
            
            comp_cell = ""
            if comp != current_comp or mun != current_mun:
                comp_cell = "\\multirow{{{}}}{{*}}{{{}}}".format(int(comp_counts[(mun, comp)]), int(comp))
                if mun == current_mun and len(output) > 10:
                    output.append("    \\cline{2-9}")
            
            current_mun, current_comp = mun, comp
            
            line = "    {} & {} & {} & {} & {} & {} & {} & {} & {:.1f} \\\\".format(
                mun_cell, comp_cell, row['Nombre Hospital'], int(row['admisiones']), 
                int(row['t_recibidos']), int(row['t_realizados']), int(row['con_amb']), 
                int(row['sin_amb']), row['estancia']
            )
            output.append(line)
            
    output.append("    \\bottomrule")
    output.append("  \\end{tabular}")
    output.append("\\end{table}")
    return "\n".join(output)

latex_code = generar_latex_detallado(detailed_table)
print("--- CÓDIGO LATEX PARA COPIAR ---")
print(latex_code)

