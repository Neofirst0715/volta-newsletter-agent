"""Consent safety: the consent status and the embargo date come only from the
start of the Consent value (the keyword first), never from the brackets after it.

Each test writes a real item file and goes through the parser and the rules.

Run from the project root:
    python3 -m unittest discover tests
"""

import datetime
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import evaluate, parse_items  # noqa: E402

NEWSLETTER_DATE = datetime.date(2026, 10, 5)
LAST_DATE = datetime.date(2026, 9, 7)


def verdict_for(consent_line):
    """Parse one story with the given Consent line (or none) and evaluate it."""
    lines = [
        "## 50",
        "- Source: Email to Bader",
        "- Date: 2026-10-01",
        "- Company: Examplecorp",
        "- Link: https://example.com/examplecorp-news",
    ]
    if consent_line is not None:
        lines.append(consent_line)
    lines += ["", "Examplecorp shipped something new."]
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "items.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        items = parse_items(path)
    last = {"sent": LAST_DATE.isoformat(), "urls": []}
    return evaluate(items, last, [], NEWSLETTER_DATE, LAST_DATE)["50"]


class ConsentParsingTest(unittest.TestCase):
    def assert_waiting_for_embargo(self, verdict):
        self.assertEqual(verdict["status"], "held")
        self.assertIn("embargo", verdict["reasons"])
        self.assertEqual(verdict["revisit_on"], "2026-10-20")

    def assert_no_consent_problem(self, verdict):
        self.assertNotIn("no_consent", verdict["reasons"])
        self.assertNotIn("embargo", verdict["reasons"])
        self.assertEqual(verdict["status"], "ready")

    def assert_no_consent(self, verdict):
        self.assertEqual(verdict["status"], "held")
        self.assertIn("no_consent", verdict["reasons"])

    def test_1_embargo_with_newsletter_date_in_brackets(self):
        self.assert_waiting_for_embargo(verdict_for(
            '- Consent: embargoed until 2026-10-20 (Bader confirmed for the 2026-10-05 issue: "please hold until Oct 20")'))

    def test_2_embargo_with_older_date_in_brackets(self):
        self.assert_waiting_for_embargo(verdict_for(
            '- Consent: embargoed until 2026-10-20 (Bader confirmed for the 2026-09-01 issue: "OK")'))

    def test_3_not_asked_with_note(self):
        self.assert_no_consent(verdict_for("- Consent: not asked (a colleague said yes, unconfirmed)"))

    def test_4_yes_with_evidence(self):
        self.assert_no_consent_problem(verdict_for(
            '- Consent: yes (Bader confirmed for the 2026-10-05 issue: "she is happy to be featured")'))

    def test_5_upper_case_and_extra_spaces(self):
        for line in ("- Consent: YES (...)", "- Consent:   yes  "):
            with self.subTest(line=line):
                self.assert_no_consent_problem(verdict_for(line))

    def test_6_embargo_ending_on_newsletter_date(self):
        self.assert_no_consent_problem(verdict_for("- Consent: embargoed until 2026-10-05 (...)"))

    def test_7_unknown_value(self):
        self.assert_no_consent(verdict_for("- Consent: maybe"))

    def test_8_no_consent_line(self):
        self.assert_no_consent(verdict_for(None))

    # Extra cases that protect the parser fix.

    def test_word_starting_with_yes_is_not_consent(self):
        self.assert_no_consent(verdict_for("- Consent: yesterday someone said it was fine"))

    def test_embargo_without_usable_date_ignores_dates_in_brackets(self):
        verdict = verdict_for("- Consent: embargoed until Oct 20 (Bader confirmed for the 2026-09-01 issue)")
        self.assertEqual(verdict["status"], "held")
        self.assertIn("embargo", verdict["reasons"])
        self.assertIsNone(verdict["revisit_on"])

    def test_full_consent_text_is_kept_as_written(self):
        line = 'yes (Bader confirmed for the 2026-10-05 issue: "she is happy to be featured")'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "items.md"
            path.write_text(f"## 51\n- Company: Examplecorp\n- Consent: {line}\n", encoding="utf-8")
            (item,) = parse_items(path)
        self.assertEqual(item["fields"]["Consent"], "yes")
        self.assertEqual(item["consent_as_written"], line)


if __name__ == "__main__":
    unittest.main()
