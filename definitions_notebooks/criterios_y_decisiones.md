# Criterios para cada tabla

## BASE 1 — Episodios (Internaciones)

### Glosario de Nomenclatura Estricta
Para asegurar la consistencia y reproducibilidad en la limpieza de datos, aplicaremos las siguientes definiciones:
* **FLAG (Bandera)**: Una nueva columna booleana en el DataFrame (ej. `flag_edad_rara`) que marca una condición anómala o interesante, pero NO elimina la fila. Sirve para auditar y para tomar decisiones en notebooks posteriores.
* **MASK (Máscara)**: Una variable booleana temporal en Python (ej. `mask_fechas_validas`) que se usa en memoria para evaluar una condición, pero que no necesariamente se guarda como columna a menos que se convierta en un flag.
* **FILTRO (Filter)**: La acción destructiva/definitiva de aplicar una máscara para crear un nuevo DataFrame, dejando filas afuera (ej. `df_limpio = df[mask_core_valido]`). Solo se aplica para datos estructuralmente insalvables.

### Arquitectura ETL (Reglas de Pipeline)
Para asegurar que los notebooks funcionen en un entorno de salud riguroso, el código sigue tres reglas inquebrantables de ETL:
1. **Cero Pérdida de Datos (Preservación Total):** Todas las variables originales y renombradas en la carga inicial (`df_base`) se mantienen intactas a lo largo de todo el código. NO se omiten columnas.
2. **Sólo Adición:** Los `FLAGS` se calculan y se agregan a `df_base` antes de aplicar los filtros destructivos, asegurando que la base limpia los herede sin perder información.
3. **Separación de Responsabilidades:** El código de transformación de datos (Carga, Flags, Masks, Filtros y Exportación) se ejecuta de forma secuencial en los bloques iniciales. Cualquier tipo de "ruido visual" (exploración, gráficos EDA, chequeos) queda estrictamente confinado al final del script.

---

### Categoría 1: Integridad Estructural (Filtros Duros)
Lo mínimo para que exista un evento clínico. Aquí aplicamos **MÁSCARAS** que terminan en **FILTROS**, ya que si faltan estos datos, la fila es insalvable y no representa un evento analizable.

Un episodio debe tener (filtro duro para mantener la fila):
* `paciente_id` **no nulo**: Sin esto, no hay historia clínica ni trayectoria.
* `fecha_ingreso` **no nula**: Esencial para ordenar cronológicamente.
* `fecha_egreso` **no nula**: Inconsistencia estructural grave si falta en retrospectiva.
* `hospital_origen` **no nulo y no vacío**: No permite ubicar el episodio en la red.

---

### Categoría 2: Coherencia Lógica (Filtros Duros)
Relaciones que rompen la física o el tiempo de los eventos hospitalarios. Dado que impiden construir una línea de tiempo real, se aplican como máscaras para **FILTRAR**.

* **Inconsistencia temporal (`fecha_ingreso <= fecha_egreso`)**: Físicamente imposible que sea al revés. Filtramos directamente manteniendolo válido si es menor o igual.
* *Nota:* Como la base tiene precisión solo de días (sin hora/minuto), se considera válido (`<=`) si ambas fechas caen en el mismo día.

---

### Categoría 3: Calidad de Datos Clínicos (Flags Suaves)
Datos atípicos que pueden ser erróneos o representar casos especiales, pero no invalidan la existencia de la internación. Se marcan exclusivamente con **FLAGS**.

* **Edad fuera de rango (`flag_edad_rara`)**: `edad < 0` o `edad > 110`. Puede corregirse después.
* **Duraciones atípicas**:
  * Negativas (si surgieran por error horario, `flag_duracion_negativa`).
  * Extremadamente largas (`flag_duracion_larga`), por ejemplo > 60 días, que pueden implicar cronicidad o fallos en el registro del alta.

---

### Categoría 4: Validez Administrativa (Flags de Sistema)
Registros explícitamente anulados o erróneos a nivel de sistema. Aunque no representan internaciones reales clínicamente, se preservan en memoria con un **FLAG** para auditar o decidir su destino en pasos posteriores (Notebook 2).

* **Registros administrativos inválidos (`flag_egreso_admin_invalido`)**: 
  Si `motivo_egreso` contiene: "anulado", "error", "carga errónea", o "duplicado administrativo".

