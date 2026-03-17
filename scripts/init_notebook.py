import os
import sys

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

# asegurar import de scripts si se corre desde notebooks
def _setup_paths():
    current = os.path.abspath(os.path.dirname(__file__))
    root = os.path.abspath(os.path.join(current, ".."))
    if root not in sys.path:
        sys.path.append(root)


def _configurar_visualizacion():
    sns.set_style("whitegrid")
    plt.rcParams["figure.figsize"] = (10, 6)


def _cargar_datos(bases, data_path, verbose=True):
    if verbose:
        print("Cargando datos principales...")

    df_pacientes = bases.cargar_datos_pacientes(
        os.path.join(data_path, "pacientes.xlsx")
    )
    traslados = bases.reconstruir_traslados(df_pacientes)

    if verbose:
        print("Pacientes y traslados cargados.")

    return df_pacientes, traslados


def _cargar_geografia(bases, data_path, verbose=True):
    if verbose:
        print("Cargando datos geográficos...")

    hosp_coords = bases.cargar_coordenadas(
        os.path.join(data_path, "hospitales_coordenadas.csv")
    )
    hosp_coords = bases.ajustar_coordenadas_upa(hosp_coords)

    municipios = bases.cargar_municipios(
        os.path.join(
            data_path,
            "shapefiles/departamento/departamentoPolygon.shp"
        )
    )

    municipios_amba = municipios[
        municipios["in1"].astype(str).str.startswith(("0"))
    ]

    amba_partidos_caso = [
        "QUILMES", "ALMIRANTE BROWN",
        "FLORENCIO VARELA", "BERAZATEGUI",
        "LANUS", "LOMAS DE ZAMORA",
        "AVELLANEDA", "MORON", "ITUZAINGO"
    ]

    municipios_amba = municipios_amba[
        municipios_amba["nam_limpio"].isin(amba_partidos_caso)
    ]

    if verbose:
        print("Datos geográficos cargados.")

    return hosp_coords, municipios, municipios_amba


def init_notebook(data_path="../data", verbose=True):
    """
    inicializa todo el entorno de analisis
    
    devuelve un dict con todos los objetos cargados
    """

    _setup_paths()

    from . import bases  # import aca para evitar problemas de path

    _configurar_visualizacion()

    df_pacientes, traslados = _cargar_datos(
        bases, data_path, verbose
    )

    hosp_coords, municipios, municipios_amba = _cargar_geografia(
        bases, data_path, verbose
    )

    return {
        "df_pacientes": df_pacientes,
        "traslados": traslados,
        "hosp_coords": hosp_coords,
        "municipios": municipios,
        "municipios_amba": municipios_amba,
    }