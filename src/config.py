# ==========================================
# CONFIGURACIONES Y CONSTANTES GLOBALES
# ==========================================
import os
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

# A. Paleta categórica general (colorblind-friendly, tonos sobrios)
# Usada en barras donde el color solo distingue categorías, sin semántica propia.
PALETA_GENERAL = [
    "#4878CF",  # Azul acero
    "#D65F00",  # Naranja apagado
    "#6A9E6F",  # Verde oliva
    "#8E72B0",  # Violeta grisáceo
    "#C4A35A",  # Ocre / dorado suave
    "#4DADA4",  # Teal apagado
    "#C46062",  # Rojo ladrillo suave
    "#8B8682",  # Gris cálido
]

# B. Paleta semántica fija para motivos de fin de caso.
# Todas las funciones que grafican desenlaces deben leer exclusivamente de aquí.
COLORES_MOTIVOS = {
    "alta":               "#3A7D44",  # Verde esmeralda apagado
    "alta-domiciliaria":  "#3A7D44",  # (igual que alta)
    "muerte":             "#8B1A1A",  # Rojo ladrillo / borgoña
    "alta hotel":         "#2E6E9E",  # Azul cobalto suave
    "hospital externo":   "#C47A2B",  # Naranja tostado
    "traslado-otro":      "#C47A2B",  # (igual que hospital externo)
    "otro/desconocido":   "#7A7A7A",  # Gris plomo
}

# C. Colormaps secuenciales
# Frecuencias absolutas / conteos (heatmaps de cantidad)
CMAP_FRECUENCIA = "YlGnBu"
# Probabilidades / porcentajes (heatmaps de transición normalizados)
CMAP_PROBABILIDAD = "Purples"

# D. Paleta para grillas de evolución temporal (una secuencia por período)
PALETA_PERIODOS = ["#4878CF", "#D65F00", "#6A9E6F", "#8E72B0"]


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
    for ruta in RUTAS_OVERLEAF.values():
        os.makedirs(ruta, exist_ok=True)


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