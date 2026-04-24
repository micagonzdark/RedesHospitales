"""
Script para agregar la sección V1-AJUSTADA al notebook 23.TRAYECTORIAS.ipynb
"""
import nbformat as nbf

# Leer el notebook existente
with open("c:/Users/micag/Documents/RedesHospitales/JAIIO_notebooks/23.TRAYECTORIAS.ipynb", "r", encoding="utf-8") as f:
    nb = nbf.read(f, as_version=4)

# ==============================================================================
# NUEVAS CELDAS: Ajustes sobre V1
# ==============================================================================

text_ajuste = """\
---

# 🔧 METODOLOGÍA 1 — AJUSTADA (v1_ajustada)

Se incorporan dos correcciones al modelo v1 basadas en patrones observados en los datos:

**Problema 1 — Duplicados con traslados:**  
Muchos pacientes tienen varios episodios con `tipo_egreso == 'traslado'`
pero un solo episodio con `alta` o `muerte`. 
Ese episodio no-traslado es el **cierre clínico real**, 
pero a veces las fechas no lo ordenan correctamente.

**Problema 2 — Definición de ingreso/egreso:**  
- `fecha_ingreso_paciente = min(fecha_ingreso)` (siempre)
- `fecha_egreso_paciente = fecha_egreso` del episodio cuyo `tipo_egreso != 'traslado'`

**Estrategia:** prioridad lógica > fechas.
"""

code_clasificacion = """\
# ==============================================================================
# AJUSTE 1 — CLASIFICACIÓN DE EPISODIOS POR ROL (intermedios vs final)
# ==============================================================================

# Marcar qué episodios son traslados (intermedios) vs finales clínicos
df_base_filtrada = df_base_filtrada.copy()

df_base_filtrada['es_traslado'] = df_base_filtrada['tipo_egreso'] == 'traslado'

# Por paciente: ¿tiene al menos un episodio NO traslado?
tiene_final = (
    df_base_filtrada
    .groupby('paciente_id')['es_traslado']
    .apply(lambda x: (x == False).any())
    .rename('tiene_final_clinico')
    .reset_index()
)

df_base_filtrada = df_base_filtrada.merge(tiene_final, on='paciente_id', how='left')

print("=== DISTRIBUCIÓN DE TIPOS DE EPISODIO ===")
print(df_base_filtrada['tipo_egreso'].value_counts())
print(f"\\nPacientes CON episodio final clínico:    {tiene_final['tiene_final_clinico'].sum()}")
print(f"Pacientes SIN episodio final clínico:     {(~tiene_final['tiene_final_clinico']).sum()}")
print(f"  -> estos quedan flagueados, NO eliminados")
"""

