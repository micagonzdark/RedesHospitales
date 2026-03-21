# RedesHospitales

Proyecto de análisis de redes de traslados de pacientes en la **Red Sudeste** (Conurbano Sur, Buenos Aires). Cubre 14 hospitales en los municipios de Quilmes, Almirante Brown, Florencio Varela y Berazategui, con datos de marzo 2020 a diciembre 2022.

## Lo que más usamos

*   **`scripts/bases.py`**: Módulo central con todas las funciones estandarizadas de carga de datos, limpieza, gráficos (plot), generación de redes y GDFs.
*   **`scripts/init_notebook.py`**: Inicializa el entorno de análisis en un notebook (carga datos, coordenadas y shapefiles de una sola vez).
*   **`scripts/limpieza.py`**: Funciones auxiliares de limpieza y preprocesamiento.
*   **`scripts/poster.py`**: Funciones específicas para generar las figuras del poster académico.

## Notebooks

*   **`notebooks/00_setup.ipynb`**: Configuración inicial y verificación del entorno.
*   **`notebooks/01_red_hospitalaria.ipynb`**: Análisis de la red de traslados: mapa, métricas de grafo (betweenness, SSR), flujos frecuentes y evolución temporal.
*   **`notebooks/02_analisis_por_hospital.ipynb`**: Análisis descriptivo por hospital: traslados, tiempo de internación, fallecidos, riesgo social y análisis combinado.
*   **`notebooks/03_trayectorias_pacientes.ipynb`**: Análisis en profundidad de trayectorias de pacientes y limpieza detallada del dataset.
*   **`notebooks/04_poster_outputs.ipynb`**: Generación de las figuras y tablas del poster académico.

## Datos necesarios (no incluidos en el repo)

Colocar en `data/`:
- `pacientes.xlsx`
- `hospitales_coordenadas.csv`
- `shapefiles/departamento/departamentoPolygon.shp`
