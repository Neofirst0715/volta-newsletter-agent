"""Hard rules 5 and 7 as checks on the scripts' own code: no network or mail
modules are imported, and the system clock is never read.

This inspects the source; it cannot prove what a future edit might add, so
it runs with every test run.

Run from the project root:
    python3 -m unittest discover tests
"""

import ast
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

NETWORK_MODULES = {"socket", "ssl", "http", "urllib", "urllib2", "urllib3", "requests", "httpx",
                   "smtplib", "imaplib", "poplib", "ftplib", "telnetlib", "email", "webbrowser",
                   "xmlrpc", "asyncio", "subprocess"}
CLOCK_CALLS = {"today", "now", "utcnow", "time", "localtime", "gmtime", "monotonic", "perf_counter"}


class NoNetworkNoClockTest(unittest.TestCase):
    def scripts(self):
        files = sorted(SCRIPTS.glob("*.py"))
        self.assertTrue(files)
        return files

    def test_scripts_import_no_network_or_mail_modules(self):
        for path in self.scripts():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    with self.subTest(script=path.name, module=name):
                        self.assertNotIn(name.split(".")[0], NETWORK_MODULES)

    def test_scripts_never_read_the_clock(self):
        for path in self.scripts():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    with self.subTest(script=path.name, line=node.lineno):
                        self.assertNotIn(node.func.attr, CLOCK_CALLS)


if __name__ == "__main__":
    unittest.main()
