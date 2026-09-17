# Registro de cambios

## 2026-09-17 · Cierre y depuración del repositorio

- Se conservaron el prototipo de 2025, el plan original y las validaciones en
  `historico/`, separados del código y de la documentación vigente.
- Se eliminaron del repositorio un log antiguo, una salida temporal y un archivo
  de ayuda generado durante la exploración.
- Se reunieron las pruebas y capturas locales en `var/pruebas/`, fuera de Git.
  Las pruebas automatizadas y sus muestras versionadas siguen en `tests/`.
- Se quitaron del equipo el entorno obsoleto `.env/`, paquetes y cachés generados,
  y una copia redundante de la clave. Se conservaron `.venv/` y `var/operacion/`.
- El inventario, las rutas actuales y los pasos de verificación se registraron
  en [MANTENIMIENTO.md](MANTENIMIENTO.md).

## 2026-09-17 · Rediseño de la web — aprobado

Se tomó `estilo_web_v2.md` como referencia visual. El usuario revisó capturas
de 1920×1080 y 1366×768, pidió ajustes de distribución y luego aprobó el
resultado, incluido el selector continuo de fechas.

| Área | Cambio realizado |
| --- | --- |
| Identidad visual | Se adoptaron la tipografía sin serif, el blanco frío, el grafito y el azul institucional de la referencia v2, conservando el carácter sobrio de la herramienta. |
| Ancho y adaptación | Se eliminó el ancho máximo que dejaba bandas laterales en pantallas grandes. El contenido usa márgenes fluidos y la tabla/filtros se reorganizan en ventanas medianas y angostas sin desborde horizontal. |
| Barra superior | Se amplió a una altura mínima de 76 px, se ajustó la tipografía y el título pasó a «Boletín Oficial EPESF». |
| Indicadores | La franja aumentó a 64 px, con más aire entre cifras y etiquetas. Muestra publicaciones, relevantes, impacto directo, impacto potencial y fechas con fallas; se retiró «con documento». |
| Filtros | Se mantuvieron relevancia y búsqueda, se incorporó tipo de publicación y se retiró el filtro «con documento». Los accesos Hoy, Ayer, Últimos 7 días y Este mes siguen disponibles. |
| Espaciado | Se separaron visualmente los filtros y la lista mediante una barra de resultados, sin volver a comprimir la pantalla. |
| Fecha | El período se elige desde un único control «Desde/Hasta». Abre un calendario de dos meses en escritorio o uno en móvil; dos clics marcan inicio y fin y resaltan el rango continuo. «Aplicar período» confirma la selección; «Borrar» reinicia la selección provisional. Un solo día sigue siendo válido. |
| Análisis y publicación | La columna Análisis ganó ancho y prioriza el resumen; los indicios pasan al detalle. Fecha ya no repite el tipo de documento; junto al título sólo aparece cuando éste no lo expresa. |
| Acciones de lista | Cómoda/Compacta y Exportar CSV pasaron de la cabecera de columnas a la barra de resultados. |
| Atajos | La ayuda se muestra en una sola línea; en ventanas estrechas se desplaza dentro de su franja. |

### Comportamiento y accesibilidad

- El filtro por tipo se aplica a las publicaciones y se conserva en los enlaces
  de navegación, exportación y preparación de correo. Las fechas iguales se
  tratan como un solo día.
- El calendario de período se puede recorrer con las flechas del teclado y
  cerrar con Escape sin cambiar el filtro. Conserva los campos nativos de fecha
  como alternativa cuando JavaScript no está disponible.
- Se mantienen el histórico, la vista de fallas, el acceso a PDF/anexos/aviso
  oficial, la selección y el borrador de correo. Quitar «con documento» no
  elimina los enlaces a documentos.
- Los controles y estados conservan etiquetas de texto, foco visible y
  comportamiento adaptable a pantallas angostas.

### Verificación

- 48 pruebas automatizadas aprobadas con `python -m unittest discover -s tests`.
- Comprobación de interacciones y capturas con datos **sintéticos** mediante
  `tests/preview_web_fixture.py` y `tests/capture_web_style.cjs`: 1920×1080,
  1366×768 y anchos intermedios y móviles hasta 320 px, sin desborde horizontal.
- Se verificaron selección continua, rangos entre meses, accesos rápidos,
  Escape, navegación con flechas, apertura en móvil, filtros, exportación,
  selección y densidad de filas.

La ficha de producto vigente está en `PRODUCT.md` y los detalles visuales y
componentes en `DESIGN.md`.
