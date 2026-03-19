# RedesHospitales

Proyecto de análisis de redes de traslados de pacientes en la **Red Sudeste** (Conurbano Sur, Buenos Aires). Cubre 14 hospitales en los municipios de Quilmes, Almirante Brown, Florencio Varela y Berazategui, con datos de marzo 2020 a diciembre 2022.

## Lo que más usamos

*   **`scripts/bases.py`**: Módulo central con todas las funciones estandarizadas de carga de datos, limpieza, gráficos (plot), generación de redes y GDFs.
*   **`scripts/init_notebook.py`**: Inicializa el entorno de análisis en un notebook (carga datos, coordenadas y shapefiles de una sola vez).
*   **`scripts/limpieza.py`**: Funciones auxiliares de limpieza y preprocesamiento.
*   **`scripts/poster.py`**: Funciones específicas para generar las figuras del poster académico.

## Notebooks

*   **`notebooks/00_setup.ipynb`**: Configuración inicial y verificación del entorno.
*   **`notebooks/01_EDA.ipynb`**: Análisis exploratorio principal: volúmenes, red hospitalaria, métricas, trayectorias y mapas.
*   **`notebooks/02_analisis_a_detalle.ipynb`**: Análisis en profundidad de trayectorias de pacientes y roles source/sink por hospital.
*   **`notebooks/03_poster_outputs.ipynb`**: Generación de las figuras y tablas del poster académico.

## Datos necesarios (no incluidos en el repo)

Colocar en `data/`:
- `pacientes.xlsx`
- `hospitales_coordenadas.csv`
- `shapefiles/departamento/departamentoPolygon.shp`

## A futuro

Construir una pantalla de decisión operativa para recomendación de derivaciones en tiempo real. Ver `docs/` para más detalles e ideas.