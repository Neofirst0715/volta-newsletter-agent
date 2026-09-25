"""Tests for scripts/package.sh and for running with an empty do-not-feature list.

The packaging tests copy the project into a temporary folder and build the zip
there, so the real project and the real zip are never touched.

Run from the project root:
    python3 -m unittest discover tests
"""

import datetime
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from check_items import evaluate, parse_do_not_feature, parse_items, parse_last_newsletter  # noqa: E402
from verify_draft import read_dnf_names  # noqa: E402

TOP = "volta-newsletter-agent"
NOT_COPIED = shutil.ignore_patterns(".git", "research", ".idea", "work", "__pycache__", "*.zip", ".DS_Store")


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / TOP
        shutil.copytree(ROOT, self.project, ignore=NOT_COPIED)
        self.zip = Path(self.tmp.name) / "volta-newsletter-agent-submission.zip"

    def tearDown(self):
        self.tmp.cleanup()

    def package(self):
        return subprocess.run(["sh", str(self.project / "scripts" / "package.sh")],
                              capture_output=True, text=True)

    def names_in_zip(self):
        with zipfile.ZipFile(self.zip) as z:
            return z.namelist()

    def test_private_and_generated_files_are_left_out(self):
        extras = {
            "inbox/2026-10-05-kelpwise.md": "- Company: Kelpwise\n",
            "intake/Volta newsletter news (Responses) - Form Responses 1.csv": "Timestamp,Email Address\n",
            "intake/old-export.csv": "Timestamp,Email Address\n",
            "drafts/2026-10-05.md": "# Draft\n",
            "state/ledger.md": "# Ledger\n",
            "state/ledger.md.bak": "# Ledger\n",
            "state/issues/2026-10-05.md": "# Last newsletter, sent 2026-10-05\n",
            "work/verdicts.json": "{}\n",
            "research/interview.md": "notes\n",
            ".env": "SECRET=1\n",
            "api-token.txt": "x\n",
        }
        for name, text in extras.items():
            (self.project / name).parent.mkdir(parents=True, exist_ok=True)
            (self.project / name).write_text(text, encoding="utf-8")

        result = self.package()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        names = self.names_in_zip()
        for name in extras:
            with self.subTest(name=name):
                self.assertNotIn(f"{TOP}/{name}", names)
        for kept in ("inbox/.gitkeep", "drafts/.gitkeep", "intake/.gitkeep", "state/issues/.gitkeep",
                     "sources/do-not-feature.md", "sources/do-not-feature.example.md", "README.md"):
            with self.subTest(kept=kept):
                self.assertIn(f"{TOP}/{kept}", names)

    def test_listing_uses_file_names_only(self):
        result = self.package()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Archive:", result.stdout)
        self.assertFalse([n for n in self.names_in_zip() if n.endswith(".zip")])

    def test_real_do_not_feature_list_stops_packaging(self):
        dnf = self.project / "sources" / "do-not-feature.md"
        dnf.write_text(dnf.read_text(encoding="utf-8")
                       + '- Brightlane Co - asked 2026-08-30: "no features, thanks"\n', encoding="utf-8")
        self.zip.write_text("old zip", encoding="utf-8")
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("the real do-not-feature list must not be submitted; empty it or use the example",
                      result.stdout)
        self.assertFalse(self.zip.exists())


class EmptyDoNotFeatureListTest(unittest.TestCase):
    """The shipped list and the example have no names, and the scripts work with them."""

    def test_shipped_lists_have_no_names(self):
        for name in ("do-not-feature.md", "do-not-feature.example.md"):
            path = ROOT / "sources" / name
            with self.subTest(file=name):
                self.assertEqual(parse_do_not_feature(path), [])
                self.assertEqual(read_dnf_names(path), [])
                self.assertFalse([l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("- ")])

    def test_check_and_verify_run_with_the_empty_list(self):
        with tempfile.TemporaryDirectory() as folder:
            results, draft = Path(folder) / "r.json", Path(folder) / "d.md"
            check = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_items.py"),
                 "--items", str(FIXTURES / "updates.md"), "--last", str(FIXTURES / "last-newsletter.md"),
                 "--dnf", str(ROOT / "sources" / "do-not-feature.md"), "--date", "2026-10-05",
                 "--json", str(results)],
                capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            draft.write_text("# Draft\n- Brightwater Health is live. https://example.com/brightwater-clinic-pilot\n",
                             encoding="utf-8")
            verify = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "verify_draft.py"), "--draft", str(draft),
                 "--verdicts", str(results), "--dnf", str(ROOT / "sources" / "do-not-feature.md"),
                 "--last", str(FIXTURES / "last-newsletter.md")],
                capture_output=True, text=True)
            self.assertEqual(verify.returncode, 0, verify.stdout)

    def test_empty_list_means_no_redaction(self):
        items = parse_items(FIXTURES / "updates.md")
        verdicts = evaluate(items, parse_last_newsletter(FIXTURES / "last-newsletter.md"),
                            parse_do_not_feature(ROOT / "sources" / "do-not-feature.md"),
                            datetime.date(2026, 10, 5), datetime.date(2026, 9, 7))
        self.assertNotIn("redact", verdicts["18"]["flags"])


if __name__ == "__main__":
    unittest.main()
