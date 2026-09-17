# Guía de estilo y UX — Boletín EPESF

Documento de especificación para Codex. Aplica a la interfaz servida por `web.py`
(`render_page`) en el servidor local. Sin frameworks: HTML semántico + CSS plano.

Contexto: herramienta de uso interno intensivo diario. El usuario entra varias veces
por día a responder una sola pregunta —*¿qué se publicó hoy que afecta a la EPE?*— y a
armar un correo con lo relevante. Todo lo que no ayude a escanear, decidir y seleccionar
rápido es ruido.

**Cambio de dirección (rev. 2).** Se abandonan el fondo crema y el serif editorial. La
nueva base es *grafito sobre blanco frío*: superficies neutras casi blancas, tinta
azul-grafito y un único acento azul institucional. Lee como instrumento de trabajo, no
como pieza impresa, sostiene mejor la densidad de datos y se acerca al azul de la EPE
sin copiar su web.

Y se recorta el encabezado: en una pantalla de 14" el cromado superior ocupa ~610px de
700px útiles y la primera publicación queda fuera de vista. Objetivo: **≤ 230px hasta la
primera fila** (§2.1).

---

## 1. Fundaciones

### 1.1 Tipografía

Tres familias, con fallback local porque el servidor puede estar sin internet.
Autohospedar los `.woff2` en `static/fonts/` y declarar `@font-face` con
`font-display: swap`. Si no se pueden hospedar, los fallbacks son aceptables.

| Rol | Familia | Fallback |
|---|---|---|
| Interfaz, títulos y cuerpo | **Archivo** 400/500/600/700 | `"Segoe UI", system-ui, sans-serif` |
| Datos y códigos (expedientes, fechas ISO, contadores) | **Space Mono** 400/700 | `Consolas, "Courier New", monospace` |

Reglas:

- **Sin serif.** Una sola familia de interfaz para todo el texto; la jerarquía se hace
  con peso, tamaño y color, no con cambio de familia. El serif daba aire de documento
  impreso y hacía que "Resolución 611/2026" compitiera con el título de la página.
- Los códigos de expediente (`RESFC-2026-507-APN-DIRECTORIO#ENREGE`) y las fechas ISO
  van en mono, tamaño menor, color secundario. Son identificadores, no prosa.
- Cifras tabulares siempre: `font-variant-numeric: tabular-nums;` en métricas, fechas,
  páginas y contadores.
- Nada por debajo de 12px. Mínimo de cuerpo: 14px.

### 1.2 Escala tipográfica

```css
:root{
  --fs-display: 1.125rem; /* 18px  Archivo 700, ls -0.01em — título en la topbar */
  --fs-h2:      0.9375rem;/* 15px  Archivo 600 — encabezados de sección */
  --fs-metric:  1.375rem; /* 22px  Archivo 700, tabular */
  --fs-title:   1.0625rem;/* 17px  Archivo 600, line-height 1.35 */
  --fs-body:    0.875rem; /* 14px  Archivo 400, line-height 1.55 */
  --fs-small:   0.8125rem;/* 13px  Archivo 400 */
  --fs-code:    0.75rem;  /* 12px  Space Mono 400 */
  --fs-eyebrow: 0.6875rem;/* 11px  Archivo 600, uppercase, ls 0.09em */
}
```

En densidad compacta (§4.8) `--fs-title` baja a 1rem y `--fs-body` a 0.8125rem.

### 1.3 Color

Paleta en `oklch` para que los acentos compartan luminosidad y croma y solo varíen de
matiz. Se mantienen los nombres existentes (`--ink`, `--paper`, `--line`) y `--gold`
queda como alias de `--accent` para no romper el CSS actual.

Todos los neutros llevan un matiz frío (hue 250) con croma bajísimo: no son grises
muertos, pero tampoco tienen la calidez amarilla del crema.

