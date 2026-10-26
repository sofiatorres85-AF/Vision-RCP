# Parámetros AHA (reglas RN-01 a RN-06)

Los umbrales derivan de las recomendaciones de la American Heart Association
(AHA) para la reanimación cardiopulmonar en adultos y están centralizados en
[`rcp/configuracion.py`](../rcp/configuracion.py), de modo que cambiar un valor
no requiere tocar la lógica.

## 1. Tabla de parámetros

| RN | Parámetro | Valor correcto | Clasificación | Campo en `Configuracion` |
|----|-----------|----------------|---------------|--------------------------|
| RN-01 | Frecuencia de compresiones | **100 a 120 cpm** | baja < 100 · alta > 120 | `cpm_minimo`, `cpm_maximo` |
| RN-02 | Profundidad de compresión | **5 a 6 cm** | insuficiente < 5 · excesiva > 6 | `profundidad_minima_cm`, `profundidad_maxima_cm` |
| RN-03 | Posición de las manos | centro del tórax (esternón) | manos separadas o desalineadas | `distancia_maxima_munecas_cm`, `tolerancia_desalineacion_esternon` |
| RN-04 | Retorno torácico completo | retorno total entre compresiones | desplazamiento residual de hombros | `tolerancia_retorno_cm` |
| RN-05 | Rectitud de brazos | brazos extendidos durante toda la compresión | brazos flexionados | `angulo_brazo_minimo` |
| RN-06 | Retroalimentación | feedback sin interrupciones > 2 s | demora excesiva | `tiempo_maximo_proceso_ms` |

## 2. Detalle por regla

### RN-01 — Frecuencia de compresiones

* **Objetivo AHA:** 100 a 120 compresiones por minuto.
* **Cálculo:** `cpm = 60 / promedio(últimos 5 intervalos entre valles de la señal)`.
* **Mensajes:** «Aumente la frecuencia (N cpm)» / «Ritmo correcto (N cpm)» /
  «Reduzca la frecuencia (N cpm)».
* **Tolerancia de precisión (RNF-02):** error absoluto ≤ 6 cpm frente a un
  metrónomo de referencia (±5 %).

### RN-02 — Profundidad de la compresión

* **Objetivo AHA:** 5 a 6 cm en adultos.
* **Cálculo:** amplitud `valle − punto_alto` de cada ciclo, promediada en las
  últimas 5 compresiones.
* **Escala:** `px_por_cm = lado_px_aruco / 5.0`, con el marcador impreso a 5,0 cm.
* **Mensajes:** «Presione más hondo (N cm)» / «Profundidad correcta (N cm)» /
  «Presione menos hondo (N cm)».
* **Tolerancia de precisión (RNF-03):** error absoluto < ±0,5 cm.

### RN-03 — Posición de las manos

* **Objetivo:** ambas manos superpuestas en el centro del esternón.
* **Se evalúa:**
  * separación entre muñecas ≤ `distancia_maxima_munecas_cm` = 12 cm;
  * desalineación del punto medio de las muñecas respecto de la referencia
    torácica (ArUco) ≤ `tolerancia_desalineacion_esternon` × ancho de hombros = 0,35.
* **Mensajes:** «Junte las manos (N cm de separación)» /
  «Centra las manos sobre el esternón».

### RN-04 — Retorno torácico completo

* **Objetivo AHA:** dejar que el tórax retorne por completo entre compresiones.
* **Cálculo:** desplazamiento vertical de la línea media de hombros respecto de
  su línea base; incumple si supera `tolerancia_retorno_cm` = 2 cm.
* **Mensaje:** «Retorno torácico incompleto: los hombros no recuperan la altura».
* **Estado:** `error` (mayor gravedad que las otras reglas).

### RN-05 — Rectitud de brazos

* **Objetivo AHA:** brazos extendidos, hombros directamente sobre las manos.
* **Cálculo:** ángulo hombro-codo-muñeca en ambos brazos; se toma el promedio.
  * incumple si < `angulo_brazo_minimo` = 150°.
* **Mensajes:** «Estire los brazos (N°)» / «Brazos extendidos».

### RN-06 — Retroalimentación

* **Objetivo:** feedback visual continuo, legible y sin demoras.
* **Umbrales de calidad:**
  * `tiempo_maximo_proceso_ms` = 100 ms por fotograma (RNF-01);
  * la actualización de la interfaz se programa con `after(1, ...)`, muy por
    debajo de los 2 s exigidos.
* **Colores (CA-08):** verde correcto, naranja/amarillo desviación leve, rojo
  desviación o incumplimiento.

## 3. Escalado físico con ArUco

| Parámetro | Valor | Dónde se configura |
|-----------|-------|--------------------|
| Diccionario | `DICT_4X4_50` | fijo en `rcp/procesamiento.py` |
| Identificador objetivo | 0 | `Configuracion.id_marcador_objetivo` |
| Tamaño real del lado | 5,0 cm | `Configuracion.tamano_marcador_cm` |
| Lado del PNG generado | 600 px | botón «Generar marcador ArUco» |

El botón **«Generar marcador ArUco»** de la interfaz produce `aruco_ID0.png`;
debe imprimirse a 5,0 cm de lado sin «ajustar a página», sobre papel blanco mate
y pegado plano en el pecho.

Sin marcador ArUco visible el sistema no puede escalar: informa «Muestre el
marcador ArUco para medir la posición» y usa una escala aproximada de 10 px/cm
únicamente para no detener la detección de la frecuencia.

## 4. Verificación de los umbrales

```
.\venv\Scripts\python -m pruebas.test_criterios
```

El conjunto de pruebas confirma la clasificación de RN-01 y RN-02, la precisión
exigida por RNF-02 y RNF-03, la detección de los errores de RN-03, RN-04 y
RN-05, y los tiempos de RNF-01.