code_ingreso_egreso = """\
# ==============================================================================
# AJUSTE 2 — FECHA DE INGRESO Y EGRESO REAL POR PACIENTE
# ==============================================================================

def calcular_ingreso_egreso_ajustado(grp):
    \"\"\"
    Ingreso real  = min(fecha_ingreso)  [siempre, no depende del motivo]
    Egreso real   = fecha_egreso del episodio con tipo_egreso != 'traslado'
                    Si no existe, usar max(fecha_egreso) y marcar flag.
    \"\"\"
    grp = grp.sort_values('fecha_ingreso')

    # Ingreso
    fecha_ingreso_paciente = grp['fecha_ingreso'].min()

    # Episodios finales (no traslado)
    finales = grp[grp['tipo_egreso'] != 'traslado']

    if len(finales) == 0:
        # Todos son traslado → inconsistente
        return pd.Series({
            'fecha_ingreso_paciente': fecha_ingreso_paciente,
            'fecha_egreso_paciente': grp['fecha_egreso'].max(),
            'flag_sin_final_clinico': True,
            'flag_multiples_finales': False,
            'tipo_egreso_final': 'desconocido'
        })
    elif len(finales) == 1:
        ep_final = finales.iloc[0]
        return pd.Series({
            'fecha_ingreso_paciente': fecha_ingreso_paciente,
            'fecha_egreso_paciente': ep_final['fecha_egreso'],
            'flag_sin_final_clinico': False,
            'flag_multiples_finales': False,
            'tipo_egreso_final': ep_final['tipo_egreso']
        })
    else:
        # Múltiples candidatos finales → usar el de mayor fecha y flaggear
        ep_final = finales.sort_values('fecha_egreso').iloc[-1]
        return pd.Series({
            'fecha_ingreso_paciente': fecha_ingreso_paciente,
            'fecha_egreso_paciente': ep_final['fecha_egreso'],
            'flag_sin_final_clinico': False,
            'flag_multiples_finales': True,
            'tipo_egreso_final': ep_final['tipo_egreso']
        })

df_ingreso_egreso = (
    df_base_filtrada
    .groupby('paciente_id')
    .apply(calcular_ingreso_egreso_ajustado)
    .reset_index()
)

print("=== INGRESO/EGRESO AJUSTADO ===")
print(f"Pacientes sin final clínico (flag):   {df_ingreso_egreso['flag_sin_final_clinico'].sum()}")
print(f"Pacientes con múltiples finales (flag): {df_ingreso_egreso['flag_multiples_finales'].sum()}")
print("\\nDistribución tipo_egreso_final:")
print(df_ingreso_egreso['tipo_egreso_final'].value_counts())
"""

code_trayectoria_ajustada = """\
# ==============================================================================
# AJUSTE 3 — CONSTRUCCIÓN DE TRAYECTORIA CON NODO FINAL ORDENADO POR LÓGICA
# ==============================================================================

def construir_trayectoria_v1_ajustada(grp):
    \"\"\"
    Construcción de trayectoria con prioridad lógica sobre fechas:
    
    1. Separa los traslados del df_traslados_strict (intermedios)
       y el episodio final (no traslado) desde df_base_filtrada.
    2. Ordena los traslados por fecha_egreso_origen.
    3. Ancla el episodio final al último lugar, independientemente
       de la fecha (prioridad lógica > orden temporal).
    4. Levanta flags en casos ambiguos.
    \"\"\"
    grp = grp.sort_values('fecha_egreso_origen')

    flags = {
        'salto_inconsistente': 0,
        'loop': 0,
        'duplicado_consecutivo': 0
    }

    current_hospital = grp.iloc[0]['hospital_origen']
    hospitales = [current_hospital]

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

    # Colapsar duplicados consecutivos
    hospitales_limpios = [hospitales[0]]
    for h in hospitales[1:]:
        if h != hospitales_limpios[-1]:
            hospitales_limpios.append(h)

    return pd.Series({
        'trayectoria_hospitalaria': str(hospitales_limpios),
        'hospital_inicio': hospitales_limpios[0],
        'hospital_final_traslados': hospitales_limpios[-1],
        'n_hospitales_unicos': len(set(hospitales_limpios)),
        **{f'flag_{k}': v for k, v in flags.items()}
    })


# Aplicar a pacientes con traslados
df_tray_ajustada_conectada = (
    df_traslados_filtrado
    .groupby('paciente_id')
    .apply(construir_trayectoria_v1_ajustada)
    .reset_index()
)

# Ahora — AJUSTE CLAVE: incorporar el nodo final desde df_base_filtrada
# El hospital del episodio final real (no-traslado) es el verdadero último nodo
df_nodo_final = (
    df_base_filtrada[df_base_filtrada['tipo_egreso'] != 'traslado']
    .sort_values(['paciente_id', 'fecha_egreso'])
    .groupby('paciente_id')
    .last()[['hospital_origen', 'tipo_egreso']]
    .rename(columns={'hospital_origen': 'hospital_nodo_final', 'tipo_egreso': 'tipo_egreso_final_ep'})
    .reset_index()
)

# Unir con trayectorias conectadas
df_tray_ajustada_conectada = df_tray_ajustada_conectada.merge(
    df_nodo_final, on='paciente_id', how='left'
)

# Flag: ¿el nodo final del traslado difiere del nodo final clínico?
df_tray_ajustada_conectada['flag_nodo_final_discrepante'] = (
    df_tray_ajustada_conectada['hospital_final_traslados'] !=
    df_tray_ajustada_conectada['hospital_nodo_final']
)

# Hospital final ajustado = hospital del episodio clínico final
# Si no existe (todos traslados), mantener el del último traslado
df_tray_ajustada_conectada['hospital_final'] = (
    df_tray_ajustada_conectada['hospital_nodo_final']
    .fillna(df_tray_ajustada_conectada['hospital_final_traslados'])
)

print("=== NODO FINAL DISCREPANTE (traslados vs clínico) ===")
print(df_tray_ajustada_conectada['flag_nodo_final_discrepante'].value_counts())
"""