---
---
---

## BASE 2 - `df_pacientes_trayectorias`

### 1. Definición

Una trayectoria es:

> La historia clínica coherente de internaciones de un paciente, representando su recorrido por la red hospitalaria desde su primer ingreso hasta su evento clínico de cierre.

Puede ser:

* **trivial**: un solo hospital (ingreso y alta en el mismo lugar)
* **conectada**: múltiples hospitales (movimientos intermedios vía traslados)

---

### 2. Unidad de análisis

* 1 fila = 1 paciente
* cada paciente tiene una única trayectoria (sintetizada lógicamente)

---

### 3. Criterios de inclusión (estrictos a nivel paciente)

Se incluye un paciente si cumple:

#### Identidad consistente

* `paciente_id` válido
* edades consistentes entre episodios:

```text
|Δedad| ≤ 2
```

* si no se cumple → **se elimina el paciente** de la base limpia

---

#### Fechas y datos mínimos

* para procesarse, el paciente debe tener al menos una `fecha_ingreso`
* episodios anulados o marcados como error administrativo se excluyen de la construcción

---

## 4. Construcción de trayectorias (LA LÓGICA SÁNDWICH)

#### Principio

**Las trayectorias se construyen directamente desde `df_base_limpia` (episodios), NO desde los traslados.** Se impone un orden clínico sobre el orden puramente cronológico.

---

#### Metodología

Para cada paciente, se separan sus episodios y se estructuran así:

* **Pan superior (Inicio):** El `min(fecha_ingreso)`
* **Relleno (Intermedios):** Todos los episodios cuyo tipo de egreso sea "traslado". Se ordenan cronológicamente entre sí.
* **Pan inferior (Cierre):** El episodio cuyo tipo de egreso NO sea traslado (alta, defunción, etc.). Se fuerza al final de la cadena.

---

## 5. Representación

Para cada paciente:

#### Trayectoria hospitalaria

* secuencia ordenada y limpia de hospitales (ej: `['Hosp A', 'Hosp B']`)
* se eliminan los duplicados consecutivos (`Hosp A → Hosp A` pasa a ser `Hosp A`)

---

#### Vínculo a episodios

* la trayectoria genera el insumo directo para construir `df_traslados_derivados`
* garantiza consistencia 1:1 entre el análisis de red y la historia del paciente

---

## 6. Lógica temporal

La **jerarquía clínica** manda sobre los errores administrativos:

* si un alta se cargó horas antes de que se registrara en sistema la llegada del último traslado, el código fuerza el alta al final de la cadena de todos modos. 
* las fechas se usan solo para ordenar *dentro* de cada categoría (traslados con traslados, finales con finales).

---

## 7. Desenlace

Se define por el episodio que ocupa la posición de **cierre clínico** (el "pan inferior"):

### Regla principal

* el desenlace de la trayectoria es el `tipo_egreso` de ese evento final (ej: muerte, alta médica)

---

#### Casos conflictivos y ambiguos

* **múltiples eventos finales:** si el paciente tiene más de un episodio clasificado como no-traslado (ej: dos altas distintas), se prioriza el último cronológicamente.
* **puro traslado:** si absolutamente todos los registros del paciente son traslados (falta el evento de cierre), el desenlace se marca como `solo_traslados` (desconocido).

---

## 8. Flags de Calidad

No se eliminan pacientes con trayectorias ambiguas, solo se marcan para análisis:

* `flag_sin_evento_final`
* `flag_multiples_finales`

---

#### Estructura final

#### Identificación

* `paciente_id`

---

#### Métricas

* `n_episodios_totales`
* `n_hospitales_unicos`
* `duracion_total_dias`
* `fecha_ingreso_paciente`
* `fecha_egreso_paciente`

---

#### Trayectoria

* `hospital_inicio`
* `hospital_final`
* `trayectoria_hospitalaria` (String para fácil lectura)
* `lista_hospitales` (Array crudo para derivar traslados)

---

#### Desenlace

* `desenlace`

---

#### Calidad

* flags de evento final

---
---
---

## BASE 3 — Traslados (Movimientos entre hospitales)

### 1. ¿Qué es un “traslado válido”?

> Un traslado válido es una transición (paso intermedio) entre dos hospitales, **derivada directamente de la trayectoria clínica ya consolidada** de un paciente, donde:

> * la trayectoria base ya garantizó la continuidad temporal y lógica
> * el episodio origen fue clasificado estructuralmente como un "traslado" (relleno del sándwich)
> * y la identidad del paciente es consistente en toda la cadena

---

## 2. Pipeline de diseño (orden IMPORTANTE)

**Ya NO HACEMOS shift temporal sobre datos sucios ni construimos traslados aislados.** Todo nace de la trayectoria.

---

### Paso 0 — Preprocesamiento crítico (a nivel episodios)

#### (0.A) Manejo de duplicados y colapsos

Problema original:

```text
A 12:30 13:00
A 12:30 13:00
B 14:00 20:00
```

Solución actual:

Al construir la trayectoria, los hospitales repetidos de forma consecutiva se colapsan matemáticamente en un solo nodo (`if h != hospitales_limpios[-1]`).
* esto evita generar pares falsos A→A
* garantiza que solo existan saltos inter-hospitalarios reales (A→B)

---

### Paso 1 — Construcción del "Sándwich" (Base 3)

* se procesa `df_base_limpia` agrupando por `paciente_id`
* se genera la lista cronológica/lógica de hospitales del paciente (ver Base 3)

---

### Paso 2 — Derivación de pares (Explotar la lista)

Generar los registros de traslado iterando sobre la lista limpia de la trayectoria:

* si la trayectoria es `[A, B, C]`
* se generan exactamente dos filas de traslado: `A → B` y `B → C`
* se asignan: `hospital_origen`, `hospital_destino`, y `paso_trayectoria` (1er traslado, 2do, etc.)

---

### Paso 3 — Variables clave heredadas

* `delta_dias` (calculado comparando fechas del episodio origen vs destino)
* `delta_edad = edad_destino - edad_origen`

---

### 3. Filtros CORE (Garantizados por diseño)

#### (A) Cambio de hospital

* `hospital_origen_i ≠ hospital_origen_{i+1}`

Al colapsar la lista de la trayectoria, esta condición se cumple al 100% por diseño. Sin esto, no hay traslado inter-hospitalario.

---

#### (B) Fechas necesarias y (C) Motivo de egreso

El episodio origen debe cumplir:

* `motivo_egreso ∈ {traslado-hospital-de-la-red}`

⚠️ importante: esto ya no es un filtro posterior, es la regla fundamental que define qué episodios van en el "medio" de la trayectoria antes de generar el traslado.

---

#### (D) Consistencia de edad

Regla:

|Δedad| ≤ 2

Si no se cumple:

* se excluye al paciente en la fase de construcción de la trayectoria (`df_base_limpia`)

---

#### (E) Regla temporal y (F) Exclusión

Como forzamos el orden lógico (evento final va al final), las superposiciones se mitigan. 
Aún así, calculando el `delta_dias`:

* aceptamos: `-5 ≤ delta_dias ≤ 30` (inconsistencias mayores marcan error estructural)
* `delta_dias > 5` → MANTENER pero con flag fuerte

---

#### (G) Identidad

* `paciente_id` no nulo

---

### 4. Edge cases importantes

#### Caso duplicado + traslado

```text
A
A (duplicado temporal)
B
```

Después de la lógica sándwich:

```text
A → B
```

✔ correcto (colapsado automático)

---

#### Caso con edad inconsistente

```text
edad A = 30
edad B = 45
```

se filtra el paciente entero antes de armar la trayectoria

---

#### Caso con buen motivo pero gap grande

```text
motivo = traslado
delta = 8 días
```

MANTENER pero:

* `flag_gap_largo = 1`

---

## 6. Flags (A nivel de traslados)

Agregar especialmente:

* `flag_edad_inconsistente`
* `flag_gap_largo`
* `flag_salto_temporal_negativo` (cuando la fecha de destino es anterior, pero el orden lógico es válido)

---

## Resumen del pipeline para trayectorias y traslados

1. **limpiar base de episodios** (identidad, edades)
2. **construir trayectoria clínica** (Regla Sándwich - Base 3)
3. **explotar lista de hospitales** para crear pares Origen → Destino
4. **calcular variables del par** (delta_dias, edades)
5. **aplicar flags de calidad** sobre los pares generados
6. **construir `df_traslados_derivados`**