
def asignar_color_origen(nombre):
    return COLORES_ORIGEN[clasificar_hospital(nombre)]

def redondear_estetico(valor):
    if valor <= 10: return 10
    if valor <= 100: return int(np.ceil(valor / 10) * 10)
    if valor <= 500: return int(np.ceil(valor / 50) * 50)
    return int(np.ceil(valor / 100) * 100)

def guardar_grafico_alta_calidad(nombre_archivo, bbox="tight"):
    ruta_salida = "results/outputs/red"
    os.makedirs(ruta_salida, exist_ok=True)
    ruta_completa = f"{ruta_salida}/{nombre_archivo}"
    
    plt.savefig(f"{ruta_completa}.png", dpi=300, bbox_inches=bbox, facecolor="white")
    plt.savefig(f"{ruta_completa}.svg", format="svg", bbox_inches=bbox)
    plt.savefig(f"{ruta_completa}.pdf", format="pdf", bbox_inches=bbox)
    print(f"Gráficos exportados en: {ruta_salida}")


# Funciones de visualizacion
###########################################

def aplicar_escala_visual(valor, max_valor, v_min, v_max, tipo='sqrt', min_valor=0):
    if max_valor == min_valor or valor == 0: 
        return v_min if valor > 0 else 0
    
    # Respetamos tu normalización original Min-Max Lineal para la escala cuadrática
    if min_valor > 0 and tipo == 'cuadratica':
        x = (valor - min_valor) / (max_valor - min_valor)
    else:
        x = valor / max_valor
        
    escala = np.sqrt(x) if tipo == 'sqrt' else (x**2 if tipo == 'cuadratica' else x)
    return v_min + (escala * (v_max - v_min))
def dibujar_grafo_nx(ax, G, posiciones, max_traslados, max_ingresos, cfg):
    lista_nodos = list(G.nodes())
    tamanos_reales = [G.nodes[n]['size'] for n in lista_nodos]

    # 1. DIBUJAR NODOS
    for forma in set(nx.get_node_attributes(G, 'shape').values()):
        nodelist = [n for n in lista_nodos if G.nodes[n]['shape'] == forma]
        if not nodelist: continue
        
        # FIX: Pasamos zorder como un parámetro de dibujo de Matplotlib
        nx.draw_networkx_nodes(
            G, posiciones, nodelist=nodelist, ax=ax, node_shape=forma, 
            node_color=[G.nodes[n]['color'] for n in nodelist], 
            node_size=[G.nodes[n]['size'] for n in nodelist], 
            alpha=[G.nodes[n]['alpha'] for n in nodelist], 
            edgecolors='white', linewidths=cfg.get('lw_nodos', 0.5),
            label=None  # A veces ayuda a limpiar
        ).set_zorder(4) # <-- Esta es la forma segura de asignar zorder en NetworkX

    # 2. DIBUJAR ARISTAS
    for u, v, data in G.edges(data=True):
        peso = data['weight']
        grosor = aplicar_escala_visual(peso, max_traslados, cfg['min_grosor'], cfg['max_grosor'], cfg.get('escala_arista', 'sqrt'))
        
        if cfg.get('color_por_origen'):
            color_flecha = asignar_color_origen(u)
        elif cfg.get('aristas_negras'):
            color_flecha = 'black'
        else:
            intensidad = 0.8 - 0.6 * (peso / max_traslados) if max_traslados > 0 else 0.2
            color_flecha = (intensidad, intensidad, intensidad)
        
        rad_dinamico = ((sum(ord(c) for c in u + v) % 90 - 35) / 100.0)
        if abs(rad_dinamico) < 0.12: rad_dinamico = 0.25 if rad_dinamico >= 0 else -0.25

        # FIX: Asignamos zorder usando el objeto retornado
        lineas = nx.draw_networkx_edges(
            G, posiciones, edgelist=[(u, v)], ax=ax, width=grosor, edge_color=[color_flecha], 
            alpha=cfg.get('alpha_arista', 0.5), arrowstyle='-|>', arrowsize=cfg.get('arrow_size', 15), 
            connectionstyle=f"arc3,rad={rad_dinamico}", 
            nodelist=lista_nodos, node_size=tamanos_reales
        )
        if lineas:
            for l in lineas:
                l.set_zorder(3)

    # 3. DIBUJAR ETIQUETAS
    labels = {k: k.replace('Módulo Hospitalario', 'MÓDULO').replace('Modulo Hospitalario', 'MÓDULO') for k in lista_nodos}
    pos_labels = {k: (v[0], v[1] + cfg.get('lbl_offset', 0.005)) for k, v in posiciones.items()} 
    
    bbox_cfg = dict(
        facecolor='white', 
        alpha=cfg.get('lbl_bbox_alpha', 0.7), 
        edgecolor='none', 
        boxstyle='round,pad=0.2'
    ) if cfg.get('lbl_bbox') else None

    # En etiquetas, zorder suele funcionar, pero lo aseguramos igual
    textos = nx.draw_networkx_labels(
        G, pos_labels, labels=labels, ax=ax, 
        font_size=cfg.get('lbl_size', 10), 
        font_color=cfg.get('lbl_color', '#333333'), 
        font_weight=cfg.get('lbl_weight', 'normal'),
        bbox=bbox_cfg
    )
    if textos:
        for t in textos.values():
            t.set_zorder(5)
    
    ax.axis('off')
    