code_trivial_ajustada = """\
# ==============================================================================
# TRAYECTORIAS TRIVIALES AJUSTADAS (sin traslados en df_traslados_strict)
# ==============================================================================

df_triviales_aj = df_base_filtrada[
    df_base_filtrada['paciente_id'].isin(pacientes_sin_traslado)
].copy()

def trayectoria_trivial_ajustada(grp):
    grp = grp.sort_values('fecha_ingreso')

    # Separar traslados de no-traslados
    intermedios = grp[grp['tipo_egreso'] == 'traslado']['hospital_origen'].tolist()
    finales = grp[grp['tipo_egreso'] != 'traslado']

    if len(finales) == 0:
        hospital_final = grp['hospital_origen'].iloc[-1]
        flag_sin_final = True
    else:
        # El hospital final es el del primer episodio no-traslado (más clínico)
        hospital_final = finales.sort_values('fecha_egreso').iloc[-1]['hospital_origen']
        flag_sin_final = False

    # Secuencia: intermedios + final
    h_seq = grp['hospital_origen'].tolist()
    hospitales_limpios = [h_seq[0]]
    for h in h_seq[1:]:
        if h != hospitales_limpios[-1]:
            hospitales_limpios.append(h)

    return pd.Series({
        'trayectoria_hospitalaria': str(hospitales_limpios),
        'hospital_inicio': hospitales_limpios[0],
        'hospital_final': hospital_final,
        'n_hospitales_unicos': len(set(hospitales_limpios)),
        'flag_salto_inconsistente': 0,
        'flag_loop': 0,
        'flag_duplicado_consecutivo': 0,
        'flag_nodo_final_discrepante': hospital_final != hospitales_limpios[-1],
        # flag_sin_final_clinico viene de df_ingreso_egreso via merge posterior
    })

if len(df_triviales_aj) > 0:
    df_tray_triviales_aj = (
        df_triviales_aj
        .groupby('paciente_id')
        .apply(trayectoria_trivial_ajustada)
        .reset_index()
    )
else:
    df_tray_triviales_aj = pd.DataFrame()
"""

