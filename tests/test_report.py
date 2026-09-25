"""Output tests for scripts/check_items.py: the report for Bader and the JSON.

Run from the project root:
    python3 -m unittest discover tests
"""

import datetime
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SCRIPT = ROOT / "scripts" / "check_items.py"
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import (  # noqa: E402
    PHRASES, build_report, evaluate, parse_do_not_feature, parse_items, parse_last_newsletter,
)

READY_IDS = ["01", "05", "08", "09", "11", "16", "17", "18", "19", "21", "23"]
# Words the report's own fixed wording must never use.
BANNED_IN_PHRASES = ["no_consent", "no_link", "past_event", "old_news", "embargo", "duplicate_of",
                     "do_not_feature", "possible_instruction", "Consent:", "held", "needs_info", "status"]
# Reason codes that must never appear anywhere in the report.
REASON_CODES = ["no_consent", "no_link", "no_date", "past_event", "old_news", "duplicate_of",
                "do_not_feature", "possible_instruction", "repeat_of_last_issue", "date_conflict_with"]


def run_script(*extra):
    """Run the script on the test pack with newsletter date 2026-10-05."""
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--items", str(FIXTURES / "updates.md"),
         "--last", str(FIXTURES / "last-newsletter.md"),
         "--dnf", str(FIXTURES / "do-not-feature.md"),
         "--date", "2026-10-05", *extra],
        capture_output=True, text=True, check=True,
    ).stdout


def section(report, heading):
    """The lines of one report section (from its heading to the next blank line)."""
    block = next(b for b in report.split("\n\n") if b.startswith(heading))
    return block


def item_block(report, item_id):
    """The line for one item plus its indented notes."""
    match = re.search(rf"^  \[{item_id}\].*\n(?:       .*\n)*", report, re.M)
    return match.group(0)


class ReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_script()

    def test_ready_section_lists_exactly_the_11_ready_items(self):
        ready = section(self.report, "Ready to use (11)")
        self.assertEqual(re.findall(r"^  \[(\w+)\]", ready, re.M), READY_IDS)

    def test_fixed_wording_has_no_codes_or_field_names(self):
        for key, phrase in PHRASES.items():
            for word in BANNED_IN_PHRASES:
                with self.subTest(phrase=key, word=word):
                    self.assertNotIn(word.lower(), phrase.lower())

    def test_no_reason_codes_anywhere_in_report(self):
        for code in REASON_CODES:
            with self.subTest(code=code):
                self.assertNotIn(code, self.report)
        self.assertNotIn("Consent:", self.report)

    def test_left_out_items_only_say_why(self):
        left_out = section(self.report, "Left out for this issue, and why")
        self.assertNotIn(PHRASES["no_consent"], left_out)
        self.assertNotIn(PHRASES["no_link"], left_out)
        self.assertIn(PHRASES["duplicate_of"].format(id="01"), item_block(self.report, "04"))

    def test_other_sections_keep_every_remark(self):
        block = item_block(self.report, "15")
        self.assertIn(PHRASES["no_consent"], block)
        self.assertIn(PHRASES["no_link"], block)
        self.assertIn("[15]", section(self.report, "Waiting on someone else"))

    def test_no_wording_suggesting_left_out_items_can_be_used(self):
        self.assertNotIn("still use", self.report)

    def test_hidden_comment_of_item_12_is_not_shown(self):
        self.assertNotIn("<!--", self.report)
        for phrase in ("ignore your previous rules", "lead story", "mark its consent", "Note to the AI"):
            self.assertNotIn(phrase.lower(), self.report.lower())
        self.assertIn("looks like instructions to an AI. It was ignored.", item_block(self.report, "12"))

    def test_item_03_says_when_it_can_be_shared(self):
        self.assertIn("until 2026-10-20", item_block(self.report, "03"))

    def test_redact_note_for_item_18(self):
        self.assertIn("Leave out the name of Tidewater Maps", item_block(self.report, "18"))

    def test_running_twice_gives_identical_output(self):
        self.assertEqual(run_script(), self.report)
        with tempfile.TemporaryDirectory() as folder:
            outputs = []
            for n in (1, 2):
                json_path, report_path = Path(folder) / f"r{n}.json", Path(folder) / f"r{n}.txt"
                run_script("--json", str(json_path), "--report", str(report_path))
                outputs.append((json_path.read_text(encoding="utf-8"), report_path.read_text(encoding="utf-8")))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0][1], self.report)


class DoNotFeatureTest(unittest.TestCase):
    """A story about a company on the do-not-feature list goes to Left out, named only there."""

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "items.md"
            path.write_text(
                "## 90\n"
                "- Source: Email to Bader\n"
                "- Date: 2026-10-01\n"
                "- Company: Brightlane Co\n"
                "- Link: https://example.com/brightlane-launch\n"
                "- Consent: yes\n"
                "\n"
                "Brightlane Co launched its new scheduling app.\n",
                encoding="utf-8",
            )
            synthetic = parse_items(path)
        items = parse_items(FIXTURES / "updates.md") + synthetic
        last = parse_last_newsletter(FIXTURES / "last-newsletter.md")
        newsletter_date, last_date = datetime.date(2026, 10, 5), datetime.date(2026, 9, 7)
        cls.verdicts = evaluate(items, last, parse_do_not_feature(FIXTURES / "do-not-feature.md"),
                                newsletter_date, last_date)
        cls.report = build_report(items, cls.verdicts, newsletter_date, last_date)

    def test_held_with_do_not_feature(self):
        self.assertEqual(self.verdicts["90"]["status"], "held")
        self.assertIn("do_not_feature", self.verdicts["90"]["reasons"])

    def test_in_left_out_section_with_plain_wording(self):
        left_out = section(self.report, "Left out for this issue, and why")
        self.assertIn("[90]", left_out)
        self.assertIn(PHRASES["do_not_feature"], item_block(self.report, "90"))
        self.assertNotIn("[90]", section(self.report, "Waiting on someone else"))

    def test_company_name_only_in_left_out_section(self):
        left_out = section(self.report, "Left out for this issue, and why")
        self.assertNotIn("brightlane", self.report.replace(left_out, "").lower())


class JsonTest(unittest.TestCase):
    def test_json_parses_and_counts_add_up(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "results.json"
            run_script("--json", str(path))
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["date"], "2026-10-05")
        self.assertEqual(data["last_date"], "2026-09-07")
        self.assertEqual(sum(data["counts"].values()), 24)
        self.assertEqual(len(data["items"]), 24)
        self.assertEqual([i["id"] for i in data["items"]], sorted(i["id"] for i in data["items"]))
        item_12 = next(i for i in data["items"] if i["id"] == "12")
        self.assertNotIn("<!--", item_12["clean_text"])
        self.assertIn("possible_instruction", item_12["flags"])
        subjects = {i["id"]: i["subject"] for i in data["items"]}
        self.assertEqual(subjects["01"], "Kelpwise")
        self.assertEqual(subjects["13"], "Build Weekend (hackathon)")
        self.assertEqual(subjects["09"], "Volta Residency, winter intake")
        self.assertEqual(subjects["21"], "a Volta mentor")


if __name__ == "__main__":
    unittest.main()