```css
:root{
  /* superficies: tres niveles, todos fríos */
  --paper:        oklch(0.985 0.003 250);  /* fondo de página, blanco frío */
  --surface:      oklch(1    0     0);     /* tarjetas y filas, blanco puro */
  --surface-sunk: oklch(0.965 0.006 250);  /* métricas, encabezado de columnas, chips */

  /* tinta grafito azulada */
  --ink:          oklch(0.26 0.020 250);   /* texto principal */
  --ink-2:        oklch(0.47 0.018 250);   /* texto secundario, resúmenes */
  --ink-3:        oklch(0.60 0.015 250);   /* etiquetas, metadatos, placeholder */

  /* líneas */
  --line:         oklch(0.915 0.006 250);  /* divisores internos */
  --line-strong:  oklch(0.82  0.010 250);  /* bordes de contenedor, inputs */

  /* acento único: azul institucional */
  --accent:       oklch(0.50 0.15 255);    /* enlaces, foco, selección, botón primario */
  --accent-ink:   oklch(0.40 0.14 255);    /* hover y texto sobre fondo suave */
  --accent-soft:  oklch(0.955 0.030 255);  /* fondo de fila seleccionada, chip activo */

  /* superficie oscura: topbar y barra de selección */
  --slate:        oklch(0.28 0.030 255);
  --on-slate:     oklch(0.97 0.006 250);

  --gold: var(--accent);                   /* alias de compatibilidad */

  /* semánticos: mismo croma/lightness, distinto matiz */
  --sig-alta:     oklch(0.50 0.15 20);     /* impacto directo */
  --sig-media:    oklch(0.50 0.13 65);     /* impacto potencial */
  --sig-ok:       oklch(0.50 0.13 150);    /* ejecución completa */
  --sig-info:     oklch(0.50 0.10 235);    /* informativo / sin impacto */
  --sig-soft-a:   oklch(0.955 0.030 20);
  --sig-soft-m:   oklch(0.955 0.030 65);
  --sig-soft-ok:  oklch(0.955 0.030 150);
  --sig-soft-i:   oklch(0.955 0.025 235);
}
```

Reglas de color:

- **Máximo tres fondos claros** en la pantalla: `--paper` para la página, `--surface`
  para las filas, `--surface-sunk` para métricas y encabezado de columnas. `--slate`
  solo en la topbar y la barra de selección.
- El acento azul aparece en pocos lugares: enlaces, foco, botón primario, chip activo y
  la barra de 3px de la fila seleccionada. Nada de bloques grandes de color.
- El acento azul y `--sig-info` son cercanos: el azul informativo nunca se usa para
  badges de relevancia junto a enlaces en la misma columna. Si hace falta distinguirlos,
  `Informativa` va en `--ink-3` sobre `--surface-sunk`.
- Texto siempre a opacidad plena. Prohibido `opacity` o `color-mix` para atenuar texto:
  usar `--ink-2` / `--ink-3`, que están calculados para cumplir 4.5:1 sobre `--paper`.
- El color nunca es el único portador de significado: todo badge lleva texto.
- Negro puro (`#000`) fuera. El botón primario usa `--accent`; las superficies oscuras,
  `--slate`.
- `a` y `a:hover` definidos explícitamente (§4.9). Nunca azul por defecto del navegador.

### 1.4 Espaciado, radios, sombras

```css
:root{
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px;
  --s5: 24px; --s6: 32px; --s7: 48px; --s8: 64px;
  --r-sm: 3px; --r-md: 6px; --r-lg: 10px;
  --shadow-1: 0 1px 2px oklch(0.24 0.012 60 / 0.06);
  --shadow-2: 0 6px 20px oklch(0.24 0.012 60 / 0.10);
}
```

Todo el espaciado sale de esa escala. Radios discretos. Sombras solo en elementos
flotantes y pegajosos (topbar al scrollear, barra de selección, popovers); las filas se
separan con `--line`, no con sombra.

---

## 2. Layout y grilla

```
┌──────────────────────────────────────────────────────────┐
│ topbar (sticky 52px, oscura)  título · pestañas · estado │
├──────────────────────────────────────────────────────────┤
│ métricas (tira de 40px, clicables)                       │
│ filtros (sticky 88px: controles + presets/chips/contador) │
├──────────────────────────────────────────────────────────┤
│ encabezado de columnas (sticky 34px) + acciones de lista │
│ lista de publicaciones                                   │
│  └ fila (grid de 5 columnas)                             │
├──────────────────────────────────────────────────────────┤
│ barra de selección (fixed bottom, solo si hay marcadas)  │
└──────────────────────────────────────────────────────────┘
```

