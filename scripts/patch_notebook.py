"""
Script de parcheo consolidado para 03_ranking_trayectorias.ipynb.

Ejecuta todos los cambios necesarios sobre la estructura JSON del notebook:
1. Reemplaza os.makedirs por crear_directorios_overleaf().
2. Agrega subcarpeta a cada llamada de funcion de graficado.

Trabaja sobre el source de cada celda como string plano, luego
reconvierte a lista-de-lineas para ser compatible con el formato ipynb.
"""

import json, pathlib, re

NB_PATH = pathlib.Path(
    r"C:\Users\micag\Documents\RedesHospitales\JAIIO_notebooks\03_ranking_trayectorias.ipynb"
)

with NB_PATH.open(encoding="utf-8") as f:
    nb = json.load(f)

print("[INFO] Notebook cargado correctamente.")


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_src(cell):
    """Devuelve el source de la celda como un unico string."""
    src = cell["source"]
    if isinstance(src, list):
        return "".join(src)
    return src

def set_src(cell, text: str):
    """Reemplaza el source de la celda con el texto dado (lista de lineas)."""
    lines = text.splitlines(keepends=True)
    # La ultima linea del source de ipynb no lleva \n segun la spec
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1].rstrip("\n")
    cell["source"] = lines


# ── 1. Parche de setup: reemplazar makedirs por crear_directorios_overleaf() ──

OLD_SETUP = "os.makedirs('graficos_overleaf', exist_ok=True)"
NEW_SETUP = (
    "from src.config import crear_directorios_overleaf\n"
    "crear_directorios_overleaf()  # Crea 1_general, 2_desenlaces, 3_tiempos, 4_evolucion, anexos"
)

p1_done = False
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        src = get_src(cell)
        if OLD_SETUP in src:
            set_src(cell, src.replace(OLD_SETUP, NEW_SETUP))
            print("[OK] Parche 1: reemplazado makedirs por crear_directorios_overleaf().")
            p1_done = True
            break

if not p1_done:
    print("[WARN] Parche 1 no aplicado: no se encontro la cadena de makedirs.")


# ── 2. Parches de subcarpeta ────────────────────────────────────────────────────
# Cada entrada: (patron, reemplazo_str_o_funcion, descripcion)
# Operamos sobre el source plano de cada celda con re.subn + DOTALL.

SUBCARPETA_PATCHES = [
    # graficar_heatmaps -> subcarpeta='general'
    (
        r"(graficar_heatmaps\([^)]*nombre_archivo='[^']*')\s*(\))",
        r"\1, subcarpeta='general'\2",
        "graficar_heatmaps subcarpeta=general",
    ),
    # graficar_top_10 trayectorias global (03_...)
    (
        r"(graficar_top_10\(.*?nombre_archivo='03_[^']*')(,?\s*)\)",
        r"\1, subcarpeta='general')",
        "graficar_top_10 03_ subcarpeta=general",
    ),
    # graficar_top_10 saltos individuales (04_...)
    (
        r"(graficar_top_10\(.*?nombre_archivo='04_[^']*')(,?\s*)\)",
        r"\1, subcarpeta='general')",
        "graficar_top_10 04_ subcarpeta=general",
    ),
    # graficar_top_10_apilado (05_...)
    (
        r"(graficar_top_10_apilado\(.*?nombre_archivo='05_[^']*')(,?\s*)\)",
        r"\1, subcarpeta='desenlaces')",
        "graficar_top_10_apilado 05_ subcarpeta=desenlaces",
    ),
    # graficar_grilla_periodos
    (
        r"(graficar_grilla_periodos\(.*?nombre_archivo='[^']*')(,?\s*)\)",
        r"\1, subcarpeta='evolucion')",
        "graficar_grilla_periodos subcarpeta=evolucion",
    ),
    # graficar_grilla_trayectorias_periodos
    (
        r"(graficar_grilla_trayectorias_periodos\(.*?nombre_archivo='[^']*')(,?\s*)\)",
        r"\1, subcarpeta='evolucion')",
        "graficar_grilla_trayectorias_periodos subcarpeta=evolucion",
    ),
    # graficar_grilla_trayectorias_dinamico
    (
        r"(graficar_grilla_trayectorias_dinamico\(.*?nombre_archivo='[^']*')(,?\s*)\)",
        r"\1, subcarpeta='evolucion')",
        "graficar_grilla_trayectorias_dinamico subcarpeta=evolucion",
    ),
]

total_patched = 0
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = get_src(cell)
    original = src
    for pattern, replacement, desc in SUBCARPETA_PATCHES:
        new_src, n = re.subn(pattern, replacement, src, flags=re.DOTALL)
        if n:
            # Guardia: verificar que no haya subcarpeta duplicada (de parches anteriores)
            if "subcarpeta" not in src or new_src.count("subcarpeta") > src.count("subcarpeta"):
                src = new_src
                total_patched += n
                print(f"  [OK] {desc}: {n} reemplazo(s)")
    if src != original:
        set_src(cell, src)

print(f"\n[INFO] Total reemplazos de subcarpeta: {total_patched}")


# ── Guardar ─────────────────────────────────────────────────────────────────────

with NB_PATH.open("w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

# Verificar que el JSON sigue siendo valido
try:
    with NB_PATH.open(encoding="utf-8") as f:
        json.load(f)
    print("[DONE] Notebook guardado y JSON validado correctamente.")
except json.JSONDecodeError as e:
    print(f"[ERROR] El notebook tiene JSON invalido: {e}")
