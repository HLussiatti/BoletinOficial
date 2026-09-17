---
version: 1
slug: "src-epe-boletin-web-ui-py"
primary_target: "src/epe_boletin/web_ui.py"
related_targets: ["src/epe_boletin/web_views.py"]
---

# Boletín Oficial EPESF · interfaz operativa

Modo: Operate. Rediseño guiado por `estilo_web_v2.md`; conserva consultas,
clasificación, documentos, histórico, fallas y preparación manual del correo.

## Direction contract

THESIS: Un instrumento diario de revisión; la lista tiene prioridad sobre el encabezado.

OWN-WORLD: Blanco frío, tinta grafito y azul institucional; una sans, códigos mono,
barra superior oscura y registros alineados sin tarjetas ni cebreado.

STORY: Confirmar cobertura, filtrar, revisar fuentes, seleccionar y preparar un borrador.

FIRST VIEWPORT: Topbar de altura mínima 76px con navegación y estado, métricas
de 64px, controles de 40px y cabecera de lista de al menos 40px. Primera fila
visible y dos registros completos en 1366×768; sin bandas laterales grandes en
1920×1080. Cómoda es la vista predeterminada.

FORM: Ancho fluido con márgenes de 16–40px y barras superiores a todo el ancho.
Filtros de período, relevancia, tipo y búsqueda. El período usa un solo control
Desde/Hasta con calendario continuo de dos meses (uno en móvil). Resumen de Análisis
prioritario; tipo sin duplicación y palabras clave en detalle. La barra de
resultados aloja Cómoda/Compacta y CSV. A 1100px se reparte en
publicación/análisis; a 700px se apila sin barras sticky, y a 400px se apilan
los campos nativos de fecha de respaldo. Detalle nativo sin recarga y barra de selección contextual.
Movimiento funcional de 160ms y variante reducida.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
