from __future__ import annotations

import unittest
from datetime import date

from epe_boletin.cli import daily_start, parser


class CliPeriodTest(unittest.TestCase):
    def test_daily_run_processes_only_today(self):
        self.assertEqual(date(2026, 9, 11), daily_start(date(2026, 9, 11)))

    def test_cli_has_no_automatic_email_send_command(self):
        with self.assertRaises(SystemExit):
            parser().parse_args(["send-email"])


if __name__ == "__main__":
    unittest.main()
