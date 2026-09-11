from __future__ import annotations

import json
import unittest

from epe_boletin.summaries import OpenAISummarizer, SummaryCandidate


class SummaryTest(unittest.TestCase):
    def test_openai_response_is_requested_as_non_stored_structured_output(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                result = {
                    "conceptual_summary": "Establece un nuevo régimen.",
                    "epesf_relationship": "Puede alcanzar a la distribuidora.",
                    "effective_date": "Desde su publicación.",
                    "needs_review": True,
                }
                return {
                    "output": [{
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }],
                    "usage": {"input_tokens": 120, "output_tokens": 40},
                }

        class Session:
            def __init__(self):
                self.request = None

            def post(self, url, **kwargs):
                self.request = (url, kwargs)
                return Response()

        candidate = SummaryCandidate(
            publication_id=1, source_id="10", title="Resolución 10/2026",
            agency="Secretaría de Energía", publication_date="2026-09-11",
            relevance="potential_sector_impact", relevance_reason="sectorial",
            detail_url="https://example.test/10", full_text="Texto completo",
            source_sha256="a" * 64,
        )
        session = Session()
        result = OpenAISummarizer("secret", "configured-model", session).summarize(
            candidate
        )
        _, request = session.request
        self.assertFalse(request["json"]["store"])
        self.assertEqual(
            "json_schema", request["json"]["text"]["format"]["type"]
        )
        self.assertEqual("Bearer secret", request["headers"]["Authorization"])
        self.assertEqual(120, result.input_tokens)
        self.assertTrue(result.needs_review)


if __name__ == "__main__":
    unittest.main()
