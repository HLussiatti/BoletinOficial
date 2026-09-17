---
name: Boletín Oficial EPESF
description: Instrumento local de revisión normativa; grafito sobre blanco frío y azul institucional.
colors:
  paper: "oklch(.985 .003 250)"
  surface: "oklch(1 0 0)"
  surface-sunk: "oklch(.965 .006 250)"
  ink: "oklch(.26 .020 250)"
  ink-2: "oklch(.47 .018 250)"
  ink-3: "oklch(.53 .015 250)"
  line: "oklch(.915 .006 250)"
  line-strong: "oklch(.64 .010 250)"
  accent: "oklch(.50 .15 255)"
  accent-ink: "oklch(.40 .14 255)"
  accent-soft: "oklch(.955 .030 255)"
  slate: "oklch(.28 .030 255)"
  on-slate: "oklch(.97 .006 250)"
  sig-alta: "oklch(.48 .13 25)"
  sig-media: "oklch(.48 .10 75)"
  sig-ok: "oklch(.48 .11 150)"
  sig-info: "oklch(.48 .11 240)"
  sig-soft-a: "oklch(.95 .03 25)"
  sig-soft-m: "oklch(.95 .03 75)"
  sig-soft-ok: "oklch(.95 .03 150)"
  sig-soft-i: "oklch(.95 .03 240)"
typography:
  display:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: "1.3125rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-.01em"
  headline:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: ".9375rem"
    fontWeight: 600
    lineHeight: 1.2
  metric:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1
  title:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.35
  title-compact:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.35
  body:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: ".875rem"
    fontWeight: 400
    lineHeight: 1.55
  small:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: ".8125rem"
  label:
    fontFamily: '"Archivo","Segoe UI",system-ui,sans-serif'
    fontSize: ".75rem"
    fontWeight: 600
    letterSpacing: ".06em"
  code:
    fontFamily: '"Space Mono",Consolas,"Courier New",monospace'
    fontSize: ".75rem"
  date:
    fontFamily: '"Space Mono",Consolas,"Courier New",monospace'
    fontSize: ".8125rem"
rounded:
  r-sm: "3px"
  r-md: "6px"
  r-lg: "10px"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "24px"
  s6: "32px"
  s7: "48px"
  s8: "64px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.r-md}"
    padding: "0 12px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.accent-ink}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.r-md}"
    padding: "0 12px"
    height: "40px"
  button-selection:
    backgroundColor: "transparent"
    textColor: "{colors.on-slate}"
    rounded: "{rounded.r-md}"
    padding: "0 12px"
    height: "40px"
  input-search:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.r-md}"
    padding: "0 32px"
    height: "40px"
  period-control:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.r-md}"
    padding: "2px 8px"
    height: "40px"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.r-sm}"
    padding: "4px 8px"
  chip-active:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-ink}"
  badge-direct:
    backgroundColor: "{colors.sig-soft-a}"
    textColor: "{colors.sig-alta}"
    rounded: "{rounded.r-sm}"
    padding: "3px 8px"
  publication-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    padding: "16px 16px"
  publication-row-selected:
    backgroundColor: "{colors.accent-soft}"
  detail:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    padding: "16px"
  topbar:
    backgroundColor: "{colors.slate}"
    textColor: "{colors.on-slate}"
    padding: "0 clamp(16px,2vw,40px)"
    height: "76px"
  metric:
    backgroundColor: "{colors.surface-sunk}"
    textColor: "{colors.ink}"
    padding: "0 24px"
    height: "64px"
---

# Design System: Boletín Oficial EPESF

## Overview

**Creative North Star: "El instrumento de revisión diaria"**

Grafito sobre blanco frío: una interfaz sobria y precisa donde el trabajo normativo
manda. El azul institucional señala acciones, foco y selección; la sans mantiene
una sola voz y la mono distingue identificadores de la prosa. La densidad se
resuelve con alineación, jerarquía y cromado corto, no con texto diminuto.

