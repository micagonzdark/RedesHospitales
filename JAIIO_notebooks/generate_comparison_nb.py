import nbformat as nbf

nb = nbf.v4.new_notebook()

text_intro = """# Comparación de Metodologías de Trayectorias

El objetivo es comparar la **metodología nueva (v1/v2)** con la **metodología anterior** (del `notebook 01`) para entender:
- Qué cambió realmente.
- Ganancias y pérdidas.
- Sesgos detectados.
"""

code_1 = """import sys
import os
sys.path.append(os.path.abspath(".."))

import pandas as pd
import ast
from IPython.display import display

# Cargar base limpia para reproducir episodios
df_base = pd.read_excel("../data/final_data/df_base_limpia.xlsx")

# ==============================================================
# 1. RECONSTRUIR OUTPUT DE LA METODOLOGÍA ANTERIOR
# ==============================================================
# Ordenamos por paciente y fecha
df_estancias_episodios = df_base.sort_values(['paciente_id', 'fecha_ingreso']).copy()

# Agrupamos como se hacía en 01_redes_basico.ipynb
df_rutas = df_estancias_episodios.groupby('paciente_id').agg(
    trayectoria_hospitalaria=('hospital_origen', lambda x: str(list(x))), 
    hospital_inicio=('hospital_origen', 'first'),
    hospital_final=('hospital_origen', 'last'),
    n_hospitales_unicos=('hospital_origen', lambda x: len(set(x))),
    n_episodios=('hospital_origen', 'count')
).reset_index()

df_old = df_rutas.copy()
"""

code_2 = """# ==============================================================
# 2. ALINEAR ESTRUCTURAS
# ==============================================================
df_v1 = pd.read_excel("../data/final_data/df_pacientes_trayectorias_v1.xlsx")
df_v2 = pd.read_excel("../data/final_data/df_pacientes_trayectorias_v2.xlsx")

def rename_cols(df, suffix):
    cols = {
        'trayectoria_hospitalaria': f'trayectoria{suffix}',
        'hospital_inicio': f'inicio{suffix}',
        'hospital_final': f'final{suffix}',
        'n_hospitales_unicos': f'n_unicos{suffix}',
        'n_episodios': f'n_episodios{suffix}'
    }
    return df.rename(columns={k: v for k, v in cols.items() if k in df.columns})

df_old = rename_cols(df_old, '_old')
df_v1 = rename_cols(df_v1, '_v1')
df_v2 = rename_cols(df_v2, '_v2')

# Unir en una mega tabla
df_comp = df_old.merge(df_v1, on='paciente_id', how='outer')\\
                .merge(df_v2, on='paciente_id', how='outer')
"""

code_3 = """# ==============================================================
# 3. COMPARACIÓN DE COBERTURA
# ==============================================================
print("=== COBERTURA ===")
print(f"Pacientes en Old: {df_old['paciente_id'].nunique()}")
print(f"Pacientes en V1:  {df_v1['paciente_id'].nunique()}")
print(f"Pacientes en V2:  {df_v2['paciente_id'].nunique()}")

comunes = df_comp.dropna(subset=['trayectoria_old', 'trayectoria_v1', 'trayectoria_v2'])
print(f"\\nPacientes en común (presentes en las 3): {len(comunes)}")

perdidos = df_comp[df_comp['trayectoria_v1'].isna() & df_comp['trayectoria_old'].notna()]
print(f"Pacientes perdidos (estaban en Old pero no en V1/V2): {len(perdidos)} (por los filtros de limpieza)")
"""

code_4 = """# ==============================================================
# 4. COMPARACIÓN DE TRAYECTORIAS
# ==============================================================
df_comunes = comunes.copy()

# Igualdad exacta (strings vs strings)
df_comunes['exact_old_v1'] = df_comunes['trayectoria_old'] == df_comunes['trayectoria_v1']
df_comunes['exact_old_v2'] = df_comunes['trayectoria_old'] == df_comunes['trayectoria_v2']
df_comunes['exact_v1_v2']  = df_comunes['trayectoria_v1'] == df_comunes['trayectoria_v2']

print("=== EXACTITUD DE TRAYECTORIAS ===")
print(f"Old igual a V1: {df_comunes['exact_old_v1'].mean():.2%}")
print(f"Old igual a V2: {df_comunes['exact_old_v2'].mean():.2%}")
print(f"V1 igual a V2:  {df_comunes['exact_v1_v2'].mean():.2%}")
"""

code_5 = """# ==============================================================
# 5. COMPARACIÓN DE RESULTADOS CLAVE
# ==============================================================
print("=== MÉTRICAS CLAVE (% que cambia respecto a Old) ===")
cambio_final_v1 = (df_comunes['final_old'] != df_comunes['final_v1']).mean()
cambio_final_v2 = (df_comunes['final_old'] != df_comunes['final_v2']).mean()
print(f"Hospital Final distinto a Old -> V1: {cambio_final_v1:.2%} | V2: {cambio_final_v2:.2%}")

cambio_unicos_v1 = (df_comunes['n_unicos_old'] != df_comunes['n_unicos_v1']).mean()
cambio_unicos_v2 = (df_comunes['n_unicos_old'] != df_comunes['n_unicos_v2']).mean()
print(f"Hospitales Únicos distinto a Old -> V1: {cambio_unicos_v1:.2%} | V2: {cambio_unicos_v2:.2%}")
"""