- Contenedor: `max-width: 1320px; margin-inline: auto; padding-inline: var(--s5);`.
  Hoy el contenido se estira a todo el ancho del monitor y las líneas de texto pasan
  los 150 caracteres.
- Todo con `display: grid` / `flex` + `gap`. Sin márgenes sueltos entre hermanos.

### 2.1 Recorte del encabezado (prioridad 1)

Medido sobre la captura de 14" (1366×700 útiles), el cromado superior consume ~610px:
título 100 · pestañas 50 · línea de período 40 · métricas 100 · filtros 150 ·
encabezado "Publicaciones" + subtítulo + acciones 130 · encabezado de columnas 30.
Queda un renglón de lista visible. Presupuesto nuevo: **230px**.

| Banda | Antes | Ahora | Cómo |
|---|---|---|---|
| Topbar | 150px (título + pestañas + estado) | **52px** | Una sola fila `--slate`: título 18px · pestañas · a la derecha pill de estado y `?` de atajos |
| "Período consultado…" | 40px | **0** | Redundante con el chip de fecha. El subtítulo descriptivo se elimina; va en el `title` del logo |
| Métricas | 100px | **40px** | Tira horizontal de una línea, no tarjetas |
| Filtros | 150px | **88px** | Dos filas: controles (40px) + presets y chips en la misma fila (40px) |
| "Publicaciones" + subtítulo + acciones | 130px | **0** | Se fusionan con el encabezado de columnas |
| Encabezado de columnas | 30px | **34px** | Sticky, con checkbox de "seleccionar todo", contador y acciones a la derecha |

**Topbar (52px, `position: sticky; top:0`)**

```
[Boletín EPESF]  Día · Histórico · Fallas          ● Completo · hoy 05:30   [?]
```

Fondo `--slate`, texto `--on-slate`, pestaña activa con `box-shadow: inset 0 -2px 0
currentColor` en `--on-slate`. Sirve de ancla oscura: el resto de la pantalla queda
blanco y la lista arranca casi de inmediato.

**Tira de métricas (40px)**

```
61 publicaciones   ·   1 relevante   ·   1 con documento   ·   0 fallas
```

Flex con `gap: var(--s5)` y separadores de 1px (`--line`), fondo `--surface-sunk`,
número 22px Archivo 700 tabular inmediatamente seguido de su etiqueta 12px `--ink-3` en
la **misma línea**. Siguen siendo botones-filtro (§4.2); el activo lleva
`background: var(--accent-soft)` y `box-shadow: inset 0 -2px 0 var(--accent)`. Cuatro
tarjetas de 100px de alto para mostrar cuatro números de dos dígitos no se justifica.

**Filtros (88px, sticky en `top: 52px`)**

Fila 1: `[‹] [fecha] [›]` · `[relevancia ▾]` · `[buscar…]` (flex-grow) · `[Aplicar]`.
Fila 2 (32px, una sola línea): presets a la izquierda, chips activos al medio, contador
a la derecha. Si la fila 2 no entra en el ancho, los presets se absorben dentro del
campo de fecha como un `▾`.

**Encabezado de columnas fusionado (34px, sticky en `top: 140px`)**

```
[☐]  FECHA   PUBLICACIÓN   ANÁLISIS   DOCUMENTOS      1 de 61 · Cómoda|Compacta · CSV · ✉
```

El `h2` "Publicaciones" y su subtítulo ("Ordenadas por incidencia estimada…") se
eliminan: el título de la pestaña ya dice dónde estamos y el orden se explica una vez en
el `title` de la columna ANÁLISIS. Los botones de densidad pasan a un toggle de 2
segmentos de 26px; `Exportar CSV` y `Generar correo` pasan a iconos con etiqueta corta
(el llamado grande a generar correo vive en la barra de selección, §4.8, que es cuando
realmente importa).

**Al scrollear:** las tres bandas sticky se reducen a dos —la tira de métricas hace
`max-height: 0` con `transition` y desaparece— dejando topbar + filtros + encabezado de
columnas en 126px. Con `prefers-reduced-motion`, sin transición.

