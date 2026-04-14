"""
Script de parcheo masivo de notebooks — Version 3.

Aplica la estandarizacion de exportacion Overleaf a:
  - JAIIO_notebooks/01_redes_basico.ipynb
  - JAIIO_notebooks/02_mapas.ipynb
  - JAIIO_notebooks/04_trayectorias_especificas.ipynb

Logica de guardado:
  - PDF a graficos_overleaf/<subcarpeta>/
  - PNG/SVG se mantienen en results/outputs/geo/ (solo 02_mapas)
  - Grillas 2x2 por periodo: ya son figuras consolidadas, se guardan como un unico PDF
"""

import json, pathlib, re

BASE = pathlib.Path("JAIIO_notebooks")


# ── Helpers ─────────────────────────────────────────────────────────────────────

def get_src(cell):
    s = cell["source"]
    return "".join(s) if isinstance(s, list) else s

def set_src(cell, text):
    lines = text.splitlines(keepends=True)
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1].rstrip("\n")
    cell["source"] = lines

def patch_nb(nb_name, patchers):
    """Aplica una lista de funciones patcher(nb) al notebook y guarda si es valido."""
    path = BASE / nb_name
    nb = json.load(path.open(encoding="utf-8"))
    print(f"\n[INFO] Parchando {nb_name}...")

    for patcher in patchers:
        patcher(nb)

    # Validar JSON antes de guardar
    serialized = json.dumps(nb, ensure_ascii=False, indent=1)
    json.loads(serialized)  # lanza si hay error

    path.write_text(serialized, encoding="utf-8")
    print(f"  [DONE] {nb_name} guardado y JSON validado.")


# ══════════════════════════════════════════════════════════════════════
# HELPERS DE INSERCION
# ══════════════════════════════════════════════════════════════════════

def add_setup_cell(nb, import_line):
    """Agrega al final de la primera celda de codigo la llamada al setup de directorios."""
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            src = get_src(cell)
            if "crear_directorios_overleaf" not in src:
                set_src(cell, src + "\n" + import_line)
                print(f"  [OK] Setup de directorios agregado.")
            else:
                print(f"  [SKIP] Setup de directorios ya existe.")
            break

def inject_before_show(src, guardar_line):
    """
    Inserta guardar_line antes de plt.show() si no existe ya.
    Retorna (nuevo_src, n_reemplazos).
    """
    # Evitar duplicados
    if guardar_line.strip() in src:
        return src, 0
    pattern = r'([ \t]*)(plt\.show\(\))'
    repl = r'\1' + guardar_line.strip() + r'\n\1\2'
    new_src, n = re.subn(pattern, repl, src, count=1)
    return new_src, n


# ══════════════════════════════════════════════════════════════════════
# NOTEBOOK 01: redes_basico.ipynb
# ══════════════════════════════════════════════════════════════════════

GRAFICOS_01 = {
    # celda_indice: (nombre_archivo, subcarpeta)
    # Las celdas 3 y 4 ya son grillas/mapas que se guardan como un unico PDF
    3:  ("01_grilla_redes_periodos",    "evolucion"),
    4:  ("02_mapa_geopandas_red",       "general"),
    12: ("03_matriz_roles",             "general"),
    13: ("04_evolucion_asimetria",      "evolucion"),
    14: ("05_roles_red_intrapredio",    "general"),
    18: ("06_mortalidad_saltos",        "desenlaces"),
    21: ("07_mortalidad_trayectoria",   "desenlaces"),
    23: ("08_evolucion_mortalidad_lineas", "evolucion"),
    24: ("09_pingpong_mortalidad",      "general"),
    # Celda 25 es solo tablas/prints — no tiene plt.show() relevante
}

def patcher_01_setup(nb):
    add_setup_cell(nb,
        "from src.config import crear_directorios_overleaf\n"
        "crear_directorios_overleaf()  # Crea subcarpetas en graficos_overleaf/"
    )

def patcher_01_graficos(nb):
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code" or i not in GRAFICOS_01:
            continue
        nombre, subcar = GRAFICOS_01[i]
        src = get_src(cell)
        guardar_line = f"guardar_pdf('{nombre}', subcarpeta='{subcar}')"
        new_src, n = inject_before_show(src, guardar_line)
        if n:
            set_src(cell, new_src)
            print(f"  [OK] Celda {i}: guardar_pdf('{nombre}', '{subcar}')")
        else:
            print(f"  [SKIP] Celda {i}: ya tenia guardar_pdf o no encontro plt.show()")


