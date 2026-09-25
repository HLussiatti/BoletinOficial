from __future__ import annotations

import calendar
import re
import unicodedata
from dataclasses import replace
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlencode

from .web import Query, WebApplication, _h, _label, _timestamp
from .web_ui import CSS


def icon(name: str) -> str:
    paths = {
        'left': '<path d="m9 3-5 5 5 5"/>',
        'right': '<path d="m6 3 5 5-5 5"/>',
        'search': '<circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 3 3"/>',
        'close': '<path d="m4 4 8 8M12 4l-8 8"/>',
        'document': '<path d="M4 2h6l3 3v9H4zM10 2v4h3M6 9h5M6 11h5"/>',
        'external': '<path d="M9 2h5v5M14 2 7 9M6 3H2v11h11v-4"/>',
        'mail': '<rect x="2" y="3" width="12" height="10" rx="1"/><path d="m2 4 6 5 6-5"/>',
        'calendar': '<rect x="2" y="3" width="12" height="11" rx="1"/><path d="M5 2v3M11 2v3M2 7h12"/>',
    }
    return f'<svg class="icon" viewBox="0 0 16 16" aria-hidden="true">{paths[name]}</svg>'


def url(query: Query, **updates: object) -> str:
    values = {'date': query.day, 'to': query.end_day, 'relevance': query.relevance,
              'category': query.category, 'q': query.text, 'view': query.view,
              'month': query.month, 'page': 1}
    values.update(updates)
    return '/?' + urlencode({k: v for k, v in values.items() if v})


