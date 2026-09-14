from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.models import Publication
from epe_boletin.relevance import DEFAULT_RULES, classify, load_rules


class RelevanceRulesTest(unittest.TestCase):
    def test_rules_are_loaded_and_applied_with_their_version(self):
        payload = {
            "version": "test-2",
            "direct_terms": ["empresa santafesina de prueba"],
            "strong_sector_terms": ["red provincial singular"],
            "electric_terms": ["electricidad"],
            "activity_terms": ["distribución"],
            "local_terms": ["santa fe"],
            "discard_nonlocal_official_notices": True,
        }
        item = Publication(
            source_id="20", publication_date=date(2026, 9, 11), section="primera",
            category="RESOLUCIONES", agency="ORGANISMO DE PRUEBA",
            title="Resolución 20/2026", reference="RESOL-2026-20",
            description="Regula la red provincial singular.",
            detail_url="https://example.test/20",
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            rules = load_rules(path)
        self.assertEqual("test-2", rules.version)
        self.assertEqual("potential_sector_impact", classify(item, rules=rules)[0])

    def test_rules_require_an_explicit_version(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "versión"):
                load_rules(path)

    def test_historical_energy_metadata_is_selected_before_pdf_download(self):
        cases = (
            ("SUBSIDIOS ENERGÉTICOS FOCALIZADOS", "Decreto 943/2025", "Disposiciones."),
            (
                "MINISTERIO DE ECONOMÍA - SUBSECRETARÍA DE TRANSICIÓN Y "
                "PLANEAMIENTO ENERGÉTICO",
                "Disposición 3/2026", "DI-2026-3-APN-SSTYPE#MEC",
            ),
            (
                "PODER EJECUTIVO", "Decreto 585/2026",
                "Prorrógase la emergencia del Sector Energético Nacional.",
            ),
        )
        for index, (agency, title, description) in enumerate(cases, start=1):
            with self.subTest(title=title):
                item = Publication(
                    source_id=str(index), publication_date=date(2026, 9, 14),
                    section="primera", category="NORMATIVA", agency=agency,
                    title=title, reference="", description=description,
                    detail_url=f"https://example.test/{index}",
                )
                self.assertEqual(
                    "potential_sector_impact",
                    classify(item, rules=DEFAULT_RULES)[0],
                )


if __name__ == "__main__":
    unittest.main()
