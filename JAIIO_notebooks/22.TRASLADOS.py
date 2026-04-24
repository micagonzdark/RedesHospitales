#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# BASE 2 — df_traslados (aristas)
# Objetivo

    # Capturar movimientos reales en la red


# Un traslado es:

# dos episodios consecutivos del mismo paciente en hospitales distintos, temporalmente compatibles

# ✅ Entonces tu máscara debería ser:

# ✔️ obligatorio:

    # hospital cambia
    # existe siguiente episodio
    # ventana temporal razonable (tu ±5 días está bien)

# ✔️ opcional:

    # motivo dice traslado → suma confianza, pero no obligatorio
    # Recomendación fuerte

# esta base responde: “¿cómo fluye la red hospitalaria?”


# In[1]:


import sys
import os
sys.path.append(os.path.abspath(".."))

import ast
import pandas as pd
import numpy as np
from src.config import *


# In[2]:


df_base = pd.read_excel("../data/final_data/df_base_limpia.xlsx")


# In[3]:


# 2. NORMALIZACION DE MOTIVO DE EGRESO
# ==============================================================================

def normalizar_motivo(x):
    if pd.isna(x):
        return np.nan
    x = str(x).lower().strip()
    return x

df_base['motivo_egreso_norm'] = df_base['motivo_egreso'].apply(normalizar_motivo)

# palabras clave de traslado (ajustar según dataset real)
KEYWORDS_TRASLADO = [
    'traslado',
    'derivacion',
    'derivación',
    'referencia',
    'transferencia'
]

def es_traslado(motivo):
    if pd.isna(motivo):
        return 0
    return int(any(k in motivo for k in KEYWORDS_TRASLADO))

df_base['flag_motivo_traslado'] = df_base['motivo_egreso_norm'].apply(es_traslado)


# In[4]:


# # 3. DEDUPLICACION TECNICA INGRESO Y EGRESO IGUAL
# # ==============================================================================

# cols_dup = [
#     'paciente_id',
#     'hospital_origen',
#     'fecha_ingreso',
#     'fecha_egreso'
# ]

# df_base['flag_duplicado_exacto'] = df_base.duplicated(subset=cols_dup, keep='first')

# # para construir traslados usamos una version sin duplicados exactos
# df_nodup = df_base[~df_base['flag_duplicado_exacto']].copy()


# ==============================================================================
# 3. DEDUPLICACION POR CERCANIA TEMPORAL (INGRESO Y EGRESO CERCA)
# ==============================================================================

# ordenar bien
df_base = df_base.sort_values([
    'paciente_id',
    'hospital_origen',
    'fecha_ingreso',
    'fecha_egreso'
])

# shift dentro de paciente + hospital
df_base['prev_ingreso'] = df_base.groupby(
    ['paciente_id', 'hospital_origen']
)['fecha_ingreso'].shift(1)

df_base['prev_egreso'] = df_base.groupby(
    ['paciente_id', 'hospital_origen']
)['fecha_egreso'].shift(1)

# diferencias en segundos
df_base['diff_ingreso_seg'] = (
    df_base['fecha_ingreso'] - df_base['prev_ingreso']
).dt.total_seconds().abs()

df_base['diff_egreso_seg'] = (
    df_base['fecha_egreso'] - df_base['prev_egreso']
).dt.total_seconds().abs()

TOL_SEGUNDOS = 60  # podés probar 30, 60, 120
# FLAG DUPLICADO
df_base['flag_duplicado_cercano'] = (
    (df_base['diff_ingreso_seg'] <= TOL_SEGUNDOS) &
    (df_base['diff_egreso_seg'] <= TOL_SEGUNDOS)
)
# CONSTRUCCION SIN ESTOS DUPLICADOS
df_nodup = df_base[~df_base['flag_duplicado_cercano']].copy()


# In[5]:


# 4. CONSTRUCCION DE PARES CONSECUTIVOS
# ==============================================================================

df_nodup = df_nodup.sort_values(['paciente_id', 'fecha_ingreso'])

# shift
df_nodup['hospital_destino'] = df_nodup.groupby('paciente_id')['hospital_origen'].shift(-1)
df_nodup['fecha_ingreso_destino'] = df_nodup.groupby('paciente_id')['fecha_ingreso'].shift(-1)
df_nodup['edad_destino'] = df_nodup.groupby('paciente_id')['edad'].shift(-1)

# también motivo del origen ya lo tenemos


# In[6]:


# 5. VARIABLES DERIVADAS (DELTA ROBUSTO)
# ==============================================================================

# delta en segundos (base)
df_nodup['delta_segundos'] = (
    df_nodup['fecha_ingreso_destino'] - df_nodup['fecha_egreso']
).dt.total_seconds()

# corrección por tolerancia
df_nodup['delta_segundos_corr'] = df_nodup['delta_segundos'].where(
    df_nodup['delta_segundos'].abs() > TOL_DELTA_SEGUNDOS,
    0
)

# delta en días ENTEROS (evita floats raros)
df_nodup['delta_dias'] = (
    df_nodup['delta_segundos_corr'] / (60 * 60 * 24)
).round().astype('Int64')

# delta edad
df_nodup['delta_edad'] = df_nodup['edad_destino'] - df_nodup['edad']


# ==============================================================================
# 5.B CLASIFICACION TEMPORAL DEL TRASLADO
# ==============================================================================

# en horas (más interpretable que segundos)
df_nodup['delta_horas'] = df_nodup['delta_segundos_corr'] / 3600

