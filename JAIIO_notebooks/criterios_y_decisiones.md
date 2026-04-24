# Criterios para cada tabla

## BASE 1 — Episodios (Internaciones)

### 1. ¿Qué es un “episodio válido”?

> Un episodio válido es una **internación que probablemente ocurrió en la realidad clínica**, aunque tenga imperfecciones administrativas.

#### Condiciones mínimas (core)

Un episodio debería tener:

* `paciente_id` **no nulo**
* `fecha_ingreso` **no nula**
* `hospital_origen` **no nulo**
* `fecha_egreso` **no nula**

Esto ya define:
*“alguien ingresó a algún hospital en algún momento”*

---

#### Variables NO obligatorias para validar

* `motivo_egreso` → puede faltar o ser ruidoso
* `edad`, `sexo`, etc. → útiles pero no estructurales

---

### 2. Criterios de eliminación (nivel fila)

En esta etapa se busca ser **minimalista pero firme**: eliminar solo lo que rompe completamente la semántica del episodio.

#### Eliminar filas si:

**(A) No hay identidad básica**

* `paciente_id` nulo
  no permite agrupar ni reconstruir trayectorias

---

**(B) No hay fecha de ingreso**

* `fecha_ingreso` nula
  no permite ordenar ni construir timeline

---

**(C) No hay hospital**

* `hospital_origen` nulo o vacío
  no permite ubicar el episodio en la red

---

**(D) Episodios imposibles (error lógico fuerte)**

* `fecha_ingreso > fecha_egreso`

inconsistencia temporal
eliminar o, como mínimo, flaggear críticamente

---

**(E) Registros administrativos explícitamente inválidos**

Si `motivo_egreso` contiene valores como:

* "anulado"
* "error"
* "carga errónea"
* "duplicado administrativo"

no representan internaciones reales

recomendación:

* preferible: crear flag `episodio_valido_admin = False`
* evitar borrar en esta etapa (decisión más segura)

---

**(F) No hay fecha de egreso**

* `fecha_egreso` nula
  inconsistencia estructural relevante

---

**(G) Duración implausible extremadamente corta**

* `fecha_egreso - fecha_ingreso < 5 minutos`
  probable error administrativo

---

### 3. Qué NO filtramos en esta etapa?

#### NO eliminar aún:

**Edad fuera de rango**

* edad < 0 o > 110

no invalida el episodio
puede corregirse más adelante

---

**Duraciones atípicas**

* 0 días
* muy largas

podría haber:

* truncamiento de datos
* internaciones crónicas

---

**Inconsistencias clínicas**

Ejemplo:

* `requiere_arm = sí` pero no pasó por terapia crítica

es ruido clínico, no invalida el episodio

---

**Duplicados**

no eliminar agresivamente todavía

pueden representar:

* múltiples cargas
* actualizaciones del mismo episodio

se resuelve en una etapa posterior

---
---
---

## BASE 2 — Traslados (Movimientos entre hospitales)

### 1. ¿Qué es un “traslado válido”?

> Un traslado válido es una transición entre dos episodios consecutivos del mismo paciente, en distintos hospitales, donde:

> * hay continuidad temporal razonable
> * el episodio origen indica traslado
> * y la identidad del paciente es consistente

---

## 2. Pipeline de diseño (orden IMPORTANTE)

 **NO HACEMOS shift directamente sobre datos sucios**

---

### Paso 0 — Preprocesamiento crítico (ANTES del shift)

#### (0.A) Manejo de duplicados

Problema:

```
A 12:30 13:00
A 12:30 13:00
B 14:00 20:00
```

Si no limpiamos esto:

* vas a generar pares falsos A→A
* o duplicar A→B

---

##### Definimos duplicado como:

Definimos duplicado como:

mismo:
* paciente_id
* hospital

y fechas muy cercanas (no necesariamente idénticas)

Tolerancia:
* |Δ ingreso| ≤ TOL_SEGUNDOS
* |Δ egreso| ≤ TOL_SEGUNDOS

```python
flag_duplicado_exacto = duplicated(...)
```

y luego para construir traslados quedarte con **una sola fila por duplicado exacto**

---

### Paso 1 — Ordenar

* por `paciente_id`, `fecha_ingreso`

---

### Paso 2 — Construcción de pares (shift)

Generar:

* hospital_destino
* fecha_ingreso_destino
* edad_destino
* etc.

---

### Paso 3 — Variables clave

* `delta_dias`
* `delta_edad = edad_destino - edad_origen`

---

### 3. Filtros CORE (más estrictos ahora)

#### (A) Cambio de hospital

* `hospital_origen_i ≠ hospital_origen_{i+1}`

Sin esto, no hay traslado inter-hospitalario

---

#### (B) Fechas necesarias

* `fecha_egreso_i` no nula
* `fecha_ingreso_{i+1}` no nula

Permiten construir continuidad temporal

---

#### (C) Motivo de egreso OBLIGATORIO

El episodio origen debe cumplir:

* `motivo_egreso ∈ {traslado-hospital-de-la-red}`

⚠️ importante:

* armarmamos una lista explícita en config.py

---

