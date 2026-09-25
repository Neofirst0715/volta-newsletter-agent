"""Carry-over between issues: check_items.py --ledger and state.py mark-sent.

A ledger entry (held, needs_info, conflict or ready) exempts its item from the
old-news rule only. Everything else applies exactly as before. Always uses a
temporary state folder, never the real one.

Run from the project root:
    python3 -m unittest discover tests
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from state import format_ledger, parse_ledger  # noqa: E402

GOOD_DRAFT = """\
# Volta newsletter, 2026-10-05

## Community wins
- Kelpwise crossed 1,000 paying users. https://example.com/kelpwise-1000-paying
- Brightwater Health is now live in two Nova Scotia clinics. https://example.com/brightwater-clinic-pilot

## Events
- AI Builders Night, 2026-10-14 at 6:00pm. https://example.com/events/ai-builders-night-oct
"""
CARRIED_READY = {  # ready on 2026-10-05 but not in the draft
    "08": "https://example.com/events/agents-lab",
    "09": "https://example.com/programs/residency-winter",
    "16": "https://example.com/programs/mentor-match",
    "17": "https://example.com/ai-lab-grant-drafter",
    "18": "https://example.com/events/build-night-sept-recap",
    "19": "https://example.com/events/women-in-ai-breakfast",
    "21": "https://example.com/mentors/gtm-hours",
    "23": "https://example.com/pennant-beta-testers",
}


class CarryOverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.state = self.folder / "state"
        (self.state / "issues").mkdir(parents=True)
        shutil.copyfile(ROOT / "state" / "ledger.example.md", self.state / "ledger.example.md")
        self.ledger = self.state / "ledger.md"
        self.issue = self.state / "issues" / "2026-10-05.md"

    def tearDown(self):
        self.tmp.cleanup()

    # Helpers

    def run_check(self, date, last, ledger=None, items=FIXTURES / "updates.md"):
        path = self.folder / f"verdicts-{date}-{'ledger' if ledger else 'plain'}.json"
        args = [sys.executable, str(SCRIPTS / "check_items.py"), "--items", str(items), "--last", str(last),
                "--dnf", str(FIXTURES / "do-not-feature.md"), "--date", date, "--json", str(path)]
        if ledger:
            args += ["--ledger", str(ledger)]
        result = subprocess.run(args, capture_output=True, text=True)
        return result, path

    def check(self, date, last, ledger=None, items=FIXTURES / "updates.md"):
        result, path = self.run_check(date, last, ledger, items)
        self.assertEqual(result.returncode, 0, result.stderr)
        return {i["id"]: i for i in json.loads(path.read_text(encoding="utf-8"))["items"]}

    def state_cmd(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPTS / "state.py"), *args, "--state-dir", str(self.state)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def october_sent(self):
        """add-held and mark-sent for 2026-10-05 with a draft of items 01, 05 and 11."""
        _, verdicts = self.run_check("2026-10-05", FIXTURES / "last-newsletter.md")
        self.state_cmd("add-held", "--verdicts", str(verdicts), "--date", "2026-10-05")
        draft = self.folder / "draft.md"
        draft.write_text(GOOD_DRAFT, encoding="utf-8")
        self.state_cmd("mark-sent", "--draft", str(draft), "--verdicts", str(verdicts), "--date", "2026-10-05",
                       "--dnf", str(FIXTURES / "do-not-feature.md"), "--last", str(FIXTURES / "last-newsletter.md"))

    def entries(self):
        return {e["key"]: e for e in parse_ledger(self.ledger.read_text(encoding="utf-8"))[1]}

    def write_ledger(self, entries):
        header = (self.state / "ledger.example.md").read_text(encoding="utf-8").splitlines()
        full = [{"subject": "x", "reasons": "none", "revisit_on": "none", "first_seen": "2026-10-05",
                 "last_checked": "2026-10-05", "used_in": "none", **e} for e in entries]
        self.ledger.write_text(format_ledger(header, full), encoding="utf-8")

    def baseline(self):
        self.issue.write_text("# Last newsletter, sent 2026-10-05\n(items not recorded)\n", encoding="utf-8")
        return self.issue

    # 1. Next month, with and without the ledger

    def test_1_next_month_with_ledger(self):
        self.october_sent()
        november = self.check("2026-11-02", self.issue, self.ledger)
        self.assertEqual(november["03"]["status"], "ready", november["03"]["reasons"])
        self.assertTrue(november["03"].get("carried_over"))
        for item_id in ("01", "05", "11"):
            with self.subTest(item=item_id):
                self.assertEqual(november[item_id]["status"], "skip")
                self.assertIn("repeat_of_last_issue", november[item_id]["reasons"])

        plain = self.check("2026-11-02", self.issue)
        self.assertEqual(plain["03"]["status"], "skip")
        self.assertIn("old_news", plain["03"]["reasons"])
        self.assertNotIn("carried_over", plain["03"])

    # 2. News never in the ledger is still old

    def test_2_item_never_in_ledger_is_still_old_news(self):
        self.october_sent()
        november = self.check("2026-11-02", self.issue, self.ledger)
        self.assertEqual(november["20"]["status"], "skip")
        self.assertIn("old_news", november["20"]["reasons"])
        self.assertNotIn("carried_over", november["20"])

    # 3. Used and dropped entries never exempt

    def test_3_used_and_dropped_entries_do_not_exempt(self):
        self.write_ledger([
            {"key": "https://example.com/northbound-preseed", "status": "dropped"},   # 02
            {"key": "https://example.com/kelpwise-1000-paying", "status": "used", "used_in": "2026-10-05"},  # 01
        ])
        november = self.check("2026-11-02", self.baseline(), self.ledger)
        for item_id in ("01", "02"):
            with self.subTest(item=item_id):
                self.assertIn("old_news", november[item_id]["reasons"])
                self.assertEqual(november[item_id]["status"], "skip")
                self.assertNotIn("carried_over", november[item_id])

    # 4. The exemption rescues nothing else

    def test_4_ledger_entry_does_not_rescue_other_problems(self):
        items = self.folder / "items.md"
        items.write_text(
            (FIXTURES / "updates.md").read_text(encoding="utf-8")
            + "\n## 90\n- Source: Email to Bader\n- Date: 2026-09-20\n- Company: Brightlane Co\n"
              "- Link: https://example.com/brightlane-launch\n- Consent: yes\n\nBrightlane Co launched.\n",
            encoding="utf-8")
        self.write_ledger([
            {"key": "https://example.com/events/pitch-practice-sept", "status": "held"},  # 06
            {"key": "https://example.com/northbound-preseed", "status": "held"},          # 02
            {"key": "https://example.com/brightlane-launch", "status": "held"},           # 90
            {"key": "https://example.com/events/build-night-sept-recap", "status": "ready"},  # 18
        ])
        november = self.check("2026-11-02", self.baseline(), self.ledger, items)

        self.assertEqual(november["06"]["status"], "skip")
        self.assertIn("past_event", november["06"]["reasons"])

        self.assertEqual(november["02"]["status"], "held")
        self.assertIn("no_consent", november["02"]["reasons"])
        self.assertNotIn("old_news", november["02"]["reasons"])

        self.assertEqual(november["90"]["status"], "held")
        self.assertIn("do_not_feature", november["90"]["reasons"])

        self.assertEqual(november["18"]["redact"], ["Tidewater Maps"])
        self.assertEqual(november["18"]["status"], "ready")

    # 5. Unused ready items are carried over by mark-sent

    def test_5_mark_sent_keeps_unused_ready_items(self):
        self.october_sent()
        entries = self.entries()
        for item_id, link in CARRIED_READY.items():
            with self.subTest(item=item_id):
                self.assertEqual(entries[link]["status"], "ready")
                self.assertEqual(entries[link]["reasons"], "carried over")
        november = self.check("2026-11-02", self.issue, self.ledger)
        for item_id in ("09", "16", "17", "18", "21", "23"):
            with self.subTest(item=item_id):
                self.assertNotIn("old_news", november[item_id]["reasons"])
        for item_id in ("08", "19"):
            with self.subTest(item=item_id):
                self.assertIn("past_event", november[item_id]["reasons"])

    def test_due_calls_them_left_over(self):
        self.october_sent()
        output = self.state_cmd("due", "--date", "2026-11-02").stdout
        self.assertIn("Left over from last time.", output)
        self.assertNotIn("carried over", output)
        self.assertNotIn("_", output)

    # 6. Missing and malformed ledger

    def test_6_missing_ledger_is_empty(self):
        missing = self.folder / "no-such-ledger.md"
        with_missing = self.check("2026-11-02", self.baseline(), missing)
        without = self.check("2026-11-02", self.issue)
        self.assertEqual(with_missing, without)
        self.assertFalse(missing.exists())

    def test_6_malformed_ledger_stops_with_clear_message(self):
        self.ledger.write_text("# Ledger\n\n## entry\n- key: x\n- colour: blue\n", encoding="utf-8")
        result, path = self.run_check("2026-11-02", self.baseline(), self.ledger)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("looks damaged", result.stderr)
        self.assertNotIn("Traceback", result.stderr + result.stdout)
        self.assertFalse(path.exists())

    # 7. Still no body text

    def test_7_ledger_has_no_body_text(self):
        self.october_sent()
        text = self.ledger.read_text(encoding="utf-8").lower()
        # Words that appear only in item bodies (item 17's subject field itself
        # says "two students", so that phrase is not a body-text marker).
        for words in ("ignore your previous", "thrilled to share", "hands-on session", "meeting notes",
                      "tidewater", "<!--"):
            with self.subTest(words=words):
                self.assertNotIn(words, text)


if __name__ == "__main__":
    unittest.main()
