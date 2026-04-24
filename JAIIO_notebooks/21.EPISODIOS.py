#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Nuestro proyecto trabaja en 3 niveles
# y cada uno necesita reglas distintas:

# 1. Episodio (fila) → una internación en un hospital
# 2. Transición (arista) → movimiento entre hospitales
# 3. Paciente (trayectoria completa) → historia total


# en este archivo:
# BASE 1 — df_base_limpia (episodios)
# - Objetivo: Tener todas las internaciones válidas, sin romper historias

# - ERROR en tu enfoque actual: Estás filtrando pacientes enteros (pacientes_final_ok), cuando acá deberías: NO eliminar pacientes todavía

# - Qué limpiar acá (solo cosas “objetivamente malas”)

#             - filas con:

#             fechas inválidas (fecha_ingreso > fecha_egreso)
#             hospitales missing
#             edad absurda (ej: <0 o >120)
#             motivos claramente basura (error, quizás nan dependiendo contexto)

#             - estandarización:

#             nombres hospitales
#             fechas
#             motivos (lowercase, strip)

#                     PERO:
#                     ❌ NO usar desenlace todavía
#                     ❌ NO eliminar pacientes completos
#                     ❌ NO usar prioridad clínica todavía


# In[1]:


import sys
import os
sys.path.append(os.path.abspath(".."))

import ast
import pandas as pd
import numpy as np
from src.config import *


# In[2]:


# 1. CARGA Y RENOMBRE COMPLETO (Recuperado de tu código original)
# ==============================================================================
df_raw = pd.read_excel("../data/pacientes.xlsx")
hospitales = pd.read_csv("../data/hospitales_coordenadas.csv")

