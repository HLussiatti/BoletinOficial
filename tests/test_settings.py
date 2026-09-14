from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from epe_boletin.settings import load_operation_settings, readiness_issues


class SettingsTest(unittest.TestCase):
    def test_example_reports_the_missing_operational_definitions(self):
        path = Path(__file__).resolve().parents[1] / "config" / "operation.example.json"
        settings = load_operation_settings(path)
        issues = readiness_issues(settings, {})
        self.assertIn("Falta definir notification_start_date", issues)
        self.assertNotIn("Falta definir summary.model", issues)
        self.assertEqual("gpt-5.6-terra", settings.summary.model)

    def test_complete_configuration_is_ready_without_exposing_secrets(self):
        payload = {
            "notification_start_date": "2026-09-12",
            "summary": {"model": "configured-model", "api_key_env": "SUMMARY_KEY"},
            "email": {"max_mb": 20},
            "schedule_time": "05:30",
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "operation.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            settings = load_operation_settings(path)
        self.assertEqual([], readiness_issues(
            settings, {"SUMMARY_KEY": "secret"}
        ))


if __name__ == "__main__":
    unittest.main()
