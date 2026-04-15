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

PERIODOS = [
    ('Primera Ola', '2020-06-01', '2020-10-31'),
    ('Intermedia', '2020-11-01', '2021-02-28'),
    ('Segunda Ola', '2021-03-01', '2021-07-31'),
    ('Post-vacunación', '2021-08-01', '2022-12-31')
]

MAPA_FORMAS = {'dot': 'o', 'star': '*'}
MAPA_ESTADOS = {'criticas': 3, 'intermedias': 2, 'generales': 1}
COLORES_ORIGEN = {'Desde MÓDULO': '#d73027', 'Desde UPA': '#fdae61', 'Desde HOSPITAL': '#1a9850'}

MIN_GROSOR_ARISTA = 0.5
MAX_GROSOR_ARISTA = 15.0

PAREJAS_MISMO_PREDIO = [
    {'UPA 17 - QU', 'Módulo Hospitalario 10 - QU'},
    {'UPA 11 - FV', 'Módulo Hospitalario 11 - FV'},
    {'UPA 5 - AB', 'Módulo Hospitalario 9 - AB'}
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
    "alta":              "#388E3C",  # Verde apagado
    "alta-domiciliaria": "#388E3C",
    "muerte":            "#D32F2F",  # Rojo oscuro/granate
    "alta hotel":        "#0288D1",  # Azul cerúleo
    "hospital externo":  "#F57C00",  # Naranja tostado
    "traslado-otro":     "#F57C00",
    "otro/desconocido":  "#9E9E9E",  # Gris neutro
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