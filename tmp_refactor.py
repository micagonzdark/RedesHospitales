import json
import os

notebook_path = r"c:\Users\micag\Documents\RedesHospitales\notebooks\05_JAIIO.ipynb"
backup_path = r"c:\Users\micag\Documents\RedesHospitales\notebooks\05_JAIIO_backup.ipynb"

# Hacer por precaucion una copia local del notebook antes de la refactorización. (Aunque ya hay git, esto refuerza el conservadurismo)
import shutil
shutil.copyfile(notebook_path, backup_path)

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Código general del render de Nodos y Aristas abstraído (A inyectar al principio del nb)
func_source = [
    "def dibujar_nodos_y_aristas(G, posiciones, ax, max_traslados):\n",
    "    formas_presentes = set(nx.get_node_attributes(G, 'shape').values())\n",
    "    for forma in formas_presentes:\n",
    "        nodelist = [n for n in G.nodes() if G.nodes[n].get('shape', 'o') == forma]\n",
    "        if not nodelist: continue\n",
    "        nx.draw_networkx_nodes(G, posiciones, nodelist=nodelist, ax=ax, \n",
    "                               node_shape=forma, \n",
    "                               node_color=[G.nodes[n].get('color', 'grey') for n in nodelist], \n",
    "                               node_size=[G.nodes[n].get('size', 100) for n in nodelist], \n",
    "                               alpha=[G.nodes[n].get('alpha', 0.9) for n in nodelist],\n",
    "                               edgecolors='white', linewidths=0.5)\n",
    "\n",
    "    for u, v, data in G.edges(data=True):\n",
    "        peso = data.get('weight', 1)\n",
    "        escala_peso = np.sqrt(peso) / np.sqrt(max_traslados) if max_traslados > 0 else 0\n",
    "        grosor = MIN_GROSOR_ARISTA + (escala_peso * (MAX_GROSOR_ARISTA - MIN_GROSOR_ARISTA))\n",
    "\n",
    "        color_flecha = asignar_color_tipo(str(u))\n",
    "    \n",
    "        suma_caracteres = sum(ord(c) for c in str(u) + str(v))\n",
    "        rad_dinamico = (suma_caracteres % 85 - 35) / 100.0\n",
    "        if abs(rad_dinamico) < 0.12: rad_dinamico = 0.25 if rad_dinamico >= 0 else -0.25\n",
    "\n",
    "        nx.draw_networkx_edges(G, posiciones, edgelist=[(u, v)], ax=ax,\n",
    "                                width=grosor, edge_color=color_flecha, alpha=0.5,\n",
    "                                arrowstyle='-|>', arrowsize=15, \n",
    "                                connectionstyle=f\"arc3,rad={rad_dinamico}\")\n"
]

new_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": "refactor_helper_functions_v1",
    "metadata": {},
    "outputs": [],
    "source": func_source
}

# Determinar dónde inyectar la celda de funciones (Después del bloque de definición "MIN_GROSOR_ARISTA")
insert_idx = 0
for i, cell in enumerate(nb['cells']):
    if cell["cell_type"] == "code":
        src = "".join(cell.get("source", []))
        if "MIN_GROSOR_ARISTA" in src and "def calc_grosor(peso):" in src:
            insert_idx = i + 1
            break

if insert_idx > 0:
    nb['cells'].insert(insert_idx, new_cell)

# Refactorizar celdas que repiten el código
modificados = 0
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        lines = cell.get('source', [])
        
        while True:
            start_idx = -1
            end_idx = -1
            for i, line in enumerate(lines):
                if "formas_presentes =" in line and "nx.get_node_attributes" in line:
                    start_idx = i
                elif ("connectionstyle=f\"arc3,rad={rad_dinamico}\"" in line or "connectionstyle=f'arc3,rad={rad_dinamico}'" in line) and start_idx != -1:
                    end_idx = i
                    break
            
            if start_idx != -1 and end_idx != -1:
                # Comprobar la indentación
                indent_str = lines[start_idx][:len(lines[start_idx]) - len(lines[start_idx].lstrip())]
                
                # Identificar la constante de máxima escala usada en la celda
                src_str = "".join(lines)
                max_var = "MAX_TRASLADOS_GLOBAL"
                if "MAX_TRASLADOS_COMPLEJIDAD" in src_str:
                    max_var = "MAX_TRASLADOS_COMPLEJIDAD"
                elif "MAX_TRASLADOS_TIPO" in src_str:
                    max_var = "MAX_TRASLADOS_TIPO"
                
                new_call = f"{indent_str}dibujar_nodos_y_aristas(G, posiciones, ax, {max_var})\n"
                
                # Eliminar las lineas del bloque duplicado e inyectar el llamado a función
                lines = lines[:start_idx] + [new_call] + lines[end_idx+1:]
                modificados += 1
            else:
                break
                
        cell['source'] = lines

print(f"Celdas modificadas/refactorizadas exitosamente: {modificados}")

# Guarda el json con el identado orginal del sistema jupyter
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    # Jupyter tiene el quirk de un \n extra al final
    f.write("\n")
