"""Rule 5 for events: a date conflict needs the same link, the same event name
and different Source text. Different events that share a page link (such as
the events calendar page) are not a conflict.

Run from the project root:
    python3 -m unittest discover tests
"""

import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import evaluate  # noqa: E402

SHARED = "https://voltaeffect.com/events"


def event(item_id, name, source, date="2026-10-14, 6:00 PM, Volta", link=SHARED):
    return {"id": item_id, "type": "event", "raw_text": "", "clean_text": "",
            "fields": {"Source": source, "Date": date, "Event": name, "Link": link}}


def run(items):
    last = {"sent": "2026-09-07", "urls": []}
    return evaluate(items, last, [], datetime.date(2026, 9, 25), datetime.date(2026, 9, 7))


def conflicts(verdict):
    return [r for r in verdict["reasons"] if r.startswith("date_conflict_with:")]


class EventConflictTest(unittest.TestCase):
    def test_1_different_events_sharing_a_page_link_are_not_a_conflict(self):
        verdicts = run([
            event("a", "AI Showcase and Mixer", "Volta events calendar", "2026-10-14, 6:00 PM"),
            event("b", "Coffee, Community and Co-Work", "Volta events calendar", "2026-10-01, 9:00 AM"),
            event("c", "DEFCON Halifax October Meet-Up",
                  "Volta events calendar (description written by DEFCON Halifax)", "2026-10-01, 6:30 PM"),
            event("d", "The Rules of the Game: Competition Law and Procurement 101",
                  "Volta events calendar (webinar hosted by the Competition Bureau)", "2026-10-20, 2:30 PM"),
            event("e", "Turning Cybersecurity, Privacy and AI Governance into a Business Advantage",
                  "Volta events calendar", "2026-09-28, 12:00 PM"),
        ])
        for item_id, verdict in verdicts.items():
            with self.subTest(item=item_id):
                self.assertEqual(conflicts(verdict), [])
                self.assertEqual(verdict["status"], "ready")

    def test_2_same_link_same_name_different_sources_conflict(self):
        verdicts = run([
            event("a", "Build Weekend", "Volta events calendar", "2026-10-17 to 2026-10-18, Volta"),
            event("b", "Build Weekend", "Email from a partner organization", "2026-10-03"),
        ])
        self.assertEqual(verdicts["a"]["status"], "conflict")
        self.assertEqual(verdicts["b"]["status"], "conflict")
        self.assertEqual(conflicts(verdicts["a"]), ["date_conflict_with:b"])
        self.assertEqual(conflicts(verdicts["b"]), ["date_conflict_with:a"])

    def test_3_names_that_differ_only_by_case_spacing_or_brackets_still_conflict(self):
        for other in ("build weekend", "BUILD   WEEKEND", "Build Weekend (hackathon)",
                      "Build Weekend [moved]", "Build Weekend!"):
            with self.subTest(other=other):
                verdicts = run([
                    event("a", "Build Weekend", "Volta events calendar", "2026-10-17, Volta"),
                    event("b", other, "Email from a partner organization", "2026-10-03"),
                ])
                self.assertEqual(verdicts["a"]["status"], "conflict")
                self.assertEqual(verdicts["b"]["status"], "conflict")

    def test_same_link_same_name_same_source_is_unchanged(self):
        # Same as before this change: identical Source text is not a conflict.
        verdicts = run([
            event("a", "Build Weekend", "Volta events calendar", "2026-10-17, Volta"),
            event("b", "Build Weekend", "Volta events calendar", "2026-10-24, Volta"),
        ])
        self.assertEqual(conflicts(verdicts["a"]), [])
        self.assertEqual(conflicts(verdicts["b"]), [])

    def test_4_real_sample_regression(self):
        with tempfile.TemporaryDirectory() as folder:
            baseline = Path(folder) / "2026-09-07.md"
            baseline.write_text("# Last newsletter, sent 2026-09-07\n", encoding="utf-8")
            out = Path(folder) / "verdicts.json"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_items.py"),
                 "--items", str(FIXTURES / "real-sample"), "--last", str(baseline),
                 "--dnf", str(ROOT / "sources" / "do-not-feature.example.md"),
                 "--date", "2026-09-25", "--json", str(out)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(len(data["items"]), 8)
        self.assertEqual(data["counts"], {"ready": 6, "skip": 2, "conflict": 0, "held": 0, "needs_info": 0})
        skipped = {i["id"]: i["reasons"] for i in data["items"] if i["status"] == "skip"}
        self.assertEqual(skipped, {"2026-09-25-yoga": ["past_event"], "2026-09-25-sprint": ["old_news"]})
        for item in data["items"]:
            with self.subTest(item=item["id"]):
                self.assertEqual(conflicts(item), [])


if __name__ == "__main__":
    unittest.main()
