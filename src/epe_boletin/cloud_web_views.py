"""Cloud presentation using the approved local interface and its design tokens."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from .web_ui import CSS, SCRIPT
from .web_views import calendar_view, category_repeats_title, icon, nice_day, signals


CLOUD_CSS = CSS + """
.cloud-account{margin-left:auto;display:flex;align-items:center;gap:var(--s2);font-size:var(--fs-small)}
.cloud-account span{color:var(--on-slate);white-space:nowrap}.cloud-account form{margin:0}
.cloud-account button{height:36px;color:var(--on-slate);background:transparent;border-color:oklch(.60 .030 255)}
.cloud-account button:hover{color:var(--on-slate);background:var(--accent-ink)}
.cloud-source-note{color:var(--ink-2);font-size:var(--fs-small);padding:var(--s3) 0}
.cloud-page-nav{display:flex;align-items:center;justify-content:center;gap:var(--s4);padding:var(--s4)}
.cloud-page-nav a{display:inline-flex;align-items:center;min-height:40px;padding:0 var(--s3)}
.cloud-disabled{color:var(--ink-3);font-size:var(--fs-small)}
.cloud-empty{padding:var(--s7) var(--s5);background:var(--surface);border-bottom:1px solid var(--line)}
.cloud-empty h2{font-size:var(--fs-title);margin-bottom:var(--s2)}
.cloud-empty p{color:var(--ink-2)}
.cloud-issues{list-style:none;margin:0;padding:0}.cloud-issue{padding:var(--s4);border-bottom:1px solid var(--line);background:var(--surface)}
.cloud-issue p{color:var(--ink-2);margin-top:var(--s2)}
.cloud-issues-title{padding:var(--s5) 0 var(--s3)}
.cloud-actions{display:flex;gap:var(--s2);flex-wrap:wrap;align-items:center}
.cloud-job{margin:var(--s3) 0;padding:var(--s3) var(--s4);background:var(--accent-soft);border:1px solid var(--accent);border-radius:var(--r-sm)}
.cloud-job.failed{background:var(--surface);border-color:var(--sig-alta)}
@media(max-width:900px){.cloud-account span{display:none}}
@media(max-width:700px){.cloud-account{margin-left:0}.cloud-account button{padding-inline:var(--s2)}}
"""

# The shared portion covers selection, the approved range picker, density,
# navigation and keyboard shortcuts. Cloud work is submitted with a CSRF token.
CLOUD_SCRIPT = (SCRIPT.split(" function emailActions", 1)[0]
                + " document.querySelectorAll('.title a')"
                + SCRIPT.split(" document.querySelectorAll('.title a')", 1)[1]
                        .split(" const actionNotice", 1)[0]
                + "})();")
CLOUD_SCRIPT = CLOUD_SCRIPT[:-5] + """
 const work=$('#cloud-work');
 if(work){
   const button=work.querySelector('button');
   button.disabled=true;button.textContent='Procesando…';
   fetch(work.action,{method:'POST',body:new URLSearchParams(new FormData(work)),credentials:'same-origin'})
     .then(response=>{if(!response.ok)throw new Error('La conexión falló');window.location.reload();})
     .catch(()=>{button.disabled=false;button.textContent='Continuar trabajo';});
 }
})();"""


def render(app, filters, csrf: str, user: str, job_id: str = "") -> bytes:
    # Import here because cloud_web loads this view only after the request is authenticated.
    from .cloud_web import PAGE_SIZE, RELEVANCE, _h, _official_pdf_url, _official_url

    today = datetime.now(timezone(timedelta(hours=-3))).date()
    overview = app._overview(filters)
    counts = overview["counts"]
    failed = int(overview["failed"])
    last = overview["last"]
    latest = app._latest_date()
    summary_enabled = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    job_notice = ""
    refresh = ""
    if job_id:
        job = app._database().job(job_id)
        if job:
            state = str(job["status"])
            label = {"pending": "Solicitud recibida; esperando ejecutor.",
                     "running": "Trabajo en curso. Esta página se actualizará.",
                     "complete": "Trabajo terminado. Ya podés revisar el resultado.",
                     "failed": "No se pudo completar el trabajo. Podés reintentarlo."}[state]
            error = f'<p>{_h(job["error"])}</p>' if state == "failed" and job["error"] else ""
            job_notice = (f'<div class="cloud-job{" failed" if state == "failed" else ""}" '
                          f'role="status"><strong>{_h(label)}</strong>{error}</div>')
            if state in ("pending", "running"):
                refresh = '<meta http-equiv="refresh" content="10">' if state == "running" else ""
                if state == "pending":
                    job_notice += (f'<form id="cloud-work" action="/?action=step" method="post">'
                                   f'<input type="hidden" name="csrf" value="{_h(csrf)}">'
                                   f'<input type="hidden" name="job" value="{_h(job_id)}">'
                                   '<button type="submit">Continuar trabajo</button></form>')
    calendar_mode = (filters.view == "history" and not filters.day and not filters.text
                     and not filters.category and filters.relevance == "active")
    total, rows = (0, []) if calendar_mode or filters.view == "failures" else app._listing(filters)

    nav_items = []
    for view, label in (("day", "Día"), ("history", "Histórico"), ("failures", "Fallas")):
        href = filters.url(view=view, date=latest if view == "day" else "",
                           to="", q="", category="", relevance="active", month="", page=1)
        current = ' aria-current="page"' if filters.view == view else ""
        nav_items.append(f'<a href="{_h(href)}"{current}>{label}</a>')
    nav = "".join(nav_items)
    last_status = str(last["status"]) if last else ""
    status_label = f"{failed} fechas con falla" if failed else (
        "Carga completa" if last_status == "complete" else "Datos históricos")
    status_class = " error" if failed else ("" if last_status == "complete" else " neutral")
    failures_url = filters.url(view="failures", date="", to="", relevance="all", page=1)
    status_link = (f'<a class="run-pill{status_class}" href="{_h(failures_url)}">'
                   if failed else f'<span class="run-pill{status_class}">')
    status_end = "</a>" if failed else "</span>"
    status = f'{status_link}<span class="dot" aria-hidden="true"></span>{_h(status_label)}{status_end}'

    metrics = []
    for value, label, updates, active in (
        (counts["all"], "publicaciones", {"relevance": "all", "page": 1}, filters.relevance == "all"),
        (counts["selected"], "relevantes", {"relevance": "selected", "page": 1}, filters.relevance == "selected"),
        (counts["direct_epesf"], "impacto directo", {"relevance": "direct_epesf", "page": 1}, filters.relevance == "direct_epesf"),
        (counts["potential_sector_impact"], "impacto potencial", {"relevance": "potential_sector_impact", "page": 1}, filters.relevance == "potential_sector_impact"),
        (failed, "fechas con fallas", {"view": "failures", "date": "", "to": "", "relevance": "all", "page": 1}, filters.view == "failures"),
    ):
        tag = "a" if value else "div"
        href = f' href="{_h(filters.url(**updates))}"' if value else ' aria-disabled="true"'
        metrics.append(f'<{tag} class="metric"{href} aria-current="{str(active).lower()}"><b>{value}</b><span>{label}</span></{tag}>')

    relevance_options = "".join(
        f'<option value="{_h(key)}"{" selected" if key == filters.relevance else ""}>'
        f'{_h(label)} ({counts[key]})</option>' for key, label in RELEVANCE.items())
    category_options = '<option value="">Todos los tipos</option>' + "".join(
        f'<option value="{_h(category)}"{" selected" if category == filters.category else ""}>'
        f'{_h(category)}</option>' for category in overview["categories"])
    day = date.fromisoformat(filters.day) if filters.day else (date.fromisoformat(latest) if latest else today)
    previous = filters.url(date=(day - timedelta(days=1)).isoformat(), to="", view="day", page=1)
    following_day = filters.url(date=(day + timedelta(days=1)).isoformat(), to="", view="day", page=1)
    next_control = (f'<a id="next-day" class="icon-button" href="{_h(following_day)}" '
                    f'aria-label="Día siguiente">{icon("right")}</a>' if day < today else
                    f'<span id="next-day" class="icon-button" aria-disabled="true" '
                    f'aria-label="Día siguiente">{icon("right")}</span>')
    previous_control = (f'<a id="previous-day" class="icon-button" href="{_h(previous)}" '
                        f'aria-label="Día anterior">{icon("left")}</a>') if filters.day and not filters.end_day else ""
    period_end = filters.end_day or filters.day
    from_label = nice_day(filters.day) if filters.day else "Elegir fecha"
    to_label = nice_day(period_end) if period_end else "Elegir fecha"
    range_control = f'''<div class="range-picker" id="range-picker" data-max="{today.isoformat()}">
      <div class="period-control range-native"><div class="period-date"><label for="date">Desde</label><input id="date" name="date" type="date" value="{_h(filters.day)}" max="{today.isoformat()}" data-auto-submit></div><div class="period-date"><label for="to">Hasta</label><input id="to" name="to" type="date" value="{_h(period_end)}" max="{today.isoformat()}" data-auto-submit></div></div>
      <button id="range-trigger" class="range-trigger" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="range-panel" aria-label="Elegir período: desde {_h(from_label)} hasta {_h(to_label)}"><span class="range-segment"><small>Desde</small><span>{_h(from_label)}</span></span><span class="range-segment"><small>Hasta</small><span>{_h(to_label)}</span></span>{icon('calendar')}</button>
      <div class="range-backdrop" hidden></div><div id="range-panel" class="range-panel" role="dialog" aria-modal="false" aria-label="Seleccionar período" hidden>
        <div class="range-panel-header"><button class="range-month-nav" type="button" data-month-step="-1" aria-label="Mes anterior">{icon('left')}</button><strong>Seleccioná el período</strong><button class="range-month-nav" type="button" data-month-step="1" aria-label="Mes siguiente">{icon('right')}</button></div>
        <div class="range-months"></div><p class="range-message" aria-live="polite"></p><div class="range-footer"><button class="range-clear" type="button">Borrar</button><button class="primary range-apply" type="button">Aplicar período</button></div>
      </div></div>'''
    presets = []
    for label, start, end in (("Hoy", today, ""), ("Ayer", today - timedelta(days=1), ""),
                              ("Últimos 7 días", today - timedelta(days=6), today.isoformat()),
                              ("Este mes", today.replace(day=1), today.isoformat())):
        active = filters.day == start.isoformat() and filters.end_day == end
        presets.append(f'<a class="chip" aria-current="{str(active).lower()}" '
                       f'href="{_h(filters.url(date=start.isoformat(), to=end, view="day", month="", page=1))}">{label}</a>')
    chips = []
    if filters.day:
        label = nice_day(filters.day) + (" – " + nice_day(filters.end_day) if filters.end_day else "")
        chips.append(f'<a class="chip active" href="{_h(filters.url(date="", to="", view="history", page=1))}">'
                     f'{_h(label)} {icon("close")}</a>')
    if filters.relevance != "all":
        chips.append(f'<a class="chip active" href="{_h(filters.url(relevance="all", page=1))}">'
                     f'{_h(RELEVANCE[filters.relevance])} {icon("close")}</a>')
    if filters.category:
        chips.append(f'<a class="chip active" href="{_h(filters.url(category="", page=1))}">{_h(filters.category)} {icon("close")}</a>')
    if filters.text:
        chips.append(f'<a class="chip active" href="{_h(filters.url(q="", page=1))}">“{_h(filters.text)}” {icon("close")}</a>')
    filters_html = f'''<form id="filters" class="filters" method="get" action="/"><fieldset><legend class="sr-only">Filtros de publicaciones</legend>
      <input type="hidden" name="view" value="{_h(filters.view)}"><input type="hidden" name="month" value="{_h(filters.month)}">
      <div class="field period-field"><span class="field-label">Período</span><div class="date-control">{previous_control}{range_control}{next_control if filters.day and not filters.end_day else ''}</div></div>
      <div class="field"><label for="relevance">Relevancia</label><select id="relevance" name="relevance" data-auto-submit>{relevance_options}</select></div>
      <div class="field"><label for="category">Tipo de publicación</label><select id="category" name="category" data-auto-submit>{category_options}</select></div>
      <div class="field search"><label class="sr-only" for="q">Buscar</label><div class="search-wrap">{icon('search')}<input id="q" name="q" type="search" maxlength="100" value="{_h(filters.text)}" placeholder="Organismo, tipo, número o texto"><button id="clear-search" class="clear-search" type="button" aria-label="Limpiar búsqueda">{icon('close')}</button></div></div>
      <button class="primary apply" type="submit">Aplicar</button></fieldset><div class="filter-state"><div class="presets preset-inline">{''.join(presets)}</div><details class="preset-menu"><summary>{icon('right')}Fechas</summary><div class="presets">{''.join(presets)}</div></details><div class="chips filter-chips">{''.join(chips)}</div></div></form>'''

    rendered_rows = []
    ready_count = 0
    for row in rows:
        publication_id = int(row["id"])
        summary = str(row["conceptual_summary"] or "")
        selectable = bool(summary and filters.day and not filters.end_day)
        ready_count += int(selectable)
        reason = "Hace falta un resumen completo" if not summary else "Elegí un solo día para preparar el correo"
        picker = (f'<input type="checkbox" name="selected" value="{publication_id}" '
                  f'aria-label="Incluir {_h(row["title"])} en el correo"'
                  + (">" if selectable else f' disabled title="{reason}">'))
        official = _official_url(row["detail_url"])
        pdf = ("" if row["pdf_availability"] == "missing" else
               (_official_url(row["pdf_url"]) or _official_pdf_url(row["detail_url"])))
        links = []
        if official:
            links.append(f'<a href="{_h(official)}" target="_blank" rel="noopener noreferrer">Aviso en BORA {icon("external")}</a>')
        if pdf:
            pdf_label = ("PDF oficial no confirmado" if row["pdf_availability"] != "available"
                         else "PDF oficial en BORA")
            links.append(f'<a href="{_h(pdf)}" target="_blank" rel="noopener noreferrer">{pdf_label} {icon("external")}</a>')
        source_links = "".join(links)
        attribution = ("Resumen incorporado tras revisión" if row["summary_model"] == "human-reviewed"
                       else "Resumen generado por IA")
        original = (f'<a href="{_h(official)}" target="_blank" rel="noopener noreferrer">'
                    f'Ver aviso original {icon("external")}</a>') if official else ""
        full_summary = (f'<div class="summary"><span class="attribution">{attribution}</span>'
                        f'<strong>Resumen conceptual</strong><p>{_h(summary)}</p>'
                        f'<strong>Relación con EPESF</strong><p>{_h(row["epesf_relationship"])}</p>'
                        f'{original}</div>') if summary else ""
        warning = ('<p class="error-text">El aviso tiene anexos sin analizar. '
                   'El resumen puede omitir su contenido.</p>' if row["annex_status"] == "unread" else "")
        reference = (f'<p class="full-reference"><strong>Expediente</strong><br>'
                     f'<span class="code">{_h(row["reference"])}</span></p>') if row["reference"] else ""
        detail = (f'<details id="detail-{publication_id}"><summary>{icon("right")}Ver detalle</summary>'
                  f'<div class="detail-body">{full_summary}{warning}<p><strong>Tipo de publicación</strong><br>'
                  f'{_h(row["category"])}</p><strong>{_h(row["agency"])}</strong>{reference}'
                  f'<p>{_h(row["description"])}</p><strong>Motivo de clasificación</strong>'
                  f'{signals(str(row["relevance_reason"]), filters.text)}<div class="links">{source_links}</div>'
                  f'</div></details>')
        if summary:
            preview = f'<p class="preview">{_h(summary)}</p>'
        elif row["relevance"] in ("direct_epesf", "potential_sector_impact"):
            disabled = "" if summary_enabled else ' disabled title="Falta configurar Gemini"'
            label = "Reintentar resumen" if row["summary_status"] == "error" else "Generar resumen"
            preview = (f'<button class="summary-action" type="submit" form="cloud-summary" '
                       f'name="id" value="{publication_id}"{disabled}>{label}</button>')
        else:
            preview = '<span class="context">Sin resumen · revisar el aviso original</span>'
        relevance = str(row["relevance"])
        badge = "Informativa · descartada" if relevance == "not_relevant" else RELEVANCE.get(relevance, relevance)
        type_hint = ("" if category_repeats_title(str(row["category"]), str(row["title"])) else
                     f'<span class="publication-type">{_h(row["category"])}</span>')
        rendered_rows.append(f'''<li><article class="row" tabindex="0" data-id="{publication_id}" data-created="{_h(row["first_seen_at"])}"><div class="pick">{picker}</div><div class="date-type"><div class="date">{_h(row["publication_date"])}</div></div><div class="identification"><div class="agency eyebrow" title="{_h(row["agency"])}">{_h(row["agency"])}</div><h3 class="title"><a href="#detail-{publication_id}">{_h(row["title"])}</a></h3>{type_hint}<div class="code" title="{_h(row["reference"])}">{_h(row["reference"])}</div></div><div class="analysis"><span class="badge {_h(relevance)}">{_h(badge)}</span>{preview}{detail}</div><div class="links">{source_links}</div></article></li>''')

    export_url = filters.url() + "&action=export"
    if calendar_mode:
        calendar_app = SimpleNamespace(database=app._database(), latest_date=app._latest_date)
        result = '<div aria-label="Histórico">' + calendar_view(calendar_app, filters, today) + '</div>'
    else:
        if rendered_rows:
            empty = ""
        else:
            coverage = overview["coverage"]
            if filters.text or filters.category:
                title, detail = "No hay resultados para estos filtros", "Probá otra búsqueda o ampliá el período."
            elif coverage and coverage["status"] == "failed":
                title, detail = "La consulta de esta fecha falló", "Revisá la fecha en Fallas."
            elif filters.day and not coverage:
                title, detail = "Esta fecha todavía no se consultó", "La carga diaria aún no registró esta edición."
            else:
                title, detail = "No hay publicaciones para esta vista", "Elegí otro día o cambiá los filtros."
            consult = ""
            if filters.day and not filters.end_day and not filters.text and not filters.category and (not coverage or coverage["status"] == "failed"):
                disabled = "" if date.fromisoformat(filters.day) <= today else ' disabled title="Consulta no disponible"'
                label = "Reintentar consulta" if coverage else "Consultar ahora"
                consult = (f'<button type="submit" form="cloud-consult" name="date" '
                           f'value="{_h(filters.day)}"{disabled}>{label}</button>')
            empty = f'<div class="cloud-empty"><h2>{_h(title)}</h2><p>{_h(detail)}</p>{consult}</div>'
        draft_note = ("Seleccioná publicaciones con resumen de un solo día para preparar el correo."
                      if not ready_count else "El borrador se descarga sin adjuntos; verificá las fuentes en BORA.")
        result = f'''<section id="results" aria-label="Publicaciones"><div class="results-toolbar"><span class="counter" aria-live="polite">{len(rows)} de {total} {'publicación' if total == 1 else 'publicaciones'}</span><div class="results-actions"><div class="density" role="group" aria-label="Densidad de la lista"><button type="button" data-density="comfortable" aria-pressed="true">Cómoda</button><button type="button" data-density="compact" aria-pressed="false">Compacta</button></div><a id="export-view" class="export-view" href="{_h(export_url)}" title="Exportar CSV de esta página" aria-label="Exportar CSV de esta página">{icon('document')}Exportar CSV</a></div></div><form id="selection-form" class="selection-form" action="/?action=draft" method="post"><input type="hidden" name="date" value="{_h(filters.day)}"><input type="hidden" name="csrf" value="{_h(csrf)}"><div class="column-head"><div class="pick"><input id="select-all" type="checkbox" aria-label="Seleccionar todas las publicaciones disponibles en esta página"{' disabled' if not ready_count else ''}></div><div class="column-cell"><span class="column-label">FECHA</span></div><div class="column-cell"><span class="column-label">PUBLICACIÓN</span></div><div class="column-cell"><span class="column-label">ANÁLISIS</span></div><div class="column-cell"><span class="column-label">DOCUMENTOS</span></div></div><ul class="publication-list">{''.join(rendered_rows)}</ul>{empty}<div id="selection-bar" class="selection-bar" hidden><strong id="selection-count" aria-live="polite">0 seleccionadas</strong><button class="primary" type="submit" data-email disabled>Generar correo</button><button id="export-selected" type="button">Exportar CSV</button><button type="button" data-select="none">Limpiar</button></div></form><p class="cloud-source-note">{draft_note}</p></section>'''
        if total > PAGE_SIZE:
            previous_page = (f'<a href="{_h(filters.url(page=filters.page - 1))}">Anterior</a>'
                             if filters.page > 1 else "")
            next_page = (f'<a href="{_h(filters.url(page=filters.page + 1))}">Siguiente</a>'
                         if filters.page * PAGE_SIZE < total else "")
            result += f'<nav class="cloud-page-nav" aria-label="Páginas">{previous_page}<span>Página {filters.page}</span>{next_page}</nav>'

    if filters.view == "failures":
        summary_disabled = "" if summary_enabled else ' disabled title="Falta configurar Gemini"'
        with app._database().connect() as connection:
            coverage_issues = connection.execute(
                "SELECT publication_date,status,error FROM coverage WHERE source='BORA' "
                "AND status='failed' ORDER BY publication_date DESC LIMIT 100").fetchall()
            publication_issues = connection.execute("""
                SELECT id,publication_date,title,detail_url,relevance,document_status,
                       summary_status,delivery_status FROM publications
                WHERE source='BORA' AND (document_status='error'
                    OR summary_status='error' OR delivery_status IN ('error','uncertain'))
                ORDER BY publication_date DESC,title LIMIT 100
            """).fetchall()
        issue_items = "".join(
            f'<li class="cloud-issue"><strong>Cobertura · {_h(item["publication_date"])}</strong>'
            f'<p>{_h(item["error"] or "La consulta no se completó")}</p>'
            f'<button type="submit" form="cloud-consult" name="date" value="{_h(item["publication_date"])}"'
            '>Reintentar consulta</button></li>'
            for item in coverage_issues)
        for item in publication_issues:
            states = []
            if item["document_status"] == "error":
                states.append("documento")
            if item["summary_status"] == "error":
                states.append("resumen")
            if item["delivery_status"] in ("error", "uncertain"):
                states.append("entrega")
            official = _official_url(item["detail_url"])
            link = (f' <a href="{_h(official)}" target="_blank" rel="noopener noreferrer">Abrir aviso</a>'
                    if official else "")
            retry = (f'<button type="submit" form="cloud-summary" name="id" value="{item["id"]}"'
                     f'{summary_disabled}>Reintentar resumen</button>'
                     if item["summary_status"] == "error" and item["relevance"] in
                     ("direct_epesf", "potential_sector_impact") else "")
            issue_items += (f'<li class="cloud-issue"><strong>Publicación · {_h(item["title"])}</strong>'
                            f'<p>{_h(item["publication_date"])} · Revisar: {_h(", ".join(states))}.{link}</p>{retry}</li>')
        issues_html = (f'<ul class="cloud-issues">{issue_items}</ul>' if issue_items else
                       '<div class="cloud-empty"><h2>No hay fallas registradas</h2></div>')
        result = f'<section aria-label="Fallas"><h2 class="cloud-issues-title">Requiere atención</h2>{issues_html}</section>'

    shortcuts = '<span><kbd>/</kbd> Buscar</span><span><kbd>←</kbd><kbd>→</kbd> Día</span><span><kbd>j</kbd><kbd>k</kbd> Recorrer</span><span><kbd>x</kbd> Seleccionar</span><span><kbd>Enter</kbd> Detalle</span><span><kbd>Esc</kbd> Limpiar</span><span><kbd>?</kbd> Ayuda</span>'
    action_forms = (f'<form id="cloud-consult" action="/?action=consult" method="post"><input type="hidden" name="csrf" value="{_h(csrf)}"></form>'
                    f'<form id="cloud-summary" action="/?action=summary" method="post"><input type="hidden" name="csrf" value="{_h(csrf)}"></form>')
    page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{refresh}<title>Boletín Oficial EPESF</title><style>{CLOUD_CSS}</style><script src="/?action=ui" defer></script></head><body><a class="skip" href="#filters">Ir a filtros</a><main class="shell"><header class="topbar"><h1 title="Seguimiento normativo de la Primera Sección del BORA">Boletín Oficial EPESF</h1><nav class="view-nav" aria-label="Vistas">{nav}</nav>{status}<a id="help-toggle" class="help" href="#keyboard-help" aria-label="Ver atajos de teclado">?</a><div class="cloud-account"><span>{_h(user)}</span><form action="/?action=logout" method="post"><input type="hidden" name="csrf" value="{_h(csrf)}"><button type="submit">Salir</button></form></div></header><section class="metrics" aria-label="Estado general">{''.join(metrics)}</section>{job_notice}{filters_html}{result}{action_forms}<details id="keyboard-help" class="keyboard-help"><summary>{icon('right')}Atajos de teclado</summary><p class="shortcut-line">{shortcuts}</p></details><footer class="foot">Datos en Turso · Fuentes oficiales en BORA · El correo se prepara para revisión y no se envía automáticamente.</footer></main></body></html>'''
    return page.encode("utf-8")
