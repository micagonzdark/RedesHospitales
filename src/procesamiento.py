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

####################################################


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




def armar_trayectoria(group):
    ruta_hosp = group['hospital_ingreso'].tolist() + [group['hospital_destino'].iloc[-1]]
    ruta_tipo = group['tipo_ingreso'].tolist() + [group['tipo_destino'].iloc[-1]]
    
    ruta_comp_num = [dict_complejidad.get(h, 0) for h in ruta_hosp] 
    ruta_tipo_num = [mapa_estados.get(str(e).lower().strip(), 0) for e in ruta_tipo]

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

df_traslados['es_ambulancia'] = df_traslados.apply(requiere_ambulancia, axis=1)

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