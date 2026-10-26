# Historias de usuario

Formato: **Como** [rol] **quiero** [acción] **para** [valor].
Identificadores `HU-01` a `HU-07` referenciados por la matriz de trazabilidad de
[`01_requisitos.md`](01_requisitos.md).

---

## HU-01 — Iniciar sesión de entrenamiento

**Como** instructor de primeros auxilios **quiero** iniciar una sesión de
entrenamiento con un clic y que la cámara se active de inmediato **para** no
perder tiempo en la demostración.

**Dado que** el sistema está abierto **cuando** pulso «1. Iniciar sesión»
**entonces** la cámara se activa en menos de 3 segundos y el video aparece en la
ventana a un mínimo de 15 fps (CA-01).

**Excepción:** si no hay cámara conectada o está en uso por otra aplicación, el
sistema muestra un mensaje de error y **la sesión no inicia**.

---

## HU-02 — Ver video con los puntos del cuerpo

**Como** instructor **quiero** ver el video de la cámara con los puntos clave
superpuestos **para** saber que el alumno está siendo analizado correctamente.

**Dado que** la sesión está activa **cuando** el alumno aparece en el encuadre
**entonces** se dibujan y rotulan sobre el video los hombros (11, 12), los codos
(13, 14), las muñecas (15, 16) y las caderas (23, 24) (CA-02).

---

## HU-03 — Medir la frecuencia de compresiones

**Como** instructor **quiero** que el sistema mida las compresiones por minuto
**para** verificar que la cadencia esté entre 100 y 120 cpm.

**Dado que** hay una sesión en curso y se detecta la postura **cuando** el alumno
realiza compresiones **entonces** el valor de cpm se recalcula tras cada ciclo y
se clasifica como baja (< 100), correcta (100 a 120) o alta (> 120) (CA-03).

---

## HU-04 — Medir la profundidad de la compresión

**Como** instructor **quiero** que el sistema estime en centímetros la
profundidad **para** corregir compresiones demasiado superficiales o peligrosas.

**Dado que** el marcador ArUco está impreso a tamaño real (5,0 cm) y pegado en el
pecho **cuando** el alumno comprime **entonces** la profundidad se calcula a
partir del desplazamiento vertical de las muñecas y se clasifica como
insuficiente (< 5 cm), correcta (5 a 6 cm) o excesiva (> 6 cm) (CA-04).

---

## HU-05 — Detectar errores técnicos

**Como** instructor **quiero** que el sistema detecte los tres errores de técnica
más frecuentes **para** corregirlos durante la práctica, no al final.

**Dado que** la sesión está activa **cuando** ocurre alguna de estas situaciones
**entonces** se detecta y se registra con su marca de tiempo:

| Error | Regla | Umbral |
|-------|-------|--------|
| Manos fuera del centro del tórax | RN-03 | separación de muñecas > 12 cm o desalineación > 0,35 × ancho de hombros |
| Retorno torácico incompleto | RN-04 | hombros por debajo de la línea base más de 2 cm |
| Brazos flexionados | RN-05 | ángulo hombro-codo-muñeca < 150° |

---

## HU-06 — Recibir retroalimentación visual inmediata

**Como** instructor **quiero** un mensaje breve y coloreado en pantalla **para**
corregir al alumno en menos de dos segundos.

**Dado que** la sesión está activa **cuando** se actualiza un fotograma **entonces**
se muestran la frecuencia y la profundidad actuales, el color de estado
(**verde** correcto, **amarillo/naranja** desviación leve, **rojo** desviación) y
un mensaje de corrección, sin demoras superiores a 2 s (CA-08).

---

## HU-07 — Finalizar sesión y ver el resumen

**Como** instructor **quiero** finalizar la sesión en cualquier momento y recibir
un resumen **para** evaluar el desempeño del alumno.

**Dado que** hay una sesión en curso **cuando** pulso «2. Finalizar sesión»
**entonces** se detienen la captura y el análisis y aparece un resumen con la
duración, el número de compresiones, la frecuencia promedio, la profundidad
promedio y los errores detectados con su marca de tiempo (CA-09).

---

## Matriz de trazabilidad HU ↔ RF

| HU | RF / RNF asociados |
|----|--------------------|
| HU-01 | RF-01, RF-02, RNF-01, RNF-05, RNF-06, RNF-07 |
| HU-02 | RF-01, RF-02, RF-09, RNF-04, RNF-07 |
| HU-03 | RF-03, RNF-01, RNF-02, RNF-07 |
| HU-04 | RF-04, RNF-01, RNF-03, RNF-07 |
| HU-05 | RF-05, RF-06, RF-07, RNF-07 |
| HU-06 | RF-05, RF-06, RF-07, RF-08, RNF-01, RNF-04, RNF-07 |
| HU-07 | RF-09, RNF-04, RNF-05, RNF-07 |