Este merge conserva decisiones funcionales y accesibles del diseño anterior, pero
sustituye expresamente crema, terracota y serif por el mundo elegido en
`estilo_web_v2.md`. La guía fija la dirección; los valores realmente implementados
en `src/epe_boletin/web_ui.py` son la fuente de verdad del frontmatter.
`web_views.py` define componentes semánticos y el contrato está en
`.impeccable/surfaces/src-epe-boletin-web-ui-py.md`. `PRODUCT.md` conserva
el propósito y las reglas operativas; este archivo documenta la interfaz aprobada.
Las decisiones de composición de esta superficie no se generalizan a toda página.

**Key Characteristics:**

- Instrumento frío, legible y sin serif ni superficies cálidas.
- Una sans de interfaz, una mono de datos y ningún servidor externo de fuentes.
- Registros planos alineados; selección y fallas visibles también mediante texto.
- Cromado breve, controles nativos y estados recuperables.

## Colors

Neutros fríos de matiz azul leve, un acento institucional y señales semánticas
reservadas para impacto o ejecución. OKLCH se conserva tal como aparece en CSS;
no hay una tabla hexadecimal competidora.

### Primary

- **Azul institucional** (`accent`): enlaces, botón primario, foco y selección.
- **Azul de respuesta** (`accent-ink`): hover y texto sobre selección suave.
- **Azul de selección** (`accent-soft`): chips activos y registro seleccionado.

### Neutral

- **Blanco frío** (`paper`): página; **blanco de trabajo** (`surface`): filas y
  controles; **blanco hundido** (`surface-sunk`): métricas, encabezado y señales.
- **Grafito azul** (`ink`): texto principal; **grafito secundario** (`ink-2`): prosa
  auxiliar; **grafito de metadatos** (`ink-3`): códigos, labels y placeholders.
- **Regla fina** (`line`): divisores; **contorno legible** (`line-strong`): controles.
- **Pizarra azul** (`slate`) y **tinta sobre pizarra** (`on-slate`): topbar y barra
  de selección, no paneles oscuros repartidos por toda la interfaz.

`sig-alta`, `sig-media`, `sig-ok` y `sig-info`, con sus fondos suaves, son señales
semánticas, no acentos decorativos. La descartada usa texto explícito sobre neutro
para no confundirse con un enlace azul. Sobre pizarra los puntos de ejecución se
aclaran; sus valores de componente están en el sidecar.

`ink-3` y `line-strong` se oscurecieron respecto de la guía para sostener contraste
de texto (4.5:1) y contornos (3:1); también se ajustaron señales semánticas. `gold`
es alias CSS de compatibilidad con `accent`, no un segundo acento ni un primitivo.

**The One Accent Rule.** Sólo el azul institucional dirige la acción; los colores semánticos comunican un estado con una etiqueta textual, nunca por sí solos.

**The Full Ink Rule.** El texto está a opacidad plena; la jerarquía usa tintas explícitas. La atenuación temporal de la lista durante carga no es un color de texto.

## Typography

**Body Font:** Archivo con Segoe UI, system-ui y sans-serif locales.
**Label/Mono Font:** Space Mono con Consolas, Courier New y monospace locales.

No se descargan fuentes ni hay solicitudes a servidores tipográficos. Las familias
preferidas se usan si están disponibles; el fallback offline es una decisión
válida, no una incidencia pendiente. Sin serif ni otra familia para títulos.

### Hierarchy

- **Display:** título breve de topbar (700), sin protagonismo editorial.
- **Headline:** encabezados de calendario y fallas (600).
- **Metric:** número sans (700), etiqueta en la misma línea y cifras tabulares.
- **Title:** publicación (600), hasta dos líneas; compacta usa su rol menor y una línea.
- **Body:** texto de revisión (400), detalle limitado a (68ch). Preview de fila con
  interlineado (1.5) y hasta tres líneas en Cómoda, dos en Compacta; no sustituye
  el resumen expandido.
- **Label:** categoría y organismo en mayúsculas, explícitamente prescritos por v2;
  mínimo (12px), no los 11px del ejemplo de la guía.
- **Code / Date:** expedientes, fechas ISO y páginas mono; métricas, fechas, páginas
  y contadores mantienen cifras tabulares.

Mínimo observado (12px), cuerpo (14px). Compacta no reduce el cuerpo a 13px:
mantiene el tamaño y reduce líneas e indicios. Badges (12px), peso (600), sin
mayúsculas forzadas, interlineado (1.35).

