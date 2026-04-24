# ==========================================
# CONFIGURACIONES Y CONSTANTES GLOBALES
# ==========================================
import os
import shutil
import matplotlib.pyplot as plt
import seaborn as sns

# Ruta por defecto a los DataFrames exportados (ej. trayectorias, eventos, etc.)
RUTA_EXCEL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "revision_dfs.xlsx"))

RUTA_MUNICIPIOS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "shapefiles", "departamento", "departamentoPolygon.shp"))

RUTA_BARRIOS_POPULARES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "renabap_geojson", "20231205_info_publica.geojson.txt"))


sns.set_style("whitegrid")



# ==============================================================================
# CONFIGURACIÓN DE CRITERIOS Y DECISIONES
# ==============================================================================

# 1. VENTANA TEMPORAL DE TRASLADO y de EDAD

DIAS_VENTANA_TRASLADO = 5 
TOLERANCIA_EDAD_ANIOS = 2 # Si la edad varía más de esto, se descarta el paciente

# tolerancia para deduplicación (segundos)
TOL_DUPLICADO_SEGUNDOS = 60

# tolerancia para delta traslado (segundos)
TOL_DELTA_SEGUNDOS = 5 * 60

# 2. JERARQUÍA DE DESENLACES CLÍNICOS
# Cuanto menor es el número, más "manda" el resultado sobre otros registros.
# Esto resuelve casos de registros duplicados o solapados.
ORDEN_PRIORIDAD_CLINICA = {
    'muerte': 1,
    'alta-domiciliaria': 2,
    'traslado-extra-sanitario': 3, # Equivale a Alta Hotel
    'traslado-otro': 4,            # Traslado fuera de la red sudeste
    'traslado': 5,                 # Traslado interno (menos prioritario)
}

# 3. CRITERIOS DE CENSURA / CASOS INCONCLUSOS
# Si el desenlace final del paciente es uno de estos, se considera que 
# perdimos el rastro del paciente.
MOTIVOS_A_DESCARTAR = [
    'otro', 
    'anulado', 
    'traslado-hospital-de-la-red', # Si es el último, es un traslado que no tuvo recepción
    None,                          # Representa los NaN
    'nan'
]

# 4. MAPEO DE NOMBRES PARA PUBLICACIÓN
# Cómo queremos que se vean los nombres en los gráficos finales.
MAPEO_NOMBRES_FINALES = {
    'alta-domiciliaria': 'Alta Médica',
    'muerte': 'Defunción',
    'traslado-otro': 'Hospital Externo',
    'traslado-extra-sanitario': 'Alta Hotel'
}



# ==========================================
# CONFIGURACIÓN GLOBAL DE TIPOGRAFÍA
# ==========================================
# Aplicamos una tipografía limpia y profesional a nivel global para todos los gráficos del proyecto
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Roboto', 'Helvetica Neue', 'Helvetica', 'Arial', 'Liberation Sans', 'DejaVu Sans', 'sans-serif'],
    'axes.unicode_minus': False, # Para evitar problemas con el signo menos en algunas fuentes
    'axes.titleweight': 'bold',
    'axes.labelweight': 'normal',
    'figure.titlesize': 14,
    'figure.titleweight': 'bold'
})


PERIODOS = [
    # ('Global', '2020-06-01', '2022-12-31'),
    ('Primera Ola', '2020-06-01', '2020-10-31'),
    ('Intermedia', '2020-11-01', '2021-02-28'),
    ('Segunda Ola', '2021-03-01', '2021-07-31'),
    ('Post-vacunación', '2021-08-01', '2022-12-31')
]

MAPA_FORMAS = {'dot': 'o', 'star': '*'}
MAPA_ESTADOS = {'criticas': 3, 'intermedias': 2, 'generales': 1}
COLORES_ORIGEN = {'Desde MÓDULO': '#d73027', 'Desde UPA': '#fdae61', 'Desde HOSPITAL': '#1a9850'}

# Umbrales para filtrado de aristas (traslados)
UMBRAL_MIN_TRASLADOS_GRAFICO = 4      # Mínimo de traslados para dibujar la arista en grafos y mapas
UMBRAL_MIN_TRASLADOS_DESCRIPCION = 0  # Mínimo de traslados para incluir en estadísticas y tablas resumen (ajustable)

PAREJAS_MISMO_PREDIO = [
    # Por IDs
    {'H01', 'H10'}, # UPA 17 - QU / Módulo 10
    {'H09', 'H11'}, # UPA 11 - FV / Módulo 11
    {'H08', 'H13'}, # UPA 5 - AB / Módulo 9
    # Por nombres limpios (para tolerancia en notebooks)
    {'UPA 17 QU', 'MODULO HOSPITALARIO 10 QU'},
    {'UPA 11 FV', 'MODULO HOSPITALARIO 11 FV'},
    {'UPA 5 AB', 'MODULO HOSPITALARIO 9 AB'}
]

