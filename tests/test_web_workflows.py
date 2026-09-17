from __future__ import annotations

import csv
import io
import json
import tempfile
import threading
import unittest
from email import policy
from email.parser import BytesParser
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from epe_boletin.db import Database
from epe_boletin.models import Publication
from epe_boletin.summaries import ConceptualSummary
from epe_boletin.web import Query, WebApplication, create_handler, render_page, open_eml


class WebWorkflowsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = Database(self.folder / 'boletin.sqlite3')
        self.db.migrate()
        self.app = WebApplication(self.db, self.folder, lambda _: None)
        self.ids = []
        for source, day, relevance in (
            ('1', date(2026, 9, 10), 'direct_epesf'),
            ('2', date(2026, 9, 11), 'potential_sector_impact'),
            ('3', date(2026, 9, 11), 'not_relevant'),
        ):
            self.ids.append(self.db.upsert_publication(Publication(
                source_id=source, publication_date=day, section='primera',
                category='RESOLUCIONES', agency='SECRETARÍA DE ENERGÍA',
                title=f'Resolución {source}/2026', reference=f'RESOL-{source}',
                description='Texto <script>no ejecutable</script>',
                detail_url=f'https://example.test/{source}', relevance=relevance,
                relevance_reason='Indicios sectoriales: energía, cammesa, ENRE, MEM',
            ), relevance != 'not_relevant'))
        self.pdf = self.folder / 'main.pdf'
        self.pdf.write_bytes(b'%PDF-1.4\n%%EOF\n')
        self.db.save_document(self.ids[0], self.pdf, 'a'*64, self.pdf.stat().st_size,
                              'https://example.test/1', page_count=2,
                              extraction_status='complete', extracted_text='Texto eléctrico')

    def start_server(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), create_handler(self.app))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f'http://127.0.0.1:{server.server_port}'

    def test_range_relevance_and_removed_document_filter(self):
        query = Query.from_url('date=2026-09-10&to=2026-09-11&relevance=selected')
        self.assertEqual({'1','2'}, {r['source_id'] for r in self.app.publications(query)})
        legacy_link = Query.from_url('date=2026-09-10&to=2026-09-11&relevance=all&documents=1')
        self.assertEqual({'1','2','3'}, {r['source_id'] for r in self.app.publications(legacy_link)})
        with self.assertRaisesRegex(ValueError, 'un solo día'):
            self.app.prepare_email(query)

    def test_fluid_header_filters_metrics_and_result_actions(self):
        page = BeautifulSoup(render_page(self.app, Query(day='2026-09-10')), 'html.parser')
        self.assertIn('Boletín Oficial EPESF', page.select_one('.topbar h1').get_text())
        self.assertTrue(page.select_one('.topbar .view-nav'))
        self.assertTrue(page.select_one('.topbar .run-pill'))
        self.assertFalse(page.select('#results h2'))
        self.assertTrue(page.select_one('.filter-state .presets'))
        self.assertTrue(page.select_one('.filter-state .filter-chips'))
        self.assertEqual('1 de 1 publicación', page.select_one('.results-toolbar .counter').get_text())
        self.assertEqual(5, len(page.select('.metric')))
        self.assertIn('1relevante', page.select('.metric')[1].get_text())
        self.assertIn('1impacto directo', page.select('.metric')[2].get_text())
        self.assertFalse(any('con documento' in metric.get_text().lower() for metric in page.select('.metric')))
        self.assertTrue(page.select_one('.column-head #select-all'))
        self.assertTrue(page.select_one('.results-toolbar #export-view'))
        self.assertTrue(page.select_one('.results-toolbar [data-density]'))
        self.assertFalse(page.select_one('.column-head #export-view'))
        self.assertFalse(page.select_one('.column-head').has_attr('aria-hidden'))
        self.assertEqual('RESOL-1', page.select_one('.identification .code')['title'])
        self.assertEqual('RESOL-1', page.select_one('.full-reference .code').get_text())
        self.assertFalse(page.select_one('.date-type .type'))
        self.assertFalse(page.select_one('.identification .publication-type'))
        for control in ('date', 'to', 'relevance', 'category'):
            self.assertTrue(page.select_one(f'label[for="{control}"]'))
        self.assertIn('sr-only', page.select_one('label[for="q"]')['class'])
        self.assertEqual('2026-09-10', page.select_one('#filters #to')['value'])
        self.assertEqual(1, len(page.select('#range-trigger')))
        self.assertEqual('dialog', page.select_one('#range-trigger')['aria-haspopup'])
        self.assertTrue(page.select_one('#range-picker .range-native #date'))
        self.assertTrue(page.select_one('#range-picker .range-native #to'))
        self.assertTrue(page.select_one('#range-panel').has_attr('hidden'))

    def test_range_picker_shows_both_dates_in_one_control(self):
        page = BeautifulSoup(render_page(self.app, Query(day='2026-09-10', end_day='2026-09-11')), 'html.parser')
        self.assertEqual('2026-09-11', page.select_one('#filters #to')['value'])
        self.assertIn('10/09/2026', page.select_one('#range-trigger').get_text())
        self.assertIn('11/09/2026', page.select_one('#range-trigger').get_text())
        self.assertEqual(1, len(page.select('.range-trigger')))
        self.assertTrue(page.select_one('#select-all').has_attr('disabled'))

    def test_equal_dates_are_a_single_day_and_category_filters(self):
        query = Query.from_url('date=2026-09-10&to=2026-09-10&category=RESOLUCIONES')
        self.assertEqual('', query.end_day)
        self.assertEqual(['1'], [row['source_id'] for row in self.app.publications(query)])
        other = self.db.upsert_publication(Publication(
            source_id='other', publication_date=date(2026, 9, 10), section='primera',
            category='AVISOS', agency='ORGANISMO DE PRUEBA', title='Documento 4/2026',
            reference='AV-4', description='Prueba', detail_url='https://example.test/4',
            relevance='not_relevant', relevance_reason='Sin incidencia',
        ), False)
        self.assertGreater(other, 0)
        page = BeautifulSoup(render_page(self.app, Query(day='2026-09-10', relevance='all')), 'html.parser')
        self.assertEqual({'AVISOS', 'RESOLUCIONES'}, {option['value'] for option in page.select('#category option') if option['value']})
        self.assertEqual('AVISOS', page.select_one('.publication-type').get_text())
        filtered = BeautifulSoup(render_page(self.app, Query(day='2026-09-10', relevance='all', category='AVISOS')), 'html.parser')
        self.assertEqual(1, len(filtered.select('.row')))
        self.assertIn('category=AVISOS', filtered.select_one('#export-view')['href'])

    def test_latest_coverage_includes_days_without_publications(self):
        self.db.save_coverage(date(2026,9,14),'not_published')
        self.assertEqual('2026-09-14',self.app.latest_date())
        page = BeautifulSoup(render_page(self.app,Query()),'html.parser')
        self.assertEqual('2026-09-14',page.select_one('#date')['value'])
        self.assertIn('No hubo publicaciones el 14/09/2026',page.get_text())

    def test_calendar_failed_day_search_and_missing_document(self):
        self.db.save_coverage(date(2026,9,12),'failed',error='Fuente temporalmente caída')
        page = BeautifulSoup(render_page(self.app,Query(history=True,month='2026-09')),'html.parser')
        self.assertIn('12/09/2026',page.select_one('.calendar-day.failed')['aria-label'])
        self.assertTrue(page.select('.calendar-day.volume-3'))
        search_page = BeautifulSoup(render_page(self.app,Query(history=True,text='1/2026')),'html.parser')
        self.assertEqual(1,len(search_page.select('.row')))
        self.assertFalse(search_page.select('.calendar-grid'))
        self.pdf.unlink()
        page = BeautifulSoup(render_page(self.app,Query(day='2026-09-10')),'html.parser')
        self.assertIn('Documento no disponible',page.get_text())
        self.assertFalse(page.select('a[href^="/document/"]'))
        self.assertFalse(page.select('script:not([src])'))

    def test_export_only_explicit_visible_selection(self):
        base = self.start_server()
        with urlopen(base+f'/export.csv?date=2026-09-11&relevance=all&selected={self.ids[1]}&selected={self.ids[0]}') as response:
            rows = list(csv.DictReader(io.StringIO(response.read().decode('utf-8-sig'))))
        self.assertEqual(['Resolución 2/2026'],[r['title'] for r in rows])

    def test_action_dispatch_error_recovery_and_origin_protection(self):
        base = self.start_server()
        with patch.object(self.app,'generate_summary') as generate:
            request = Request(base+'/summary',data=f'id={self.ids[0]}'.encode(),headers={'Origin':base})
            with urlopen(request) as response:
                self.assertEqual('complete',json.load(response)['status'])
            generate.assert_called_once_with(self.ids[0])
        with patch.object(self.app,'consult_day',side_effect=ValueError('La fecha no puede ser futura')):
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base+'/consult',data=b'date=2099-01-01',headers={'Origin':base}))
            self.assertEqual(400,error.exception.code)
            self.assertIn('futura',json.load(error.exception)['error'])
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(base+'/consult',data=b'date=2026-09-11',headers={'Origin':'https://example.test'}))
        self.assertEqual(403,error.exception.code)
        self.assertFalse(self.app.action_lock.locked())

    def test_summary_without_key_gives_actionable_message(self):
        with patch.dict('os.environ',{'GEMINI_API_KEY':'','EPE_SUMMARY_PROVIDER':'gemini'}):
            with self.assertRaisesRegex(ValueError,'Falta configurar la clave'):
                self.app.generate_summary(self.ids[0])

    def test_generated_email_opens_automatically_without_blocking_response(self):
        candidate = self.db.summary_candidates('test', 'test', 1)[0]
        self.db.save_summary(candidate, ConceptualSummary('Resumen', 'Incidencia directa', 'Publicación', False), 'test', 'test')
        base = self.start_server()
        entered, release = threading.Event(), threading.Event()
        def blocked_open(path):
            entered.set()
            release.wait(3)
            raise OSError('No hay aplicación predeterminada')
        with patch.object(self.app, 'email_opener', side_effect=blocked_open) as opener:
            with urlopen(Request(base+'/prepare-email', data=urlencode({'date':'2026-09-10','selected':self.ids[0]}).encode(), headers={'Origin':base,'Accept':'application/json'}), timeout=2) as response:
                self.assertEqual(200,response.status)
                result=json.load(response)
            self.assertTrue(result['generated'])
            self.assertTrue(entered.wait(1))
            token=result['token']
            with urlopen(base+'/email-open-status?token='+token) as response:
                self.assertEqual('pending',json.load(response)['status'])
            with urlopen(base+result['files'][0]['url']) as response:
                self.assertIn('attachment;',response.headers['Content-Disposition'])
                message=BytesParser(policy=policy.default).parsebytes(response.read())
            self.assertEqual(1,len(list(message.iter_attachments())))
            self.assertIsNone(message['To'])
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base+'/open-email',data=urlencode({'eml':result['files'][0]['name']}).encode(),headers={'Origin':base}))
            self.assertEqual(400,error.exception.code)
            release.set()
            for _ in range(20):
                with urlopen(base+'/email-open-status?token='+token) as response:
                    state=json.load(response)
                if state['status'] != 'pending':
                    break
                threading.Event().wait(.01)
            self.assertEqual('error',state['status'])
            self.assertIn('No hay aplicación predeterminada',state['error'])
            opener.assert_called_once_with((self.folder/'outbox'/'boletin_2026_09_10.eml').resolve())
        page=BeautifulSoup(render_page(self.app,Query(day='2026-09-10',email_status='prepared')),'html.parser')
        self.assertFalse(page.select('.email-notice'))
        self.assertNotIn('Elegir aplicación para abrir',page.get_text())
        error_page=BeautifulSoup(render_page(self.app,Query(day='2026-09-10',email_status='prepared',email_error='No hay aplicación predeterminada',email_names=(result['files'][0]['name'],))),'html.parser')
        self.assertTrue(error_page.select('.email-notice.error a[download]'))
        for name in ('../main.pdf','main.eml','C:\\secret.eml'):
            with self.assertRaises(HTTPError) as error:
                urlopen(base+'/email?'+urlencode({'name':name}))
            self.assertEqual(404,error.exception.code)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(base+'/open-email',data=urlencode({'eml':result['files'][0]['name']}).encode(),headers={'Origin':'https://example.test'}))
        self.assertEqual(403,error.exception.code)

    def test_generation_failure_does_not_request_opening(self):
        base=self.start_server()
        with patch.object(self.app,'email_opener') as opener:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base+'/prepare-email',data=b'date=2026-09-10',headers={'Origin':base,'Accept':'application/json'}))
            self.assertEqual(400,error.exception.code)
            result=json.load(error.exception)
            self.assertFalse(result['generated'])
            self.assertIn('Seleccioná',result['error'])
            opener.assert_not_called()

    def test_windows_uses_default_application(self):
        with patch('epe_boletin.web.os.name','nt'),patch('epe_boletin.web.os.startfile') as startfile:
            open_eml(self.pdf)
            startfile.assert_called_once_with(str(self.pdf.resolve()),'open')


if __name__ == '__main__':
    unittest.main()
