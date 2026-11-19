# Pruebas funcionales — `pruebas/test_criterios.py`

Documentación de las pruebas que verifican los criterios de aceptación
**sin cámara, sin pantalla y sin GPU**. Este documento describe qué comprueba
cada función, con qué datos sintéticos y qué resultado se obtuvo en la última
ejecución.

> **Nota de alcance.** Estas pruebas validan la lógica de medición, las reglas
> de negocio, el feedback y el ciclo de sesión. **No** sustituyen las pruebas
> con cámara (CA-01, CA-09, CA-13, CA-14, CA-15), que se describen en la §7.
> Sirven como evidencia de CP-16 / RNF-07: todo el núcleo se ejecuta sin
> `cv2` ni `tkinter`.

---

## 1. Cómo ejecutar

```bat
:: desde la raíz del repositorio, con el Python del venv
.\venv\Scripts\python -m pruebas.test_criterios
```

* No requiere cámara ni marcador ArUco impreso.
* El script devuelve código de salida `0` si todas las comprobaciones pasan y
  `1` si alguna falla (útil para automatizar en el futuro).
* En Windows conviene ejecutarlo desde `cmd` o desde PowerShell sin activar
  nada más: el intérprete global no tiene `cv2`, pero estas pruebas tampoco lo
  necesitan; aun así se usa el venv por consistencia con el resto del proyecto.

Salida esperada al final:

```
=== Resultado ===
Todas las pruebas pasaron.
```

---

## 2. Estructura del script

| Elemento | Función |
|----------|---------|
| `comprobar(nombre, condicion, detalle)` | Registra un `PASS`/`FALLA`, imprime el detalle y acumula los fallos. |
| `senal_compresiones(...)` | Genera la señal vertical de las muñecas (en cm o px). |
| `landmarks_sinteticos(...)` | Construye un mapa de 8 landmarks plausible. |
| `ejecutar_sesion_sintetica(...)` | Simula 30 s a 60 fps y devuelve las métricas finales. |
| `prueba_*()` | Una función por criterio; cada una imprime sus propias líneas. |
| `main()` | Ejecuta las 13 funciones en orden y resume el resultado. |

Una **comprobación** es una línea `[PASS]`/`[FALLA]`. En la última ejecución se
ejecutaron **13 funciones** con **45 comprobaciones**, todas en `PASS`.

El script **no** usa `pytest` ni `unittest` a propósito: así se puede ejecutar
con un solo comando y sin dependencias extra en el equipo de la sustentación.

---

## 3. Modelo sintético de entrada

Las pruebas que necesitan una sesión completa no usan la cámara: generan
landmarks con geometría conocida. Eso permite comparar contra una verdad
absoluta (cpm y profundidad reales) y medir el error del algoritmo.

### 3.1 `senal_compresiones(t, cpm, amplitud_cm)`

```python
amplitud_cm / 2 * (1 - cos(2 * pi * cpm / 60 * t))
```

* Es un coseno elevado: un ciclo completo por compresión.
* Va de `0` a `amplitud_cm`, por lo que la **amplitud pico a pico** es
  exactamente `amplitud_cm`. Esa es la magnitud que el sistema debe estimar
  como profundidad.
* La frecuencia real es exactamente `cpm`: sirve de referencia para CP-11.

### 3.2 `landmarks_sinteticos(compresion_px, angulo_brazos, separacion_munecas_px, inclinacion_postural_px)`

* Lienzo de 640 px de ancho; hombros separados 90 px a cada lado del centro.
* `compresion_px` hunde hombros, codos y muñecas **la misma cantidad**. Es
  deliberado: con brazos rígidos las muñecas acompañan a los hombros, que es
  justo lo que mide el sistema (`desplazamiento vertical de muñecas`).
* `separacion_munecas_px` controla la distancia entre muñecas (CA-05).
* `inclinacion_postural_px` simula una deriva global del tronco, sin cambiar la
  amplitud de la compresión; se usa para CA-06.
* `angulo_brazos` coloca los codos; `180°` deja el brazo completamente recto.

> **Trampa conocida:** si en el modelo se movieran las muñecas más que los
> hombros, la profundidad medida quedaría inflada y CP-12 pasaría por la razón
> equivocada. Por eso ambos se desplazan igual.

### 3.3 `ejecutar_sesion_sintetica(...)`