def generar_leyendas(ax, v_max_raw, i_min_raw, i_max_raw, max_traslados, max_ingresos, cfg, posiciones_bbox):
    """ Creador maestro de leyendas con redondeo estricto e igualación visual """
    
    # REDONDEO OBLIGATORIO para que la leyenda siempre sea limpia
    v_max_g = redondear_estetico(v_max_raw)
    v_min_g = 5
    v_med_g = redondear_estetico(v_max_g / 2)
    
    i_max_g = redondear_estetico(i_max_raw)
    # Respetamos el comportamiento duro del mapa global (min = 50) si la config lo pide
    i_min_g = 50 if cfg.get('forzar_i_min_50') else redondear_estetico(i_min_raw)
    i_med_g = redondear_estetico(i_max_g / 2) if cfg.get('forzar_i_min_50') else redondear_estetico((i_max_g + i_min_g) / 2)
    
    # Helpers: calculan el tamaño usando el valor REDONDEADO contra el MÁXIMO REAL
    f_grosor = lambda p: aplicar_escala_visual(p, max_traslados, cfg['min_grosor'], cfg['max_grosor'], cfg.get('escala_arista', 'sqrt'))
    f_nodo = lambda i: np.sqrt(aplicar_escala_visual(i, max_ingresos, cfg['min_tamano'], cfg['max_tamano'], cfg.get('escala_nodo', 'sqrt'), cfg.get('min_ingresos_real', 0)))

    # === EL ARREGLO DE COLOR ===
    # Atamos el color y la transparencia de la leyenda a lo que diga la configuración del grafo
    color_linea = 'black' if cfg.get('aristas_negras') else 'grey'
    alpha_linea = cfg.get('alpha_arista', 0.5)

    # === CORRECCIÓN EN generar_leyendas ===

    # 1. Definimos los valores que queremos mostrar en la leyenda
    v_min_leg = 5 
    v_med_leg = 75
    v_max_leg = v_max_g

    proxies_vol = [
        mlines.Line2D([], [], color=color_linea, alpha=alpha_linea, 
                    linewidth=f_grosor(v_min_leg), label=f'{int(v_min_leg)}'),
        
        mlines.Line2D([], [], color=color_linea, alpha=alpha_linea, 
                    linewidth=f_grosor(v_med_leg), label=f'{int(v_med_leg)}'),
        
        mlines.Line2D([], [], color=color_linea, alpha=alpha_linea, 
                    linewidth=f_grosor(v_max_leg), label=f'{int(v_max_leg)}')
    ]
    
    proxies_col = [mlines.Line2D([], [], color=v, lw=3, label=k) for k, v in COLORES_ORIGEN.items()] if cfg.get('color_por_origen') else []
    
    # Los nodos los dejamos en gris oscuro (#444444) que es el estándar neutro para leyendas de tamaño
    proxies_nod = [
        mlines.Line2D([], [], color='white', marker='o', markerfacecolor='#444444', markersize=f_nodo(val), label=f'{int(val)}') 
        for val in [i_min_g, i_med_g, i_max_g]
    ]

    # 1. Calculamos el tamaño del círculo más grande para empujar los márgenes
    tamano_max_marcador = f_nodo(i_max_g)
    
    # 2. Espaciados dinámicos
    lbl_spc = max(1.5, tamano_max_marcador / 20) if cfg.get('leg_dynamic_spc') else 2.0
    h_height = max(2.0, tamano_max_marcador / 15) if cfg.get('leg_dynamic_spc') else 2.0

    # 3. DICCIONARIO MAESTRO DE ESTILO: Obliga a todas las leyendas a verse igual
    estilo_base = {
        'frameon': True,
        'title_fontsize': cfg.get('leg_title_sz', 14),
        'fontsize': cfg.get('leg_lbl_sz', 12),
        'borderpad': 1.8,             
        'labelspacing': lbl_spc,      
        'handletextpad': 1.5,         
        'handleheight': h_height      
    }

    # 4. Renderizamos (SIN duplicados y CON validación None)
    if posiciones_bbox[0] is not None:
        leg1 = ax.legend(handles=proxies_vol, title="Traslados", loc='upper left', 
                         bbox_to_anchor=posiciones_bbox[0], **estilo_base)
        ax.add_artist(leg1)
    
    if proxies_col and len(posiciones_bbox) > 1 and posiciones_bbox[1] is not None:
        leg2 = ax.legend(handles=proxies_col, title="Origen", loc='upper left', 
                         bbox_to_anchor=posiciones_bbox[1], **estilo_base)
        ax.add_artist(leg2)
    
    if posiciones_bbox[-1] is not None:
        ax.legend(handles=proxies_nod, title="Ingresos", loc='upper left', 
                  bbox_to_anchor=posiciones_bbox[-1], **estilo_base)


