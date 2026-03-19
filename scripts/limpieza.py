"""
limpieza.py
-----------
Pipeline de limpieza detallada del dataset de pacientes.
Trabaja con columnas en snake_case (después de renombrar_columnas).

Rol en el proyecto:
    - Renombrar y normalizar columnas al estándar snake_case del proyecto
    - Feature engineering: tipo_egreso, evolucion, episodios
    - Chequeos de calidad (post-limpieza, coherencia de datos)

Nota: las funciones clasificar_egreso y clasificar_evolucion también
están disponibles en bases.py para usarse directamente con columnas originales.
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------
# Renombrado y normalización de columnas
# ---------------------------------------------------------
def renombrar_columnas(df):
    """
    Renombra columnas del Excel original a snake_case consistente.

    Returns
    -------
    pd.DataFrame con columnas renombradas.
    """
    mapping = {
        "Id Hospital":                    "hospital_id",
        "Nombre Hospital":                "hospital_nombre",
        "Id":                             "paciente_id",
        "Fecha inicio":                   "fecha_inicio",
        "Fecha egreso":                   "fecha_egreso",
        "Última actualización":           "ultima_actualizacion",
        "Estado al ingreso":              "estado_ingreso",
        "Tipo al ingreso":                "tipo_ingreso",
        "Último estado":                  "estado_final",
        "Último tipo":                    "tipo_final",
        "Sexo":                           "sexo",
        "Edad":                           "edad",
        "Asistencia Respiratoria Mecánica": "arm",
        "Motivo":                         "motivo_egreso",
        "Operación":                      "operacion",
        "Pasó por Críticas":              "paso_criticas",
        "Pasó por Intermedias":           "paso_intermedias",
        "Pasó por Generales":             "paso_generales",
        "Duracion días":                  "duracion_dias",
        "murio":                          "murio",
    }
    return df.rename(columns=mapping)


def normalizar_strings(df):
    """
    Normaliza variables categóricas: minúsculas, sin espacios, 'nan' → NA.
    Opera sobre columnas en snake_case.
    """
    cols = [
        "estado_ingreso", "estado_final",
        "tipo_ingreso",   "tipo_final",
        "sexo", "motivo_egreso", "operacion"
    ]
    for col in cols:
        if col in df.columns:
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
    Estandariza valores categóricos y filtra tipos de cama inválidos.
    """
    # estado: quita espacios internos
    for col in ["estado_ingreso", "estado_final"]:
        if col in df.columns:
            df[col] = df[col].replace({"ocupadas covid": "ocupadas_covid"})

    # tipos válidos de cama
    tipos_validos = ["criticas", "intermedias", "generales"]
    for col in ["tipo_ingreso", "tipo_final"]:
        if col in df.columns:
            df[col] = df[col].replace({"uti-pediatrica": "criticas"})
            df[col] = df[col].where(df[col].isin(tipos_validos))

    return df


def convertir_tipos(df):
    """
    Convierte columnas a sus tipos de datos correctos.
    Opera sobre columnas en snake_case.
    """
    date_cols = ["fecha_inicio", "fecha_egreso", "ultima_actualizacion"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "edad" in df.columns:
        df["edad"] = pd.to_numeric(df["edad"], errors="coerce")
    if "duracion_dias" in df.columns:
        df["duracion_dias"] = pd.to_numeric(df["duracion_dias"], errors="coerce")

    bool_cols = ["paso_criticas", "paso_intermedias", "paso_generales"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"si": True, "no": False})

    return df


# ---------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------
def clasificar_egreso(x):
    """
    Clasifica el motivo de egreso.
    Retorna: 'muerte', 'alta', 'traslado', 'otro', 'desconocido'.
    Opera sobre valores ya normalizados (minúsculas).
    """
    if pd.isna(x):
        return "desconocido"
    x = str(x).lower().strip()
    if "muert" in x or "fallec" in x:
        return "muerte"
    if "alta" in x:
        return "alta"
    if "traslad" in x:
        return "traslado"
    return "otro"