Simula `DURACION_S = 30 s` a `FPS_SIMULADO = 60 fps` (1800 fotogramas) y
devuelve el objeto `Metricas` final.

| Parámetro | Valor por defecto | Uso |
|-----------|-------------------|-----|
| `cpm_real` | — | Frecuencia de referencia (CP-11). |
| `amplitud_cm` | — | Profundidad pico a pico real (CP-12). |
| `angulo` | `170.0` | Ángulo de brazos. |
| `separacion_munecas_px` | `30.0` | Separación de muñecas (CA-05). |
| `px_por_cm` | `20.0` | Escala simulada. |
| `colapso_postural_cm` | `0.0` | Deriva de hombros que aparece a los 10 s y se completa en 5 s (CA-06). |

La escala se introduce como si el ArUco estuviera en el encuadre:

```python
lado_aruco_px = tamano_marcador_cm * px_por_cm   # 5,0 cm * 20 px/cm = 100 px
centro_aruco  = (320.0, 220.0)
```

Con `px_por_cm = 20`, 30 px de separación de muñecas equivalen a 1,5 cm y
400 px a 20 cm. El analizador calcula la escala a partir del lado del ArUco
(100 px / 5 cm = 20 px/cm), no la recibe directamente.

---

## 4. Resumen de la última ejecución

| # | Función | Criterio | Comprobaciones | Resultado |
|---|---------|----------|----------------|-----------|
| 1 | `prueba_ca02_indices` | CA-02 / RF-02 | 2 | PASS |
| 2 | `prueba_ca03_cpm` | CA-03 / RF-03 / RN-01 | 3 | PASS |
| 3 | `prueba_ca04_clasificacion_profundidad` | CA-04 / RF-04 / RN-02 | 3 | PASS |
| 4 | `prueba_cp11_precision_frecuencia` | CP-11 / RNF-02 | 3 | PASS |
| 5 | `prueba_cp12_precision_profundidad` | CP-12 / RNF-03 | 3 | PASS |
| 6 | `prueba_ca05_posicion_manos` | CA-05 / RF-05 / RN-03 | 2 | PASS |
| 7 | `prueba_ca06_retorno_toracico` | CA-06 / RF-06 / RN-04 | 2 | PASS |
| 8 | `prueba_ca07_angulo_brazos` | CA-07 / RF-07 / RN-05 | 4 | PASS |
| 9 | `prueba_ca08_feedback` | CA-08 / RF-08 / RN-06 | 3 | PASS |
| 10 | `prueba_cp10_tiempo_proceso` | CP-10 / RNF-01 / CA-10 | 1 | PASS |
| 11 | `prueba_sesion_registro_errores` | CA-05/06/07, RF-09 | 5 | PASS |
| 12 | `prueba_cuenta_atras` | RNF-04 / CA-09 | 11 | PASS |
| 13 | `prueba_configuracion_cuenta_atras` | RNF-04 | 3 | PASS |

---

## 5. Detalle por prueba

### 5.1 `prueba_ca02_indices` — landmarks requeridos

**Criterio:** CA-02 / RF-02. El sistema debe detectar y superponer hombros
(11, 12), codos (13, 14), muñecas (15, 16) y caderas (23, 24).

**Qué verifica**

1. `set(INDICES_REQUERIDOS) == {11, 12, 13, 14, 15, 16, 23, 24}`: el contrato
   de índices coincide exactamente con el exigido. Un índice de más también
   haría fallar la prueba.
2. Tras una sesión sintética, `metricas.pose_detectada` es `True`: el
   analizador considera válida una postura con esos ocho puntos.

**Resultado medido**

```
[PASS] CA-02 indices 11,12,13,14,15,16,23,24 -> (11, 12, 13, 14, 15, 16, 23, 24)
[PASS] CA-02 postura detectada
```

**Límite:** no comprueba que MediaPipe detecte esos puntos en una persona
real; eso requiere cámara y el modelo `.task` (ver §7).

---

### 5.2 `prueba_ca03_cpm` — clasificación de frecuencia

**Criterio:** CA-03 / RF-03 / RN-01. Menos de 100 cpm es baja, entre 100 y 120
es correcta, más de 120 es alta.

**Qué verifica.** Construye `Metricas` con la cpm fija y evalúa solo la regla
`RN-01`, comprobando que el mensaje contenga la palabra clave esperada.