#### (D) Consistencia de edad

Regla:

| \Delta edad | \leq 2

Si no se cumple:

* excluimos traslado

---

#### (E) Regla temporal

* aceptamos: `-2 ≤ delta_dias ≤ 10`

Pero:

* `delta > 5` → flag fuerte

---

#### (F) Exclusión de inconsistencias fuertes

* `delta_dias < -5`
* `delta_dias > 30`

---

#### (G) Identidad

* `paciente_id` no nulo

---

### 4. Edge cases importantes

#### Caso duplicado + traslado

```
A
A (duplicado)
B
```

Después del dedup:

```
A → B
```

✔ correcto

---

#### Caso con edad inconsistente

```
edad A = 30
edad B = 45
```

eliminar traslado

probablemente error de paciente

---

#### Caso con buen motivo pero gap grande

```
motivo = traslado
delta = 8 días
```

MANTENER pero:

* `flag_gap_largo = 1`

---

#### Caso sin motivo pero con estructura perfecta

POR AHORA se elimina

---

## 6. Flags 

Agregar especialmente:

* `flag_edad_inconsistente`
* `flag_motivo_valido`
* `flag_duplicado_origen`
* `flag_duplicado_destino`

---

## 7. Resumen del pipeline final

1. **deduplicar técnico (exactos)**
2. ordenar
3. shift por paciente
4. construir pares
5. calcular:

   * delta_dias
   * delta_edad
6. aplicar filtros:

   * hospital distinto
   * fechas válidas
   * motivo traslado obligatorio
   * |delta_edad| ≤ 2
   * ventana temporal
7. generar flags
8. construir `df_traslados`

---

Construir **dos versiones**:

* `df_traslados_strict` → con motivo
* `df_traslados_loose` → sin motivo

y comparar

----------------
-----------------------
-----------------








## BASE 3 - `df_pacientes_trayectorias`

### 1. Definición

Una trayectoria es:

> la secuencia temporal de internaciones de un paciente, representando su recorrido por la red hospitalaria.

Puede ser:

* **trivial**: un solo hospital
* **conectada**: múltiples hospitales (vía traslados)

---

### 2. Unidad de análisis

* 1 fila = 1 paciente
* cada paciente tiene una única trayectoria

---

### 3. Criterios de inclusión (estrictos)

Se incluye un paciente si cumple:

#### Identidad consistente

* `paciente_id` válido
* edades consistentes entre episodios:

```
|Δedad| ≤ 2
```

* si no se cumple → **se elimina el paciente**

---

#### Fechas completas

* todos los episodios tienen:

  * `fecha_ingreso`
  * `fecha_egreso`

* si falta egreso → **se elimina**

---

#### Consistencia temporal mínima

Se permite pequeño error administrativo:

```
fecha_ingreso ≤ fecha_egreso + tolerancia (minutos)
```

---

#### Egreso no administrativo

* se excluyen pacientes cuyo recorrido termina en:

  * anulado / error / duplicado

---

## 4. Construcción de trayectorias

#### Principio

Las trayectorias se construyen desde `df_traslados` (no directamente desde episodios)

---

#### Casos

**A. Trayectorias conectadas**

* pacientes con traslados
* reconstrucción del path:

```
hospital A → hospital B → hospital C
```

---

**B. Trayectorias triviales**

* pacientes sin traslados
* un solo hospital

---

## 5. Representación

Para cada paciente:

#### Trayectoria hospitalaria

* secuencia ordenada de hospitales

---

#### Vínculo a episodios

* cada paso mantiene referencia a `df_base_limpia`

permite auditar y recuperar datos

---

#### Trayectorias derivadas

* estados (ej: `tipo_egreso`)
* complejidad (mapa hospital → nivel)

---

## 6. Lógica temporal

Se reutiliza la de `df_traslados`:

* gaps
* overlaps
* cambios de hospital

no se recalculan desde cero

---

## 7. Desenlace

Se define a nivel trayectoria:

### Regla principal

* si existe muerte → desenlace = muerte (primera ocurrencia)

---

#### Caso sin muerte

* usar la **trayectoria completa**, no solo el último episodio

---

#### Caso ambiguo

* `desenlace = desconocido`

---

## 8. Flags

No se eliminan más pacientes, solo se marcan:

* `flag_overlap_episodios`
* `flag_gap_extremo`
* `flag_eventos_post_muerte`
* `flag_multiples_muertes`
* `flag_no_conectado`

---

#### Estructura final

#### Identificación

* `paciente_id`

---

#### Métricas

* `n_episodios`
* `n_hospitales_unicos`
* `duracion_total`

---

#### Trayectoria

* `hospital_inicio`
* `hospital_final`
* `trayectoria_hospitalaria`
* `trayectoria_estados`
* `trayectoria_complejidad`

---

#### Desenlace

* `desenlace`
* `fecha_desenlace`

---

#### Calidad

* flags

#### Idea clave del diseño

* las trayectorias se construyen desde **movimientos reales (traslados)**
* los filtros fuertes se aplican solo para asegurar identidad
* todo lo demás se **marca, no se elimina**
* se mantiene trazabilidad con las bases anteriores
