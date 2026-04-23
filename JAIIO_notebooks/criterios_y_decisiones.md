# Criterios y Reglas de Negocio: Proyecto RedesHospitales

Este documento detalla las decisiones metodológicas tomadas para la limpieza, procesamiento y construcción de la red de traslados de la **Red Sudeste (Conurbano Sur, Buenos Aires)**.

## 1. Calidad de Datos e Identidad (Data Quality)

Para garantizar que una trayectoria pertenezca fehacientemente al mismo individuo y no sea producto de errores de carga de ID, se aplican los siguientes filtros:

* **Consistencia de Edad:** Se valida que la edad del paciente no varíe en más de **2 años** entre diferentes registros de internación.
    * *Razón:* Cambios mayores sugieren errores de tipeo en el ID o reutilización de identificadores en el sistema hospitalario.
* **Limpieza de Nombres:** Normalización de nombres de hospitales (ej: Módulos Hospitalarios) para evitar duplicación de nodos en la red por errores de acentuación o espacios.

## 2. Definición del Desenlace Clínico (Fin de Caso)

Dada la existencia de registros duplicados o actualizaciones administrativas posteriores al evento clínico, se descarta la regla de "último registro" (`last`) en favor de una **Jerarquía de Prioridad Clínica**:

1.  **Defunción (Prioridad 1):** Si existe un registro de óbito, este se considera el desenlace final absoluto, invalidando registros administrativos posteriores.
2.  **Alta Médica (Prioridad 2):** Cierre clínico estándar.
3.  **Traslado Extra-Sanitario / Hotel (Prioridad 3).**
4.  **Traslado fuera de la Red (Prioridad 4).**

### Manejo de Censura e Inconclusos
Los pacientes cuyo último registro sea **"Otro"**, **"Anulado"** o **"NaN"** se clasifican como **Censurado/Inconcluso**. No se imputan como "Alta" para evitar sesgos de supervivencia y sobreestimación del éxito clínico de la red.

## 3. Construcción de Trayectorias (La Red)

La red se construye identificando "aristas" (traslados) entre episodios de internación de un mismo paciente.

### La Estrategia del "Pegamento" (Shift Logic)
Se utiliza la función `shift(-1)` agrupada por `paciente_id` para alinear el hospital de origen con el hospital de destino inmediato en una sola fila de análisis.

### Validación Cruzada de Traslados
Un traslado se considera válido únicamente si cumple con la intersección de dos criterios:
1.  **Intención Médica:** El motivo de egreso indica "Traslado" O el motivo es ambiguo (Otro/Vacío) pero la realidad del sistema confirma el movimiento.
2.  **Realidad Sistémica:** El paciente efectivamente ingresa a un hospital distinto en un periodo de tiempo lógico.

## 4. Ventana Temporal y Tolerancia Administrativa

Esta es la regla crítica para la construcción de la red. Se define una ventana de **±5 días** entre el egreso del Hospital A y el ingreso al Hospital B.

* **Límite Superior (+5 días):** Se considera que un reingreso después de los 5 días de un alta no es una derivación directa, sino un nuevo episodio independiente (ej: el paciente volvió a su casa y re-intervino el sistema por un evento nuevo).
* **Límite Inferior / Solapamiento (-5 días):** Se permite un gap negativo (el ingreso a B ocurre antes del egreso de A) de hasta 5 días.
    * *Justificación:* En la gestión hospitalaria real, es frecuente que un paciente sea trasladado físicamente un lunes, pero su ficha administrativa en el hospital de origen se cierre recién el jueves. Sin esta **Tolerancia Administrativa**, perderíamos un gran volumen de traslados reales debido a demoras de carga burocrática.
* **Regla de Física:** En ningún caso el ingreso al Hospital B puede ser anterior al ingreso al Hospital A.

## 5. Resumen de Estados Excluidos

Los siguientes motivos de egreso se consideran "Ruido" y no se utilizan para definir cierres de trayectoria válidos ni traslados, a menos que la ventana temporal de ingreso al siguiente nodo demuestre lo contrario:
* `anulado`
* `otro`
* `traslado-hospital-de-la-red` (cuando es el último registro, se considera un traslado fallido o sin recepción confirmada).