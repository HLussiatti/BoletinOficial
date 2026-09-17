# Guía de estilo y UX — Boletín EPESF

Documento de especificación para Codex. Aplica a la interfaz servida por `web.py`
(`render_page`) en el servidor local. Sin frameworks: HTML semántico + CSS plano.

Contexto: herramienta de uso interno intensivo diario. El usuario entra varias veces
por día a responder una sola pregunta —*¿qué se publicó hoy que afecta a la EPE?*— y a
armar un correo con lo relevante. Todo lo que no ayude a escanear, decidir y seleccionar
rápido es ruido.

La dirección actual (papel crema, serif editorial, negro) es un buen punto de partida y
se conserva. Lo que cambia es la jerarquía, la densidad, el color semántico y los estados.

---

## 1. Fundaciones

### 1.1 Tipografía

Tres familias, con fallback local porque el servidor puede estar sin internet.
Autohospedar los `.woff2` en `static/fonts/` y declarar `@font-face` con
`font-display: swap`. Si no se pueden hospedar, los fallbacks son aceptables.

| Rol | Familia | Fallback |
|---|---|---|
| Display (título, cifras, encabezados de sección) | **Newsreader** 500/600 | `Georgia, "Times New Roman", serif` |
| Interfaz y cuerpo (todo lo demás) | **Archivo** 400/500/600 | `"Segoe UI", system-ui, sans-serif` |
| Datos y códigos (expedientes, fechas ISO, contadores) | **Space Mono** 400/700 | `Consolas, "Courier New", monospace` |

Reglas:

- El serif es solo para el título de la app, los encabezados de sección y los números
  de las métricas. **Nunca para títulos de publicación ni para cuerpo.** Hoy
  "Resolución 611/2026" está en serif y compite con el título de la página.
- Los códigos de expediente (`RESFC-2026-507-APN-DIRECTORIO#ENREGE`) y las fechas ISO
  van en mono, tamaño menor, color secundario. Son identificadores, no prosa.
- Cifras tabulares siempre: `font-variant-numeric: tabular-nums;` en métricas, fechas,
  páginas y contadores.
- Nada por debajo de 12px. Mínimo de cuerpo: 14px.

### 1.2 Escala tipográfica

```css
:root{
  --fs-display: 2.25rem;  /* 36px  Newsreader 600, line-height 1.05, ls -0.02em */
  --fs-h2:      1.3125rem;/* 21px  Newsreader 600, line-height 1.2 */
  --fs-metric:  2rem;     /* 32px  Newsreader 600, tabular */
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

```css
:root{
  /* superficies: solo dos fondos en toda la app */
  --paper:        oklch(0.975 0.008 85);   /* fondo de página, crema */
  --surface:      oklch(0.995 0.004 85);   /* tarjetas y filas, casi blanco */
  --surface-sunk: oklch(0.955 0.010 85);   /* barra de métricas, celdas de encabezado */

  /* tinta */
  --ink:          oklch(0.24 0.012 60);    /* texto principal */
  --ink-2:        oklch(0.46 0.012 60);    /* texto secundario, resúmenes */
  --ink-3:        oklch(0.62 0.010 60);    /* etiquetas, metadatos, placeholder */

  /* líneas */
  --line:         oklch(0.905 0.012 82);   /* divisores internos */
  --line-strong:  oklch(0.80 0.016 82);    /* bordes de contenedor, inputs */

  /* acento único de marca */
  --accent:       oklch(0.52 0.13 45);     /* terracota: enlaces, foco, selección */
  --accent-ink:   oklch(0.38 0.11 45);     /* texto sobre fondo suave */
  --accent-soft:  oklch(0.945 0.035 45);   /* fondo teñido de fila seleccionada */
  --gold: var(--accent);                    /* alias de compatibilidad */

  /* semánticos: mismo croma/lightness, distinto matiz */
  --sig-alta:     oklch(0.52 0.13 25);     /* relevancia alta / impacto directo */
  --sig-media:    oklch(0.52 0.13 75);     /* impacto potencial */
  --sig-ok:       oklch(0.52 0.13 150);    /* ejecución completa */
  --sig-info:     oklch(0.52 0.13 240);    /* informativo / sin impacto */
  --sig-soft-a:   oklch(0.95 0.03 25);
  --sig-soft-m:   oklch(0.95 0.03 75);
  --sig-soft-ok:  oklch(0.95 0.03 150);
  --sig-soft-i:   oklch(0.95 0.03 240);
}
```

Reglas de color:

- **Máximo dos fondos** en la pantalla: `--paper` para la página, `--surface` para las
  filas. `--surface-sunk` solo en la banda de métricas.
- Texto siempre a opacidad plena. Prohibido `opacity` o `color-mix` para atenuar texto:
  usar `--ink-2` / `--ink-3`, que están calculados para cumplir 4.5:1 sobre `--paper`.
- El color nunca es el único portador de significado: todo badge lleva texto.
- Negro puro (`#000`) fuera. El botón primario usa `--ink`, no negro.
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