def agregar_etiquetas_grafico(ax, tipo='bar'):
    """ Agrega los números encima de las barras o los puntos """
    max_y = ax.get_ylim()[1]
    
    if tipo == 'bar' or tipo == 'stack':
        max_y_per_x = {}
        for p in ax.patches:
            h = p.get_height()
            if h > 0:
                x_c = p.get_x() + p.get_width() / 2.
                y_t = p.get_y() + h
                max_y_per_x[x_c] = max(max_y_per_x.get(x_c, 0), y_t)
        
        for x, top in max_y_per_x.items():
            if top >= (max_y * 0.02):
                ax.text(x, top * 1.1, f'{int(top)}', ha="center", va="bottom", fontsize=10, fontweight='bold', color='#333333')
    
    elif tipo == 'scatter':
        for c in ax.collections:
            for x, y in c.get_offsets():
                if y > 0: ax.text(x, y * 1.25, f'{int(y)}', ha="center", va="bottom", fontsize=10, fontweight='bold')
    
    ax.set_ylim(0.5 if ax.get_yscale() == 'log' else 0, max_y * 5 if ax.get_yscale() == 'log' else max_y * 1.1)



def generar_tabla_resumen(pacientes_df, traslados_df, periodos, hospitales_conocidos):
    columnas_tabla = {}
    
    for titulo, inicio, fin in periodos:
        fecha_ini, fecha_fin = pd.to_datetime(inicio), pd.to_datetime(fin)
        total_days = (fecha_fin - fecha_ini).days + 1
        
        # Admisiones
        df_p_per = pacientes_df[pacientes_df['fecha_ingreso'].between(inicio, fin)]
        admissions = len(df_p_per)
        pacientes_admitidos_unicos = df_p_per['paciente_id'].nunique()
        
        # Traslados Válidos (filtrando self-loops y no conocidos, igual que el mapa)
        df_t_bruto = traslados_df[traslados_df['fecha_egreso'].between(inicio, fin)]
        mask_validos = (df_t_bruto['hospital_ingreso'].isin(hospitales_conocidos)) & (df_t_bruto['hospital_destino'].isin(hospitales_conocidos)) & (df_t_bruto['hospital_ingreso'] != df_t_bruto['hospital_destino'])
        df_t_limpio = df_t_bruto[mask_validos]
        
        pesos_rutas = df_t_limpio.groupby(['hospital_ingreso', 'hospital_destino']).size().reset_index(name='peso')
        rutas_dibujables = pesos_rutas[pesos_rutas['peso'] > 2]
        df_t_periodo = df_t_limpio.merge(rutas_dibujables[['hospital_ingreso', 'hospital_destino']], on=['hospital_ingreso', 'hospital_destino'])
        
        total_transfers = len(df_t_periodo)
        df_amb_periodo = df_t_periodo[df_t_periodo['es_ambulancia']]
        amb_transfers = len(df_amb_periodo)
        
        edges_totales = df_t_periodo[['hospital_ingreso', 'hospital_destino']].drop_duplicates().shape[0]
        edges_amb = df_amb_periodo[['hospital_ingreso', 'hospital_destino']].drop_duplicates().shape[0]
        
        df_refuerzo = df_t_periodo[df_t_periodo['hospital_ingreso'].apply(es_upa_o_modulo)]
        
        columnas_tabla[titulo] = {
            'Días totales': f"{total_days}",
            'Admisiones (Prom. diario)': f"{admissions} ({admissions/total_days if total_days>0 else 0:.1f})",
            'Pacientes admitidos': f"{pacientes_admitidos_unicos}",
            'Traslados totales (% admisiones)': f"{total_transfers} ({(total_transfers/admissions*100) if admissions>0 else 0:.1f}%)",
            'Pacientes trasladados': f"{df_t_periodo['paciente_id'].nunique()}",
            'Promedio diario de traslados': f"{total_transfers/total_days if total_days>0 else 0:.1f}",
            'Traslados en ambulancia (% total)': f"{amb_transfers} ({(amb_transfers/total_transfers*100) if total_transfers>0 else 0:.1f}%)",
            'Traslados UPA-Módulos': f"{len(df_refuerzo)}",
            'Rutas UPA-Módulos': f"{df_refuerzo[['hospital_ingreso', 'hospital_destino']].drop_duplicates().shape[0]}",
            'Rutas totales | Ambulancia': f"{edges_totales} | {edges_amb}",
            'Promedio traslados por ruta | Ambulancia': f"{total_transfers/edges_totales if edges_totales>0 else 0:.1f} | {amb_transfers/edges_amb if edges_amb>0 else 0:.1f}"
        }

    orden_filas = ['Días totales', 'Admisiones (Prom. diario)', 'Pacientes admitidos', 'Traslados totales (% admisiones)', 'Pacientes trasladados', 'Promedio diario de traslados', 'Traslados en ambulancia (% total)', 'Traslados UPA-Módulos', 'Rutas UPA-Módulos', 'Rutas totales | Ambulancia', 'Promedio traslados por ruta | Ambulancia']
    return pd.DataFrame(columnas_tabla).loc[orden_filas]

