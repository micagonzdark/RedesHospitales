import json
import os

notebook_path = r'c:\Users\micag\Documents\RedesHospitales\notebooks\03_trayectorias_pacientes.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# 1. Agregar import a la primera celda
first_cell = nb['cells'][1] # La primera es markdown, la segunda es código
if 'import networkx as nx' not in "".join(first_cell['source']):
    first_cell['source'].insert(4, 'import networkx as nx\n')

# 2. Definir función auxiliar y agregarla después de filtrar_validos_code
helper_functions = """
def graficar_grafo_transicion(matriz, titulo, node_size=2000, font_size=10, k=1.5):
    import networkx as nx
    G = nx.DiGraph()
    
    # Crear nodos y aristas con pesos
    for i in matriz.index:
        for j in matriz.columns:
            weight = matriz.loc[i, j]
            if weight > 0.01: # Solo mostrar transiciones significativas
                G.add_edge(str(i), str(j), weight=weight)
    
    pos = nx.spring_layout(G, k=k, seed=42)
    plt.figure(figsize=(12, 8))
    
    # Dibujar nodos
    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color='skyblue', alpha=0.7)
    nx.draw_networkx_labels(G, pos, font_size=font_size, font_family='sans-serif')
    
    # Dibujar aristas con grosores proporcionales al peso
    edges = G.edges(data=True)
    weights = [d['weight'] * 10 for u, v, d in edges]
    nx.draw_networkx_edges(G, pos, width=weights, edge_color='gray', arrowsize=20, alpha=0.5)
    
    # Etiquetas de aristas (pesos)
    edge_labels = {(u, v): f"{d['weight']:.1%}" for u, v, d in edges}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=font_size-2)
    
    plt.title(titulo)
    plt.axis('off')
    plt.show()
"""

# Buscar índice de filtro_validos_code
idx_filter = -1
for i, cell in enumerate(nb['cells']):
    if cell.get('id') == 'filtro_validos_code':
        idx_filter = i
        break

if idx_filter != -1:
    new_cell = {
        "cell_type": "code",
        "execution_count": None,
        "id": "helper_graphs",
        "metadata": {},
        "outputs": [],
        "source": [helper_functions.strip()]
    }
    nb['cells'].insert(idx_filter + 1, new_cell)

# 3. Actualizar Redes
for cell in nb['cells']:
    cid = cell.get('id')
    if cid == 'red_1_poblacion':
        cell['source'].append("\n# Grafo simple de flujo global\n")
        cell['source'].append("df_red1 = pd.DataFrame({'ALTA': [p_alta], 'MUERTE': [p_muerte]}, index=['POBLACIÓN'])\n")
        cell['source'].append("graficar_grafo_transicion(df_red1, 'Grafo de Flujo Global', node_size=3000, k=2)\n")
    
    elif cid == 'red_2_secuencial':
        cell['source'].append("\n# Grafo de trayectoria secuencial\n")
        cell['source'].append("edges_seq = []\n")
        cell['source'].append("for i, row in df_resumen_pasos.iterrows():\n")
        cell['source'].append("    idx = int(i.split()[-1])\n")
        cell['source'].append("    if row['Traslado'] > 0: edges_seq.append({'Origen': i, 'Destino': f'Hospi {idx+1}', 'Prob': row['Traslado']})\n")
        cell['source'].append("    if row['Alta'] > 0: edges_seq.append({'Origen': i, 'Destino': '[ALTA]', 'Prob': row['Alta']})\n")
        cell['source'].append("    if row['Muerte'] > 0: edges_seq.append({'Origen': i, 'Destino': '[MUERTE]', 'Prob': row['Muerte']})\n")
        cell['source'].append("df_edges_seq = pd.DataFrame(edges_seq)\n")
        cell['source'].append("matriz_seq = df_edges_seq.pivot(index='Origen', columns='Destino', values='Prob').fillna(0)\n")
        cell['source'].append("graficar_grafo_transicion(matriz_seq, 'Grafo de Trayectoria Secuencial', node_size=2500, k=2)\n")

    elif cid == 'red_3_hospitalaria':
        cell['source'].append("\n# Grafo de transición hospitalaria\n")
        cell['source'].append("graficar_grafo_transicion(matriz_hosp, 'Grafo de Transición entre Hospitales', node_size=1500, font_size=8, k=3)\n")
    
    elif cid == 'red_4_niveles':
        cell['source'].append("\n# Grafo de transición de niveles de complejidad\n")
        cell['source'].append("graficar_grafo_transicion(matriz_niveles, 'Grafo de Transición de Niveles de Complejidad', node_size=3000, k=2)\n")

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook actualizado correctamente.")
