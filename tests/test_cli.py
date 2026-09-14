from __future__ import annotations

import unittest
from datetime import date

from epe_boletin.cli import daily_start, parser


class CliPeriodTest(unittest.TestCase):
    def test_daily_period_recovers_gap_and_overlap(self):
        self.assertEqual(
            date(2026, 8, 26),
            daily_start(date(2026, 9, 1), date(2026, 9, 11), 7),
        )

    def test_first_daily_run_starts_today(self):
        self.assertEqual(
            date(2026, 9, 11), daily_start(None, date(2026, 9, 11), 7)
        )

    def test_cli_has_no_automatic_email_send_command(self):
        with self.assertRaises(SystemExit):
            parser().parse_args(["send-email"])


if __name__ == "__main__":
    unittest.main()
