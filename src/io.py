import os
import sys
import pandas as pd
import geopandas as gpd
import seaborn as sns
import matplotlib.pyplot as plt
from src.procesamiento import (
    limpiar_pacientes, limpiar_coordenadas, limpiar_nombre, 
    reconstruir_traslados, ajustar_coordenadas_upa, check_post_limpieza
)

def _setup_paths():
    """Agrega el directorio raíz al sys.path para importar scripts/."""
    current = os.path.abspath(os.path.dirname(__file__))
    root = os.path.abspath(os.path.join(current, ".."))
    if root not in sys.path:
        sys.path.append(root)

def _configurar_visualizacion():
    """Aplica estilo visual por defecto a todos los gráficos."""
    sns.set_style("whitegrid")
    plt.rcParams["figure.figsize"] = (10, 6)

def _cargar_datos(data_path, verbose=True):
    """Carga y limpia el dataset de pacientes y reconstruye los traslados."""
    if verbose:
        print("Cargando datos de pacientes...")
    df_pacientes = cargar_datos_pacientes(os.path.join(data_path, "pacientes.xlsx"))
    traslados    = reconstruir_traslados(df_pacientes)
    if verbose:
        print(f"  → {len(df_pacientes):,} registros | {df_pacientes['Id'].nunique():,} pacientes únicos")
        print(f"  → {len(traslados):,} traslados reconstruidos")
    return df_pacientes, traslados

def _cargar_geografia(data_path, verbose=True):
    """Carga coordenadas de hospitales y shapefiles de municipios."""
    if verbose:
        print("Cargando datos geográficos...")

    hosp_coords = cargar_coordenadas(
        os.path.join(data_path, "hospitales_coordenadas.csv")
    )
    hosp_coords = ajustar_coordenadas_upa(hosp_coords)

    municipios = cargar_municipios(
        os.path.join(data_path, "shapefiles/departamento/departamentoPolygon.shp")
    )

    # municipios del AMBA relevantes para el proyecto
    amba_partidos = [
        "QUILMES", "ALMIRANTE BROWN", "FLORENCIO VARELA", "BERAZATEGUI",
        "LANUS", "LOMAS DE ZAMORA", "AVELLANEDA", "MORON", "ITUZAINGO"
    ]
    municipios_amba = municipios[
        municipios["nam_limpio"].isin(amba_partidos)
    ]

    if verbose:
        print(f"  → {len(hosp_coords)} hospitales con coordenadas")
        print(f"  → {len(municipios_amba)} municipios AMBA cargados")

    return hosp_coords, municipios, municipios_amba

def init_notebook(data_path="../data", verbose=True):
    """
    Inicializa el entorno completo de análisis.

    Parámetros
    ----------
    data_path : str
        Ruta a la carpeta de datos (relativa al notebook).
    verbose : bool
        Si True, imprime resumen de carga.

    Retorna
    -------
    dict con claves:
        df_pacientes, traslados, hosp_coords, municipios, municipios_amba
    """
    _setup_paths()

    _configurar_visualizacion()

    df_pacientes, traslados = _cargar_datos(data_path, verbose)
    hosp_coords, municipios, municipios_amba = _cargar_geografia(data_path, verbose)

    if verbose:
        print("\n✓ Entorno listo.\n")
        check_post_limpieza(df_pacientes)

    return {
        "df_pacientes":    df_pacientes,
        "traslados":       traslados,
        "hosp_coords":     hosp_coords,
        "municipios":      municipios,
        "municipios_amba": municipios_amba,
    }


def coords_a_dict(hosp_coords):
    """Convierte un dataframe de coordenadas en diccionario {hospital: (lat, lon)}"""
    return dict(zip(
        hosp_coords["Nombre Hospital"],
        zip(hosp_coords["Latitud"], hosp_coords["Longitud"])
    ))

def cargar_datos_pacientes(path):
    return limpiar_pacientes(pd.read_excel(path))

def cargar_coordenadas(path):
    return limpiar_coordenadas(pd.read_csv(path))

def cargar_municipios(path_shp):
    municipios = gpd.read_file(path_shp)
    municipios["nam_limpio"] = municipios["nam"].apply(limpiar_nombre)
    return municipios

def cargar_provincias(path_shp):
    return gpd.read_file(path_shp)