Todo el espaciado sale de esa escala. Radios discretos: la estética es documental, no
de app de consumo. Sombras solo en elementos flotantes (barra de selección, popovers);
las filas se separan con `--line`, no con sombra.

---

## 2. Layout y grilla

```
┌──────────────────────────────────────────────────────────┐
│ topbar  (sticky, 56px)  título · estado de ejecución     │
├──────────────────────────────────────────────────────────┤
│ métricas (4 tarjetas clicables, banda sunk)              │
│ filtros  (sticky bajo el topbar)                         │
│ chips de filtros activos + contador de resultados        │
├──────────────────────────────────────────────────────────┤
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
- `topbar` y `.filters` `position: sticky` (`top: 0` y `top: 56px`), con
  `background: var(--paper)` y `border-bottom: 1px solid var(--line)` al scrollear.
  En una lista de 129 publicaciones, los filtros deben estar siempre a mano.
- Título de la app reducido: el `display` de 60px actual ocupa un cuarto del alto útil
  sin aportar nada a un usuario que entra 6 veces por día. 36px, y al scrollear la
  topbar lo comprime a 18px en una sola línea junto al estado.

### Grilla de la fila

```css
.row{
  display: grid;
  grid-template-columns:
    28px                /* checkbox */
    132px               /* fecha + tipo */
    minmax(0, 1.5fr)    /* identificación: organismo, título, código */
    minmax(0, 1.35fr)   /* análisis: relevancia, indicios, resumen */
    168px;              /* documentos */
  gap: var(--s4) var(--s5);
  align-items: start;
  padding: var(--s4) var(--s4);
  border-bottom: 1px solid var(--line);
}
```

Las columnas se mantienen alineadas fila a fila (hoy los enlaces de la derecha
"bailan"). Por debajo de 1100px el grid colapsa a dos columnas y los documentos pasan
a una fila propia; no hay diseño mobile, pero no debe romperse en una ventana angosta.

---

## 3. Encabezado de columnas

Sobre la lista, una fila de encabezados sticky en mono 11px uppercase `--ink-3`:
`FECHA · PUBLICACIÓN · ANÁLISIS · DOCUMENTOS`. Con 129 filas iguales, el usuario
necesita saber qué significa cada columna sin deducirlo.

---

## 4. Componentes

### 4.1 Estado de ejecución (`.status`)

Hoy dice "Última ejecución / Completo / 15/09/2026 05:30" en tres líneas alineadas a la
derecha, en gris, sin color. Pasa a un solo *pill* en la topbar:

```
● Completo · hoy 05:30        ← punto en --sig-ok, texto --ink
▲ 3 fechas con falla · 05:30  ← punto en --sig-alta, pill clicable → vista de fallas
```

- Punto de 8px + texto 13px. Fecha en relativo (`hoy 05:30`, `ayer 05:30`,
  `hace 3 días`) con la fecha absoluta en `title`.
- Si hubo falla, el pill es un `<button>` que filtra la lista por fechas con error y
  ofrece **Reintentar**. Un estado de error que no es accionable es decoración.

### 4.2 Métricas (`.metrics`)

Cuatro tarjetas en `grid-template-columns: repeat(4, 1fr)` sobre `--surface-sunk`,
separadas por `--line`, radio `--r-lg`, sin borde exterior dorado.

- Número en Newsreader 600 32px tabular; etiqueta debajo en 12px `--ink-3`.
- **Cada métrica es un filtro.** "42 relevantes" → `?relevance=selected`;
  "44 documentos descargados" → filtra a publicaciones con documento;
  "0 fechas con fallas" → vista de fallas. La métrica activa lleva
  `background: var(--accent-soft)` y `box-shadow: inset 2px 0 0 var(--accent)`.
- Si el valor es 0, la tarjeta baja a `--ink-3` y no es clicable (`aria-disabled`).
- Delta opcional respecto al día anterior, en 12px mono: `+7 vs. ayer`.

### 4.3 Filtros (`.filters`)

```
FECHA                      RELEVANCIA          BUSCAR
[‹] [15/09/2026] [›]       [ select      ▾]    [ 🔍 Organismo, tipo, número…    ]
Hoy · Ayer · 7 días · Mes                                        [Aplicar filtros]
```

- `<fieldset>` sin borde con `<legend class="sr-only">Filtros</legend>`; cada control
  con su `<label for>` real (hoy las etiquetas son texto suelto).
- **Flechas ‹ › para día anterior / siguiente.** Es la interacción más frecuente de
  toda la app y hoy exige abrir el datepicker. `›` deshabilitado si la fecha es hoy.
- Presets como chips: *Hoy*, *Ayer*, *Últimos 7 días*, *Este mes*. Con rango de fechas,
  el título pasa a "Período consultado: 01/09 – 15/09".
- Relevancia: opciones explícitas en lugar de "Seleccionadas y pendientes":
  *Todas* · *Relevantes* · *Impacto potencial* · *Descartadas* · *Sin clasificar*,
  cada una con su conteo entre paréntesis.
- `q`: `type="search"`, icono de lupa a la izquierda, `✕` para limpiar, y submit con
  Enter. Fecha y relevancia hacen submit al cambiar (`onchange`): "Aplicar filtros"
  queda solo como respaldo para el texto, no como peaje obligatorio.
- Inputs: alto 38px, `border: 1px solid var(--line-strong)`, radio `--r-md`, fondo
  `--surface`. Foco: `outline: 2px solid var(--accent); outline-offset: 2px`.
- Debajo, **chips de filtros activos** con `✕` (`15/09/2026 ✕` · `relevantes ✕` ·
  `"cammesa" ✕`) y a la derecha `129 publicaciones · 42 relevantes` en `aria-live`.
  Un estado de filtrado invisible es la principal fuente de confusión en este tipo de
  herramienta.
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

- Sobre la lista: `Seleccionar las 42 visibles` / `Quitar selección`, más el toggle de
  densidad **Cómoda / Compacta** (persistido en `?density=` o `localStorage`).
- Con ≥1 fila marcada aparece una barra `position: fixed; bottom: 0`, ancho del
  contenedor, fondo `--ink`, texto `--paper`, `--shadow-2`, entrando con
  `transform: translateY(100%) → 0` en 160ms:

```
3 seleccionadas   [Generar correo]  [Exportar CSV]  [Limpiar]
```

- Botón primario: fondo `--accent`, texto `--paper`, 38px de alto, radio `--r-md`.
  Secundarios: `border: 1px solid` sobre transparente.
- "Generar correo con seleccionadas" deshabilitado (no oculto) cuando no hay selección,
  con `title` explicando por qué. Hoy es un botón negro grande siempre activo que no
  informa cuántas van.
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

Reemplazar el enlace "Ver todo el histórico" por pestañas bajo el título:
**Día** · **Histórico** · **Fallas**.

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

1. Tokens de color y tipografía, contenedor de 1320px, escala de espaciado.
2. Grilla de la fila en 5 columnas + jerarquía tipográfica interna + encabezados de columna.
3. Filtros: flechas de día, presets, submit al cambiar, chips activos, contador.
4. Badges de relevancia y chips de indicios.
5. Barra de selección flotante con conteo + confirmación explícita del borrador de correo.
6. Métricas clicables + pill de estado de ejecución accionable.
7. Estados vacíos, de carga y de error.
8. Atajos de teclado, foco y semántica.
9. Pestaña Histórico con calendario y pestaña Fallas.

Los puntos 1 a 5 ya cambian sustancialmente la experiencia; 6 a 9 son los que la
convierten en una herramienta de trabajo.