| cpm | Palabra esperada | Umbral en `configuracion.py` |
|-----|------------------|------------------------------|
| 80 | `Aumente` | `cpm_minimo = 100` |
| 110 | `correcto` | dentro de `[100, 120]` |
| 140 | `Reduzca` | `cpm_maximo = 120` |

**Resultado medido**

```
[PASS] CA-03 clasificacion 80 cpm -> Aumente la frecuencia (80 cpm)
[PASS] CA-03 clasificacion 110 cpm -> Ritmo correcto (110 cpm)
[PASS] CA-03 clasificacion 140 cpm -> Reduzca la frecuencia (140 cpm)
```

**Nota:** 100 y 120 exactos se consideran correctos (la comparación es
estricta: `< 100` y `> 120`).

---

### 5.3 `prueba_ca04_clasificacion_profundidad` — clasificación de profundidad

**Criterio:** CA-04 / RF-04 / RN-02. Menos de 5 cm es insuficiente, entre 5 y
6 cm es correcta, más de 6 cm es excesiva.

**Qué verifica.** Evalúa `RN-02` con profundidades fijas y busca la palabra
clave en el mensaje.

| Profundidad | Palabra esperada |
|-------------|------------------|
| 3,5 cm | `más hondo` |
| 5,5 cm | `correcta` |
| 8,0 cm | `menos hondo` |

**Resultado medido**

```
[PASS] CA-04 clasificacion 3.5 cm -> Presione más hondo (3.5 cm)
[PASS] CA-04 clasificacion 5.5 cm -> Profundidad correcta (5.5 cm)
[PASS] CA-04 clasificacion 8.0 cm -> Presione menos hondo (8.0 cm)
```

---

### 5.4 `prueba_cp11_precision_frecuencia` — error de frecuencia

**Criterio:** CP-11 / RNF-02. Con una referencia conocida, el error absoluto
debe ser ≤ 6 cpm (±5 %).

**Qué verifica.** Para 100, 110 y 120 cpm ejecuta una sesión sintética de 30 s
con profundidad de 5,5 cm y compara las cpm medidas contra las reales.

| Referencia | Medido | Error | Límite |
|------------|--------|-------|--------|
| 100 cpm | 100,0 | 0,00 cpm | 6 cpm |
| 110 cpm | 110,4 | 0,40 cpm | 6 cpm |
| 120 cpm | 120,0 | 0,00 cpm | 6 cpm |

El límite sale de `Configuracion.error_maximo_cpm`.

**Resultado medido**

```
[PASS] CP-11 frecuencia 100 cpm (medido 100.0) -> error 0.00 cpm (limite 6)
[PASS] CP-11 frecuencia 110 cpm (medido 110.4) -> error 0.40 cpm (limite 6)
[PASS] CP-11 frecuencia 120 cpm (medido 120.0) -> error 0.00 cpm (limite 6)
```

**Interpretación:** el error de 0,40 cpm en 110 se debe al redondeo del
instante de cada valle al fotograma más cercano (60 fps → 16,7 ms). Es unas
15 veces menor que el límite exigido.

**Límite:** la señal sintética no tiene ruido, ni fotogramas perdidos, ni
movimiento de cámara. Esta prueba valida el **algoritmo**, no la robustez
frente a una cámara real.

---

### 5.5 `prueba_cp12_precision_profundidad` — error de profundidad

**Criterio:** CP-12 / RNF-03. Error absoluto menor que ±0,5 cm contra una
profundidad conocida entre 5 y 6 cm.

**Qué verifica.** Con 110 cpm constantes, simula profundidades de 5,0, 5,5 y
6,0 cm con escala de 20 px/cm y compara contra el valor real.

| Real | Medido | Error |
|------|--------|-------|
| 5,0 cm | 4,93 cm | 0,07 cm |
| 5,5 cm | 5,42 cm | 0,08 cm |
| 6,0 cm | 5,92 cm | 0,08 cm |

El límite sale de `Configuracion.error_maximo_profundidad_cm = 0.5`.

**Resultado medido**

```
[PASS] CP-12 profundidad 5.0 cm (medido 4.93) -> error 0.07 cm
[PASS] CP-12 profundidad 5.5 cm (medido 5.42) -> error 0.08 cm
[PASS] CP-12 profundidad 6.0 cm (medido 5.92) -> error 0.08 cm
```

**Interpretación:** hay una subestimación sistemática de 0,07–0,08 cm. Es
consistente con el suavizado de la señal (`muestras_suavizado = 3`), que
recorta ligeramente los extremos del ciclo. Está muy por debajo de la
tolerancia.