code_merge_final = """\
# ==============================================================================
# UNIFICACIÓN Y MERGE FINAL → df_pacientes_trayectorias_v1_ajustada
# ==============================================================================

df_tray_ajustada = pd.concat([
    df_tray_ajustada_conectada,
    df_tray_triviales_aj
], ignore_index=True)

# Merge con métricas ajustadas de ingreso/egreso
df_tray_ajustada_final = (
    df_tray_ajustada
    .merge(df_ingreso_egreso, on='paciente_id', how='left')
    .merge(
        df_base_filtrada.groupby('paciente_id')['hospital_origen']
        .count().reset_index().rename(columns={'hospital_origen': 'n_episodios'}),
        on='paciente_id', how='left'
    )
)

# Desenlace desde tipo_egreso_final (ya calculado con la lógica ajustada)
df_tray_ajustada_final['desenlace'] = df_tray_ajustada_final['tipo_egreso_final']

# Métricas de duración usando ingreso/egreso ajustado
df_tray_ajustada_final['duracion_total'] = (
    (df_tray_ajustada_final['fecha_egreso_paciente'] - df_tray_ajustada_final['fecha_ingreso_paciente'])
    .dt.days
)

# Guardar
df_tray_ajustada_final.to_excel("../data/final_data/df_pacientes_trayectorias_v1_ajustada.xlsx", index=False)

print("=== RESUMEN FINAL — V1 AJUSTADA ===")
print(f"Pacientes totales:                {len(df_tray_ajustada_final)}")
print(f"Con nodo final discrepante:       {df_tray_ajustada_final['flag_nodo_final_discrepante'].sum()}")
print(f"Sin final clinico (flag):         {df_tray_ajustada_final['flag_sin_final_clinico'].sum()}")
print(f"Con multiples finales (flag):     {df_tray_ajustada_final['flag_multiples_finales'].sum()}")
print(f"\\nDesenlace:")
print(df_tray_ajustada_final['desenlace'].value_counts())
print(f"\\nHospitales unicos promedio:       {df_tray_ajustada_final['n_hospitales_unicos'].mean():.2f}")
print(f"Duracion total mediana (dias):   {df_tray_ajustada_final['duracion_total'].median():.1f}")
"""

code_validacion = """\
# ==============================================================================
# VALIDACIÓN — COMPARAR V1 original vs V1 AJUSTADA
# ==============================================================================

df_v1_orig = pd.read_excel("../data/final_data/df_pacientes_trayectorias_v1.xlsx")

comp = df_v1_orig[['paciente_id', 'hospital_final', 'desenlace']].merge(
    df_tray_ajustada_final[['paciente_id', 'hospital_final', 'desenlace', 'flag_nodo_final_discrepante']],
    on='paciente_id', suffixes=('_orig', '_aj'), how='inner'
)

comp['cambio_hospital_final'] = comp['hospital_final_orig'] != comp['hospital_final_aj']
comp['cambio_desenlace']      = comp['desenlace_orig'] != comp['desenlace_aj']

print("=== V1 ORIGINAL vs V1 AJUSTADA ===")
print(f"Pacientes comparados:              {len(comp)}")
print(f"Con cambio en hospital final:      {comp['cambio_hospital_final'].sum()} ({comp['cambio_hospital_final'].mean():.1%})")
print(f"Con cambio en desenlace:           {comp['cambio_desenlace'].sum()} ({comp['cambio_desenlace'].mean():.1%})")

# Muestra de casos que cambiaron
print("\\n=== SAMPLE DE CASOS CON NODO FINAL DISTINTO ===")
sample_cambios = comp[comp['cambio_hospital_final']].sample(min(5, comp['cambio_hospital_final'].sum()), random_state=42)
for _, row in sample_cambios.iterrows():
    ep_cols = ['fecha_ingreso', 'fecha_egreso', 'hospital_origen', 'tipo_egreso']
    print(f"\\nPaciente {row['paciente_id']}")
    print(f"  Hospital final ORIGINAL: {row['hospital_final_orig']}")
    print(f"  Hospital final AJUSTADO: {row['hospital_final_aj']}")
    from IPython.display import display
    display(df_base_filtrada[df_base_filtrada['paciente_id'] == row['paciente_id']][ep_cols])
"""

# Agregar celdas al notebook existente
nb.cells.extend([
    nbf.v4.new_markdown_cell(text_ajuste),
    nbf.v4.new_code_cell(code_clasificacion),
    nbf.v4.new_code_cell(code_ingreso_egreso),
    nbf.v4.new_code_cell(code_trayectoria_ajustada),
    nbf.v4.new_code_cell(code_trivial_ajustada),
    nbf.v4.new_code_cell(code_merge_final),
    nbf.v4.new_code_cell(code_validacion),
])

with open("c:/Users/micag/Documents/RedesHospitales/JAIIO_notebooks/23.TRAYECTORIAS.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print("OK - Celdas de v1_ajustada agregadas al notebook 23.TRAYECTORIAS.ipynb")
