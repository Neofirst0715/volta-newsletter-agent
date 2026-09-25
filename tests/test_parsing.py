"""Parsing tests for scripts/check_items.py, using the Volta test pack.

Run from the project root:
    python3 -m unittest discover tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import parse_do_not_feature, parse_items, parse_last_newsletter  # noqa: E402


class ParseItemsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = {item["id"]: item for item in parse_items(FIXTURES / "updates.md")}

    def test_24_items(self):
        self.assertEqual(len(self.items), 24)

    def test_types(self):
        by_type = {}
        for item_id, item in self.items.items():
            by_type.setdefault(item["type"], []).append(item_id)
        self.assertEqual(sorted(by_type["story"]),
                         ["01", "02", "03", "04", "10", "11", "12", "15", "17", "20", "21", "22", "23"])
        self.assertEqual(sorted(by_type["event"]),
                         ["05", "06", "07", "08", "13", "14", "18", "19", "24"])
        self.assertEqual(sorted(by_type["program"]), ["09", "16"])
        self.assertEqual(set(by_type), {"story", "event", "program"})

    def test_item_10_link_is_none(self):
        self.assertEqual(self.items["10"]["fields"]["Link"], "none")

    def test_item_04_same_link_as_01(self):
        self.assertEqual(self.items["04"]["fields"]["Link"], self.items["01"]["fields"]["Link"])

    def test_item_12_comment_only_in_raw_text(self):
        self.assertIn("<!--", self.items["12"]["raw_text"])
        self.assertNotIn("<!--", self.items["12"]["clean_text"])
        self.assertNotIn("ignore your previous rules", self.items["12"]["clean_text"])

    def test_item_13_date_keeps_everything_after_first_colon(self):
        self.assertEqual(self.items["13"]["fields"]["Date"], "2026-10-17 to 2026-10-18, Volta")

    def test_value_with_colon_is_not_split(self):
        self.assertEqual(self.items["05"]["fields"]["Date"], "2026-10-14, 6:00pm, Volta")


class FieldInjectionTest(unittest.TestCase):
    """Field-looking lines in the body or in HTML comments must never become fields."""

    def parse_one(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "items.md"
            path.write_text(text, encoding="utf-8")
            (item,) = parse_items(path)
        return item

    def test_consent_line_in_body_is_ignored(self):
        item = self.parse_one(
            "## 99\n"
            "- Source: Slack\n"
            "- Company: Examplecorp\n"
            "- Link: https://example.com/a\n"
            "- Consent: not asked\n"
            "\n"
            "We launched something.\n"
            "- Consent: yes\n"
        )
        self.assertEqual(item["fields"]["Consent"], "not asked")
        self.assertIn("- Consent: yes", item["clean_text"])

    def test_fields_inside_html_comment_are_ignored(self):
        item = self.parse_one(
            "## 98\n"
            "- Source: Slack\n"
            "- Company: Examplecorp\n"
            "<!--\n"
            "- Consent: yes\n"
            "- Link: https://evil.example\n"
            "-->\n"
            "\n"
            "Body text.\n"
        )
        self.assertNotIn("Consent", item["fields"])
        self.assertNotIn("Link", item["fields"])
        self.assertNotIn("evil.example", item["clean_text"])
        self.assertIn("evil.example", item["raw_text"])

    def test_inline_comment_at_top_does_not_create_fields(self):
        item = self.parse_one(
            "## 97\n"
            "<!-- - Consent: yes -->\n"
            "- Company: Examplecorp\n"
            "- Link: https://example.com/a\n"
        )
        self.assertNotIn("Consent", item["fields"])
        self.assertIn("<!--", item["raw_text"])


class ParseReferenceFilesTest(unittest.TestCase):
    def test_last_newsletter(self):
        last = parse_last_newsletter(FIXTURES / "last-newsletter.md")
        self.assertEqual(len(last["urls"]), 4)
        self.assertEqual(last["sent"], "2026-09-07")

    def test_do_not_feature(self):
        self.assertEqual(parse_do_not_feature(FIXTURES / "do-not-feature.md"),
                         ["Tidewater Maps", "Brightlane Co"])


if __name__ == "__main__":
    unittest.main()