---

### 5.6 `prueba_ca05_posicion_manos` — manos sobre el esternón

**Criterio:** CA-05 / RF-05 / RN-03. Manos juntas y centradas sobre el tórax.

**Qué verifica.** Dos sesiones sintéticas completas:

| Caso | Separación | Medida | `esternon_ok` |
|------|-----------|--------|----------------|
| Manos juntas y centradas | 30 px | 1,5 cm | `True` |
| Manos separadas | 400 px | 20,0 cm | `False` |

El umbral es `distancia_maxima_munecas_cm = 12.0`; además, el punto medio de
las muñecas debe caer dentro del 35 % del ancho de hombros respecto del ArUco
(`tolerancia_desalineacion_esternon = 0.35`).

**Resultado medido**

```
[PASS] CA-05 manos juntas y centradas -> separacion 1.5 cm
[PASS] CA-05 manos separadas detectadas -> separacion 20.0 cm
```

**Límite:** el caso "manos juntas pero descentradas" no está cubierto por una
aserción propia; lo cubre indirectamente la lógica de `esternon_ok`, pero no
se prueba con un desplazamiento lateral explícito.

---

### 5.7 `prueba_ca06_retorno_toracico` — retorno completo

**Criterio:** CA-06 / RF-06 / RN-04. Los hombros deben recuperar la altura
entre compresiones.

**Qué verifica**

1. **Retorno completo:** `Metricas` con `desvio_hombros_cm = 0.4` y
   `retorno_ok = True`. La regla `RN-04` debe cumplirse y responder
   "Retorno torácico completo".
2. **Retorno insuficiente:** sesión sintética con `colapso_postural_cm = 4.0`.
   La deriva empieza en el segundo 10 y se completa hacia el segundo 15. Como
   4 cm supera la tolerancia de 2 cm, la regla debe incumplirse.

**Resultado medido**

```
[PASS] CA-06 retorno completo aceptado -> Retorno torácico completo
[PASS] CA-06 retorno insuficiente detectado -> Retorno torácico incompleto: los hombros no recuperan la altura
```

**Nota:** la prueba no comprueba el valor exacto del desvío, solo el veredicto
de la regla. El umbral vive en `tolerancia_retorno_cm = 2.0`.

---

### 5.8 `prueba_ca07_angulo_brazos` — rectitud de brazos

**Criterio:** CA-07 / RF-07 / RN-05. El ángulo hombro-codo-muñeca debe ser
≥ 150°.

**Qué verifica**

1. `angulo_abc` con tres puntos colineales devuelve 180,00°.
2. `angulo_abc` con un codo en ángulo recto devuelve 90,00°.
3. Regla `RN-05` con 120° → mensaje que contiene "Estire".
4. Regla `RN-05` con 168° → `cumple == True`.

**Resultado medido**

```
[PASS] CA-07 angulo recto = 180 -> 180.00
[PASS] CA-07 angulo recto de brazo = 90 -> 90.00
[PASS] CA-07 detecta brazos flexionados -> Estire los brazos (120°)
[PASS] CA-07 acepta brazos extendidos -> Brazos extendidos
```

**Nota:** 168° se usa para el caso correcto y no 180° para reflejar que en una
persona real el brazo nunca queda perfectamente recto.

---

### 5.9 `prueba_ca08_feedback` — mensaje y color

**Criterio:** CA-08 / RF-08 / RN-06. Feedback con color (verde correcto,
rojo/amarillo desviación) y mensajes breves.

**Qué verifica**

1. **Todo correcto:** cpm 110, profundidad 5,5 cm, brazos 168°, manos juntas y
   centradas, retorno completo, desvío 0,2 cm → color `green`.
2. **Dos correcciones:** cpm 60 y profundidad 2,0 cm → el mensaje completo debe
   contener "frecuencia" y "hondo" a la vez.
3. **Color de desviación:** debe ser `red` u `orange`.

**Resultado medido**

```
[PASS] CA-08 feedback correcto en verde -> Hombros, codos, muñecas y caderas detectados (green)
[PASS] CA-08 feedback con dos correcciones -> Aumente la frecuencia (60 cpm) | Presione más hondo (2.0 cm) | Muestre el marcador ArUco para medir la posición | Sin escala de referencia | Sin datos de codos
[PASS] CA-08 color de desviacion -> orange
```