code_6 = """# ==============================================================
# 6. ANÁLISIS DE CASOS DIFERENTES (CLAVE)
# ==============================================================
casos_A = df_comunes[~df_comunes['exact_old_v1']]
casos_B = df_comunes[~df_comunes['exact_old_v2']]
casos_C = df_comunes[~df_comunes['exact_v1_v2']]

print("=== CONTEO DE CONFLICTOS ===")
print(f"🔴 Caso A (Old != V1): {len(casos_A)} pacientes")
print(f"🔵 Caso B (Old != V2): {len(casos_B)} pacientes")
print(f"🟣 Caso C (V1 != V2):  {len(casos_C)} pacientes")
"""

code_7 = """# ==============================================================
# MUESTRA DETALLADA DE CONFLICTOS
# ==============================================================
def mostrar_ejemplo(paciente_id, label):
    row = df_comunes[df_comunes['paciente_id'] == paciente_id].iloc[0]
    print("\\n" + "="*80)
    print(f"EJEMPLO: {label} | PACIENTE ID: {paciente_id}")
    print("-"*80)
    print(f"OLD: {row['trayectoria_old']}")
    print(f"V1:  {row['trayectoria_v1']}")
    print(f"V2:  {row['trayectoria_v2']}")
    print("\\n👉 Episodios Originales:")
    ep_cols = ['fecha_ingreso', 'fecha_egreso', 'hospital_origen', 'motivo_egreso']
    display(df_base[df_base['paciente_id'] == paciente_id][ep_cols])

# Mostrar todos los IDs que difieren en V1 vs V2
print("\\n🟣 LISTADO COMPLETO DE PACIENTES DONDE V1 != V2:")
display(casos_C['paciente_id'].tolist()[:50]) # limitamos a 50 visuales por si son muchos

# Mostrar samples detallados
if not casos_A.empty: mostrar_ejemplo(casos_A['paciente_id'].sample(1, random_state=42).iloc[0], "🔴 Caso A (Old != V1)")
if not casos_B.empty: mostrar_ejemplo(casos_B['paciente_id'].sample(1, random_state=43).iloc[0], "🔵 Caso B (Old != V2)")

# Mostrar unos cuantos de V1 != V2
print("\\n\\n🟣 SAMPLES DE V1 != V2:")
for p_id in casos_C['paciente_id'].sample(min(5, len(casos_C)), random_state=44).tolist():
    mostrar_ejemplo(p_id, "Caso C (V1 != V2)")
"""

text_conclusion = """## 7. INTERPRETACIÓN Y CONCLUSIÓN

### 7.1 Sobre la metodología vieja
* **¿Qué estaba asumiendo sin hacerlo explícito?** Asumía que toda aparición de un paciente en un hospital formaba parte de una cadena conectada de eventos. Si un paciente iba a la guardia, se iba de alta y volvía 3 años después a otro hospital, la base vieja lo consideraba una "trayectoria" (A -> B). Además, no colapsaba registros repetidos consecutivos causados por burocracia (A -> A).
* **¿Dónde puede fallar?** Altera severamente los gráficos de red al inyectar "flujos" (aristas) que no son traslados reales, inflando las conexiones entre hospitales.

### 7.2 Sobre v1 (Traslados)
* **¿Qué mejora?** Aisla la **verdadera red de derivaciones logísticas**. Obliga a que la transición esté respaldada por una ventana temporal minúscula (o un motivo de traslado explícito), eliminando saltos temporales absurdos.
* **¿Qué pierde?** Puede perder conexiones donde administrativamente un hospital dio el "alta" en vez del "traslado" y el paciente tardó varios días en ingresar al destino, clasificándolo erróneamente como dos episodios inconexos.

### 7.3 Sobre v2 (Episodios)
* **¿Qué mantiene de la vieja?** Mantiene la secuencia cronológica pura sin exigir validación de traslados logísticos.
* **¿Qué cambia?** Ahora es explícita y levanta *flags* (alertas de gaps y overlaps) además de colapsar eventos A -> A repetidos, depurando la visualización cronológica.

### 7.4 Conclusión Final
* **¿Cuál representa mejor la realidad de la red hospitalaria?** Para análisis de flujos, cuellos de botella y mapas logísticos, la **V1 es inmensamente superior**. Evita graficar conexiones donde no hubo ambulancia ni transferencia real de pacientes.
* **¿Cuál es más robusta a errores administrativos?** **V1**. Mitiga las altas mal codificadas al no asumir conexiones espontáneas de largo plazo.
* **Veredicto:** Combinar. Usar **V1** como "Ground Truth" para cualquier cálculo de "Derivación en Red", y usar **V2 filtrando aquellos con flags de gap grande** para un análisis puro de reingresos crónicos a largo plazo.
"""

nb.cells.extend([
    nbf.v4.new_markdown_cell(text_intro),
    nbf.v4.new_code_cell(code_1),
    nbf.v4.new_code_cell(code_2),
    nbf.v4.new_code_cell(code_3),
    nbf.v4.new_code_cell(code_4),
    nbf.v4.new_code_cell(code_5),
    nbf.v4.new_code_cell(code_6),
    nbf.v4.new_code_cell(code_7),
    nbf.v4.new_markdown_cell(text_conclusion)
])

with open("c:/Users/micag/Documents/RedesHospitales/JAIIO_notebooks/24.COMPARACION.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print("Notebook 24.COMPARACION.ipynb generado.")
