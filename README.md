# Análisis de derivaciones hospitalarias

Analizamos los **traslados de pacientes entre hospitales** como una **red dirigida**.  
Combinamos el análisis exploratorio clásico con herramientas de **teoría de redes** para entender los patrones de derivación entre instituciones.

---

# Estructura del repositorio

## `bases.py`

Archivo con **funciones reutilizables** que vamos a usar a lo largo de todo el proyecto.

Incluye funciones para:

- limpieza de datos
- análisis de derivaciones
- construcción de redes hospitalarias
- visualización de grafos
- mapas geográficos de derivaciones

La idea es **centralizar ahí toda la lógica reusable** para que los notebooks queden más limpios.

---

## Datos

### `traslados.csv`

Dataset principal con **instancias de pacientes trasladados entre hospitales**.

Incluye información como:

- hospital de origen
- hospital de destino
- fecha
- motivo de traslado
- información clínica básica

Este dataset es la base para construir la red hospitalaria.

---

### `hospitales_coordenadas.csv`

Archivo con **coordenadas geográficas de hospitales**.

Las coordenadas fueron **extraídas manualmente de Google Maps**, por lo que todavía **falta revisarlas y validarlas**.

Se usan para:

- visualizaciones geográficas
- mapas de derivaciones
- redes hospitalarias sobre mapa

---

# Notebooks

## 1. `EDA.ipynb`

Primer análisis exploratorio del dataset.

Objetivos:

- entender la estructura de los datos
- revisar calidad de los datos
- detectar problemas de limpieza
- ver distribuciones básicas
- entender volumen de traslados

Es un **EDA clásico de dataset**.

---

## 2. `EDA_redes.ipynb`

Análisis exploratorio pero **desde el punto de vista de teoría de redes**.

Se construye la red de hospitales y se analizan propiedades como:

- nodos (hospitales)
- aristas (derivaciones)
- pesos (cantidad de traslados)
- grado de los nodos
- patrones de derivación

La idea es usar **herramientas típicas de network analysis** para entender la estructura del sistema.

---

## 3. `poster_replicacion.ipynb`

Notebook para **recrear todos los resultados y gráficos del poster de Tomás**.

*(En desarrollo: semana del 9 al 13 de marzo)*

La idea es tener **una versión reproducible** de todos los resultados del poster.

---

## 4. `trayectorias_pacientes.ipynb`

Notebook enfocado en **trayectorias individuales de pacientes**.

Objetivos iniciales:

- reconstruir secuencias de hospitales por paciente
- analizar longitud de trayectorias
- ver patrones de derivación
- detectar recorridos frecuentes

Este análisis es **más preliminar** y se va a desarrollar durante la semana siguiente.

---

# Función principal: `analizar_red_hospitalaria`

Construye una **red dirigida de derivaciones hospitalarias** a partir de un dataframe de traslados.  
Puede filtrar datos, generar el grafo (`networkx`) y opcionalmente visualizarlo.

## Parámetros

- `traslados` — DataFrame con los registros de traslados
- `hosp_coords` — DataFrame con las coordenadas de los hospitales (necesario para modos visuales)
- `fecha_inicio`, `fecha_fin` — filtros por fecha
- `filtrar_motivo` — lista de motivos de traslado a incluir
- `hospital_origen`, `hospital_destino` — filtros por hospital
- `peso_minimo` — mínimo de traslados para incluir una arista
- `modo` — `"grafo"`, `"geo"`, `"mapa"`, `"interactivo"`
- `graficar` — si `True`, muestra la visualización
- `mostrar_pesos` — muestra pesos de aristas
- `layout` — layout del grafo (`spring`, `circular`, `kamada_kawai`)
- `mostrar_resumen` — imprime resumen de la red

## Retorna

Devuelve la tupla `(G, edges)` con el grafo de `networkx` y el dataframe de aristas.

## Ejemplos

```python
# Construir la red sin graficar
G, edges = analizar_red_hospitalaria(df_traslados, graficar=False)

# Grafo simple
analizar_red_hospitalaria(df_traslados, modo="grafo", mostrar_pesos=True)

# Red geográfica
analizar_red_hospitalaria(df_traslados, hosp_coords, modo="geo")

# Mapa interactivo
m = analizar_red_hospitalaria(df_traslados, hosp_coords, modo="interactivo")
m.save("red_hospitalaria.html")
```