**The Identifier Rule.** Los códigos identifican y la prosa explica: mono para datos, sans para títulos y lectura; nunca serif ni texto inferior a 12px.

## Layout

Contenedor fluido sin máximo de 1320px, con margen interno lateral
`clamp(16px,2vw,40px)`. Topbar y franja de métricas ocupan todo el ancho; el
contenido conserva márgenes de seguridad y el texto del análisis tiene medida
limitada. Ritmo base `s1`–`s8`; badges y bordes son ajustes de componente.

Topbar de altura mínima (76px), métricas (64px), controles principales (40px).
Entre filtros y tabla hay una barra de resultados: conteo a la izquierda;
densidad y exportación CSV a la derecha. La cabecera queda sólo para nombres de
columnas y selección. En 1366×768 la primera fila empieza alrededor de (380px)
y dos publicaciones completas permanecen visibles; en 1920×1080 no hay bandas
vacías laterales grandes.

Grilla de cinco columnas: selección (28px), fecha flexible entre (94–132px),
publicación `minmax(0,1.25fr)`, análisis `minmax(0,1.75fr)` y documentos
flexibles entre (158–220px), con gap horizontal (24px). Análisis gana espacio;
su resumen aparece antes que los indicios, ahora dentro del detalle. Cómoda
muestra hasta tres líneas y Compacta hasta dos. Padding vertical (16px)/(8px).

Tras desplazar (32px), métricas colapsadas y presets/chips ocultos en escritorio;
cromado sticky observado alrededor de (196px). El offset de filtros y cabecera
se calcula con los altos reales de topbar y filtros en scroll/resize.

Breakpoints: (1250px) presets en desplegable; (1150px) filtros en dos filas;
(1100px) publicación y análisis en dos columnas con documentos debajo;
(900px) métricas en grilla y filtros reordenados; (700px) filas de una columna y
barras sin sticky; (400px) período agrupado en vertical. En móvil el organismo
y los códigos envuelven, sin scroll horizontal de toda la página.

## Elevation & Depth

Plano por defecto: filas con reglas finas, sin sombras ni cebreado. Superficies
hundidas agrupan instrumentos. Las dos sombras CSS exactas viven en el sidecar:
topbar al desplazar, barra de selección y popover de presets. Trazos inset en
navegación, métricas y selección son estado, no elevación.

**The Flat Work Rule.** El registro permanece plano; sólo los instrumentos flotantes o pegajosos reciben sombra.

Movimiento funcional: estado y chevron (160ms, ease-out), entrada de selección
por transform, colapso de métricas por max-height. Carga con barra (2px), animación
(1s), sin skeleton. Movimiento reducido elimina animaciones, transiciones y scroll
suave. Max-height es una excepción explícita v2, no permiso para animar cualquier tamaño.

## Shapes

Controles discretos (`r-md`), chips/badges tensos (`r-sm`), filas rectas. Estado
superior pill (99px), punto circular (8px); no generalizar esa silueta a etiquetas.
`r-lg` existe en escala, no justifica tarjetas nuevas. Barra inferior redondeada
sólo arriba. Detalle con borde azul izquierdo (3px), requerido en §4.7 v2;
selección/novedad con marca inset (3px). Son excepciones intencionales, no defectos
canonizados ni ornamentación para cada contenedor.

## Components

### Buttons

Primario azul, secundario blanco con contorno legible, acciones de selección
transparentes sobre pizarra. Alto principal (40px), peso (600), padding horizontal `s3`.
Hover cambia azul/tinta; disabled conserva acción visible. Foco (2px), offset
(2px), nunca eliminado. Acciones de columna (32px); resumen (28px).

### Inputs / Fields

Nativos, blancos con `line-strong`; lupa SVG inline (14px), reserva lateral `s6`,
limpieza etiquetada. Labels reales ocultos y fieldset/legend recuperan espacio.
Desde/Hasta permanecen visibles dentro de un único control de período que abre
un calendario: dos meses en escritorio, uno en móvil, selección continua con
inicio/fin y confirmación explícita. Las fechas iguales equivalen a un solo día;
sin JavaScript quedan los dos campos nativos como respaldo. Relevancia y tipo de
publicación aplican al cambiar; búsqueda con Enter/Aplicar. Flechas de día sólo
en fecha única; presets
y chips removibles hacen visible el filtrado. Los tipos provienen de categorías
reales del período.

