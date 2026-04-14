"""
Script de parcheo para 03_ranking_trayectorias.ipynb.

Realiza dos cambios:
1. En la celda de imports, agrega la creacion de graficos_overleaf/.
2. Pasa nombre_archivo a cada llamada de funcion de graficado.
"""

import json, pathlib, re

NB_PATH = pathlib.Path(
    r"C:\Users\micag\Documents\RedesHospitales\JAIIO_notebooks\03_ranking_trayectorias.ipynb"
)

with NB_PATH.open(encoding="utf-8") as f:
    nb = json.load(f)


# ── Helpers ────────────────────────────────────────────────────────────────────

def source_str(cell):
    """Devuelve el source de la celda como string unificado."""
    return "".join(cell["source"])

def set_source(cell, text: str):
    """Reemplaza el source de la celda con el texto dado (como lista de lineas)."""
    lines = text.splitlines(keepends=True)
    # La ultima linea no lleva \n en los notebooks
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1].rstrip("\n")
    cell["source"] = lines


# ── Parche 1: celda de imports ─────────────────────────────────────────────────

MAKEDIRS_BLOCK = (
    "\n"
    "\n"
    "# Crear directorio para exportar graficos a Overleaf\n"
    "os.makedirs('graficos_overleaf', exist_ok=True)"
)

for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        src = source_str(cell)
        if "import numpy as np" in src and "os.makedirs" not in src:
            set_source(cell, src + MAKEDIRS_BLOCK)
            print("[OK] Parche 1: agregado os.makedirs() en celda de imports.")
            break


# ── Parche 2: llamadas de graficado ───────────────────────────────────────────

REPLACEMENTS = [
    # --- graficar_heatmaps ---
    (
        r"graficar_heatmaps\(df_probabilidades,\s*df_cantidades\)",
        "graficar_heatmaps(df_probabilidades, df_cantidades, nombre_archivo='01_heatmaps_matrices')",
    ),
    # --- top10 trayectorias CON traslados ---
    (
        r"(graficar_top_10\(\s*df=top_10,\s*x_col=['\"]Frecuencia['\"],\s*y_col=['\"]Ruta['\"],\s*"
        r"titulo=['\"]Top 10 Trayectorias de Complejidad M.s Frecuentes['\"],\s*"
        r"xlabel=['\"]Pacientes['\"],\s*ylabel=['\"]Trayectoria['\"],\s*sufijo=['\"]pac\.['\"]"
        r"\s*\))",
        (
            "graficar_top_10(\n"
            "    df=top_10, x_col='Frecuencia', y_col='Ruta',\n"
            "    titulo='Top 10 Trayectorias de Complejidad Mas Frecuentes',\n"
            "    xlabel='Pacientes', ylabel='Trayectoria', sufijo='pac.',\n"
            "    nombre_archivo='02_top10_trayectorias_con_traslados'\n"
            ")"
        ),
    ),
    # --- top10 trayectorias GLOBAL (con y sin traslados) ---
    (
        r"(graficar_top_10\(\s*df=top_10,\s*x_col=['\"]Frecuencia['\"],\s*y_col=['\"]Ruta['\"],\s*"
        r"titulo=['\"]Top 10 Trayectorias de Complejidad \(Incluyendo Estacionarios\)['\"],\s*"
        r"xlabel=['\"]Total de Pacientes['\"],\s*ylabel=['\"]Trayectoria / Nivel .nico['\"],\s*"
        r"sufijo=['\"]pac\.['\"]"
        r"\s*\))",
        (
            "graficar_top_10(\n"
            "    df=top_10, x_col='Frecuencia', y_col='Ruta',\n"
            "    titulo='Top 10 Trayectorias de Complejidad (Incluyendo Estacionarios)',\n"
            "    xlabel='Total de Pacientes', ylabel='Trayectoria / Nivel Unico', sufijo='pac.',\n"
            "    nombre_archivo='03_top10_trayectorias_global'\n"
            ")"
        ),
    ),
    # --- top10 saltos individuales ---
    (
        r"(graficar_top_10\(\s*df=top_10_saltos,\s*x_col=['\"]Frecuencia['\"],\s*y_col=['\"]Salto['\"],\s*"
        r"titulo=['\"]Top 10 traslados m.s Frecuentes \(Tramo a Tramo\)['\"],\s*"
        r"xlabel=['\"]Cantidad de traslados['\"],\s*ylabel=['\"]Salto \(Origen .{1,5} Destino\)['\"],\s*"
        r"sufijo=['\"]['\"]"
        r"\s*\))",
        (
            "graficar_top_10(\n"
            "    df=top_10_saltos, x_col='Frecuencia', y_col='Salto',\n"
            "    titulo='Top 10 traslados mas Frecuentes (Tramo a Tramo)',\n"
            "    xlabel='Cantidad de traslados', ylabel='Salto (Origen > Destino)', sufijo='',\n"
            "    nombre_archivo='04_top10_saltos_individuales'\n"
            ")"
        ),
    ),
    # --- top10_apilado (saltos + motivo) ---
    (
        r"(graficar_top_10_apilado\(\s*df_pivot=pivot_saltos,\s*"
        r"titulo=['\"]Top 10 Traslados M.s Frecuentes Tramo a Tramo \(por Motivo Final\)['\"],\s*"
        r"xlabel=['\"]Cantidad de traslados['\"],\s*"
        r"ylabel=['\"]Salto \(Origen .{1,5} Destino\)['\"],\s*"
        r"total_general=total_saltos,\s*sufijo=['\"]['\"]"
        r"\s*\))",
        (
            "graficar_top_10_apilado(\n"
            "    df_pivot=pivot_saltos,\n"
            "    titulo='Top 10 Traslados Mas Frecuentes Tramo a Tramo (por Motivo Final)',\n"
            "    xlabel='Cantidad de traslados',\n"
            "    ylabel='Salto (Origen > Destino)',\n"
            "    total_general=total_saltos,\n"
            "    sufijo='',\n"
            "    nombre_archivo='05_top10_saltos_apilados'\n"
            ")"
        ),
    ),
]

patched = 0
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = source_str(cell)
    for pattern, replacement in REPLACEMENTS:
        new_src, n = re.subn(pattern, replacement, src, flags=re.DOTALL)
        if n:
            src = new_src
            patched += 1
            print(f"[OK] Parche 2 aplicado: {replacement[:70]}")
    set_source(cell, src)

print(f"\n[INFO] Total de reemplazos en celdas: {patched}")


# ── Guardar ────────────────────────────────────────────────────────────────────
with NB_PATH.open("w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("[DONE] Notebook guardado con exito en", NB_PATH)