# ══════════════════════════════════════════════════════════════════════
# NOTEBOOK 02: mapas.ipynb
# ══════════════════════════════════════════════════════════════════════

def patcher_02_setup(nb):
    """Agrega crear_directorios_overleaf() a la primera celda de codigo."""
    add_setup_cell(nb,
        "from src.config import crear_directorios_overleaf\n"
        "crear_directorios_overleaf()"
    )

def patcher_02_savefigs(nb):
    """
    Para cada celda con plt.savefig:
    - Mantiene PNG y SVG en results/outputs/geo/ (sin cambios)
    - Reemplaza el plt.savefig(...pdf...) por guardar_pdf() de config
    - Si no habia PDF, agrega guardar_pdf() antes del plt.show()
    """
    # Mapeo nombre_archivo -> (nombre_overleaf, subcarpeta)
    MAPA_NOMBRES = {
        "mapa_buenos_aires":          ("01_mapa_buenos_aires",         "general"),
        "mapa_red_sudeste_opcion1":   ("02_mapa_red_sudeste_opt1",     "general"),
        "mapa_red_sudeste_opcion2":   ("02_mapa_red_sudeste_opt2",     "general"),
        "mapa_barrios_populares":     ("03_mapa_barrios_populares",    "general"),
    }

    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src = get_src(cell)
        if "plt.savefig" not in src and "plt.show" not in src:
            continue

        new_src = src
        patched = False

        for var_nombre, (nombre_ov, subcar) in MAPA_NOMBRES.items():
            # Reemplazar el savefig de PDF por guardar_pdf()
            pattern_pdf = (
                r'plt\.savefig\(\s*\n?\s*f?["\']' +
                r'[^"\']*' + re.escape(var_nombre) +
                r'[^"\']*\.pdf[^"\']*["\'][^\)]*\)'
            )
            guardar_call = f"guardar_pdf('{nombre_ov}', subcarpeta='{subcar}')"
            new_src2, n = re.subn(pattern_pdf, guardar_call, new_src, flags=re.DOTALL)
            if n:
                new_src = new_src2
                patched = True
                print(f"  [OK] Celda {i}: reemplazado savefig PDF -> guardar_pdf('{nombre_ov}')")

        if patched:
            set_src(cell, new_src)
        elif "plt.show" in src and "guardar_pdf" not in src and "plt.savefig" not in src:
            # Celda con show pero sin savefig — agregar generico si es de mapa
            if any(kw in src.lower() for kw in ["fig, ax", "geopandas", "gpd.", "barrios"]):
                guardar_line = "guardar_pdf('mapa_adicional', subcarpeta='general')"
                new_src, n = inject_before_show(src, guardar_line)
                if n:
                    set_src(cell, new_src)
                    print(f"  [OK] Celda {i}: agregado guardar_pdf generico de mapa")


# ══════════════════════════════════════════════════════════════════════
# NOTEBOOK 04: trayectorias_especificas.ipynb
# ══════════════════════════════════════════════════════════════════════

GRAFICOS_04 = {
    2: ("01_desenlaces_por_trayectoria",  "desenlaces"),
    4: ("02_evolucion_desenlaces_nivel0", "evolucion"),
    5: ("03_boxplot_tiempos_traslado",    "tiempos"),
}

def patcher_04_setup(nb):
    add_setup_cell(nb,
        "from src.config import crear_directorios_overleaf, guardar_pdf\n"
        "crear_directorios_overleaf()"
    )

def patcher_04_graficos(nb):
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code" or i not in GRAFICOS_04:
            continue
        nombre, subcar = GRAFICOS_04[i]
        src = get_src(cell)
        guardar_line = f"guardar_pdf('{nombre}', subcarpeta='{subcar}')"
        new_src, n = inject_before_show(src, guardar_line)
        if n:
            set_src(cell, new_src)
            print(f"  [OK] Celda {i}: guardar_pdf('{nombre}', '{subcar}')")
        else:
            print(f"  [SKIP] Celda {i}: ya tenia guardar_pdf o no encontro plt.show()")


# ══════════════════════════════════════════════════════════════════════
# EJECUCION
# ══════════════════════════════════════════════════════════════════════

patch_nb("01_redes_basico.ipynb",           [patcher_01_setup, patcher_01_graficos])
patch_nb("02_mapas.ipynb",                  [patcher_02_setup, patcher_02_savefigs])
patch_nb("04_trayectorias_especificas.ipynb", [patcher_04_setup, patcher_04_graficos])

print("\n[ALL DONE] Todos los notebooks fueron parchados exitosamente.")