cfg_grilla = {
    'min_grosor': 0.05, 'max_grosor': 18.0, 'min_tamano': 80, 'max_tamano': 3000,
    'escala_nodo': 'cuadratica', 'color_por_origen': False, 'aristas_negras': True,
    'alpha_arista': 0.5, 'arrow_size': 18, 'forzar_i_min_50': True,
    'leg_title_sz': 16, 'leg_lbl_sz': 14, 'leg_dynamic_spc': True, 'lbl_size': 10,
    'lbl_weight': 'bold',
    'lbl_offset': 0.006,
    'lbl_bbox': True,
    'lbl_bbox_alpha': 0.6,
    'lbl_color': '#333333'
}

max_plot = 100
max_plot_nodo = 100
bins_5dias = 20
bins_mov_5 = 20

N_TOP = 10


# ==========================================
# PALETAS DE COLORES — ESTILO ACADÉMICO
# ==========================================
# =========================================================
# CONFIGURACIÓN DE COLORES Y PALETAS (ESTILO ACADÉMICO)
# =========================================================

# A. Barras categóricas (graficar_top_10, rankings generales)
# Escala monocromática: tonos del mismo azul acero para no distraer.
PALETA_GENERAL = [
    "#08306B",  # Azul muy oscuro (para el valor más alto)
    "#08519C",
    "#2171B5",
    "#4292C6",
    "#6BAED6",
    "#9ECAE1",
    "#C6DBEF",
    "#DEEBF7"   # Azul muy clarito (para los valores más bajos)
]

# B. Motivos de egreso (graficar_top_10_apilado)
# Colores semánticos sobrios y profesionales.


COLORES_MOTIVOS = {
    "alta":              "#6F8F7B",  # verde grisáceo
    "alta-domiciliaria": "#6F8F7B",

    "muerte":            "#8C5A5A",  # rojo apagado (tirando a marrón)

    "alta hotel":        "#7C8DA6",  # azul grisáceo

    "hospital externo":  "#9A8F6A",  # beige/marrón claro (MUCHO mejor que naranja)
    "traslado-otro":     "#9A8F6A",

    "otro/desconocido":  "#B0B0B0",  # gris neutro claro
}

# C. Heatmaps de probabilidad 
# Escala de Naranjas (ideal para porcentajes/probabilidades)
CMAP_PROBABILIDAD = "Oranges"

# D. Heatmaps de frecuencia/cantidades
# Escala de Azules (ideal para volumen de pacientes absolutos)
CMAP_FRECUENCIA = "Blues"

# E. Paneles de períodos en grillas 2x2
# Como los períodos son una línea de tiempo (Ola 1 a Ola 4), 
# usamos un degradé que va de más claro (pasado) a más oscuro (presente).
PALETA_PERIODOS = [
    "#9ECAE1",  # Ola 1 (Claro)
    "#6BAED6",  # Ola 2
    "#2171B5",  # Ola 3
    "#08306B"   # Ola 4 (Oscuro)
]
# ==========================================
# ESTRUCTURA DE SUBCARPETAS OVERLEAF
# ==========================================

RUTAS_OVERLEAF = {
    "general":    "graficos_overleaf/1_general",
    "desenlaces": "graficos_overleaf/2_desenlaces",
    "tiempos":    "graficos_overleaf/3_tiempos",
    "evolucion":  "graficos_overleaf/4_evolucion",
    "anexos":     "graficos_overleaf/anexos",
}


def crear_directorios_overleaf():
    """Crea todas las subcarpetas de exportación. Llamar una vez al inicio del notebook."""
    base_dir = "graficos_overleaf"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
        
    for ruta in RUTAS_OVERLEAF.values():
        os.makedirs(ruta, exist_ok=True)
        
    # Crear índice
    indice_path = os.path.join(base_dir, "00_LEEME_INDICE.txt")
    with open(indice_path, "w", encoding="utf-8") as f:
        f.write("=== INDICE DE GRAFICOS OVERLEAF ===\n\n")
        f.write("1_general/ : Matrices globales, heatmaps y distribuciones generales de traslados.\n")
        f.write("2_desenlaces/ : Gráficos apilados y normalizados que muestran motivos de fin de caso (altas vs muertes).\n")
        f.write("3_tiempos/ : Distribuciones de tiempos de internación y boxplots temporales.\n")
        f.write("4_evolucion/ : Análisis de cómo variaron las métricas o estructuras a lo largo de los períodos de la pandemia.\n")
        f.write("anexos/ : Gráficos de soporte adicionales.\n")


def guardar_pdf(nombre_archivo: str, subcarpeta: str = "general"):
    """
    Guarda el gráfico activo como PDF en la subcarpeta temática correspondiente.

    Parámetros
    ----------
    nombre_archivo : str
        Nombre del archivo sin extensión (ej. '01_heatmaps_matrices').
    subcarpeta : str
        Clave del dict RUTAS_OVERLEAF. Opciones: 'general', 'desenlaces',
        'tiempos', 'evolucion', 'anexos'. Default: 'general'.
    """
    ruta = RUTAS_OVERLEAF.get(subcarpeta, RUTAS_OVERLEAF["general"])
    os.makedirs(ruta, exist_ok=True)
    plt.savefig(f"{ruta}/{nombre_archivo}.pdf", bbox_inches="tight", dpi=300)