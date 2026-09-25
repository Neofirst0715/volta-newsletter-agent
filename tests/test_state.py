"""Tests for scripts/state.py. Always a temporary state folder, never the real one.

Run from the project root:
    python3 -m unittest discover tests
"""

import json
import re
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

from state import parse_ledger  # noqa: E402

GOOD_DRAFT = """\
# Volta newsletter, 2026-10-05

## Community wins
- Kelpwise crossed 1,000 paying users. https://example.com/kelpwise-1000-paying
- Brightwater Health is now live in two Nova Scotia clinics. https://example.com/brightwater-clinic-pilot

## Events
- AI Builders Night, 2026-10-14 at 6:00pm. https://example.com/events/ai-builders-night-oct
"""
EXPECTED_KEYS = {
    "https://example.com/northbound-preseed": "held",          # 02
    "https://example.com/saltbox-seed": "held",                # 03
    "https://example.com/quaychat-v2": "held",                 # 12
    "nolink:dory analytics|2026-09-30": "held",                # 15
    "nolink:fogline robotics|2026-10-02": "needs_info",        # 10
    "https://example.com/events/build-weekend": "conflict",    # 13 + 14
}


class StateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.state = self.folder / "state"
        (self.state / "issues").mkdir(parents=True)
        (self.state / "issues" / ".gitkeep").write_text("", encoding="utf-8")
        shutil.copyfile(ROOT / "state" / "ledger.example.md", self.state / "ledger.example.md")
        self.ledger = self.state / "ledger.md"
        self.verdicts = self.check("2026-10-05")

    def tearDown(self):
        self.tmp.cleanup()

    # Helpers

    def check(self, date, last=FIXTURES / "last-newsletter.md"):
        """Run check_items on the test pack and return the path of its JSON."""
        path = self.folder / f"verdicts-{date}.json"
        subprocess.run(
            [sys.executable, str(SCRIPTS / "check_items.py"), "--items", str(FIXTURES / "updates.md"),
             "--last", str(last), "--dnf", str(FIXTURES / "do-not-feature.md"),
             "--date", date, "--json", str(path)],
            capture_output=True, text=True, check=True,
        )
        return path

    def state_cmd(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "state.py"), *args, "--state-dir", str(self.state)],
            capture_output=True, text=True,
        )

    def add_held(self, verdicts=None, date="2026-10-05"):
        result = self.state_cmd("add-held", "--verdicts", str(verdicts or self.verdicts), "--date", date)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def mark_sent(self, draft_text, date="2026-10-05", verdicts=None, *extra):
        draft = self.folder / f"draft-{date}.md"
        draft.write_text(draft_text, encoding="utf-8")
        return self.state_cmd("mark-sent", "--draft", str(draft), "--verdicts", str(verdicts or self.verdicts),
                              "--date", date, "--dnf", str(FIXTURES / "do-not-feature.md"),
                              "--last", str(FIXTURES / "last-newsletter.md"), *extra)

    def entries(self):
        return {e["key"]: e for e in parse_ledger(self.ledger.read_text(encoding="utf-8"))[1]}

    # 1-3: add-held

    def test_1_add_held_creates_exactly_six_entries(self):
        self.add_held()
        entries = self.entries()
        self.assertEqual({k: e["status"] for k, e in entries.items()}, EXPECTED_KEYS)
        merged = entries["https://example.com/events/build-weekend"]
        self.assertIn("date_conflict_with:14", merged["reasons"])
        self.assertIn("date_conflict_with:13", merged["reasons"])
        self.assertEqual(entries["https://example.com/saltbox-seed"]["revisit_on"], "2026-10-20")
        self.assertEqual(entries["https://example.com/northbound-preseed"]["revisit_on"], "next issue")

    def test_2_ledger_has_no_body_text(self):
        self.add_held()
        text = self.ledger.read_text(encoding="utf-8").lower()
        self.assertNotIn("ignore your previous", text)
        for words in ("thrilled to share", "please don't share", "someone at lunch", "<!--"):
            self.assertNotIn(words, text)

    def test_3_add_held_twice_changes_nothing_and_keeps_first_seen(self):
        self.add_held()
        first = self.ledger.read_text(encoding="utf-8")
        self.add_held()
        self.assertEqual(self.ledger.read_text(encoding="utf-8"), first)

        self.add_held(self.check("2026-10-12"), "2026-10-12")
        entry = self.entries()["https://example.com/northbound-preseed"]
        self.assertEqual(entry["first_seen"], "2026-10-05")
        self.assertEqual(entry["last_checked"], "2026-10-12")
        self.assertEqual(len(self.entries()), 6)

    # 4: due

    def test_4_due_reminders_in_plain_words(self):
        self.add_held()
        october = self.state_cmd("due", "--date", "2026-10-21").stdout
        saltbox = re.search(r"^  Saltbox AI\n(?:     .*\n)*", october, re.M).group(0)
        self.assertIn("The date to look again (2026-10-20) has been reached.", saltbox)
        self.assertNotIn("over a month", october)

        november = self.state_cmd("due", "--date", "2026-11-15").stdout
        self.assertIn("Nothing has changed for over a month. Still worth keeping?", november)

        for output in (october, november):
            for code in ("no_consent", "no_link", "date_conflict_with", "embargo", "needs_info"):
                self.assertNotIn(code, output)
            self.assertNotIn("_", output)
            self.assertNotIn("Consent:", output)
            self.assertNotIn("status", output.lower())

    def test_due_never_changes_the_ledger(self):
        self.add_held()
        before = self.ledger.read_text(encoding="utf-8")
        self.state_cmd("due", "--date", "2026-12-31")
        self.assertEqual(self.ledger.read_text(encoding="utf-8"), before)

    # 5-6: file safety

    def test_5_malformed_ledger_makes_every_write_refuse(self):
        self.add_held()
        broken = self.ledger.read_text(encoding="utf-8").replace("- status: held", "- status: maybe", 1)
        self.ledger.write_text(broken, encoding="utf-8")
        before = self.ledger.read_bytes()
        attempts = {
            "add-held": lambda: self.state_cmd("add-held", "--verdicts", str(self.verdicts), "--date", "2026-10-05"),
            "drop": lambda: self.state_cmd("drop", "--key", "https://example.com/quaychat-v2", "--date", "2026-10-05"),
            "mark-sent": lambda: self.mark_sent(GOOD_DRAFT),
        }
        for name, attempt in attempts.items():
            with self.subTest(command=name):
                result = attempt()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("looks damaged", result.stdout)
                self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse((self.state / "issues" / "2026-10-05.md").exists())

    def test_6_ledger_created_from_template_and_backed_up(self):
        self.assertFalse(self.ledger.exists())
        self.add_held()
        template = (self.state / "ledger.example.md").read_text(encoding="utf-8")
        self.assertTrue(self.ledger.read_text(encoding="utf-8").startswith(template.rstrip("\n")))
        self.add_held()
        self.assertTrue((self.state / "ledger.md.bak").exists())
        leftovers = [p.name for p in self.state.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    # 7: mark-sent

    def test_7_mark_sent_good_draft(self):
        self.add_held()
        result = self.mark_sent(GOOD_DRAFT)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("3 item(s) recorded as used", result.stdout)
        self.assertIn("8 ready item(s) kept for next time", result.stdout)

        issue = (self.state / "issues" / "2026-10-05.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(issue[0], "# Last newsletter, sent 2026-10-05")
        self.assertEqual(issue[1], "")
        self.assertEqual(issue[2:], [l for l in GOOD_DRAFT.splitlines() if l.startswith("- ")])

        entries = self.entries()
        for link in ("https://example.com/kelpwise-1000-paying", "https://example.com/brightwater-clinic-pilot",
                     "https://example.com/events/ai-builders-night-oct"):
            self.assertEqual(entries[link]["status"], "used")
            self.assertEqual(entries[link]["used_in"], "2026-10-05")
        self.assertEqual(entries["https://example.com/northbound-preseed"]["status"], "held")

    def test_7_mark_sent_refuses_a_failing_draft(self):
        self.add_held()
        before = self.ledger.read_bytes()
        result = self.mark_sent(GOOD_DRAFT + "- Invented. https://example.com/made-up-news\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("https://example.com/made-up-news", result.stdout)
        self.assertFalse((self.state / "issues" / "2026-10-05.md").exists())
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_7_mark_sent_twice_needs_force(self):
        self.assertEqual(self.mark_sent(GOOD_DRAFT).returncode, 0)
        second = self.mark_sent(GOOD_DRAFT)
        self.assertEqual(second.returncode, 1)
        self.assertIn("already recorded", second.stdout)
        self.assertEqual(self.mark_sent(GOOD_DRAFT, "2026-10-05", None, "--force").returncode, 0)

    def test_held_entry_becomes_ready_then_used(self):
        self.add_held()
        later = self.check("2026-10-21")  # Saltbox's embargo ended on 2026-10-20
        self.add_held(later, "2026-10-21")
        self.assertEqual(self.entries()["https://example.com/saltbox-seed"]["status"], "ready")
        draft = "# Volta newsletter\n- Saltbox AI closed a seed round. https://example.com/saltbox-seed\n"
        result = self.mark_sent(draft, "2026-10-21", later)
        self.assertEqual(result.returncode, 0, result.stdout)
        entry = self.entries()["https://example.com/saltbox-seed"]
        self.assertEqual((entry["status"], entry["used_in"], entry["first_seen"]), ("used", "2026-10-21", "2026-10-05"))

    def test_verdicts_for_another_date_are_refused(self):
        result = self.state_cmd("add-held", "--verdicts", str(self.verdicts), "--date", "2026-10-06")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.ledger.exists())

    # 8: last-issue

    def test_8_last_issue(self):
        result = self.state_cmd("last-issue")
        self.assertEqual((result.returncode, result.stdout.strip()), (2, "none"))
        for name in ("2026-08-03.md", "2026-09-07.md", "example.md", "2026-13-01.md", "notes.txt"):
            (self.state / "issues" / name).write_text("# x\n", encoding="utf-8")
        result = self.state_cmd("last-issue")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), str(self.state / "issues" / "2026-09-07.md"))

    # 9: next month

    def test_9_next_month_skips_what_went_out(self):
        self.assertEqual(self.mark_sent(GOOD_DRAFT).returncode, 0)
        november = json.loads(self.check("2026-11-02", self.state / "issues" / "2026-10-05.md")
                              .read_text(encoding="utf-8"))
        items = {i["id"]: i for i in november["items"]}
        for item_id in ("01", "05", "11"):
            with self.subTest(item=item_id):
                self.assertEqual(items[item_id]["status"], "skip")
                self.assertIn("repeat_of_last_issue", items[item_id]["reasons"])

    # The "item 03 is ready next month" half of test 9 needs the ledger:
    # see tests/test_carry_over.py.


if __name__ == "__main__":
    unittest.main()
