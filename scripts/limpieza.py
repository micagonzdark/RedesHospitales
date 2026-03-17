##########################################
# # # # # # Limpieza principal # # # # # #
##########################################

import pandas as pd
import numpy as np
import re
import unicodedata


# ---------------------------------------------------------
# funciones de limpieza y carga de datos
# ---------------------------------------------------------
def limpiar_dataset_pro(df):
    """
    Ejecuta el pipeline completo de limpieza y feature engineering
    sobre el dataset de pacientes.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset original de pacientes.

    Returns
    -------
    pd.DataFrame
        Dataset limpio con variables derivadas listas para análisis.

    Notas
    -----
    - No elimina filas (solo transforma).
    - Agrega variables clave como 'tipo_egreso', 'fallecio' y 'evolucion'.
    """

    df = df.copy()

    # 1. renombrar columnas
    df = renombrar_columnas(df)

    # 2. normalizar strings
    df = normalizar_strings(df)

    # 3. tipos (nivel de cuidado)
    df["tipo_ingreso"] = df["tipo_ingreso"].replace({
        "uti-pediatrica": "criticas"
    })

    df["tipo_final"] = df["tipo_final"].replace({
        "uti-pediatrica": "criticas"
    })

    # 4. convertir booleanos
    for col in ["paso_criticas", "paso_intermedias", "paso_generales"]:
        df[col] = df[col].map({
            "si": True,
            "no": False
        })

    # 5. fechas y numeros
    df["fecha_inicio"] = pd.to_datetime(df["fecha_inicio"], errors="coerce")
    df["fecha_egreso"] = pd.to_datetime(df["fecha_egreso"], errors="coerce")
    df["ultima_actualizacion"] = pd.to_datetime(df["ultima_actualizacion"], errors="coerce")

    df["edad"] = pd.to_numeric(df["edad"], errors="coerce")
    df["duracion_dias"] = pd.to_numeric(df["duracion_dias"], errors="coerce")

    # 6. clasificar egreso (MUY IMPORTANTE)
    def clasificar_egreso(x):
        if pd.isna(x):
            return "desconocido"
        if x == "muerte":
            return "muerte"
        if x == "alta-domiciliaria":
            return "alta"
        if "traslado" in x:
            return "traslado"
        if x in ["otro", "anulado"]:
            return "otro"
        return "otro"

    df["tipo_egreso"] = df["motivo_egreso"].apply(clasificar_egreso)

    # 7. variable outcome final
    df["fallecio"] = df["tipo_egreso"] == "muerte"

    # 8. feature: evolucion del paciente
    orden = {"generales": 1, "intermedias": 2, "criticas": 3}

    df["nivel_ingreso"] = df["tipo_ingreso"].map(orden)
    df["nivel_final"] = df["tipo_final"].map(orden)

    df["evolucion"] = df["nivel_final"] - df["nivel_ingreso"]

    # interpretación:
    # >0 empeoró
    # <0 mejoró
    # =0 igual

    # 9. flag datos incompletos
    df["datos_incompletos"] = df["fecha_inicio"].isna()

    return df


# ---------------------------------------------------------
# funciones de limpieza y carga de datos
# ---------------------------------------------------------
def renombrar_columnas(df):
    """
    Renombra columnas a un formato consistente (snake_case).

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """
    mapping = {
        "Id Hospital": "hospital_id",
        "Nombre Hospital": "hospital_nombre",
        "Id": "paciente_id",

        "Fecha inicio": "fecha_inicio",
        "Fecha egreso": "fecha_egreso",
        "Última actualización": "ultima_actualizacion",

        "Estado al ingreso": "estado_ingreso",
        "Tipo al ingreso": "tipo_ingreso",

        "Último estado": "estado_final",
        "Último tipo": "tipo_final",

        "Sexo": "sexo",
        "Edad": "edad",

        "Asistencia Respiratoria Mecánica": "arm",

        "Motivo": "motivo_egreso",
        "Operación": "operacion",

        "Pasó por Críticas": "paso_criticas",
        "Pasó por Intermedias": "paso_intermedias",
        "Pasó por Generales": "paso_generales",

        "Duracion días": "duracion_dias",
        "murio": "murio"
    }

    df = df.rename(columns=mapping)
    return df

def normalizar_strings(df):
    """
    Normaliza variables categóricas:
    - pasa a minúsculas
    - elimina espacios
    - convierte 'nan' string a NA real

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """

    cols = [
        "estado_ingreso", "estado_final",
        "tipo_ingreso", "tipo_final",
        "sexo", "motivo_egreso", "operacion"
    ]

    for col in cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.lower()
            .str.strip()
            .replace("nan", pd.NA)
        )

    return df


def estandarizar_categorias(df):
    """
    Estandariza valores categóricos y filtra tipos inválidos.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """
    # estados
    df["estado_ingreso"] = df["estado_ingreso"].replace({
        "ocupadas covid": "ocupadas_covid"
    })
    df["estado_final"] = df["estado_final"].replace({
        "ocupadas covid": "ocupadas_covid"
    })

    # tipos
    tipos_validos = ["criticas", "intermedias", "generales"]
    df["tipo_ingreso"] = df["tipo_ingreso"].where(df["tipo_ingreso"].isin(tipos_validos))
    df["tipo_final"] = df["tipo_final"].where(df["tipo_final"].isin(tipos_validos))

    return df

