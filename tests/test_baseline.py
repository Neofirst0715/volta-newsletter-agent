"""First-run situations from AGENTS.md: a baseline last-issue file with no
items recorded, an empty inbox, and non-.md files in the inbox folder.

Run from the project root:
    python3 -m unittest discover tests
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SCRIPT = ROOT / "scripts" / "check_items.py"
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import parse_items, parse_last_newsletter  # noqa: E402

BASELINE = "# Last newsletter, sent 2026-09-07\n(items not recorded)\n"


def run_check(items, last, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--items", str(items), "--last", str(last),
         "--dnf", str(FIXTURES / "do-not-feature.md"), "--date", "2026-10-05", *extra],
        capture_output=True, text=True,
    )


class BaselineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.baseline = self.folder / "2026-09-07.md"
        self.baseline.write_text(BASELINE, encoding="utf-8")
        self.inbox = self.folder / "inbox"
        self.inbox.mkdir()
        (self.inbox / ".gitkeep").write_text("", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_baseline_file_gives_date_and_no_urls(self):
        last = parse_last_newsletter(self.baseline)
        self.assertEqual(last["sent"], "2026-09-07")
        self.assertEqual(last["urls"], [])

    def test_check_items_runs_with_baseline_as_last(self):
        result = run_check(FIXTURES / "updates.md", self.baseline, "--json", str(self.folder / "r.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ready to use", result.stdout)
        data = json.loads((self.folder / "r.json").read_text(encoding="utf-8"))
        self.assertEqual(data["last_date"], "2026-09-07")
        self.assertEqual(sum(data["counts"].values()), 24)

    def test_empty_inbox_says_nothing_to_check(self):
        result = run_check(self.inbox, self.baseline, "--json", str(self.folder / "r.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nothing to check", result.stdout.lower())
        data = json.loads((self.folder / "r.json").read_text(encoding="utf-8"))
        self.assertEqual(data["items"], [])
        self.assertEqual(sum(data["counts"].values()), 0)

    def test_empty_inbox_report_file_says_nothing_to_check(self):
        report = self.folder / "report.md"
        result = run_check(self.inbox, self.baseline, "--report", str(report))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nothing to check", report.read_text(encoding="utf-8").lower())

    def test_folder_mode_only_reads_md_files(self):
        item = ("- Source: Volta events calendar\n- Event: Demo Day\n"
                "- Date: 2026-10-09, 3:00pm, Volta\n- Link: https://example.com/demo-day\n\nDemos.\n")
        (self.inbox / "2026-10-05-demo-day.md").write_text(item, encoding="utf-8")
        (self.inbox / "notes.txt").write_text(item, encoding="utf-8")
        (self.inbox / "._2026-10-05-demo-day.md").write_text(item, encoding="utf-8")  # macOS metadata file
        self.assertEqual([i["id"] for i in parse_items(self.inbox)], ["2026-10-05-demo-day"])


if __name__ == "__main__":
    unittest.main()