# clasificacion
df_nodup['tipo_traslado'] = np.select(
    [
        df_nodup['delta_segundos_corr'] == 0,
        (df_nodup['delta_horas'] > 0) & (df_nodup['delta_horas'] <= 24),
        df_nodup['delta_horas'] > 24
    ],
    [
        'inmediato',   # mismo evento (<= 5 min)
        'rapido',      # dentro del mismo día
        'diferido'     # más de 1 día
    ],
    default='otro'  # incluye negativos raros o edge cases
)


# In[7]:


#  6. FLAGS DE CALIDAD
# ==============================================================================

df_nodup['flag_mismo_hospital'] = (
    df_nodup['hospital_origen'] == df_nodup['hospital_destino']
)

df_nodup['flag_fechas_faltantes'] = (
    df_nodup['fecha_egreso'].isna() |
    df_nodup['fecha_ingreso_destino'].isna()
)

df_nodup['flag_overlap'] = df_nodup['delta_dias'] < 0
df_nodup['flag_overlap_extremo'] = df_nodup['delta_dias'] < -2

df_nodup['flag_gap_corto'] = df_nodup['delta_dias'].between(0, 2)
df_nodup['flag_gap_medio'] = df_nodup['delta_dias'].between(3, 5)
df_nodup['flag_gap_largo'] = df_nodup['delta_dias'] > 5

df_nodup['flag_edad_inconsistente'] = df_nodup['delta_edad'].abs() > 2

df_nodup['flag_inmediato'] = df_nodup['tipo_traslado'] == 'inmediato'
df_nodup['flag_diferido'] = df_nodup['tipo_traslado'] == 'diferido'


# In[8]:


#  7. FILTROS BASE (SIN MOTIVO)
# ==============================================================================

cond_base = (
    (df_nodup['hospital_destino'].notna()) &
    (~df_nodup['flag_mismo_hospital']) &
    (~df_nodup['flag_fechas_faltantes']) &
    (df_nodup['delta_dias'] >= -5) &
    (df_nodup['delta_dias'] <= 30) &
    (~df_nodup['flag_edad_inconsistente'])
)

df_pares_validos = df_nodup[cond_base].copy()


# In[9]:


# 8. DF TRASLADOS LOOSE
# ==============================================================================

df_traslados_loose = df_pares_validos.copy()


# In[10]:


# 9. DF TRASLADOS STRICT
# ==============================================================================

cond_motivo = df_pares_validos['flag_motivo_traslado'] == 1

df_traslados_strict = df_pares_validos[cond_motivo].copy()


# In[11]:


# 10. COLUMNAS FINALES
# ==============================================================================

cols_finales = [
    'paciente_id',
    'hospital_origen',
    'hospital_destino',
    'fecha_egreso',
    'fecha_ingreso_destino',
    'delta_dias',
    'edad',
    'edad_destino',
    'delta_edad',
    'flag_motivo_traslado',
    'flag_overlap',
    'flag_overlap_extremo',
    'flag_gap_corto',
    'flag_gap_medio',
    'flag_gap_largo',
    'flag_edad_inconsistente',
    'delta_segundos_corr',
    'tipo_traslado',
    'delta_horas',
    'flag_inmediato',
    'flag_diferido'
]

df_traslados_loose = df_traslados_loose[cols_finales].rename(columns={
    'fecha_egreso': 'fecha_egreso_origen'
})

df_traslados_strict = df_traslados_strict[cols_finales].rename(columns={
    'fecha_egreso': 'fecha_egreso_origen'
})


# In[13]:


df_traslados_loose.to_excel("../data/final_data/df_traslados_loose.xlsx", index=False)

df_traslados_strict.to_excel("../data/final_data/df_traslados_strict.xlsx", index=False)

# df_nodup.to_parquet("../data/debug/df_nodup_debug.parquet")


# ### verificaciones y explroacion

# In[14]:


# SANITY CHECKS GENERALES
# ==============================================================================

print("=== TAMAÑOS ===")
print("Base original:", len(df_base))
print("Sin duplicados:", len(df_nodup))
print("Traslados loose:", len(df_traslados_loose))
print("Traslados strict:", len(df_traslados_strict))


print("\n=== DELTA DIAS (LOOSE) ===")
print(df_traslados_loose['delta_dias'].describe())

print("\n=== DELTA DIAS (STRICT) ===")
print(df_traslados_strict['delta_dias'].describe())


print("\n=== DELTA EDAD ===")
print(df_traslados_loose['delta_edad'].describe())


print("\n=== PROPORCION CON MOTIVO ===")
print(df_traslados_loose['flag_motivo_traslado'].value_counts(normalize=True))


print("\n=== EJEMPLOS RANDOM ===")
display(df_traslados_loose.sample(5))


print("\n=== CHEQUEO CLAVE: hospitales distintos ===")
print((df_traslados_loose['hospital_origen'] == df_traslados_loose['hospital_destino']).sum())


print("\n=== CHEQUEO EDAD ===")
print((df_traslados_loose['delta_edad'].abs() > 2).sum())


print("\n=== OVERLAPS ===")
print(df_traslados_loose['flag_overlap'].value_counts())


print("\n=== TOP FLUJOS A->B ===")
print(
    df_traslados_loose
    .groupby(['hospital_origen', 'hospital_destino'])
    .size()
    .sort_values(ascending=False)
    .head(10)
)


# In[15]:


print("\n=== DISTRIBUCION POR DELTA ===")
print(df_traslados_loose['delta_dias'].value_counts().sort_index())


# In[16]:


print("\n=== TIPOS DE TRASLADO ===")
print(df_traslados_loose['tipo_traslado'].value_counts(normalize=True))

