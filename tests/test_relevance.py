from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from epe_boletin.models import Publication
from epe_boletin.relevance import classify, load_rules


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


if __name__ == "__main__":
    unittest.main()