**Regla general:** ningún bloque de chrome puede tener más alto que la fila de datos que
lo sigue. Si en 14" no se ven al menos 5 publicaciones sin scrollear, sobra algo arriba.

### 2.2 Grilla de la fila

```css
.row{
  display: grid;
  grid-template-columns:
    28px                /* checkbox */
    132px               /* fecha + tipo */
    minmax(0, 1.5fr)    /* identificación: organismo, título, código */
    minmax(0, 1.35fr)   /* análisis: relevancia, indicios, resumen */
    168px;              /* documentos */
  gap: var(--s3) var(--s5);
  align-items: start;
  padding: var(--s3) var(--s4);
  border-bottom: 1px solid var(--line);
}
```

Alto objetivo de fila: ~72px en densidad cómoda, ~52px en compacta.

Las columnas se mantienen alineadas fila a fila (hoy los enlaces de la derecha
"bailan"). Por debajo de 1100px el grid colapsa a dos columnas y los documentos pasan
a una fila propia; no hay diseño mobile, pero no debe romperse en una ventana angosta.

---

## 3. Encabezado de columnas

Fila sticky (§2.1) en mono 11px uppercase `--ink-3` sobre `--surface-sunk`:
`FECHA · PUBLICACIÓN · ANÁLISIS · DOCUMENTOS`, alineada a la misma grilla de 5 columnas.
Con 61 filas iguales, el usuario necesita saber qué significa cada columna sin deducirlo.
A la derecha de la misma fila viven el contador, el toggle de densidad y las acciones de
lista.

---

## 4. Componentes

### 4.1 Estado de ejecución (`.status`)

Hoy dice "Última ejecución / Completo / 15/09/2026 05:30" en tres líneas alineadas a la
derecha, en gris, sin color. Pasa a un solo *pill* en la topbar oscura:

```
● Completo · hoy 05:30        ← punto en --sig-ok, texto --on-slate
▲ 3 fechas con falla · 05:30  ← punto en --sig-alta, pill clicable → vista de fallas
```

- Sobre `--slate` los semánticos se aclaran una parada (`oklch(0.72 …)` con el mismo
  matiz) para mantener 4.5:1.
- Punto de 8px + texto 13px. Fecha en relativo (`hoy 05:30`, `ayer 05:30`,
  `hace 3 días`) con la fecha absoluta en `title`.
- Si hubo falla, el pill es un `<button>` que filtra la lista por fechas con error y
  ofrece **Reintentar**. Un estado de error que no es accionable es decoración.

### 4.2 Métricas (`.metrics`)

Tira horizontal de 40px (§2.1), no tarjetas: `display: flex; gap: var(--s5)` sobre
`--surface-sunk`, con separadores de 1px `--line` entre ítems.

- Cada ítem es un `<button>` de una sola línea: número 22px Archivo 700 tabular +
  etiqueta 12px `--ink-3` al lado. Etiquetas en singular/plural correcto
  (`1 relevante`, no `1 relevantes` — error visible en la captura actual).
- **Cada métrica es un filtro.** "42 relevantes" → `?relevance=selected`;
  "44 con documento" → filtra a publicaciones con documento; "0 fallas" → vista de
  fallas. La activa lleva `background: var(--accent-soft)` y
  `box-shadow: inset 0 -2px 0 var(--accent)`.
- Si el valor es 0, el ítem baja a `--ink-3` y no es clicable (`aria-disabled`).
- Delta opcional respecto al día anterior, en 12px mono: `+7 vs. ayer`.
- La tira se colapsa al scrollear (§2.1).

### 4.3 Filtros (`.filters`)

```
[‹] [15/09/2026] [›]   [ relevancia ▾ ]   [ 🔍 Organismo, tipo, número o texto  ]  [Aplicar]
Hoy · Ayer · 7 días · Mes    15/09/2026 ✕  relevantes ✕          1 de 61 publicaciones
```

- `<fieldset>` sin borde con `<legend class="sr-only">Filtros</legend>`; los rótulos
  `FECHA / RELEVANCIA / BUSCAR` dejan de ocupar una línea propia: pasan a `<label>`
  visualmente oculto + `placeholder` y `aria-label` en cada control (recupera 24px).