dict_comp = dict(zip(hospitales['Nombre Hospital'], hospitales['complejidad']))
hospitales['color_rgb'] = hospitales['color'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

df_base = df_raw.rename(columns={
    'Id Hospital': 'hospital_id', 'Nombre Hospital': 'hospital_origen',
    'Id': 'paciente_id', 'Fecha inicio': 'fecha_ingreso', 'Fecha egreso': 'fecha_egreso',
    'Estado al ingreso': 'estado_ingreso', 'Tipo al ingreso': 'tipo_ingreso',
    'Último estado': 'estado_ultimo', 'Último tipo': 'tipo_ultimo',
    'Sexo': 'sexo', 'Edad': 'edad', 'Nivel riesgo clínico': 'riesgo_clinico',
    'Nivel riesgo social': 'riesgo_social', 'Enfermedades preexistentes Covid-19': 'comorbilidades_covid',
    'Enfermedades preexistentes pediatría': 'comorbilidades_pediatria', 'Vacuna': 'vacuna',
    'Cant. dosis': 'cantidad_dosis', '1º dosis': 'fecha_dosis_1', '2º dosis': 'fecha_dosis_2',
    'Buscado en el ministerio': 'validado_ministerio', 'Obra social': 'obra_social',
    'Asistencia Respiratoria Mecánica': 'requiere_arm', 'Motivo': 'motivo_egreso',
    'Operación': 'operacion', 'Última actualización': 'fecha_ultima_actualizacion',
    'Pasó por Críticas': 'paso_criticas', 'Pasó por Intermedias': 'paso_intermedias',
    'Pasó por Generales': 'paso_generales'
}).copy()

df_base['hospital_origen'] = df_base['hospital_origen'].replace({
    'Módulo Hospitalario 11- FV': 'Módulo Hospitalario 11 - FV',
    'Módulo Hospitalario  9 - AB': 'Módulo Hospitalario 9 - AB'
}).str.strip()


df_base['fecha_ingreso'] = pd.to_datetime(df_base['fecha_ingreso'], errors='coerce')
df_base['fecha_egreso'] = pd.to_datetime(df_base['fecha_egreso'], errors='coerce')
df_base['edad'] = pd.to_numeric(df_base['edad'], errors='coerce')
df_base['dias_en_nodo'] = (
    (df_base['fecha_egreso'] - df_base['fecha_ingreso'])
    .dt.days
)

df_base = df_base.sort_values(['paciente_id', 'fecha_ingreso'])


# In[3]:


# 2. FLAGS DE VALIDACIÓN (nivel episodio)
# ==============================================================================

# --- validez mínima (estructura del episodio)
df_base['valido_core'] = (
    df_base['paciente_id'].notna() &
    df_base['hospital_origen'].notna() &
    df_base['fecha_egreso'].notna()
)

# --- consistencia de fechas
df_base['fechas_validas'] = (
    (df_base['fecha_ingreso'] <= df_base['fecha_egreso'])
    # &
    # (df_base['fecha_egreso'] - df_base['fecha_ingreso'] >= pd.Timedelta(minutes=5))
)


# In[4]:


# 3. FLAGS DE CALIDAD (NO filtran, solo informan)
# ==============================================================================

# edad fuera de rango razonable
df_base['edad_rara'] = (
    (df_base['edad'] < 0) | (df_base['edad'] > 110)
)

# duración negativa o muy larga
df_base['duracion_negativa'] = df_base['dias_en_nodo'] < 0
df_base['duracion_larga'] = df_base['dias_en_nodo'] > 60  # ajustable

# hospital faltante o vacío
df_base['hospital_raro'] = df_base['hospital_origen'].isna() | (df_base['hospital_origen'] == '')


# In[5]:


# 4. LIMPIEZA DE motivo_egreso (sin eliminar todavía)
# ==============================================================================

# normalizar texto
df_base['motivo_egreso_clean'] = (
    df_base['motivo_egreso']
    .astype(str)
    .str.lower()
    .str.strip()
)

# flag administrativo inválido
df_base['egreso_admin_invalido'] = df_base['motivo_egreso_clean'].str.contains(
    'anulado|error|duplicado', case=False, na=False
)

# clasificación simple (puede crecer después)
def clasificar_egreso(x):
    if pd.isna(x):
        return 'desconocido'
    x = str(x).lower()
    if 'muerte' in x:
        return 'muerte'
    elif 'alta-domiciliaria' in x:
        return 'alta'
    elif 'traslado-extra-sanitario' in x:
        return 'hotel'
    elif 'traslado-otro' in x:
        return 'hospital-externo'
    elif 'traslado-hospital-de-la-red' in x:
        return 'traslado'
    elif 'anulado' in x or 'otro' in x:
        return 'administrativo'
    elif 'traslado-extra-sanitario' in x:
        return 'hotel'
    else:
        return 'administrativo'

df_base['tipo_egreso'] = df_base['motivo_egreso'].apply(clasificar_egreso)


# In[6]:


# 5. CONSTRUCCIÓN DE BASE LIMPIA (mínimamente filtrada)
# ==============================================================================

df_base_limpia = df_base[
    df_base['valido_core'] &
    df_base['fechas_validas']
].copy()


# In[7]:


# 6. CHECKS BÁSICOS (para que mires calidad sin romper nada)
# ==============================================================================

print("Total episodios:", len(df_base))
print("Episodios válidos:", len(df_base_limpia))

print("\n% edad rara:", df_base_limpia['edad_rara'].mean())
print("% sin fecha egreso:", df_base_limpia['fecha_egreso'].isna().mean())
print("% egreso administrativo:", df_base_limpia['egreso_admin_invalido'].mean())

print("\nDuración (días) resumen:")
print(df_base_limpia['dias_en_nodo'].describe())

print("\nTop hospitales:")
print(df_base_limpia['hospital_origen'].value_counts().head(10))


# In[8]:


# esta base responde
# “qué internaciones existieron realmente”
# (o deberian. Para mi hay repetidos que no se como sacar)
    # # faltaria:
    # - resolver duplicados
    # - resolver superposiciones
    # - consistencia longitudinal por paciente


# In[10]:


df_base_limpia.to_excel("../data/final_data/df_base_limpia.xlsx", index=False)
# df_base_limpia.to_parquet("../data/final_data/df_base_limpia.parquet", index=False)


# ### Extra: busqueda de errores o casos raros

# In[11]:


# pacientes que estuvieron la mayor cantidad de tiempo internados
# me llamo la atencion 500 dias asi que reviso esto..
cols = [
    'paciente_id',
    'hospital_origen',
    'fecha_ingreso',
    'fecha_egreso',
    'dias_en_nodo',
    'motivo_egreso',
    'tipo_egreso'
]

df_base_limpia.loc[
    df_base_limpia['dias_en_nodo'] == df_base_limpia['dias_en_nodo'].max(),
    cols
]

df_base_limpia.nlargest(10, 'dias_en_nodo')[cols]

(df_base_limpia['dias_en_nodo'] > 100).mean()


# In[12]:


# pacientes que estuvieron la mayor cantidad de tiempo internados
df_base_limpia.nsmallest(10, 'dias_en_nodo')[cols]
(df_base_limpia['dias_en_nodo'] < 1).mean()


# In[13]:


# distribución de duración
import matplotlib.pyplot as plt

# 1. Calculamos el límite del percentil (ej: 95%)
# Esto ignora el 5% de los casos con estancias extremadamente largas
limite_outliers = df_base_limpia['dias_en_nodo'].quantile(0.95)

# 2. Filtramos los datos
df_filtrado = df_base_limpia[df_base_limpia['dias_en_nodo'] <= limite_outliers]

# 3. Configuramos los bins para que cada uno sea un entero
valor_max = int(df_filtrado['dias_en_nodo'].max())
# Usamos np.arange para crear cortes cada 0.5 para que el entero quede en el centro
bins = np.arange(0, valor_max + 2) - 0.5

# 4. Graficamos
plt.figure(figsize=(12, 6))
plt.hist(df_filtrado['dias_en_nodo'], bins=bins, edgecolor='white', color='#3498db')

# Forzamos a que el eje X muestre los números de 1 en 1
plt.xticks(range(0, valor_max + 1))

plt.title(f'Distribución de Estancia (Corte en {limite_outliers:.1f} días)')
plt.xlabel('Días (cada barra es 1 día entero)')
plt.ylabel('Frecuencia (Nº de casos)')
plt.grid(axis='y', alpha=0.3)
plt.show()

print(f"El gráfico muestra el 95% de los datos. El valor máximo mostrado es {valor_max} días.")


# In[14]:


# 2 mins de diferencia egreso - ingreso

# Calcular la diferencia exacta en minutos
# .total_seconds() / 60 nos da la precisión que buscas
duracion_minutos = (df_base_limpia['fecha_egreso'] - df_base_limpia['fecha_ingreso']).dt.total_seconds() / 60

# Filtrar los que duran 2 minutos o menos (incluye negativos si los hay)
errores_tiempo = df_base_limpia[duracion_minutos <= 2]

# Resultados
total_errores = len(errores_tiempo)
porcentaje_errores = (total_errores / len(df_base_limpia)) * 100

print(f"Detectados {total_errores} registros con duración <= 2 minutos.")
print(f"Representan el {porcentaje_errores:.2f}% del total de la base.")

# Ver una muestra de esos errores para confirmar
print("\nMuestra de posibles errores:")
print(errores_tiempo[['fecha_ingreso', 'fecha_egreso', 'dias_en_nodo']].head())


# In[15]:


# pacientes con muchos episodios
df_base_limpia['paciente_id'].value_counts().head(10)


# In[16]:


# episodios que potencialmente son duplicados
df_base_limpia[
    df_base_limpia.duplicated(
        subset=['paciente_id', 'hospital_origen', 'fecha_ingreso'], ## obs, hay un problema grande con las fechas de ingreso.
        # Para mi se hacian en un momento dado del dia se actualizaban todas
        keep=False
    )
].sort_values(['paciente_id', 'fecha_ingreso']).head(10)


# In[17]:


# hospitales con duracion de estadias mas altos
df_base_limpia.groupby('hospital_origen')['dias_en_nodo'].mean().sort_values(ascending=False).head(10)


# In[18]:


# cuantos hay de cada tipo, para ver cuantos son administrativos
df_base_limpia['tipo_egreso'].value_counts(normalize=True)


# In[19]:


# columnas que NO podemos usar:
print(df_base_limpia.isna().mean().sort_values(ascending=False).head(10))


# In[ ]:




