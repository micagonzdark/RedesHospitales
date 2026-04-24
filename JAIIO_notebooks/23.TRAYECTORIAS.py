#!/usr/bin/env python
# coding: utf-8

# # Construcción de df_pacientes_trayectorias
# Este notebook construye la base `df_pacientes_trayectorias` a partir de `df_base_limpia` (episodios) y `df_traslados_strict` (transiciones).
# Cada fila representará **un paciente con su trayectoria hospitalaria**.
# 
# Se implementarán y compararán dos metodologías:
# 1. **Metodología 1 — Anclada en Traslados (Principal)**
# 2. **Metodología 2 — Desde Episodios (Alternativa)**
# 

# In[1]:


import sys
import os
sys.path.append(os.path.abspath(".."))

import pandas as pd
import numpy as np
from src.config import *

# Carga de datos
df_base = pd.read_excel("../data/final_data/df_base_limpia.xlsx")
df_traslados = pd.read_excel("../data/final_data/df_traslados_strict.xlsx")

# Ordenar
df_base['fecha_ingreso'] = pd.to_datetime(df_base['fecha_ingreso'])
df_base['fecha_egreso'] = pd.to_datetime(df_base['fecha_egreso'])
df_base = df_base.sort_values(['paciente_id', 'fecha_ingreso']).copy()

df_traslados['fecha_egreso_origen'] = pd.to_datetime(df_traslados['fecha_egreso_origen'])
df_traslados['fecha_ingreso_destino'] = pd.to_datetime(df_traslados['fecha_ingreso_destino'])


# ## 1. Limpieza (nivel paciente — filtros estrictos)
# Aplicamos filtros a `df_base` para obtener una lista de `pacientes_validos`.

# In[2]:


# --- fechas incompletas
df_base['flag_fechas_incompletas'] = df_base['fecha_ingreso'].isna() | df_base['fecha_egreso'].isna()

# --- consistencia temporal (tolerancia de 10 mins)
TOL_MINUTOS = 10
df_base['delta_min'] = (df_base['fecha_egreso'] - df_base['fecha_ingreso']).dt.total_seconds() / 60
df_base['flag_fechas_invalidas'] = df_base['delta_min'] < -TOL_MINUTOS

# --- consistencia de edad (delta > 2)
df_base['edad_next'] = df_base.groupby('paciente_id')['edad'].shift(-1)
df_base['delta_edad_episodios'] = df_base['edad_next'] - df_base['edad']
df_base['flag_edad_inconsistente'] = df_base['delta_edad_episodios'].abs() > 2

# --- egreso administrativo final
idx_last = df_base.groupby('paciente_id')['fecha_ingreso'].idxmax()
df_last = df_base.loc[idx_last, ['paciente_id', 'tipo_egreso']].copy()
df_last['flag_fin_admin'] = df_last['tipo_egreso'] == 'administrativo'

# --- agregación por paciente
df_flags_paciente = df_base.groupby('paciente_id').agg({
    'flag_fechas_incompletas': 'max',
    'flag_fechas_invalidas': 'max',
    'flag_edad_inconsistente': 'max'
}).reset_index()

df_flags_paciente = df_flags_paciente.merge(df_last[['paciente_id', 'flag_fin_admin']], on='paciente_id', how='left')

# paciente válido si no incumple ninguna regla
df_flags_paciente['paciente_valido'] = (
    ~df_flags_paciente['flag_fechas_incompletas'] &
    ~df_flags_paciente['flag_fechas_invalidas'] &
    ~df_flags_paciente['flag_edad_inconsistente'] &
    ~df_flags_paciente['flag_fin_admin']
)

pacientes_validos = df_flags_paciente.loc[df_flags_paciente['paciente_valido'], 'paciente_id']
df_base_filtrada = df_base[df_base['paciente_id'].isin(pacientes_validos)].copy()

print(f"Total pacientes originales: {df_base['paciente_id'].nunique()}")
print(f"Total pacientes válidos: {len(pacientes_validos)}")


# # METODOLOGÍA 1 — ANCLADA EN TRASLADOS (PRINCIPAL)

# In[3]:


# 2. Trayectorias con múltiples hospitales (DESDE TRASLADOS)
df_traslados_filtrado = df_traslados[df_traslados['paciente_id'].isin(pacientes_validos)].copy()
df_traslados_filtrado = df_traslados_filtrado.sort_values(['paciente_id', 'fecha_egreso_origen'])

pacientes_con_traslado = df_traslados_filtrado['paciente_id'].unique()
pacientes_sin_traslado = list(set(pacientes_validos) - set(pacientes_con_traslado))

def construir_trayectoria_m1(grp):
    hospitales = []
    flags = {
        'salto_inconsistente': 0,
        'loop': 0,
        'duplicado_consecutivo': 0
    }
    
    current_hospital = grp.iloc[0]['hospital_origen']
    hospitales.append(current_hospital)
    
    for _, row in grp.iterrows():
        origen = row['hospital_origen']
        destino = row['hospital_destino']
        
        if origen != current_hospital:
            flags['salto_inconsistente'] = 1
        
        if destino == current_hospital:
            flags['duplicado_consecutivo'] = 1
        elif destino in hospitales:
            flags['loop'] = 1
            
        hospitales.append(destino)
        current_hospital = destino
        
    # Eliminar duplicados consecutivos
    hospitales_limpios = [hospitales[0]]
    for h in hospitales[1:]:
        if h != hospitales_limpios[-1]:
            hospitales_limpios.append(h)
            
    return pd.Series({
        'trayectoria_hospitalaria': str(hospitales_limpios),
        'hospital_inicio': hospitales_limpios[0],
        'hospital_final': hospitales_limpios[-1],
        'n_hospitales_unicos': len(set(hospitales_limpios)),
        'flag_salto_inconsistente': flags['salto_inconsistente'],
        'flag_loop': flags['loop'],
        'flag_duplicado_consecutivo': flags['duplicado_consecutivo']
    })

df_tray_conectadas = df_traslados_filtrado.groupby('paciente_id').apply(construir_trayectoria_m1).reset_index()


# In[4]:


# 3. Trayectorias de un solo hospital
df_triviales = df_base_filtrada[df_base_filtrada['paciente_id'].isin(pacientes_sin_traslado)].copy()

def trayectoria_trivial(grp):
    h_seq = grp.sort_values('fecha_ingreso')['hospital_origen'].tolist()
    # colapsar repetidos
    hospitales_limpios = [h_seq[0]]
    for h in h_seq[1:]:
        if h != hospitales_limpios[-1]:
            hospitales_limpios.append(h)
            
    return pd.Series({
        'trayectoria_hospitalaria': str(hospitales_limpios),
        'hospital_inicio': hospitales_limpios[0],
        'hospital_final': hospitales_limpios[-1],
        'n_hospitales_unicos': len(set(hospitales_limpios)),
        'flag_salto_inconsistente': 0,
        'flag_loop': 0,
        'flag_duplicado_consecutivo': 0
    })

if len(df_triviales) > 0:
    df_tray_triviales = df_triviales.groupby('paciente_id').apply(trayectoria_trivial).reset_index()
else:
    df_tray_triviales = pd.DataFrame()

# 4. Unificación
df_tray_v1 = pd.concat([df_tray_conectadas, df_tray_triviales], ignore_index=True)


# In[5]:


# 5. Enriquecimiento y 6. Desenlace
df_metrics = df_base_filtrada.groupby('paciente_id').agg({
    'fecha_ingreso': 'min',
    'fecha_egreso': 'max',
    'hospital_origen': 'count'
}).rename(columns={
    'fecha_ingreso': 'fecha_primer_ingreso',
    'fecha_egreso': 'fecha_ultimo_egreso',
    'hospital_origen': 'n_episodios'
}).reset_index()

df_metrics['duracion_total'] = (df_metrics['fecha_ultimo_egreso'] - df_metrics['fecha_primer_ingreso']).dt.days

def calcular_desenlace(grp):
    grp = grp.sort_values('fecha_ingreso')
    muerte = grp[grp['tipo_egreso'] == 'muerte']
    
    if len(muerte) > 0:
        return pd.Series({'desenlace': 'muerte'})
    
    ultimo = grp.iloc[-1]['tipo_egreso']
    if pd.isna(ultimo) or ultimo == '':
        return pd.Series({'desenlace': 'desconocido'})
    
    return pd.Series({'desenlace': ultimo})

df_desenlace = df_base_filtrada.groupby('paciente_id').apply(calcular_desenlace).reset_index()

# Merge Final M1
df_pacientes_trayectorias_v1 = df_tray_v1.merge(df_metrics, on='paciente_id', how='left').merge(df_desenlace, on='paciente_id', how='left')
df_pacientes_trayectorias_v1.to_excel("../data/final_data/df_pacientes_trayectorias_v1.xlsx", index=False)


# # METODOLOGÍA 2 — DESDE EPISODIOS (ALTERNATIVA)

# In[6]:


# 2. Construcción directa desde df_base_limpia
def construir_trayectoria_m2(grp):
    grp = grp.sort_values('fecha_ingreso')
    
    hospitales = grp['hospital_origen'].tolist()
    fechas_in = grp['fecha_ingreso'].tolist()
    fechas_out = grp['fecha_egreso'].tolist()
    
    flags = {
        'overlap': 0,
        'gap_grande': 0
    }
    
    hospitales_limpios = [hospitales[0]]
    
    for i in range(1, len(grp)):
        prev_out = fechas_out[i-1]
        curr_in = fechas_in[i]
        
        delta_dias = (curr_in - prev_out).total_seconds() / (3600*24)
        
        if delta_dias < 0:
            flags['overlap'] = 1
        elif delta_dias > 5:
            flags['gap_grande'] = 1
            
        if hospitales[i] != hospitales_limpios[-1]:
            hospitales_limpios.append(hospitales[i])
            
    return pd.Series({
        'trayectoria_hospitalaria': str(hospitales_limpios),
        'hospital_inicio': hospitales_limpios[0],
        'hospital_final': hospitales_limpios[-1],
        'n_hospitales_unicos': len(set(hospitales_limpios)),
        'flag_overlap': flags['overlap'],
        'flag_gap_grande': flags['gap_grande']
    })

df_tray_v2 = df_base_filtrada.groupby('paciente_id').apply(construir_trayectoria_m2).reset_index()

df_pacientes_trayectorias_v2 = df_tray_v2.merge(df_metrics, on='paciente_id', how='left').merge(df_desenlace, on='paciente_id', how='left')
df_pacientes_trayectorias_v2.to_excel("../data/final_data/df_pacientes_trayectorias_v2.xlsx", index=False)


# # ⚖️ COMPARACIÓN ENTRE METODOLOGÍAS

# In[7]:


# 1. Cobertura y 2. Trayectorias
print("=== METODOLOGÍA 1 (Anclada en Traslados) ===")
print(f"Pacientes: {len(df_pacientes_trayectorias_v1)}")
print(f"Hospitales únicos promedio: {df_pacientes_trayectorias_v1['n_hospitales_unicos'].mean():.2f}")
print(f"Deselance muerte: {(df_pacientes_trayectorias_v1['desenlace'] == 'muerte').sum()}")

print("\n=== METODOLOGÍA 2 (Desde Episodios) ===")
print(f"Pacientes: {len(df_pacientes_trayectorias_v2)}")
print(f"Hospitales únicos promedio: {df_pacientes_trayectorias_v2['n_hospitales_unicos'].mean():.2f}")
print(f"Deselance muerte: {(df_pacientes_trayectorias_v2['desenlace'] == 'muerte').sum()}")

# 3. Diferencias estructurales
df_comp = df_pacientes_trayectorias_v1[['paciente_id', 'trayectoria_hospitalaria', 'hospital_final', 'desenlace']].merge(
    df_pacientes_trayectorias_v2[['paciente_id', 'trayectoria_hospitalaria', 'hospital_final', 'desenlace']],
    on='paciente_id', suffixes=('_v1', '_v2')
)

df_comp['diff_trayectoria'] = df_comp['trayectoria_hospitalaria_v1'] != df_comp['trayectoria_hospitalaria_v2']
df_comp['diff_hospital_final'] = df_comp['hospital_final_v1'] != df_comp['hospital_final_v2']
df_comp['diff_desenlace'] = df_comp['desenlace_v1'] != df_comp['desenlace_v2']

print("\n=== DIFERENCIAS ESTRUCTURALES ===")
print(f"Diferencia en trayectoria: {df_comp['diff_trayectoria'].sum()} pacientes")
print(f"Diferencia en hospital final: {df_comp['diff_hospital_final'].sum()} pacientes")
print(f"Diferencia en desenlace: {df_comp['diff_desenlace'].sum()} pacientes")


# In[8]:


# 4. Casos conflictivos (MUY IMPORTANTE)
conflictos = df_comp[df_comp['diff_trayectoria']].head()

print("Ejemplos de diferencias en trayectorias:")
for _, row in conflictos.iterrows():
    print(f"\nPaciente: {row['paciente_id']}")
    print(f"V1: {row['trayectoria_hospitalaria_v1']}")
    print(f"V2: {row['trayectoria_hospitalaria_v2']}")


# ## 5. Conclusión esperada
# 
# **¿Qué metodología representa mejor la red hospitalaria?**
# La **Metodología 1 (Anclada en Traslados)** representa mejor el verdadero flujo logístico de la red. Al depender explícitamente de los "pares" de episodios validados y verificados temporalmente (y filtrados por saltos/overlaps en `22.TRASLADOS.ipynb`), evitamos conectar internaciones aisladas en el tiempo que un paciente pueda tener a lo largo de los años por motivos no relacionados. 
# 
# **¿Cuál es más robusta a errores administrativos?**
# La **Metodología 1**. Al usar `df_traslados_strict`, que exige un "motivo de traslado" validado por el sistema o por tiempos logísticos consistentes, mitigamos el ruido introducido por altas mal cargadas o episodios fragmentados dentro del mismo hospital o red. La Metodología 2 es susceptible a falsas derivaciones: si un paciente recibe un alta y luego de 4 meses vuelve a otro hospital, la V2 lo considera una trayectoria conectada que fluye, lo cual es incorrecto a nivel operativo de derivaciones críticas.
# 
# **¿Qué sesgos introduce cada una?**
# - **Metodología 1 (Sesgo de omisión):** Puede perder "traslados reales" si el origen no documentó bien la salida o si hay un gap administrativo justo mayor a la tolerancia, cayendo en pacientes con trayectorias triviales cuando en realidad fluyeron.
# - **Metodología 2 (Sesgo de falsa conectividad):** Tiende a sobre-conectar episodios. Una persona con enfermedades crónicas puede asistir a múltiples hospitales durante 3 años, y la Metodología 2 creará una "super-trayectoria" larga que parece una derivación secuencial pero que en realidad son episodios independientes.
# 
