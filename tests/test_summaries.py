from __future__ import annotations

import json
import unittest

from epe_boletin.summaries import GeminiSummarizer, OpenAISummarizer, SummaryCandidate


class SummaryTest(unittest.TestCase):
    @staticmethod
    def candidate():
        return SummaryCandidate(
            publication_id=1, source_id="10", title="Resolución 10/2026",
            agency="Secretaría de Energía", publication_date="2026-09-11",
            relevance="potential_sector_impact", relevance_reason="sectorial",
            detail_url="https://example.test/10", full_text="Texto completo",
            source_sha256="a" * 64,
        )

    def test_openai_response_is_requested_as_non_stored_structured_output(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                result = {
                    "conceptual_summary": "Establece un nuevo régimen.",
                    "epesf_relationship": "Puede alcanzar a la distribuidora.",
                    "effective_date": "Desde su publicación.",
                    "needs_review": False,
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

        session = Session()
        result = OpenAISummarizer("secret", "configured-model", session).summarize(
            self.candidate()
        )
        _, request = session.request
        self.assertFalse(request["json"]["store"])
        self.assertEqual(
            "json_schema", request["json"]["text"]["format"]["type"]
        )
        self.assertEqual("Bearer secret", request["headers"]["Authorization"])
        self.assertEqual(120, result.input_tokens)
        self.assertTrue(result.needs_review)

    def test_gemini_uses_interactions_structured_output_and_retries(self):
        class Response:
            def __init__(self, status_code, payload=None):
                self.status_code = status_code
                self.payload = payload or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    import requests
                    raise requests.HTTPError(str(self.status_code))

            def json(self):
                return self.payload

        class Session:
            def __init__(self):
                self.requests = []

            def post(self, url, **kwargs):
                self.requests.append((url, kwargs))
                if len(self.requests) == 1:
                    return Response(503)
                result = {
                    "conceptual_summary": "Establece un régimen.",
                    "epesf_relationship": "Puede incidir en EPESF.",
                    "effective_date": "Desde la publicación.",
                    "needs_review": False,
                }
                return Response(200, {
                    "steps": [{"type": "model_output", "content": [
                        {"type": "text", "text": json.dumps(result)}
                    ]}],
                    "usage": {"total_input_tokens": 80, "total_output_tokens": 30},
                })

        session = Session()
        sleeps = []
        result = GeminiSummarizer(
            "secret", session=session, sleep_func=sleeps.append
        ).summarize(self.candidate())

        self.assertEqual([2], sleeps)
        self.assertEqual(2, len(session.requests))
        url, request = session.requests[-1]
        self.assertTrue(url.endswith("/v1beta/interactions"))
        self.assertEqual("gemini-3.5-flash-lite", request["json"]["model"])
        self.assertFalse(request["json"]["store"])
        self.assertEqual("application/json", request["json"]["response_format"]["mime_type"])
        self.assertEqual("secret", request["headers"]["x-goog-api-key"])
        self.assertEqual(80, result.input_tokens)
        self.assertTrue(result.needs_review)


if __name__ == "__main__":
    unittest.main()