def clasificar_evolucion(df, col_ingreso="tipo_ingreso", col_final="tipo_final"):
    """
    Agrega columnas de nivel numérico y evolución de complejidad clínica.
    evolucion > 0 → empeoró | < 0 → mejoró | = 0 → igual.
    Opera sobre columnas en snake_case.
    """
    orden = {"generales": 1, "intermedias": 2, "criticas": 3}
    df["nivel_ingreso"] = df[col_ingreso].map(orden)
    df["nivel_final"]   = df[col_final].map(orden)
    df["evolucion"]     = df["nivel_final"] - df["nivel_ingreso"]
    return df


def limpiar_dataset_pro(df):
    """
    Pipeline completo de limpieza y feature engineering (columnas snake_case).

    Pasos:
        1. Renombrar columnas
        2. Normalizar strings categóricos
        3. Estandarizar categorías (uti-pediatrica → criticas, etc.)
        4. Convertir tipos (fechas, numéricos, booleanos)
        5. Clasificar tipo de egreso
        6. Calcular evolución clínica
        7. Flag de datos incompletos

    No elimina filas, solo transforma.
    """
    df = df.copy()
    df = renombrar_columnas(df)
    df = normalizar_strings(df)
    df = estandarizar_categorias(df)
    df = convertir_tipos(df)

    if "motivo_egreso" in df.columns:
        df["tipo_egreso"] = df["motivo_egreso"].apply(clasificar_egreso)
        df["fallecio"]    = df["tipo_egreso"] == "muerte"

    df = clasificar_evolucion(df)

    if "fecha_inicio" in df.columns:
        df["datos_incompletos"] = df["fecha_inicio"].isna()

    return df


# ---------------------------------------------------------
# Chequeos de calidad
# ---------------------------------------------------------
def detectar_problemas(df):
    """
    Detecta problemas básicos en el dataset (opera sobre columnas snake_case).
    """
    print("\n--- PROBLEMAS DETECTADOS ---")
    if "fecha_inicio" in df.columns:
        print(f"Sin fecha_inicio:  {df['fecha_inicio'].isna().sum()}")
    if "fecha_egreso" in df.columns:
        print(f"Sin fecha_egreso:  {df['fecha_egreso'].isna().sum()}")
    if "paciente_id" in df.columns:
        print(f"IDs no numéricos:  {(~df['paciente_id'].astype(str).str.isnumeric()).sum()}")
    if "tipo_final" in df.columns and "paso_criticas" in df.columns:
        mask = (df["tipo_final"] == "criticas") & (df["paso_criticas"] == False)
        print(f"Tipo_final=criticas sin paso_criticas=True: {mask.sum()}")


def check_coherencia(df):
    """
    Compara duración calculada vs. registrada (columnas snake_case).
    """
    if "fecha_inicio" in df.columns and "fecha_egreso" in df.columns and "duracion_dias" in df.columns:
        df = df.copy()
        df["_duracion_calc"] = (df["fecha_egreso"] - df["fecha_inicio"]).dt.days
        diff = df["_duracion_calc"] - df["duracion_dias"]
        print("\nDiferencia duración calculada vs. registrada:")
        print(diff.describe())


def check_post_limpieza(df):
    """
    Resumen rápido post-limpieza (columnas snake_case).
    """
    print("\n--- CHEQUEO POST-LIMPIEZA (snake_case) ---")
    for col, label in [("paciente_id", "Pacientes únicos"),
                       ("hospital_nombre", "Hospitales únicos")]:
        if col in df.columns:
            print(f"{label}: {df[col].nunique()}")
    print(f"Filas: {len(df)}")
    if "tipo_egreso" in df.columns:
        print("\nDistribución tipo_egreso:")
        print(df["tipo_egreso"].value_counts())
    if "evolucion" in df.columns:
        print("\nDistribución evolución clínica:")
        print(df["evolucion"].value_counts())