"""Rule tests for evaluate() in scripts/check_items.py.

Run from the project root:
    python3 -m unittest discover tests
"""

import datetime
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import evaluate, parse_do_not_feature, parse_items, parse_last_newsletter  # noqa: E402

NEWSLETTER_DATE = datetime.date(2026, 10, 5)


class ExpectedAnswersTest(unittest.TestCase):
    """Compare evaluate() on the test pack with tests/expected.json."""

    @classmethod
    def setUpClass(cls):
        last = parse_last_newsletter(FIXTURES / "last-newsletter.md")
        cls.verdicts = evaluate(
            parse_items(FIXTURES / "updates.md"),
            last,
            parse_do_not_feature(FIXTURES / "do-not-feature.md"),
            NEWSLETTER_DATE,
            datetime.date.fromisoformat(last["sent"]),
        )
        cls.expected = json.loads((ROOT / "tests" / "expected.json").read_text(encoding="utf-8"))

    def test_every_item_has_a_verdict(self):
        self.assertEqual(sorted(self.verdicts), sorted(self.expected))

    def test_each_item(self):
        for item_id, want in sorted(self.expected.items()):
            got = self.verdicts[item_id]
            with self.subTest(item=item_id):
                self.assertEqual(got["status"], want["status"])
                for reason in want["reasons"]:
                    self.assertIn(reason, got["reasons"])
                if "redact" in want:
                    self.assertEqual(got["flags"].get("redact"), want["redact"])
                if "possible_instruction" in want:
                    self.assertEqual(got["flags"].get("possible_instruction"), want["possible_instruction"])
                if "revisit_on" in want:
                    self.assertEqual(got["revisit_on"], want["revisit_on"])


def make_item(item_id, item_type, **fields):
    return {"id": item_id, "fields": fields, "raw_text": "", "clean_text": "", "type": item_type}


def run_one(item):
    last = {"sent": "2026-09-07", "urls": []}
    return evaluate([item], last, [], NEWSLETTER_DATE, datetime.date(2026, 9, 7))[item["id"]]


class DateEdgeTest(unittest.TestCase):
    def test_event_on_newsletter_date_is_not_past(self):
        verdict = run_one(make_item(
            "e1", "event", Source="Volta events calendar", Event="Same-day event",
            Date="2026-10-05, 6:00pm, Volta", Link="https://example.com/same-day"))
        self.assertEqual(verdict["status"], "ready")
        self.assertNotIn("past_event", verdict["reasons"])

    def test_embargo_ending_on_newsletter_date_is_fine(self):
        verdict = run_one(make_item(
            "s1", "story", Source="Email to Bader", Company="Examplecorp", Date="2026-10-01",
            Link="https://example.com/embargo", Consent="embargoed until 2026-10-05"))
        self.assertEqual(verdict["status"], "ready")
        self.assertNotIn("embargo", verdict["reasons"])
        self.assertIsNone(verdict["revisit_on"])


class NoDateTest(unittest.TestCase):
    def test_calendar_event_without_date_needs_info(self):
        verdict = run_one(make_item(
            "e2", "event", Source="Volta events calendar", Event="Undated event",
            Date="TBD", Link="https://example.com/undated"))
        self.assertEqual(verdict["status"], "needs_info")
        self.assertIn("no_date", verdict["reasons"])

    def test_story_without_date_only_gets_the_reason(self):
        verdict = run_one(make_item(
            "s2", "story", Source="Slack", Company="Examplecorp",
            Link="https://example.com/undated-story", Consent="yes"))
        self.assertEqual(verdict["status"], "ready")
        self.assertIn("no_date", verdict["reasons"])


if __name__ == "__main__":
    unittest.main()