**Interpretación del mensaje largo:** además de las dos correcciones reales
(frecuencia y profundidad), se listan tres mensajes en estado *espera*
(`Muestre el marcador ArUco…`, `Sin escala de referencia`, `Sin datos de
codos`). No son errores: son prerequisitos que faltan porque el objeto
`Metricas` de esa comprobación no trae escala ni codos. El generador concatena
todo lo que no está en `ok` (`estado in (alerta, error, espera)`).

**Nota:** el color es `orange` porque la regla más grave resulta ser una
*alerta* (frecuencia y profundidad). En este caso `RN-04` no llega a evaluarse
como error: falta la escala (`desvio_hombros_cm is None`) y queda en *espera*.
El rojo se reserva para cuando el retorno torácico se detecta como incompleto.

---

### 5.10 `prueba_cp10_tiempo_proceso` — rendimiento por fotograma

**Criterio:** CP-10 / RNF-01 / CA-10. Análisis + reglas + feedback en menos de
100 ms por fotograma.

**Qué verifica.** Durante 600 fotogramas (10 s a 60 fps) cronometra con
`time.perf_counter()` el bloque completo:

```python
metricas = analizador.actualizar(...)
reglas   = motor.evaluar(metricas)
generador.generar(reglas)
```

y se queda con el **peor** fotograma, que es el caso crítico.

**Resultado medido**

```
[PASS] CP-10 tiempo de proceso < 100 ms -> peor fotograma 0.35 ms
```

*(En una ejecución posterior en el mismo equipo el peor fotograma fue 0,12 ms;
el valor cambia con la carga del sistema, por eso se reporta como rango.)*

El límite sale de `Configuracion.tiempo_maximo_proceso_ms = 100.0`.

**Muy importante — qué mide y qué no:**

* Mide solo la **capa de análisis** (matemática de señal, reglas y feedback).
* **No** incluye la inferencia de MediaPipe ni la captura de cámara, que son
  las que dominan el tiempo real.
* El valor absoluto varía entre equipos y ejecuciones (0,12–0,35 ms en el
  equipo de pruebas). Lo relevante es que el margen frente a 100 ms es de
  más de dos órdenes de magnitud, por lo que esta capa no es el cuello de
  botella.
* El rendimiento extremo a extremo se mide en la GUI y está limitado por la
  cámara del equipo de pruebas (≈ 12,4–12,7 fps), no por este código.

---

### 5.11 `prueba_sesion_registro_errores` — ciclo de sesión y errores

**Criterios:** CA-05, CA-06, CA-07 (registro con marca de tiempo) y RF-09
(resumen al finalizar).

**Qué verifica.** Crea una `Sesion`, la inicia, y le pasa métricas
deliberadamente malas en un solo fotograma: 50 cpm, 2,0 cm, brazos a 100°,
retorno incompleto con 5 cm de desvío.

| Comprobación | Condición | Resultado |
|--------------|-----------|-----------|
| Registro con marca de tiempo | ≥ 3 errores | 4 errores: `RN-04`, `RN-01`, `RN-02`, `RN-05` |
| Formato `HH:MM:SS.mmm` | 12 caracteres | `01:08:21.223` |
| Sin duplicados por enfriamiento | segunda llamada devuelve 0 | 0 nuevos |
| Duración del resumen | ≥ 29 s al finalizar 30 s después | 30,0 s |
| Resumen con errores | ≥ 3 errores en el resumen | 4 errores |

**Resultado medido**

```
[PASS] Registro de errores con marca de tiempo -> 4 errores: ['RN-04', 'RN-01', 'RN-02', 'RN-05']
[PASS] Marca de tiempo formato HH:MM:SS.mmm -> 01:08:21.223
[PASS] Sin errores duplicados por enfriamiento -> 0 nuevos
[PASS] Resumen de sesion con duracion -> 30.0 s
[PASS] Resumen con errores detectados -> 4 errores
```

**Interpretación:**

* El orden `RN-04, RN-01, RN-02, RN-05` refleja la prioridad por gravedad:
  el retorno incompleto es `error`, el resto son `alerta`.
* No aparece `RN-03` porque las métricas no traen `distancia_munecas_cm`
  (`None`), así que la regla queda en *espera* y no se registra.
* El enfriamiento (`enfriamiento_error_s = 1.0`) evita que el mismo error se
  repita en fotogramas consecutivos. Es la razón por la que la segunda llamada
  inmediata devuelve 0.