def exportar_tabla_estetica(tabla_df):
    """ Dibuja la tabla con Matplotlib y exporta a LaTeX """
    # 1. LaTeX
    latex_code = tabla_df.reset_index().style.format(escape="latex").hide(axis="index").to_latex(
        buf="results/outputs/red/tabla_resumen.tex", column_format='l' + 'c' * len(tabla_df.columns), hrules=True
    )
    
    # 2. Matplotlib
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.axis('tight'); ax.axis('off')
    tabla_mpl = ax.table(cellText=tabla_df.values, rowLabels=tabla_df.index, colLabels=tabla_df.columns, loc='center', cellLoc='center')
    
    tabla_mpl.auto_set_font_size(False)
    tabla_mpl.set_fontsize(12)
    tabla_mpl.scale(1.2, 2.2)

    for (row, col), cell in tabla_mpl.get_celld().items():
        cell.set_edgecolor('#cccccc')
        if row == 0: cell.set_facecolor('#4c72b0'); cell.set_text_props(weight='bold', color='white')
        elif col == -1: cell.set_facecolor('#e8e8e8'); cell.set_text_props(weight='bold', color='#333333'); cell._loc = 'left'
        else: cell.set_facecolor('#f5f5f5' if row % 2 == 0 else '#ffffff')

    plt.title("Resumen de Admisiones y Traslados por Periodo", fontsize=18, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.show()



# Funciones de Anotación Originales (Intactas)
def agregar_valores_scatter(ax, x_vals, y_vals):
    for x, y in zip(x_vals, y_vals):
        if y > 0: ax.text(x, y * 1.25, f'{int(y)}', ha="center", va="bottom", fontsize=10, fontweight='bold', color='#2b2b2b')
    ax.set_ylim(0.5, (max(y_vals) if len(y_vals) > 0 else 1) * 5)

def agregar_valores_barras(ax):
    for p in ax.patches:
        h = p.get_height()
        if h > 0: ax.text(p.get_x() + p.get_width() / 2., (p.get_y() + h) * 1.2, f'{int(h)}', ha="center", va="bottom", fontsize=10, fontweight='bold', color='#2b2b2b')
    ax.set_ylim(0.5, ax.get_ylim()[1] * 5)

def agregar_valores_totales(ax):
    max_y_per_x = {}
    for p in ax.patches:
        h = p.get_height()
        if h > 0:
            x_c, y_t = p.get_x() + p.get_width() / 2., p.get_y() + h
            if x_c not in max_y_per_x or y_t > max_y_per_x[x_c]: max_y_per_x[x_c] = y_t
    
    max_y_axis = ax.get_ylim()[1]
    for x_c, total_height in max_y_per_x.items():
        if total_height >= (max_y_axis * 0.02):
            ax.text(x_c, total_height + (max_y_axis * 0.01), f'{int(total_height)}', ha="center", va="bottom", fontsize=9, fontweight='bold', color='#333333')
    ax.set_ylim(0, max_y_axis * 1.1)

def graficar_traslados_paciente(df_stats, df_pacientes, es_global=False):
    global promedios_traslados
    
    if es_global:
        fig, axes = plt.subplots(figsize=(14, 8)); axes = [axes]
        iteracion = [("Global", None, None)]
    else:
        # REQ 7: sharex=True y sharey=True para mantener todos en la misma escala
        fig, axes = plt.subplots(2, 2, figsize=(18, 12), sharex=True, sharey=True)
        fig.suptitle("Número de traslados por paciente por Periodo", fontsize=22, fontweight='bold', y=0.98)
        axes = axes.flatten()
        iteracion = PERIODOS

    fig.patch.set_facecolor('white')

    for ax, (titulo, inicio, fin) in zip(axes, iteracion):
        mask_p = df_pacientes['fecha_ingreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_pacientes.index)
        mask_t = df_stats['fecha_egreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_stats.index)
        
        df_t_per, df_p_per = df_stats[mask_t], df_pacientes[mask_p]
        cero_traslados = len(set(df_p_per['paciente_id']) - set(df_t_per['paciente_id']))
        
        # REQ 5: Calcular promedio total de traslados por paciente (incluyendo ceros)
        total_pacientes = df_p_per['paciente_id'].nunique()
        total_traslados = len(df_t_per)
        promedio = total_traslados / total_pacientes if total_pacientes > 0 else 0
        promedios_traslados["Global" if es_global else titulo] = promedio
        
        if not df_p_per.empty: # Evaluamos df_p_per para que grafique incluso si solo hay pacientes con 0
            conteo = df_t_per.groupby('paciente_id').size().value_counts()
            
            # REQ 1: Agregar pacientes con 0 traslados a la serie de datos
            if cero_traslados > 0:
                conteo.loc[0] = cero_traslados
            
            # Ordenamos el índice (0, 1, 2, 3...) para que la línea se dibuje bien
            conteo = conteo.sort_index()

            # REQ 2: Curva uniendo los puntos (se sacó el ax.vlines de las barras)
            ax.plot(conteo.index, conteo.values, color='#4c72b0', linestyle='-', linewidth=2.5, alpha=0.6, zorder=2)
            # Mantenemos el scatter de los puntos
            sns.scatterplot(x=conteo.index, y=conteo.values, color='#4c72b0', s=150 if not es_global else 250, edgecolor='black', linewidth=1.5, ax=ax, zorder=3)
            
            ax.set_yscale('log')
            agregar_valores_scatter(ax, conteo.index, conteo.values)
        
        # REQ 3 y REQ 6: Sin "(Log)" y con valores de ejes más grandes
        ax.set_title(titulo, fontsize=16)
        ax.set_xlabel("Cantidad de traslados", fontsize=14)
        ax.set_ylabel("Cantidad de pacientes", fontsize=14)
        ax.tick_params(axis='both', which='major', labelsize=12)
        
        # REQ 4: Sacar la cuadrícula
        ax.grid(False)
        
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        # REQ 1: Se eliminó la leyenda `ax.legend(...)` que mostraba los 0 traslados apartados

    plt.tight_layout(rect=[0, 0, 1, 0.96 if not es_global else 1], pad=3.0)
    plt.show()

def graficar_tiempo_sistema(df_todas, df_traslados, es_global=False):
    if es_global:
        # REQ 3: sharey=True y sharex=True para asegurar la misma escala en ambos gráficos
        fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=True, sharex=True)
        fig.suptitle("Tiempo total en el sistema: Global vs Trasladados", fontsize=22, fontweight='bold', y=1.02)
        iteraciones = [("Global", None, None, axes)]
    else:
        # REQ 4: Versión por periodo (Cuadrícula dinámica de N filas x 2 columnas)
        filas = len(PERIODOS)
        fig, axes = plt.subplots(filas, 2, figsize=(16, 5 * filas), sharey=True, sharex=True)
        fig.suptitle("Tiempo total en el sistema por Periodo", fontsize=22, fontweight='bold', y=0.98)
        iteraciones = [(titulo, inicio, fin, axes[i]) for i, (titulo, inicio, fin) in enumerate(PERIODOS)]

    fig.patch.set_facecolor('white')

    for titulo_per, inicio, fin, axes_row in iteraciones:
        # Filtrar datos por periodo usando la fecha de ingreso
        mask_per = df_todas['ingreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_todas.index)
        df_todas_per = df_todas[mask_per]
        # Nos quedamos con los trasladados que corresponden a ese subset temporal
        df_traslados_per = df_traslados[df_traslados.index.isin(df_todas_per.index)]

        for ax, subtitulo, df_subset, color in zip(axes_row, ["Todos los pacientes", "Solo Trasladados"], [df_todas_per, df_traslados_per], ['#4c72b0', '#1a9850']):
            if not df_subset.empty:
                sns.histplot(df_subset['dias_en_sistema'], bins=bins_5dias, color=color, ax=ax, edgecolor='black', alpha=0.8)
                
                # REQ 2: Se mantiene explícitamente la escala logarítmica
                ax.set_yscale('log')
                agregar_valores_barras(ax)
                
                mediana = df_subset['dias_en_sistema'].median()
                if not pd.isna(mediana):
                    ax.axvline(mediana, color='red', linestyle='dashed', linewidth=2)
                    # REQ 1: Se eliminó la palabra "Mediana:", quedando solo "X días"
                    ax.text(mediana + 1, ax.get_ylim()[1]*0.5, f'{int(mediana)} días', color='red', fontweight='bold', fontsize=12)
            
            # Formato general de ejes y títulos estandarizado
            titulo_final = f"{titulo_per} - {subtitulo}" if not es_global else subtitulo
            ax.set_title(titulo_final, fontsize=16)
            ax.set_xlabel("Días totales", fontsize=14)
            ax.set_ylabel("Cantidad de personas", fontsize=14) # Eliminado "(Log)" del texto
            ax.set_xlim(0, max_plot)
            ax.set_xticks(np.arange(0, max_plot + 5, 10))
            ax.tick_params(axis='both', which='major', labelsize=12)
            ax.grid(False)

    plt.tight_layout(rect=[0, 0, 1, 0.96 if not es_global else 1], pad=3.0)
    plt.show()

def graficar_tiempo_traslado(df_mov, es_global=False):
    if es_global:
        fig, axes = plt.subplots(figsize=(14, 8)); axes = [axes]
        iteracion = [("Tiempo hasta traslado (Estadía en nodo origen) - Global", None, None)]
    else:
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle("Tiempo hasta traslado (Estadía en nodo origen) por Periodo", fontsize=22, fontweight='bold', y=0.98)
        axes = axes.flatten()
        iteracion = PERIODOS

    fig.patch.set_facecolor('white')

    for ax, (titulo, inicio, fin) in zip(axes, iteracion):
        mask_m = df_mov['fecha_egreso'].between(inicio, fin) if inicio else pd.Series(True, index=df_mov.index)
        df_m_per = df_mov[mask_m]
        
        if not df_m_per.empty:
            sns.histplot(data=df_m_per, x='dias_antes_traslado', hue='tipo_hospital', palette=COLORES_ORIGEN, multiple='stack', bins=bins_mov_5, ax=ax, edgecolor='white')
            agregar_valores_totales(ax)
            
        ax.set(title=titulo, xlabel="Días de estadía antes de ser trasladado", ylabel="Cantidad de traslados", xlim=(0, max_plot_nodo))

    plt.tight_layout(rect=[0, 0, 1, 0.95], pad=3.0)
    plt.show()