- **Flechas ‹ › para día anterior / siguiente.** Es la interacción más frecuente de
  toda la app y hoy exige abrir el datepicker. `›` deshabilitado si la fecha es hoy.
- Presets como chips en la fila 2: *Hoy*, *Ayer*, *Últimos 7 días*, *Este mes*. El
  preset activo usa `--accent-soft` + borde `--accent`. Con rango de fechas, el chip de
  fecha activa muestra `01/09 – 15/09`; no se agrega una línea de "Período consultado".
- Relevancia: opciones explícitas en lugar de "Seleccionadas y pendientes":
  *Todas* · *Relevantes* · *Impacto potencial* · *Descartadas* · *Sin clasificar*,
  cada una con su conteo entre paréntesis.
- `q`: `type="search"`, icono de lupa a la izquierda, `✕` para limpiar, y submit con
  Enter. Fecha y relevancia hacen submit al cambiar (`onchange`): "Aplicar filtros"
  queda solo como respaldo para el texto, no como peaje obligatorio.
- Inputs: alto **36px**, `border: 1px solid var(--line-strong)`, radio `--r-md`, fondo
  `--surface`. Foco: `outline: 2px solid var(--accent); outline-offset: 2px`.
- En la **misma fila 2**, a continuación de los presets, los **chips de filtros activos**
  con `✕` (`15/09/2026 ✕` · `relevantes ✕` · `"cammesa" ✕`) y a la derecha
  `1 de 61 publicaciones` en `aria-live`. Un estado de filtrado invisible es la principal
  fuente de confusión en este tipo de herramienta — pero no merece dos renglones.
- "Ver todo el histórico" no es un enlace suelto bajo los filtros: es una pestaña
  (§4.10).

### 4.4 Fila de publicación (`.row`)

Cinco columnas, una idea por columna:

1. **Selección** — checkbox 18px, sin texto al lado. La etiqueta accesible va en
   `aria-label="Incluir Resolución 611/2026 en el correo"`. Hoy la primera columna
   alterna entre "Incluir" y "Sin resumen", que son dos cosas distintas en el mismo
   lugar: eso desaparece.
2. **Fecha y tipo** — fecha en mono 13px `--ink`; tipo (`RESOLUCIONES SINTETIZADAS`)
   como eyebrow 11px uppercase `--ink-3`, máximo dos líneas.
3. **Identificación** — organismo como eyebrow `--ink-3`; luego el título
   (`Resolución 611/2026`) en Archivo 600 17px `--ink`, que es el ancla visual de la
   fila y un enlace al detalle; debajo el código en mono 12px `--ink-3` con
   `overflow-wrap: anywhere`.
4. **Análisis** — badge de relevancia (§4.5) + indicios sectoriales como chips
   discretos (§4.6) + primera línea del resumen IA si existe, en `--ink-2`, recortada
   con `-webkit-line-clamp: 2`.
5. **Documentos** — máximo tres enlaces, apilados con `gap: var(--s1)`, cada uno con
   icono de 14px y el peso en mono: `PDF principal · 2 pág.`, `Anexo · 2 pág.`,
   `Aviso en BORA ↗`. Enlaces externos con `target="_blank" rel="noopener"` y `↗`.

Estados de la fila:

```css
.row:hover            { background: var(--surface); }
.row:focus-within     { outline: 2px solid var(--accent); outline-offset: -2px; }
.row[data-selected]   { background: var(--accent-soft);
                        box-shadow: inset 3px 0 0 var(--accent); }
.row[data-unread]     { /* publicación nueva desde la última visita */
                        box-shadow: inset 3px 0 0 var(--sig-info); }
```

Cebreado alterno **no**: con divisores de 1px y padding suficiente alcanza, y el rayado
compite con el fondo de selección.

### 4.5 Badge de relevancia

Un solo badge por fila, en pastilla con fondo suave y texto pleno:

| Etiqueta | Texto | Fondo |
|---|---|---|
| `Impacto directo` | `--sig-alta` | `--sig-soft-a` |
| `Impacto potencial` | `--sig-media` | `--sig-soft-m` |
| `Informativa` | `--sig-info` | `--sig-soft-i` |
| `Sin clasificar` | `--ink-3` | `--surface-sunk` |