def nice_day(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime('%d/%m/%Y')
    except ValueError:
        return value


def relative_time(value: object) -> str:
    try:
        instant = datetime.fromisoformat(str(value)).astimezone()
        days = (date.today() - instant.date()).days
        if days in (0, 1):
            return ('hoy' if days == 0 else 'ayer') + instant.strftime(' %H:%M')
        if days > 1:
            return f'hace {days} días'
    except ValueError:
        pass
    return _timestamp(value)


def signals(reason: str, search: str) -> str:
    if ':' not in reason or not reason.casefold().startswith('indicios sectoriales'):
        return f'<p class="preview">{_h(reason)}</p>' if reason else ''
    terms = [term.strip() for term in reason.split(':', 1)[1].split(',') if term.strip()]
    chips = []
    for term in terms[:3]:
        parts = re.split('(' + re.escape(search) + ')', term, flags=re.I) if search else [term]
        highlighted = ''.join(f'<mark>{_h(part)}</mark>' if search and part.casefold() == search.casefold() else _h(part) for part in parts)
        chips.append(f'<span class="signal">{highlighted}</span>')
    if len(terms) > 3:
        chips.append(f'<span class="signal" title="{_h(", ".join(terms[3:]))}">+{len(terms)-3}</span>')
    return '<div class="chips" aria-label="Indicios sectoriales">' + ''.join(chips) + '</div>'


def category_repeats_title(category: str, title: str) -> bool:
    def words(value: str) -> list[str]:
        plain = unicodedata.normalize('NFKD', value.casefold())
        plain = ''.join(char for char in plain if not unicodedata.combining(char))
        return [word for word in re.findall(r'[a-z]+', plain) if len(word) >= 5]

    category_words = words(category)
    title_words = words(title)
    return bool(category_words) and all(
        any(title_word.startswith(category_word[:6]) for title_word in title_words)
        for category_word in category_words
    )


def calendar_view(app: WebApplication, query: Query) -> str:
    try:
        month = date.fromisoformat(query.month + '-01')
    except ValueError:
        month = date.fromisoformat((app.latest_date() or date.today().isoformat())[:7] + '-01')
    next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    prev_month = (month - timedelta(days=1)).replace(day=1)
    with app.database.connect() as connection:
        counts = {str(row['publication_date']): dict(row) for row in connection.execute("""
            SELECT publication_date,COUNT(*) total,
              SUM(relevance IN ('direct_epesf','potential_sector_impact')) relevant
            FROM publications WHERE publication_date>=? AND publication_date<? GROUP BY publication_date
        """, (month.isoformat(), next_month.isoformat()))}
        coverage = {str(row['publication_date']): str(row['status']) for row in connection.execute(
            'SELECT publication_date,status FROM coverage WHERE publication_date>=? AND publication_date<?',
            (month.isoformat(), next_month.isoformat()))}
    peak = max((r['relevant'] for r in counts.values()), default=1) or 1
    names = ('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre')
    with app.database.connect() as connection:
        first = connection.execute('SELECT MIN(publication_date) FROM (SELECT publication_date FROM publications UNION SELECT publication_date FROM coverage)').fetchone()[0]
    first_month = date.fromisoformat(str(first)[:7] + '-01') if first else month
    first_month = min(first_month, month)
    month_options = []
    cursor = max(date.today().replace(day=1), month)
    while cursor >= first_month:
        value = cursor.strftime('%Y-%m')
        selected = ' selected' if cursor == month else ''
        month_options.append(f'<option value="{value}"{selected}>{names[cursor.month-1].capitalize()} {cursor.year}</option>')
        if cursor.year == 1 and cursor.month == 1:
            break
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    month_picker = (
        '<form class="month-picker" method="get">'
        '<input type="hidden" name="view" value="history">'
        f'<input type="hidden" name="relevance" value="{_h(query.relevance)}">'
        '<label class="sr-only" for="calendar-month">Mes calendario</label>'
        '<select id="calendar-month" name="month" data-month-submit>'
        + ''.join(month_options) + '</select>'
        '<noscript><button type="submit">Ver mes</button></noscript></form>'
    )
    cells = ''.join(f'<span class="weekday">{name}</span>' for name in ('Lun','Mar','Mié','Jue','Vie','Sáb','Dom'))
    for week in calendar.monthcalendar(month.year, month.month):
        for number in week:
            if not number:
                cells += '<span aria-hidden="true"></span>'
                continue
            day = month.replace(day=number).isoformat()
            count = counts.get(day, {'total': 0, 'relevant': 0})
            state = coverage.get(day, '')
            classes = ['calendar-day']
            if count['relevant']:
                classes.append(f'volume-{min(3, max(1, (count["relevant"]*3+peak-1)//peak))}')
            if state == 'failed':
                classes.append('failed')
            if day == date.today().isoformat():
                classes.append('today')
            if not state and not count['total']:
                classes.append('unprocessed')
            label = f'{count["relevant"]} ' + ('relevante' if count['relevant']==1 else 'relevantes')
            if state == 'failed': label = 'Consulta fallida'
            elif not state and not count['total']: label = 'Sin consultar' if day <= date.today().isoformat() else 'Fecha futura'
            elif state == 'not_published': label = 'Sin edición'
            cells += f'<a class="{" ".join(classes)}" href="{_h(url(query, date=day, to="", view="day", month=""))}" aria-label="{_h(nice_day(day))}: {_h(label)}"><strong>{number}</strong><span>{_h(label)}</span><span class="calendar-total">{count["total"]} publicaciones</span></a>'
    next_link = f'<a href="{_h(url(query, month=next_month.strftime("%Y-%m")))}">Mes siguiente {icon("right")}</a>' if next_month <= date.today().replace(day=1) else '<span class="context">Mes actual</span>'
    return f'<section aria-label="Calendario histórico"><div class="calendar-nav"><a href="{_h(url(query, month=prev_month.strftime("%Y-%m")))}">{icon("left")} Mes anterior</a><div class="calendar-heading"><h2>{names[month.month-1].capitalize()} {month.year}</h2>{month_picker}</div>{next_link}</div><div class="calendar-grid">{cells}</div><p class="calendar-legend"><span>La intensidad indica el volumen de relevantes.</span><span class="error-text">Borde rojo: consulta fallida.</span><span>Sin consultar: cobertura pendiente.</span></p></section>'


def render(app: WebApplication, query: Query, raw_query: str = '') -> bytes:
    today = date.today()
    if query.history:
        query = replace(query, view='history')
    if query.view not in ('day', 'history', 'failures'):
        query = replace(query, view='day')
    for attr in ('day', 'end_day'):
        if getattr(query, attr):
            try: date.fromisoformat(getattr(query, attr))
            except ValueError: query = replace(query, **{attr: ''})
    if query.end_day and (not query.day or query.end_day < query.day):
        query = replace(query, end_day='')
    if query.end_day == query.day:
        query = replace(query, end_day='')
    if not query.day and query.view == 'day':
        query = replace(query, day=app.latest_date() or today.isoformat())
    if query.relevance not in ('active','all','selected','direct_epesf','potential_sector_impact','needs_review','not_relevant'):
        query = replace(query, relevance='active')
    rows = app.publications(query)
    categories_rows = app.publications(replace(query, relevance='all', category='', text='', view='day'))
    categories = sorted({str(row['category']) for row in categories_rows if row['category']}, key=str.casefold)
    period_rows = [row for row in categories_rows if not query.category or row['category'] == query.category]
    total = len(period_rows)
    relevant = sum(r['relevance'] in ('direct_epesf','potential_sector_impact') for r in period_rows)
    direct = sum(r['relevance'] == 'direct_epesf' for r in period_rows)
    potential = sum(r['relevance'] == 'potential_sector_impact' for r in period_rows)
    status = app.database.status()
    last = status.get('last_run') or {}
    failed = int(status.get('failed_dates') or 0)
    all_issues = app.operational_issues()
    scoped_issues = [i for i in all_issues if not query.day or (i['kind']=='Cobertura' and query.day <= i['title'] <= (query.end_day or query.day)) or (i['kind']=='Publicación' and query.day <= i.get('day','') <= (query.end_day or query.day))]
    ready_count = sum(bool(r.get('conceptual_summary')) for r in rows) if query.day and not query.end_day else 0
    day = date.fromisoformat(query.day) if query.day else today
    previous_url = url(query, date=(day-timedelta(days=1)).isoformat(), to='', view='day')
    next_url = url(query, date=(day+timedelta(days=1)).isoformat(), to='', view='day')
    options = [('active','Relevantes y sin clasificar'),('all','Todas'),('selected','Relevantes'),('direct_epesf','Impacto directo'),('potential_sector_impact','Impacto potencial'),('not_relevant','Descartadas'),('needs_review','Sin clasificar')]
    counts = {k: sum(1 for r in period_rows if k=='all' or (k=='active' and r['relevance']!='not_relevant') or (k=='selected' and r['relevance'] in ('direct_epesf','potential_sector_impact')) or r['relevance']==k) for k,_ in options}
    option_html = ''.join(f'<option value="{k}"{" selected" if k==query.relevance else ""}>{label} ({counts[k]})</option>' for k,label in options)
    category_options = '<option value="">Todos los tipos</option>' + ''.join(
        f'<option value="{_h(category)}"{" selected" if category==query.category else ""}>{_h(category)}</option>'
        for category in categories
    )
    view_label = 'Histórico desde noviembre de 2025' if query.view=='history' and not query.day else nice_day(query.day)
    if query.end_day: view_label += ' – ' + nice_day(query.end_day)
    if query.view=='failures': view_label = 'Fallas de consulta y publicaciones' + (' · '+view_label if query.day else '')
    run_label = f'{failed} fechas con falla' if failed else _label(last.get('status'))
    run_error = failed or last.get('status') in ('failed','partial')
    run_element = 'a' if run_error else 'span'
    run_href = ' href="/?view=failures&amp;relevance=all"' if run_error else ''
    run_class = ' error' if run_error else (' neutral' if last.get('status')!='complete' else '')
    run = f'<{run_element} class="run-pill{run_class}"{run_href} title="Última ejecución: {_h(_timestamp(last.get("finished_at")))}"><span class="dot" aria-hidden="true"></span>{_h(run_label)} · {_h(relative_time(last.get("finished_at")))}</{run_element}>'
    metrics = []
    for value,label,updates,active in (
        (total,'publicación' if total==1 else 'publicaciones',{'relevance':'all'},query.relevance=='all' and query.view!='failures'),
        (relevant,'relevante' if relevant==1 else 'relevantes',{'relevance':'selected'},query.relevance=='selected'),
        (direct,'impacto directo',{'relevance':'direct_epesf'},query.relevance=='direct_epesf'),
        (potential,'impacto potencial',{'relevance':'potential_sector_impact'},query.relevance=='potential_sector_impact'),
        (failed,'fecha con falla' if failed==1 else 'fechas con fallas',{'view':'failures','date':'','to':'','q':'','relevance':'all'},query.view=='failures'),
    ):
        element = 'a' if value else 'div'
        href = f' href="{_h(url(query, **updates))}"' if value else ' aria-disabled="true"'
        metrics.append(f'<{element} class="metric"{href} aria-current="{str(active).lower()}"><b>{value}</b><span>{label}</span></{element}>')
    chips = []
    if query.day: chips.append(f'<a class="chip active" href="{_h(url(query,date="",to="",view="history"))}">{_h(view_label)} {icon("close")}<span class="sr-only">Quitar fecha</span></a>')
    if query.relevance!='all': chips.append(f'<a class="chip active" href="{_h(url(query,relevance="all"))}">{dict(options)[query.relevance]} {icon("close")}<span class="sr-only">Quitar relevancia</span></a>')
    if query.category: chips.append(f'<a class="chip active" href="{_h(url(query,category=""))}">{_h(query.category)} {icon("close")}<span class="sr-only">Quitar tipo de publicación</span></a>')
    if query.text: chips.append(f'<a class="chip active" href="{_h(url(query,q=""))}">“{_h(query.text)}” {icon("close")}<span class="sr-only">Quitar búsqueda</span></a>')
    presets = []
    for label,start,end in (('Hoy',today,''),('Ayer',today-timedelta(days=1),''),('Últimos 7 días',today-timedelta(days=6),today.isoformat()),('Este mes',today.replace(day=1),today.isoformat())):
        active = query.day==start.isoformat() and query.end_day==end
        presets.append(f'<a class="chip" aria-current="{str(active).lower()}" href="{_h(url(query,date=start.isoformat(),to=end,view="day",month=""))}">{label}</a>')
    next_control = f'<a id="next-day" class="icon-button" href="{_h(next_url)}" aria-label="Día siguiente">{icon("right")}</a>' if day<today else f'<span id="next-day" class="icon-button" aria-disabled="true" aria-label="Día siguiente">{icon("right")}</span>'
    from_label = nice_day(query.day) if query.day else 'Elegir fecha'
    to_label = nice_day(query.end_day or query.day) if query.day else 'Elegir fecha'
    range_control = f'''<div class="range-picker" id="range-picker" data-max="{today}">
      <div class="period-control range-native"><div class="period-date"><label for="date">Desde</label><input id="date" name="date" type="date" value="{_h(query.day)}" max="{today}" data-auto-submit></div><div class="period-date"><label for="to">Hasta</label><input id="to" name="to" type="date" value="{_h(query.end_day or query.day)}" max="{today}" data-auto-submit></div></div>
      <button id="range-trigger" class="range-trigger" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="range-panel" aria-label="Elegir período: desde {_h(from_label)} hasta {_h(to_label)}"><span class="range-segment"><small>Desde</small><span>{_h(from_label)}</span></span><span class="range-segment"><small>Hasta</small><span>{_h(to_label)}</span></span>{icon('calendar')}</button>
      <div class="range-backdrop" hidden></div><div id="range-panel" class="range-panel" role="dialog" aria-modal="false" aria-label="Seleccionar período" hidden>
        <div class="range-panel-header"><button class="range-month-nav" type="button" data-month-step="-1" aria-label="Mes anterior">{icon('left')}</button><strong>Seleccioná el período</strong><button class="range-month-nav" type="button" data-month-step="1" aria-label="Mes siguiente">{icon('right')}</button></div>
        <div class="range-months"></div><p class="range-message" aria-live="polite"></p><div class="range-footer"><button class="range-clear" type="button">Borrar</button><button class="primary range-apply" type="button">Aplicar período</button></div>
      </div></div>'''
    filter_form = f'''<form id="filters" class="filters" method="get"><fieldset><legend class="sr-only">Filtros de publicaciones</legend>
      <input type="hidden" name="month" value="{_h(query.month)}"><input type="hidden" name="view" value="{_h(query.view)}">
      <div class="field period-field"><span class="field-label">Período</span><div class="date-control">{'' if query.end_day else f'<a id="previous-day" class="icon-button" href="{_h(previous_url)}" aria-label="Día anterior">{icon("left")}</a>'}{range_control}{'' if query.end_day else next_control}</div></div>
      <div class="field"><label for="relevance">Relevancia</label><select id="relevance" name="relevance" data-auto-submit>{option_html}</select></div>
      <div class="field"><label for="category">Tipo de publicación</label><select id="category" name="category" data-auto-submit>{category_options}</select></div>
      <div class="field search"><label class="sr-only" for="q">Buscar</label><div class="search-wrap">{icon('search')}<input id="q" name="q" type="search" value="{_h(query.text)}" placeholder="Organismo, tipo, número o texto"><button id="clear-search" class="clear-search" type="button" aria-label="Limpiar búsqueda">{icon('close')}</button></div></div>
      <button class="primary apply" type="submit">Aplicar</button></fieldset><div class="filter-state"><div class="presets preset-inline">{''.join(presets)}</div><details class="preset-menu"><summary>{icon('right')}Fechas</summary><div class="presets">{''.join(presets)}</div></details><div class="chips filter-chips">{''.join(chips)}</div></div></form>'''
    is_calendar = query.view=='history' and not query.text and not query.day and not query.category and query.relevance=='active'
    page_number = min(query.page, max(1, (len(rows)+99)//100))
    displayed_rows = [] if is_calendar else (rows[(page_number-1)*100:page_number*100] if query.view=='history' else rows)
    rendered_rows = []
    for row in displayed_rows:
        pid = int(row['id'])
        summary = row.get('conceptual_summary')
        docs = row['documents']
        primary = next((d for d in docs if d['kind']=='main'), None)
        doc_links = []
        for d in docs:
            if not app.document(int(d['id'])):
                doc_links.append('<span class="error-text">Documento no disponible</span>')
                continue
            doc_links.append(f'<a href="/document/{d["id"]}" target="_blank" rel="noopener">{icon("document")}<span>{"PDF principal" if d["kind"]=="main" else "Anexo"} · <span class="pages">{d["page_count"] or "?"} pág.</span></span></a>')
        bora = f'<a href="{_h(row["detail_url"])}" target="_blank" rel="noopener">Aviso en BORA {icon("external")}</a>' if row['detail_url'] else ''
        pdf_state = row.get('official_pdf_availability')
        pdf_label = {'available': 'PDF oficial en BORA',
                     'missing': 'PDF oficial no disponible',
                     'unknown': 'PDF oficial · disponibilidad sin confirmar'}.get(pdf_state, '')
        pdf_link = (f'<a href="{_h(row["official_pdf_url"])}" target="_blank" rel="noopener">'
                    f'{_h(pdf_label)} {icon("external")}</a>') if row.get('official_pdf_url') else ''
        annex_warning = ('<p class="error-text">El aviso tiene anexos sin analizar. '
                         'El resumen puede omitir contenido del anexo.</p>'
                         if row.get('annex_status') == 'unread' else '')
        shown_docs = ''.join(doc_links[:2]) + bora + pdf_link
        if len(doc_links)>2: shown_docs += '<details><summary>'+icon('right')+f'{len(doc_links)-2} documentos más</summary><div class="links">'+''.join(doc_links[2:])+'</div></details>'
        selectable = bool(summary and query.day and not query.end_day)
        disabled_reason = 'Hace falta un resumen completo' if not summary else 'Elegí un solo día para preparar el correo'
        picker = f'<input type="checkbox" name="selected" value="{pid}" aria-label="Incluir {_h(row["title"])} en el correo"'+('>' if selectable else f' disabled title="{disabled_reason}">')
        original = f'<a href="/document/{primary["id"]}" target="_blank" rel="noopener">Ver texto original {icon("external")}</a>' if primary and app.document(int(primary['id'])) else bora
        attribution = 'Resumen incorporado tras revisión' if row.get('summary_model')=='human-reviewed' else 'Resumen generado por IA'
        full_summary = f'<div class="summary"><span class="attribution">{attribution}</span><strong>Resumen conceptual</strong><p>{_h(summary)}</p><strong>Relación con EPESF</strong><p>{_h(row.get("epesf_relationship"))}</p>{original}</div>' if summary else ''
        reference_detail = f'<p class="full-reference"><strong>Expediente</strong><br><span class="code">{_h(row["reference"])}</span></p>' if row['reference'] else ''
        reason_detail = signals(str(row['relevance_reason']), query.text)
        detail = f'<details id="detail-{pid}"><summary>{icon("right")}Ver detalle</summary><div class="detail-body">{full_summary}{annex_warning}<p><strong>Tipo de publicación</strong><br>{_h(row["category"])}</p><strong>{_h(row["agency"])}</strong>{reference_detail}<p>{_h(row["description"])}</p><strong>Motivo de clasificación</strong>{reason_detail}<div class="links">{"".join(doc_links)}{bora}{pdf_link}</div></div></details>'
        if summary:
            summary_action = f'<p class="preview">{_h(summary)}</p>'
        elif row['relevance'] in ('direct_epesf','potential_sector_impact'):
            summary_action = ('<p class="error-text">El resumen no está disponible</p>' if row['summary_status']=='error' else '') + f'<button class="summary-action" type="button" data-action="summary" data-id="{pid}">{"Reintentar resumen" if row["summary_status"]=="error" else "Generar resumen"}</button>'
        else:
            summary_action = '<span class="context">Sin resumen · revisar el aviso original</span>'
        type_hint = '' if category_repeats_title(str(row['category']), str(row['title'])) else f'<span class="publication-type">{_h(row["category"])}</span>'
        rendered_rows.append(f'''<li><article class="row" tabindex="0" data-id="{pid}" data-created="{_h(row.get('first_seen_at'))}"><div class="pick">{picker}</div><div class="date-type"><div class="date">{_h(row['publication_date'])}</div></div><div class="identification"><div class="agency eyebrow" title="{_h(row['agency'])}">{_h(row['agency'])}</div><h3 class="title"><a href="#detail-{pid}">{_h(row['title'])}</a></h3>{type_hint}<div class="code" title="{_h(row['reference'])}">{_h(row['reference'])}</div></div><div class="analysis"><span class="badge {_h(row['relevance'])}">{'Informativa · descartada' if row['relevance']=='not_relevant' else _h(_label(row['relevance']))}</span>{summary_action}{detail}</div><div class="links">{shown_docs}</div></article></li>''')
    empty = ''
    if not rows:
        with app.database.connect() as connection:
            coverage = connection.execute('SELECT status,error FROM coverage WHERE publication_date=?',(query.day,)).fetchone()
        if query.text:
            title, explanation, action = f'Sin resultados para “{query.text}”', 'Probá otro término o ampliá la búsqueda a todas las fechas.', f'<a href="{_h(url(query,date="",to="",view="history"))}">Buscar en todo el histórico</a>'
        elif total:
            title, explanation, action = 'Ninguna publicación coincide con los filtros', 'Quitá los filtros activos para revisar todas las publicaciones del período.', f'<a href="{_h(url(query,relevance="all",category="",q=""))}">Limpiar filtros</a>'
        elif query.day and coverage and coverage['status']=='failed':
            title, explanation, action = f'No se pudo leer el BORA del {nice_day(query.day)}', 'La consulta falló. Podés intentar nuevamente.', f'<button type="button" data-action="consult" data-day="{_h(query.day)}">Reintentar</button><details><summary>{icon("right")}Detalle técnico</summary><p>{_h(coverage["error"])}</p></details>'
        elif query.day and not coverage:
            title, explanation, action = 'Esta fecha todavía no se consultó', 'Consultá la edición para registrar su cobertura y publicaciones.', f'<button type="button" data-action="consult" data-day="{_h(query.day)}"'+(' disabled title="La fecha no puede ser futura"' if day>today else '')+'>Consultar ahora</button>'
        else:
            title, explanation, action = f'No hubo publicaciones el {nice_day(query.day)}', 'No se registraron publicaciones para esta fecha.', f'<a href="{_h(previous_url)}">Ver día anterior</a>'
        empty = f'<div class="empty"><h3>{_h(title)}</h3><p>{_h(explanation)}</p>{action}</div>'
    hidden = ''.join(f'<input type="hidden" name="{_h(k)}" value="{_h(v)}">' for k,v in {'date':query.day,'to':query.end_day,'q':query.text,'relevance':query.relevance,'category':query.category,'view':query.view}.items())
    export_url = '/export.csv' + url(query)[1:]
    result = f'''<section id="results" aria-label="Publicaciones" aria-busy="false"><div class="results-toolbar"><span class="counter" aria-live="polite">{len(rows)} de {total} {'publicación' if total==1 else 'publicaciones'}</span><div class="results-actions"><div class="density" role="group" aria-label="Densidad de la lista"><button type="button" data-density="comfortable" aria-pressed="true">Cómoda</button><button type="button" data-density="compact" aria-pressed="false">Compacta</button></div><a id="export-view" class="export-view" href="{_h(export_url)}" aria-label="Exportar CSV de la vista ({len(rows)})">{icon('document')}Exportar CSV</a></div></div><form id="selection-form" class="selection-form" action="/prepare-email" method="post">{hidden}<div class="column-head"><div class="pick"><input id="select-all" type="checkbox" aria-label="Seleccionar todas las publicaciones disponibles en esta página" title="Seleccionar las publicaciones con resumen de esta página"{' disabled' if not ready_count else ''}></div><div class="column-cell"><span class="column-label">FECHA</span></div><div class="column-cell"><span class="column-label">PUBLICACIÓN</span></div><div class="column-cell"><span class="column-label" title="Ordenadas por incidencia estimada en EPESF dentro de cada fecha.">ANÁLISIS</span></div><div class="column-cell"><span class="column-label">DOCUMENTOS</span></div></div><ul class="publication-list">{''.join(rendered_rows)}</ul>{empty}<div id="selection-bar" class="selection-bar" hidden><strong id="selection-count" aria-live="polite">0 seleccionadas</strong><button class="primary" type="submit" data-email disabled>Generar correo</button><button id="export-selected" type="button">Exportar CSV</button><button type="button" data-select="none">Limpiar</button></div></form></section>'''
    if query.view=='history' and len(rows)>100 and not is_calendar:
        pagination = f'<p class="calendar-nav">Página {page_number} de {(len(rows)+99)//100} · 100 publicaciones por página'
        if page_number>1: pagination += f'<a href="{_h(url(query,page=page_number-1))}">Anterior</a>'
        if page_number*100<len(rows): pagination += f'<a href="{_h(url(query,page=page_number+1))}">Siguiente</a>'
        result += pagination + '</p>'
    if is_calendar:
        result = '<div aria-label="Histórico desde noviembre de 2025">' + calendar_view(app,query) + '</div>'
    if query.view=='failures':
        issues = scoped_issues
        issue_html = []
        for issue in issues:
            issue_day = issue['title'] if issue['kind']=='Cobertura' else issue.get('day', '')
            button = f'<button type="button" data-action="consult" data-day="{_h(issue_day)}">Reintentar consulta</button>' if issue_day else ''
            if issue.get('id') and 'resumen' in issue['detail']:
                button += f'<button type="button" data-action="summary" data-id="{_h(issue["id"])}">Reintentar resumen</button>'
            link = f'<a href="{_h(issue["url"])}" target="_blank" rel="noopener">Abrir aviso {icon("external")}</a>' if issue.get('url') else ''
            issue_html.append(f'<li class="issue"><strong>{_h(issue["kind"])} · {_h(issue["title"])}</strong><details><summary>{icon("right")}Detalle de la falla</summary><p>{_h(issue["detail"])}</p></details><div class="actions">{button}{link}</div></li>')
        issue_content = '<ul class="issue-list">'+''.join(issue_html)+'</ul>' if issues else '<div class="empty"><h3>No hay fallas pendientes</h3><p>Las consultas y publicaciones no tienen errores registrados para esta vista.</p><a href="/?view=day">Volver al día</a></div>'
        result = f'<section><div class="result-head"><h2>Requiere atención</h2><span class="counter">{len(issues)} incidencias</span></div>{issue_content}</section>' + (result if rows else '')
    notice = ''
    if query.email_status=='prepared' and query.email_error:
        email_links = []
        for name in dict.fromkeys(query.email_names):
            path = app.email_file(name)
            if not path:
                continue
            download = '/email?' + urlencode({'name': name})
            fields = {'date': query.day, 'view': query.view, 'relevance': query.relevance,
                      'category': query.category, 'q': query.text,
                      'items': query.email_items, 'eml': name}
            reopen_hidden = ''.join(f'<input type="hidden" name="{key}" value="{_h(value)}">' for key,value in fields.items())
            email_links.append(f'<div class="email-file"><a href="{_h(download)}" download>Descargar {_h(name)}</a><form class="email-open-form" action="/open-email" method="post">{reopen_hidden}<button type="submit">Volver a abrir</button></form><span class="email-open-feedback" role="status" aria-live="polite"></span></div>')
        warning = f'<p role="alert">{_h(query.email_error)}</p>' if query.email_error else ''
        notice = f'<div class="notice error email-notice" role="alert"><strong>El correo quedó guardado, pero no se pudo abrir.</strong>{warning}{"".join(email_links)}</div>'
    elif query.email_error:
        notice = f'<div class="notice error" role="alert">{_h(query.email_error)}</div>'
    done = parse_qs(raw_query).get('action_done',[''])[0]
    if done in ('summary','consult'):
        notice += f'<div class="notice" role="status">{"Resumen generado. Ya podés revisarlo y seleccionarlo." if done=="summary" else "Consulta finalizada. Revisá las publicaciones y el estado de cobertura."}</div>'
    nav = ''.join(f'<a href="{_h(url(query,view=view,date=query.day if view=="day" else "",to="",q="",category="",month="",relevance="active"))}"'+(' aria-current="page"' if query.view==view else '')+f'>{label}</a>' for view,label in [('day','Día'),('history','Histórico'),('failures','Fallas')])
    shortcuts = '<span><kbd>/</kbd> Buscar</span><span><kbd>←</kbd><kbd>→</kbd> Día</span><span><kbd>j</kbd><kbd>k</kbd> Recorrer</span><span><kbd>x</kbd> Seleccionar</span><span><kbd>Enter</kbd> Detalle</span><span><kbd>Esc</kbd> Limpiar</span><span><kbd>?</kbd> Ayuda</span><span class="shortcut-note">No se activan mientras escribís.</span>'
    html = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Boletín Oficial EPESF</title><style>{CSS}</style><script src="/ui.js" defer></script></head><body><div id="progress" aria-hidden="true"></div><a class="skip" href="#filters">Ir a filtros</a><main class="shell"><header class="topbar"><h1 title="Seguimiento normativo de la Primera Sección del BORA">Boletín Oficial EPESF</h1><nav class="view-nav" aria-label="Vistas">{nav}</nav>{run}<a id="help-toggle" class="help" href="#keyboard-help" aria-label="Ver atajos de teclado">?</a></header><section class="metrics" aria-label="Estado general">{''.join(metrics)}</section>{notice}<div id="action-notice" class="notice error" role="alert" hidden></div>{filter_form}{result}<details id="keyboard-help" class="keyboard-help"><summary>{icon('right')}Atajos de teclado</summary><p class="shortcut-line">{shortcuts}</p></details><noscript><p class="notice">Usá Aplicar para actualizar la vista. La selección y el correo funcionan; los atajos y las consultas requieren JavaScript.</p><p><button type="submit" form="selection-form">Generar correo con seleccionadas</button></p></noscript><footer class="foot">Servicio local · Los datos y documentos permanecen en este equipo.</footer></main></body></html>'''
    return html.encode('utf-8')
