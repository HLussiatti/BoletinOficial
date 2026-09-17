# Boletín Oficial EPESF

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

El usuario principal es personal técnico o regulatorio de la Empresa Provincial
de la Energía de Santa Fe (EPESF). Revisa las publicaciones de la Primera Sección
del Boletín Oficial de la República Argentina (BORA) que podrían afectar a la
empresa y contrasta cada conclusión con su fuente oficial.

## Product Purpose

Aplicación local para detectar, clasificar y revisar esas publicaciones sin
ocultar el respaldo documental ni el estado de cada ejecución. Debe reducir el
volumen de lectura manual, hacer visibles los posibles impactos y ayudar a
preparar una comunicación revisada por una persona.

## Positioning

El flujo reúne en el mismo equipo la cobertura diaria, la clasificación de
impacto, los resúmenes conceptuales, los documentos oficiales y la selección
para correo. Las señales y los resúmenes ayudan a priorizar la revisión; no son
texto oficial ni sustituyen la decisión de EPESF. La aplicación prepara un
borrador, pero no envía correos automáticamente.

## Operating Context

- La tarea diaria comienza a las 05:30, consulta la fecha corriente y genera
  con Gemini los resúmenes pendientes de esa edición. La persona suele revisar
  el resultado después de ese proceso desde una PC de trabajo con Windows.
- La interfaz se abre en el navegador mediante un servicio local que escucha
  sólo en `127.0.0.1`. Los datos SQLite, PDF, documentos y credenciales
  permanecen en el equipo; no hay alojamiento público ni dependencia de Node.js
  para usar la aplicación.
- El histórico consolidado desde el 01/11/2025 se consulta en la misma interfaz.
  Una edición sin publicaciones relevantes es un resultado válido y no genera
  un correo vacío.

## Tareas principales

- Confirmar si la edición diaria se procesó completa o presenta fallas.
- Consultar por día o período continuo, relevancia, tipo de publicación,
  organismo, número o texto; recorrer el histórico.
- Distinguir impacto directo, impacto potencial, pendientes de revisión y
  descartadas; leer primero el resumen conceptual y luego el motivo de
  clasificación.
- Abrir el aviso oficial, el PDF principal y sus anexos.
- Identificar errores de cobertura, documentos, resúmenes o entregas.
- Exportar la vista filtrada a CSV o seleccionar publicaciones para preparar
  un `.eml` en el cliente de correo predeterminado.

## Capabilities and Constraints

- La interfaz aprobada usa «Boletín Oficial EPESF», cinco indicadores
  (publicaciones, relevantes, impacto directo, impacto potencial y fechas con
  fallas), filtros por período/relevancia/tipo/texto, y vistas Día, Histórico
  y Fallas. No incluye el antiguo contador ni filtro «con documento»; los
  enlaces a documentos siguen disponibles en cada publicación.
- El período se elige desde un único control: el calendario permite marcar
  inicio y fin de manera continua, muestra dos meses en escritorio y uno en
  móvil, y conserva los accesos Hoy, Ayer, Últimos 7 días y Este mes. Sin
  JavaScript quedan campos de fecha nativos como respaldo.
- La columna Análisis prioriza el resumen sobre los indicios; el tipo de
  publicación no se repite en Fecha y sólo se muestra junto al título cuando
  éste no lo expresa. La densidad Cómoda/Compacta y la exportación CSV de la
  vista están sobre la lista, fuera de su cabecera.
- Los archivos se nombran `YYYY_MM_DD_Tipo_Número.pdf`; los anexos agregan
  `_Anexo_N`. Se preservan los caracteres españoles, incluida «Resolución».
- El texto por artículo y sus páginas se conserva como respaldo interno. La
  salida principal para la persona es un resumen conceptual, que debe
  contrastarse con la publicación oficial.
- Los avisos eléctricos particulares sin vínculo con EPESF o Santa Fe se
  descartan, aunque pueden descargarse inicialmente para evaluar su texto.
- El CSV no se genera durante la ejecución diaria. La exportación habitual
  incluye publicaciones seleccionadas o pendientes; incluir descartadas exige
  una acción explícita de control. El CSV de la interfaz exporta la vista
  filtrada o la selección, según la acción elegida.
- La aplicación genera un `.eml` sin remitente ni destinatarios. Una persona
  completa esos campos, revisa el borrador y decide si lo envía.
- El modelo inicial para los resúmenes es `gemini-3.5-flash-lite` mediante la
  Interactions API de Gemini, en su nivel gratuito y con salida JSON
  estructurada.

## Brand Commitments

El nombre visible aprobado es «Boletín Oficial EPESF». La interfaz y los
documentos de uso hablan en español y distinguen claramente la información
oficial de los análisis y estados del aplicativo. La dirección visual aprobada
se documenta por separado en `DESIGN.md`, con `estilo_web_v2.md` como referencia.

## Evidence on Hand

- Las validaciones reales del 11/09/2026 y 14/09/2026 comprobaron lectura,
  descarga, nomenclatura, clasificación, anexos, idempotencia, resúmenes
  revisados, correo de simulación, respaldo y restauración. La segunda
  validación confirmó un día sin novedades relevantes.
- El rediseño fue aprobado por el usuario tras revisar la web en 1920×1080 y
  1366×768, y luego el selector continuo inspirado en la captura adjunta de
  Despegar. El detalle de decisiones y verificaciones está en `CHANGELOG.md`.
- La última verificación de esta interfaz pasó 48 pruebas automatizadas. La
  comprobación visual y de interacciones usa datos sintéticos en
  `tests/preview_web_fixture.py` y `tests/capture_web_style.cjs`; no debe
  presentarse como validación de publicaciones oficiales.

## Product Principles

1. Priorizar lo que puede incidir en EPESF sin ocultar el conjunto ni la
   clasificación de los demás registros.
2. Mantener la fuente oficial y los documentos accesibles junto a cada
   resumen; la interpretación siempre requiere revisión humana.
3. Conservar el control local de datos, credenciales, exportaciones y envío
   de correos.
4. Hacer visible el estado operativo y permitir recuperar o investigar fallas.
5. Sostener la lectura y el filtrado en distintos tamaños de pantalla sin
   sacrificar información crítica.

## Accessibility & Inclusion

La interfaz debe funcionar con teclado, mostrar foco visible y expresar los
estados con texto además de color. El selector de período permite navegar días
con flechas y cerrar con Escape; los atajos generales no deben interferir con
la escritura. La disposición responde a pantallas de oficina y ventanas
angostas sin desborde horizontal ni dependencia de interacciones frágiles.