### Chips

Filtros (12px), borde fino, `r-sm`. Activo azul suave/tinta profunda/borde azul.
Indicios sobre neutro hundido, tres términos y `+N` con title; coincidencias en mark.
Un badge textual por registro: directo/potencial semánticos, descartada neutral.

### Navigation / Metrics

Día, Histórico y Fallas dentro de topbar, hover tonal y pestaña actual con inset
inferior (2px), `aria-current=page`. Estado en pill de una línea: fecha relativa,
absoluta en title; falla enlaza a vista accionable. Ayuda `?`, no otra banda.
Métricas en tira: publicaciones, relevantes, impacto directo, impacto potencial y
fechas con fallas. Relevantes suma directo y potencial; cada indicador positivo
enlaza a su filtro. Cero no clicable con aria-disabled. El antiguo indicador y
filtro de «con documento» desaparece; los enlaces de documentos permanecen en fila.

### Publication / Detail

ul/li/article, una idea por columna. Título oscuro abre details sin recarga ni
pérdida de scroll; hover azul/subrayado. Foco dentro del registro outline interno
(2px); selección fondo/marca; nueva marca informativa. Organismos/códigos abreviados
en fila con title completo; el tipo aparece junto al título sólo si éste no lo
expresa, y siempre se conserva en el detalle. La fecha ya no repite el tipo.
El expediente completo envuelve dentro del detalle.
Prosa limitada (68ch), atribución IA o revisión humana, organismo, motivo y fuente.
Documento ausente no elimina fila. PDF/anexos/BORA con SVG, páginas mono y destino
externo explícito; documentos adicionales en details.

### Contextual Selection

Barra pizarra sólo con selección, conteo accesible, correo, CSV y limpiar.
Densidad local en la barra de resultados; selección por fecha en sesión. CSV allí: vista completa;
barra: seleccionadas. Correo requiere un día y resumen completo; confirmación de
borrador y que no se envió nada. Si no abre, queda descargar/volver a abrir.

### Calendar / Issues / Feedback

Calendario siete columnas, navegación y selector directo mes/año; intensidad azul
por relevantes y borde rojo con texto de falla. Listas históricas paginadas (100),
CSV completo. Fallas con detalle/reintentos. Vacíos con causa/salida, sin ilustración
ni icono grande, explicación (52ch). Éxito role=status, error role=alert,
operaciones aria-busy. Pie local: datos y documentos permanecen en este equipo.
Atajos /, flechas, j/k, x, Enter, Esc y ? en una sola línea desplazable sólo
dentro de su franja en ventanas angostas; no interfieren con escritura.
El empaquetado offline y límites de servicio/origen/PDF siguen siendo restricciones
funcionales del producto, no tokens visuales ni motivos para exponer claves.

## Do's and Don'ts

### Do:

- **Do** usar tokens reales y fallback local sin red de fuentes.
- **Do** preservar etiquetas reales, texto de estado, foco visible y movimiento reducido.
- **Do** comprobar 1920×1080 sin bandas laterales grandes y 1366×768 con la primera fila visible; verificar además 1024, 700, 390 y 320px sin desborde horizontal.
- **Do** mantener referencias completas en title y wrapping dentro del detalle.
- **Do** dar causa y salida a vacíos y errores; conservar el borrador recuperable.

### Don't:

- **Don't** reintroducir crema, terracota, serif, negro puro o un segundo acento decorativo.
- **Don't** reducir texto por debajo de 12px ni usar opacidad para jerarquía tipográfica.
- **Don't** convertir métricas en tarjetas altas, agregar otra banda de título o cebrear registros.
- **Don't** confundir indicios o resumen IA con texto oficial o aprobación.
- **Don't** usar sombras en filas ni generalizar borde lateral o transición max-height.
- **Don't** prometer fuentes autohospedadas, modo oscuro o altos rígidos que no existen.
