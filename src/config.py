# ==========================================
# CONFIGURACIONES Y CONSTANTES GLOBALES
# ==========================================
import seaborn as sns
import os

# Ruta por defecto a los DataFrames exportados (ej. trayectorias, eventos, etc.)
RUTA_EXCEL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "revision_dfs.xlsx"))

# ---> ¡ASÍ DEBEN QUEDAR LAS LÍNEAS! <---
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