"""
Parcheo quirurgico de 02_mapas.ipynb:
- Mantiene PNG y SVG en results/outputs/geo/
- Reemplaza plt.savefig(... .pdf ...) por guardar_pdf() de config
- Agrega guardar_pdf() donde falta (celda 8 ya tiene mapa_adicional)
"""
import json, pathlib, re

NB_PATH = pathlib.Path("JAIIO_notebooks/02_mapas.ipynb")
nb = json.load(NB_PATH.open(encoding="utf-8"))

def get_src(cell):
    s = cell["source"]
    return "".join(s) if isinstance(s, list) else s

def set_src(cell, text):
    lines = text.splitlines(keepends=True)
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1].rstrip("\n")
    cell["source"] = lines

# ── Celda 5: mapa_buenos_aires ────────────────────────────────────────
cell5 = nb["cells"][5]
src5 = get_src(cell5)

# Reemplazamos el bloque de savefig PDF de la celda 5
src5_new = re.sub(
    r"plt\.savefig\(\s*\n?\s*f?\"\{nombre_archivo\}\.pdf\"[^\)]*\)",
    "guardar_pdf('01_mapa_buenos_aires', subcarpeta='general')",
    src5,
    flags=re.DOTALL
)
if src5_new != src5:
    set_src(cell5, src5_new)
    print("[OK] Celda 5: reemplazado savefig pdf -> guardar_pdf('01_mapa_buenos_aires')")
else:
    print("[MISS] Celda 5: no se encontro el patron de savefig pdf")

# ── Celda 6: mapa_red_sudeste opt1 y opt2 ────────────────────────────
cell6 = nb["cells"][6]
src6 = get_src(cell6)

src6_new = re.sub(
    r'plt\.savefig\(f"\{nombre_archivo_1\}\.pdf"[^\)]*\)',
    "guardar_pdf('02_mapa_red_sudeste_opt1', subcarpeta='general')",
    src6
)
src6_new = re.sub(
    r'plt\.savefig\(f"\{nombre_archivo_2\}\.pdf"[^\)]*\)',
    "guardar_pdf('02_mapa_red_sudeste_opt2', subcarpeta='general')",
    src6_new
)
if src6_new != src6:
    set_src(cell6, src6_new)
    print("[OK] Celda 6: reemplazados savefig pdf opt1 y opt2 -> guardar_pdf()")
else:
    print("[MISS] Celda 6: no se encontraron los patrones")

# ── Guardar y validar ─────────────────────────────────────────────────
serialized = json.dumps(nb, ensure_ascii=False, indent=1)
json.loads(serialized)
NB_PATH.write_text(serialized, encoding="utf-8")
print("[DONE] 02_mapas.ipynb guardado y JSON validado.")
