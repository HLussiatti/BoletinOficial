"""Isolated, synthetic preview for visual checks; never opens mail or calls BORA."""
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from epe_boletin.db import Database
from epe_boletin.models import Publication
from epe_boletin.summaries import ConceptualSummary
from epe_boletin.web import WebApplication, create_handler


def main():
    with TemporaryDirectory(prefix='epesf-visual-') as folder:
        root = Path(folder)
        database = Database(root / 'boletin.sqlite3')
        database.migrate()
        today = date.today()
        agencies = ['SECRETARÍA DE ENERGÍA', 'ENTE NACIONAL REGULADOR DE LA ELECTRICIDAD',
                    'MINISTERIO DE ECONOMÍA', 'SECRETARÍA DE ENERGÍA ELÉCTRICA']
        for index in range(10):
            relevant = index != 9
            category = 'DISPOSICIONES' if index == 8 else 'RESOLUCIONES SINTETIZADAS'
            pid = database.upsert_publication(Publication(
                source_id=str(index), publication_date=today, section='primera',
                category=category, agency=agencies[index % 4],
                title=f'{"Disposición" if index == 8 else "Resolución Sintetizada"} {611 + index}/2026',
                reference=f'RESOL-2026-{611 + index}-APN-DIRECTORIO#ENRE',
                description='Datos sintéticos para comprobar el diseño; no es una publicación oficial.',
                detail_url='https://www.boletinoficial.gob.ar/',
                relevance='direct_epesf' if index == 0 else ('potential_sector_impact' if relevant else 'not_relevant'),
                relevance_reason='Indicios sectoriales: energía eléctrica, cammesa, ENRE, MEM',
            ), relevant)
            pdf = root / f'demo-{index}.pdf'
            pdf.write_bytes(b'%PDF-1.4\n%%EOF\n')
            database.save_document(pid, pdf, str(index) * 64, pdf.stat().st_size,
                                   'https://www.boletinoficial.gob.ar/', page_count=2,
                                   extraction_status='complete', extracted_text='Texto de prueba')
        for candidate in database.summary_candidates('visual-test', 'test', 20):
            database.save_summary(candidate, ConceptualSummary(
                'Referencia sintética para verificar la lectura: se establecen disposiciones del mercado eléctrico, sus plazos de aplicación y los organismos responsables. El equipo deberá contrastar el alcance con el texto original antes de tomar una decisión.',
                'Evaluar la incidencia en EPESF con el texto original.', 'Demostración', False,
            ), 'visual-test', 'test')
        database.save_coverage(today, 'complete')
        application = WebApplication(database, root, lambda _: None)
        server = ThreadingHTTPServer(('127.0.0.1', 8871), create_handler(application))
        print('Synthetic preview: http://127.0.0.1:8871', flush=True)
        try:
            server.serve_forever()
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