---

### 5.12 `prueba_cuenta_atras` — cuenta regresiva de posicionamiento

**Criterio:** RNF-04 / CA-09 (usabilidad). Antes de medir, el alumno tiene 5 s
para ubicarse frente a la cámara.

**Qué verifica.** El ciclo de vida completo de `CuentaAtras`, que es lógica
pura (sin Tkinter):

| Comprobación | Condición | Resultado |
|--------------|-----------|-----------|
| Inicia detenida | `terminada == True` | — |
| Arranca en 5 s | `iniciar() == 5` | 5 |
| En curso | `en_ejecucion and not terminada` | — |
| Recorrido 5→0 | `[4, 3, 2, 1, 0]` | `[4, 3, 2, 1, 0]` |
| Terminada en 0 | `terminada and restantes == 0` | — |
| Avanzar tras terminar | devuelve 0 | 0 |
| Reinicio | `iniciar() == 5` y en curso | — |
| Cancelación | `cancelar()` deja 0 y terminada | — |
| Desactivada arranca en 0 | `CuentaAtras(0).iniciar() == 0` | 0 |
| Desactivada termina ya | `terminada` | — |
| Duración por defecto | 5 s | 5 |

**Resultado medido**

```
[PASS] Cuenta atras inicia detenida
[PASS] Cuenta atras arranca en 5 s -> 5
[PASS] Cuenta atras en curso
[PASS] Cuenta atras 5->0 -> [4, 3, 2, 1, 0]
[PASS] Cuenta atras terminada en 0
[PASS] Avanzar tras terminar devuelve 0
[PASS] Reinicio de la cuenta atras
[PASS] Cancelacion inmediata
[PASS] Cuenta atras desactivada arranca en 0
[PASS] Cuenta atras desactivada termina ya
[PASS] Duracion por defecto de 5 s -> 5
```

**Por qué importa:** esta clase se puede probar sin abrir una ventana. Si la
lógica de la cuenta atrás viviera dentro de `interfaz.py`, habría que abrir
Tkinter y esperar 5 s reales para verificarla; así se comprueba en
milisegundos y sin pantalla (CP-16).

---

### 5.13 `prueba_configuracion_cuenta_atras` — umbral no hardcodeado

**Criterio:** RNF-04 y la regla del proyecto de que los parámetros viven en
`rcp/configuracion.py`.

**Qué verifica**

1. `config.cuenta_atras_s == 5`.
2. `config.mensaje_cuenta_atras` no está vacío.
3. `CuentaAtras(config.cuenta_atras_s).segundos_totales == 5`: la clase y la
   configuración están realmente enlazadas.

**Resultado medido**

```
[PASS] cuenta_atras_s = 5 -> 5
[PASS] mensaje de cuenta atras definido
[PASS] Cuenta atras enlazada con la configuracion
```

**Por qué importa:** garantiza que el valor vive en la configuración y que la
clase lo respeta. Si mañana se cambia la duración a 3 s, las comprobaciones 1
y 3 fallan **a propósito**: es la señal para actualizar la prueba y este
documento, de modo que el cambio quede consciente y trazado. Lo que estas
pruebas no pueden detectar por sí solas es que la interfaz llame a
`CuentaAtras(5)` con un literal; eso exige revisar `rcp/interfaz.py` o una
prueba de la GUI.

---

## 6. Trazabilidad criterio → prueba

| Criterio | Requisito | Regla | Función de prueba |
|----------|-----------|-------|-------------------|
| CA-02 | RF-02 | — | `prueba_ca02_indices` |
| CA-03 | RF-03 | RN-01 | `prueba_ca03_cpm` |
| CA-04 | RF-04 | RN-02 | `prueba_ca04_clasificacion_profundidad` |
| CA-05 | RF-05 | RN-03 | `prueba_ca05_posicion_manos` |
| CA-06 | RF-06 | RN-04 | `prueba_ca06_retorno_toracico` |
| CA-07 | RF-07 | RN-05 | `prueba_ca07_angulo_brazos` |
| CA-08 | RF-08 | RN-06 | `prueba_ca08_feedback` |
| CA-10 | RNF-01 | — | `prueba_cp10_tiempo_proceso` |
| CA-11 | RNF-02 | RN-01 | `prueba_cp11_precision_frecuencia` |
| CA-12 | RNF-03 | RN-02 | `prueba_cp12_precision_profundidad` |
| CA-09 (parcial) | RF-09 / RNF-04 | — | `prueba_cuenta_atras`, `prueba_configuracion_cuenta_atras`, `prueba_sesion_registro_errores` |
| CA-05/06/07 (registro) | RF-05, RF-06, RF-07, RF-09 | RN-03..05 | `prueba_sesion_registro_errores` |