11px Archivo 600, uppercase, `letter-spacing: .06em`, padding `3px 8px`, radio
`--r-sm`, **sin borde**. El badge verde con borde actual lee como "aprobado", que es lo
contrario de lo que significa "impacto potencial".

### 4.6 Indicios sectoriales

Hoy es una frase corrida que se repite idéntica en decenas de filas y se lee como
párrafo. Pasa a chips: `energía eléctrica` `cammesa` `ENRE` `+2`, en 12px `--ink-2`,
fondo `--surface-sunk`, radio `--r-sm`. Máximo tres visibles; el resto detrás de `+N`
con `title`. Los términos que coinciden con `q` van en `<mark>` con fondo
`--sig-soft-m`.

### 4.7 Detalle y resumen IA (`.summary`)

- `<details>`/`<summary>` con el triángulo actual reemplazado por un chevron propio que
  rota 90°; `summary` sin `list-style`.
- Contenido expandido: bloque sobre `--surface` con `border-left: 3px solid var(--accent)`,
  padding `--s4`, ancho de texto limitado a `68ch`. Dentro: resumen, artículos citados,
  organismo completo, enlaces a anexos.
- El resumen IA lleva una atribución discreta arriba: `Resumen generado por IA` en 11px
  `--ink-3`, para que nadie lo confunda con texto oficial. Y un enlace
  `Ver texto original` al PDF.
- Si `Sin resumen`: no es una etiqueta gris en la columna izquierda, es un botón
  secundario en la columna de análisis — **`Generar resumen`** — con estado
  `Generando…` y `aria-busy`. Convierte un dato muerto en una acción.
- Abrir un detalle no debe recargar la página ni perder el scroll.

### 4.8 Acciones masivas y barra de selección

- En la fila de encabezado de columnas (§3): checkbox de "seleccionar todo lo visible",
  `Quitar selección` cuando hay algo marcado, y el toggle de densidad **Cómoda /
  Compacta** (persistido en `?density=` o `localStorage`). Sin bloque propio.
- Con ≥1 fila marcada aparece una barra `position: fixed; bottom: 0`, ancho del
  contenedor, fondo `--slate`, texto `--on-slate`, `--shadow-2`, entrando con
  `transform: translateY(100%) → 0` en 160ms:

```
3 seleccionadas   [Generar correo]  [Exportar CSV]  [Limpiar]
```

- Botón primario: fondo `--accent`, texto blanco, 36px de alto, radio `--r-md`.
  Secundarios: `border: 1px solid currentColor` sobre transparente.
- El botón grande `Generar correo con seleccionadas` desaparece del encabezado: en la
  fila de columnas queda como icono ✉ con `title`, y el llamado pleno vive en esta
  barra, que es cuando hay algo que enviar. Deshabilitado (no oculto) sin selección.
- Como el correo no se envía solo, el resultado debe decirlo: confirmación
  `Borrador listo — se abrió en tu cliente de correo. No se envió nada automáticamente.`
- "Exportar esta vista" pasa a `Exportar CSV (129)` con el conteo real de lo que va a
  bajar.

### 4.9 Enlaces y foco

```css
a{ color: var(--accent); text-decoration: underline;
   text-underline-offset: 2px; text-decoration-thickness: 1px; }
a:hover{ color: var(--accent-ink); text-decoration-thickness: 2px; }
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible{
   outline: 2px solid var(--accent); outline-offset: 2px; border-radius: var(--r-sm); }
```

Nunca eliminar el outline. Es una herramienta de teclado (§6).

### 4.10 Navegación de vistas

Reemplazar el enlace "Ver todo el histórico" por pestañas **dentro de la topbar**
(§2.1), no en una banda propia: **Día** · **Histórico** · **Fallas**.

Para *Histórico*, en lugar de una lista infinita: una grilla de calendario por mes con
una celda por día mostrando el conteo de relevantes, con la intensidad de
`--accent-soft` proporcional al volumen y borde `--sig-alta` en las fechas con falla.
Click en el día → vista de día. Es la forma natural de recorrer un boletín diario y
resuelve "¿qué días me perdí?" de un vistazo.

---

## 5. Estados vacíos, carga y error

