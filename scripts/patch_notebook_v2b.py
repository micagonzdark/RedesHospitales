"""
Script de parcheo v2b para 03_ranking_trayectorias.ipynb.

Agrega subcarpeta a las llamadas de graficar_top_10 que estan en formato
multilínea en el JSON del notebook. Trabaja directamente con el texto
raw del JSON.
"""

import pathlib, re

NB_PATH = pathlib.Path(
    r"C:\Users\micag\Documents\RedesHospitales\JAIIO_notebooks\03_ranking_trayectorias.ipynb"
)

with NB_PATH.open(encoding="utf-8") as f:
    raw = f.read()

# En el JSON del notebook el notebook ya tiene la linea
#   "    nombre_archivo='03_top10_trayectorias_global'\n",
# seguida de
#   ")"
# Sin subcarpeta.
# Reemplazamos cada una puntualmente.

FIXES = [
    (
        r'"    nombre_archivo=\'03_top10_trayectorias_global\'\\n"',
        '"    nombre_archivo=\'03_top10_trayectorias_global\',\\n",\n     "    subcarpeta=\'general\'\\n"',
    ),
    (
        r'"    nombre_archivo=\'04_top10_saltos_individuales\'\\n"',
        '"    nombre_archivo=\'04_top10_saltos_individuales\',\\n",\n     "    subcarpeta=\'general\'\\n"',
    ),
    (
        r'"    nombre_archivo=\'05_top10_saltos_apilados\'\\n"',
        '"    nombre_archivo=\'05_top10_saltos_apilados\',\\n",\n     "    subcarpeta=\'desenlaces\'\\n"',
    ),
]

patched = 0
for pattern, replacement in FIXES:
    new_raw, n = re.subn(pattern, replacement, raw)
    if n:
        raw = new_raw
        patched += n
        print(f"[OK] Reemplazado: {pattern[:60]}")
    else:
        print(f"[MISS] No encontrado: {pattern[:60]}")

print(f"\n[INFO] Total de reemplazos: {patched}")

with NB_PATH.open("w", encoding="utf-8") as f:
    f.write(raw)

print("[DONE] Notebook guardado.")
