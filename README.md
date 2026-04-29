# RedesHospitales

Proyecto de análisis de redes de traslados de pacientes en la **Red Sudeste** (Conurbano Sur, Buenos Aires). Cubre 14 hospitales en los municipios de Quilmes, Almirante Brown, Florencio Varela y Berazategui, con datos de marzo 2020 a diciembre 2022.

## Estructura del repositorio

```
RedesHospitales/
├── JAIIO_notebooks/          # Notebooks de producción (para publicación)
│   └── results/outputs/      # Outputs generados (mapas, tablas)
│         └── /red/
│         └── /geo/           
│   ├── 01_redes_basico.ipynb
│   ├── 02_mapas.ipynb
│   ├── 03_ranking_trayectorias.ipynb
│   └── 04_trayectorias_causas.ipynb
├── definitions_notebooks/    # Definición de reglas clínicas y pipelines (ETL)
│   ├── 01_limpieza_episodios.ipynb
│   ├── 02.TRAYECTORIAS.ipynb
│   ├── 03.TRASLADOS.ipynb
│   ├── 04.COMPARACION.ipynb
│   └── criterios_y_decisiones.md
├── data/                     # Datos (no incluidos en el repo, ver abajo)
├── docs/                     # Documentación y notas del proyecto
├── src/                      # Módulos Python reutilizables
│   ├── config.py
│   ├── io.py
│   ├── funciones_complejas.py
│   └── visualizacion.py
├── scripts/                  # Scripts auxiliares (viejos)
├── results/                  # Resultados y análisis
└── requirements.txt
```

> Los notebooks de exploración anteriores se encuentran en `OLD_notebooks/exploracion_vieja/` (solo local, ignorados por git).

## Notebooks de producción (JAIIO)

Ejecutar en orden desde `JAIIO_notebooks/`:

| # | Notebook | Descripción |
|---|---|---|
| 01 | `01_redes_basico.ipynb` | Construcción y análisis de la red de traslados (grafo, métricas, visualización) |
| 02 | `02_mapas.ipynb` | Mapas geográficos interactivos de la red hospitalaria |
| 03 | `03_ranking_trayectorias.ipynb` | Ranking y análisis de trayectorias de pacientes |
| 04 | `04_trayectorias_causas.ipynb` | Análisis de trayectorias por causa de internación |

## Instalación

```bash
pip install -r requirements.txt
```

## Datos necesarios (no incluidos en el repo)

Colocar en `data/`:

- `pacientes.xlsx` — base de episodios de internación
- `hospitales_coordenadas.csv` — coordenadas de los hospitales
- `shapefiles/departamento/departamentoPolygon.shp` — shapefile de departamentos

## Módulos principales (`src/`)

- **`config.py`**: Rutas y parámetros globales del proyecto.
- **`io.py`** (`init_notebook`): Inicializa el entorno de análisis (carga datos, coordenadas y shapefiles).
- **`funciones_complejas.py`**: Construcción y análisis de grafos/redes.
- **`visualizacion.py`**: Funciones de graficación y mapas.