def convertir_tipos(df):
    """
    Convierte columnas a tipos de datos correctos:
    - fechas a datetime
    - numéricos a float/int
    - booleanos a True/False

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """
    # fechas
    df["fecha_inicio"] = pd.to_datetime(df["fecha_inicio"], errors="coerce")
    df["fecha_egreso"] = pd.to_datetime(df["fecha_egreso"], errors="coerce")
    df["ultima_actualizacion"] = pd.to_datetime(df["ultima_actualizacion"], errors="coerce")

    # numéricos
    df["edad"] = pd.to_numeric(df["edad"], errors="coerce")
    df["duracion_dias"] = pd.to_numeric(df["duracion_dias"], errors="coerce")

    # booleanos
    bool_cols = ["paso_criticas", "paso_intermedias", "paso_generales"]

    for col in bool_cols:
        df[col] = df[col].map({
            "si": True,
            "no": False
        })

    return df

def detectar_problemas(df):
    """
    Detecta problemas y chequeos básicos en el dataset.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    None
    """
    print("\n--- PROBLEMAS ---")

    # pacientes sin fecha inicio
    print("\nSin fecha inicio:")
    print(df["fecha_inicio"].isna().sum())

    # sin fecha egreso pero con duración
    print("\nDuración sin egreso:")
    print(df[(df["fecha_egreso"].isna()) & (df["duracion_dias"].notna())].shape[0])

    # ids raros
    print("\nIDs no numéricos:")
    print(df[~df["paciente_id"].astype(str).str.isnumeric()].head())

    # inconsistencias tipo
    print("\nTipo final distinto sin haber pasado:")
    mask = (
        (df["tipo_final"] == "criticas") &
        (df["paso_criticas"] == False)
    )
    print(df[mask].shape[0])


def check_coherencia(df):
    """
    Chequea coherencia entre variables derivadas.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    None
    """
    # duración vs fechas
    df["duracion_calculada"] = (df["fecha_egreso"] - df["fecha_inicio"]).dt.days

    print("\nDiferencias duración:")
    print((df["duracion_calculada"] - df["duracion_dias"]).describe())


# ---------------------------------------------------------
# feature engineering
# ---------------------------------------------------------

def clasificar_egreso(x):
    """
    Clasifica el tipo de egreso del paciente.

    Parameters
    ----------
    x : str
        Valor de la columna 'motivo_egreso'.

    Returns
    -------
    str
        Categoría del egreso: 'muerte', 'alta', 'traslado', 'otro', 'desconocido'.
    """
    if pd.isna(x):
        return "desconocido"
    if x == "muerte":
        return "muerte"
    if x == "alta-domiciliaria":
        return "alta"
    if "traslado" in x:
        return "traslado"
    if x in ["otro", "anulado"]:
        return "otro"
    return "otro"

def clasificar_evolucion(df):
    """
    Clasifica la evolución del paciente según el tipo de unidad.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        DataFrame con columnas 'nivel_ingreso', 'nivel_final' y 'evolucion'.
    """
    orden = {"generales": 1, "intermedias": 2, "criticas": 3}

    df["nivel_ingreso"] = df["tipo_ingreso"].map(orden)
    df["nivel_final"] = df["tipo_final"].map(orden)

    df["evolucion"] = df["nivel_final"] - df["nivel_ingreso"]

    # interpretación:
    # >0 empeoró
    # <0 mejoró
    # =0 igual

    return df


# ---------------------------------------------------------
# chequeos finales
# ---------------------------------------------------------

def detectar_problemas(df):
    """
    Detecta problemas y chequeos básicos en el dataset.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    None
    """
    print("\n--- PROBLEMAS ---")

    # pacientes sin fecha inicio
    print("\nSin fecha inicio:")
    print(df["fecha_inicio"].isna().sum())

    # sin fecha egreso pero con duración
    print("\nDuración sin egreso:")
    print(df[(df["fecha_egreso"].isna()) & (df["duracion_dias"].notna())].shape[0])

    # ids raros
    print("\nIDs no numéricos:")
    print(df[~df["paciente_id"].astype(str).str.isnumeric()].head())

    # inconsistencias tipo
    print("\nTipo final distinto sin haber pasado:")
    mask = (
        (df["tipo_final"] == "criticas") &
        (df["paso_criticas"] == False)
    )
    print(df[mask].shape[0])


def check_coherencia(df):
    """
    Chequea coherencia entre variables derivadas.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    None
    """
    # duración vs fechas
    df["duracion_calculada"] = (df["fecha_egreso"] - df["fecha_inicio"]).dt.days

    print("\nDiferencias duración:")
    print((df["duracion_calculada"] - df["duracion_dias"]).describe())


def check_post_limpieza(df):
    """
    Realiza chequeos post-limpieza en el dataset.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    None
    """
    print("\n--- CHEQUEOS POST-LIMPIEZA ---")

    # 1. tipos de datos
    print("\nTipos de datos:")
    print(df.dtypes)

    # 2. valores nulos
    print("\nValores nulos:")
    print(df.isna().sum())

    # 3. filas duplicadas
    print("\nFilas duplicadas:")
    print(df.duplicated().sum())

    # 4. pacientes únicos
    print("\nPacientes únicos:")
    print(df["paciente_id"].nunique())

    # 5. hospitales únicos
    print("\nHospitales únicos:")
    print(df["hospital_nombre"].nunique())

    # 6. distribución de evolucion
    print("\nDistribución de evolucion:")
    print(df["evolucion"].value_counts())

    # 7. fallecidos
    print("\nFallecidos:")
    print(df["fallecio"].value_counts())

    # 8. duraciones
    print("\nDuración (días):")
    print(df["duracion_dias"].describe())