Cada estado tiene causa y salida. Todos con el mismo bloque centrado:
título 17px `--ink`, explicación 14px `--ink-2` (máx. `52ch`), una acción primaria.
Sin ilustraciones ni iconos grandes.

| Situación | Título | Acción |
|---|---|---|
| Sin publicaciones para la fecha | `No hubo publicaciones el 15/09/2026` | `Ver día anterior` |
| Filtro sin resultados | `Ninguna publicación coincide con los filtros` | `Limpiar filtros` (listar los activos) |
| Búsqueda sin resultados | `Sin resultados para "cammesa"` | `Buscar en todo el histórico` |
| Fecha no procesada | `Esta fecha todavía no se consultó` | `Consultar ahora` |
| Falla de scraping | `No se pudo leer el BORA del 15/09` + motivo técnico en `<details>` | `Reintentar` |
| Resumen IA no disponible | `El resumen no está disponible` + `Ver PDF original` | `Reintentar` |
| Cargando (submit de filtros) | barra de progreso 2px `--accent` en el tope + `aria-busy="true"` en la lista + opacidad 0.6 | — |

Notas:

- Como el render es server-side, no hay skeletons: basta la barra de progreso superior
  y deshabilitar el botón durante el submit.
- Un error de un documento no debe vaciar la lista: la fila se muestra con badge
  `Documento no disponible` en `--sig-alta` y el resto sigue usable.
- El pie "Servicio local · Los datos y documentos permanecen en este equipo" se
  conserva: es información valiosa. Ubicarlo en el footer, 12px `--ink-3`.

---

## 6. Teclado y accesibilidad

Uso diario intensivo: el teclado no es un extra.

- `/` enfoca el buscador · `←` `→` día anterior/siguiente · `j`/`k` mueven el foco entre
  filas · `x` marca la fila enfocada · `Enter` abre el detalle · `Esc` limpia la
  búsqueda. Un `?` muestra la lista de atajos.
- Lista como `<ul>`/`<li>` con `<article>` por fila, no como `<div>`s anidados.
- Contraste mínimo 4.5:1 en texto y 3:1 en bordes de control. `--ink-3` sobre `--paper`
  queda en ~4.6:1: no bajar más su luminosidad.
- `aria-live="polite"` en el contador de resultados y en la confirmación del correo.
- Orden de tabulación: filtros → acciones de lista → filas → barra de selección.
- Respetar `prefers-reduced-motion`: sin transiciones de expansión ni de barra.
- Sin modo oscuro por ahora (queda fuera de alcance).

---

## 7. Movimiento

Discreto y funcional. Transiciones de 120–180ms, `ease-out`.
Solo cuatro: hover de fila, expansión del detalle, entrada de la barra de selección,
barra de progreso al filtrar. Nada más se anima.

---

## 8. Orden de implementación

1. **Recorte del encabezado (§2.1): topbar de 52px, métricas en tira, filtros en dos
   filas, eliminación del bloque "Publicaciones". Es el cambio de mayor impacto.**
2. Tokens de color nuevos (grafito sobre blanco frío) y tipografía sin serif.
3. Contenedor de 1320px, escala de espaciado, alto de fila de 72/52px.
4. Grilla de la fila en 5 columnas + jerarquía tipográfica interna + encabezado de
   columnas sticky con acciones de lista.
5. Filtros: flechas de día, presets, submit al cambiar, chips activos, contador.
6. Badges de relevancia y chips de indicios.
7. Barra de selección flotante con conteo + confirmación explícita del borrador de correo.
8. Métricas clicables + pill de estado de ejecución accionable.
9. Estados vacíos, de carga y de error.
10. Atajos de teclado, foco y semántica.
11. Pestaña Histórico con calendario y pestaña Fallas.

Los puntos 1 a 7 ya cambian sustancialmente la experiencia; 8 a 11 son los que la
convierten en una herramienta de trabajo.

---

## 9. Criterio de aceptación visual

En una ventana de 1366×700 (14"), con la vista por defecto:

- Se ven **al menos 5 publicaciones completas** sin scrollear.
- El chrome superior mide ≤ 230px y, al scrollear, ≤ 130px.
- No hay ningún fondo cálido/crema ni texto serif.
- Hay exactamente un color de acento visible además de los badges semánticos.