---

## 7. Cobertura: lo que estas pruebas **no** cubren

Estas pruebas no pueden sustituir la validación con hardware. Quedan fuera:

| Criterio | Qué falta | Cómo se verifica |
|----------|-----------|------------------|
| CA-01 / RF-01 | Apertura de cámara < 3 s y video ≥ 15 fps | Manual: lanzar `ejecutar_rcp.bat` y leer los fps del panel. |
| CA-02 (real) | Que MediaPipe detecte los ocho landmarks en una persona | Manual, con cámara y el modelo descargado. |
| CA-09 / RF-09 (GUI) | Video, landmarks superpuestos, botones, resumen en pantalla | Manual: iniciar y finalizar una sesión. |
| CA-13 / RNF-04 | Prueba piloto sin capacitación | Con usuarios. |
| CA-14 / RNF-05 | Disponibilidad e inactividad < 5 % | Operación programada. |
| CA-15 / RNF-06 | Cámara USB 640×480 en CPU sin GPU | Equipo objetivo. |
| ArUco real | Escala con el marcador impreso | Manual, con `aruco_ID0.png` a 5,0 cm. |

**Sobre CA-16 / RNF-07:** estas pruebas sí aportan evidencia indirecta. El
hecho de que `rcp/analisis.py`, `rcp/reglas.py`, `rcp/retroalimentacion.py` y
`rcp/sesion.py` se importen y ejecuten sin `cv2` ni `tkinter` demuestra el
aislamiento que exige el criterio. Una prueba de importación explícita que
falle si aparece `cv2`/`tkinter` en esos módulos sería una mejora futura.

---

## 8. Limitaciones y advertencias

1. **Datos sintéticos ideales.** No hay ruido, oclusión, fotogramas perdidos
   ni movimiento de cámara. Un resultado `PASS` aquí es necesario pero no
   suficiente para afirmar precisión en condiciones reales.
2. **Tiempos de CPU variables.** CP-10 depende del equipo; el valor reportado
   (0,12–0,35 ms) no es una constante del proyecto. El criterio es el margen
   frente a 100 ms.
3. **Escala simulada.** `px_por_cm = 20` es una escala de laboratorio. En la
   aplicación real la escala sale del ArUco; sin marcador el sistema degrada a
   ~10 px/cm y avisa (no hay centímetros fiables).
4. **Ángulo de brazos.** El modelo coloca los codos con una geometría
   simplificada; la prueba de CA-07 usa `Metricas` con el ángulo ya calculado,
   no la geometría. La función `angulo_abc` sí se prueba por separado con
   valores exactos.
5. **Un solo fotograma para el registro de errores.** `prueba_sesion_registro_errores`
   evalúa un único conjunto de métricas; no simula una secuencia de errores que
   aparecen y desaparecen. El enfriamiento se prueba solo en el caso inmediato.
6. **`pruebas/` no se versiona.** Por decisión del proyecto, la carpeta de
   pruebas permanece sin seguimiento en Git, así que este documento tampoco se
   sube al repositorio. Es la referencia escrita que acompaña a
   `test_criterios.py` y se entrega junto con él.

---

## 9. Mantenimiento

* **Al agregar un criterio:** añade una función `prueba_caXX_...`, regístrala
  en la tupla `pruebas` de `main()` y documéntala aquí con su fila en la §4 y
  su sección en la §5.
* **Al cambiar un umbral:** el cambio va en `rcp/configuracion.py` y en
  `docs/04_parametros_aha.md`; actualiza la tabla de la prueba afectada.
* **Al cambiar un mensaje de la interfaz:** las pruebas buscan palabras clave
  (`Aumente`, `correcto`, `Reduzca`, `más hondo`, `correcta`, `menos hondo`,
  `Estire`). Si cambias la redacción, ajusta la prueba **y** el documento; no
  cambies la prueba para que pase sin cambiar el comportamiento.
* **Si una prueba falla:** corrige el código de producción, no la aserción.
  La única excepción es que el requisito haya cambiado de forma aprobada.
