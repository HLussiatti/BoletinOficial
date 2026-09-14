# Diseño de la interfaz local

## Dirección

La interfaz adopta el lenguaje de un expediente operativo: papel cálido, tinta
oscura, reglas finas y una línea dorada continua que conecta el estado con el flujo
documental y reaparece al desplegar un resumen conceptual. La composición privilegia lectura, comparación y
trazabilidad por encima de elementos decorativos.

## Jerarquía

La cabecera identifica la edición consultada y el resultado de la última ejecución.
Cuatro indicadores muestran el volumen registrado, la cantidad relevante, los
documentos descargados y las fechas con fallas. Los filtros forman una sola franja
antes de la lista documental. En el encabezado de resultados se agrupan la
exportación y la preparación manual del correo. Cada registro listo ofrece una
casilla y el botón genera el correo únicamente con la selección explícita.

Cada publicación presenta fecha y tipo, organismo e identificación, clasificación
con su fundamento y accesos al BORA o a los PDF locales. El resumen conceptual y la
descripción se despliegan cuando existen, manteniendo compacta la revisión inicial.

## Sistema visual

- Fondo marfil y paneles claros para sostener sesiones largas de lectura.
- Negro para estructura, grafito para información secundaria y dorado como único
  acento de orientación.
- Georgia en títulos documentales y Segoe UI en controles y datos operativos.
- Estados siempre expresados con texto y borde; el color sólo refuerza el sentido.
- Líneas horizontales continuas para conservar la relación entre columnas sin
  convertir cada registro en una tarjeta independiente.

## Adaptación y accesibilidad

En ventanas amplias, cada publicación usa una columna breve de selección y cuatro
columnas de contenido. Debajo de 1050 px se
transforma en una secuencia vertical y los enlaces se agrupan en una línea. Los
indicadores pasan de cuatro a dos columnas y, debajo de 360 px, a una. Todos los controles tienen
etiqueta, foco visible y HTML nativo compatible con teclado. No se usan animaciones
ni el color como única señal.

## Límites de seguridad

El servidor escucha sólo en `127.0.0.1`. Los documentos se entregan únicamente si
están registrados en SQLite, existen en disco y resuelven dentro de la carpeta de
datos configurada. Las respuestas deshabilitan caché, restringen contenido activo y
evitan que la interfaz sea embebida por otra página.
