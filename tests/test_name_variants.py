"""How verify_draft.py handles variants of names, as it behaves TODAY.

Tests named test_known_limit_* record a miss on purpose: they assert the
current behaviour so the limit written in README.md is backed by a test.
If the verifier is ever improved, these tests will fail and must be updated
together with the README. No fuzzy matching is added here.

Run from the project root:
    python3 -m unittest discover tests
"""

import datetime
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import (  # noqa: E402
    build_json, evaluate, parse_do_not_feature, parse_items, parse_last_newsletter,
)
from verify_draft import read_dnf_names, read_last_urls, run_checks  # noqa: E402

GOOD_DRAFT = """\
# Volta newsletter, 2026-10-05

## Community wins
- Brightwater Health is now live in two Nova Scotia clinics. https://example.com/brightwater-clinic-pilot
"""
READY_LINK_05 = "https://example.com/events/ai-builders-night-oct"


class NameVariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        items = parse_items(FIXTURES / "updates.md")
        last = parse_last_newsletter(FIXTURES / "last-newsletter.md")
        newsletter_date, last_date = datetime.date(2026, 10, 5), datetime.date(2026, 9, 7)
        verdicts = evaluate(items, last, parse_do_not_feature(FIXTURES / "do-not-feature.md"),
                            newsletter_date, last_date)
        cls.verdicts = build_json(items, verdicts, newsletter_date, last_date)
        cls.dnf = read_dnf_names(FIXTURES / "do-not-feature.md")
        cls.last = read_last_urls(FIXTURES / "last-newsletter.md")

    def failed_checks(self, sentence):
        """Good draft plus one bullet using item 05's (ready) link. Returns the failing check numbers."""
        draft = GOOD_DRAFT + f"- {sentence} {READY_LINK_05}\n"
        return {check for check, level, _ in run_checks(draft, self.verdicts, self.dnf, self.last) if level == "FAIL"}

    # Caught today

    def test_upper_case_name_is_caught(self):
        self.assertEqual(self.failed_checks("QUAYCHAT shipped a widget."), {5})

    def test_possessive_name_is_caught(self):
        self.assertEqual(self.failed_checks("Tidewater Maps' founders spoke."), {4, 6})

    def test_ready_company_passes_in_any_case(self):
        for sentence in ("Kelpwise crossed 1,000 users.", "kelpwise crossed 1,000 users."):
            with self.subTest(sentence=sentence):
                self.assertEqual(self.failed_checks(sentence), set())

    # Known limits: missed today (only whole, exact names are matched)

    def test_known_limit_partial_do_not_feature_name(self):
        # "Tidewater" alone is not "Tidewater Maps", so the draft PASSES.
        self.assertEqual(self.failed_checks("Tidewater won the Build Night pitch."), set())

    def test_known_limit_partial_subject_name(self):
        # "Saltbox" alone is not "Saltbox AI" (item 03, not ready), so the draft PASSES.
        self.assertEqual(self.failed_checks("Saltbox raised money."), set())


if __name__ == "__main__":
    unittest.main()
