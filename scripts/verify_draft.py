"""Check a newsletter draft against the results of check_items.py.

What is allowed comes only from the verdicts JSON written by check_items.py
(--json). This script does not run the checking rules again, and nothing in
the draft can change what is allowed. Standard library only. Nothing is sent.

Usage:
    python3 scripts/verify_draft.py --draft <draft.md> --verdicts <results.json> \
        --dnf <do-not-feature.md> --last <last-newsletter.md>

Exit code: 0 if every check passes (warnings allowed), 1 if any check fails,
2 if a file could not be read.
"""

import argparse
import json
import re
import sys
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s<>\"'\]]+")
TRAILING_PUNCTUATION = ".,;:!?)"
DNF_RE = re.compile(r"^- (.+?) - asked")
ZERO_WIDTH = ("​", "‌", "‍", "⁠", "﻿")


# ---------------------------------------------------------------------------
# Reading the inputs

def _urls(text):
    """Every URL in the text, without trailing punctuation."""
    return [u.rstrip(TRAILING_PUNCTUATION) for u in URL_RE.findall(text)]


def _same_url(url):
    """A URL in a form that can be compared: lower case, no trailing slash."""
    return url.lower().rstrip("/")


def read_last_urls(path):
    return _urls(Path(path).read_text(encoding="utf-8"))


def read_dnf_names(path):
    names = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = DNF_RE.match(line)
        if match:
            names.append(match.group(1).strip())
    return names


def _name_in(name, text):
    """True if the name appears as whole words, ignoring case."""
    return re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text, re.IGNORECASE) is not None


def _normalise_subject(entry):
    """The name to look for. Events drop "(...)" and keep only the part before a colon."""
    name = entry.get("subject") or ""
    if entry.get("type") == "event":
        name = re.sub(r"\([^)]*\)", "", name).split(":", 1)[0]
    return " ".join(name.split())


def _list(things):
    """"A", "A and B", "A, B and C"."""
    things = list(things)
    return things[0] if len(things) == 1 else ", ".join(things[:-1]) + " and " + things[-1]


def hidden_lines(lines):
    """Line numbers that contain hidden text: any part of an HTML comment
    (including every line of a comment that spans several lines, or one that
    never closes) or an invisible character.

    These lines are never shown in any message and are left out of the other
    checks; check 7 fails for them instead.
    """
    hidden, inside = set(), False
    for n, line in enumerate(lines, 1):
        touched, rest = inside, line
        while True:
            if inside:
                end = rest.find("-->")
                if end < 0:
                    break
                rest, inside = rest[end + 3:], False
            else:
                start = rest.find("<!--")
                if start < 0:
                    break
                rest, inside, touched = rest[start + 4:], True, True
        if touched or "-->" in line or any(ch in line for ch in ZERO_WIDTH):
            hidden.add(n)
    return hidden


def _bullets(lines):
    return [(n, line) for n, line in enumerate(lines, 1) if line.lstrip().startswith("- ")]


# ---------------------------------------------------------------------------
# Checks. Each returns (passed, message).

def check_bullets_have_links(lines):
    """1. Every bullet ends with a source link, so every bullet needs a URL."""
    missing = [n for n, line in _bullets(lines) if not _urls(line)]
    if missing:
        where = _list(f"line {n}" for n in missing)
        return False, f"FAIL: {where} {'is a bullet' if len(missing) == 1 else 'are bullets'} without a source link."
    return True, "PASS: every bullet has a source link."


def check_links_are_ready(text, verdicts):
    """2. Every link must be the link of an item that is ready for this issue."""
    ready = {_same_url(e["link"]) for e in verdicts["items"] if e["status"] == "ready" and e.get("link")}
    bad = list(dict.fromkeys(u for u in _urls(text) if _same_url(u) not in ready))
    if bad:
        return False, f"FAIL: the draft links to {_list(bad)}, which {'is' if len(bad) == 1 else 'are'} not one of the items ready for this issue."
    return True, "PASS: every link in the draft belongs to an item that is ready for this issue."


def check_not_in_last_issue(text, last_urls):
    """3. Nothing that went out in the last newsletter is linked again."""
    last = {_same_url(u) for u in last_urls}
    repeats = list(dict.fromkeys(u for u in _urls(text) if _same_url(u) in last))
    if repeats:
        return False, f"FAIL: the draft links to {_list(repeats)}, which was already in the last newsletter."
    return True, "PASS: nothing from the last newsletter is linked again."


def check_do_not_feature(text, dnf_names):
    """4. Nobody on the do-not-feature list is named anywhere."""
    named = [name for name in dnf_names if _name_in(name, text)]
    if named:
        return False, f"FAIL: the draft names {_list(named)}, who asked not to be named in any Volta channel."
    return True, "PASS: nobody from the do-not-feature list is named."


def check_only_ready_subjects(text, verdicts):
    """5. No company, person, event or program that is not ready is named.

    A name that also belongs to a ready item is allowed (for example a company
    with one ready item and one skipped duplicate).
    """
    ready = {_normalise_subject(e).lower() for e in verdicts["items"] if e["status"] == "ready"}
    not_ready = []
    for entry in verdicts["items"]:
        name = _normalise_subject(entry)
        if entry["status"] != "ready" and name and name.lower() not in ready and name not in not_ready:
            not_ready.append(name)
    named = [name for name in not_ready if _name_in(name, text)]
    if named:
        return False, f"FAIL: the draft names {_list(named)}, which {'is' if len(named) == 1 else 'are'} not ready for this issue. See the report for why."
    return True, "PASS: the draft only names things that are ready for this issue."


def check_redactions(text, verdicts):
    """6. Names that ready items must leave out are not in the draft."""
    names = []
    for entry in verdicts["items"]:
        if entry["status"] == "ready":
            names += [n for n in entry.get("redact", []) if n not in names]
    named = [name for name in names if _name_in(name, text)]
    if named:
        return False, f"FAIL: the draft names {_list(named)}, which must be left out (they asked not to be named)."
    return True, "PASS: names that must be left out are not in the draft."


def check_no_hidden_text(hidden):
    """7. No HTML comments and no invisible characters. Only line numbers are shown."""
    if hidden:
        numbers = sorted(hidden)
        if len(numbers) == 1:
            return False, f"FAIL: line {numbers[0]} contains hidden text."
        return False, f"FAIL: lines {_list(str(n) for n in numbers)} contain hidden text."
    return True, "PASS: no hidden text in the draft."


def warn_unlinked_text(lines):
    """Soft check: text that is neither a heading nor a bullet has no source link."""
    warnings = []
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("- "):
            warnings.append(f'WARN: line {n} is not a heading or a bullet, so it has no source link. Please read it: "{stripped[:80]}"')
    return warnings


def run_checks(draft_text, verdicts, dnf_names, last_urls):
    """All checks in order.

    Returns a list of (check, level, message): check is 1-7 (or 0 for a
    warning), level is PASS, FAIL or WARN.
    """
    all_lines = draft_text.splitlines()
    hidden = hidden_lines(all_lines)
    # Checks 1-6 and the warning only see visible lines, so no message can
    # ever repeat hidden text. Line numbers stay the same.
    lines = ["" if n in hidden else line for n, line in enumerate(all_lines, 1)]
    text = "\n".join(lines)
    results = [
        check_bullets_have_links(lines),
        check_links_are_ready(text, verdicts),
        check_not_in_last_issue(text, last_urls),
        check_do_not_feature(text, dnf_names),
        check_only_ready_subjects(text, verdicts),
        check_redactions(text, verdicts),
        check_no_hidden_text(hidden),
    ]
    out = [(n, "PASS" if passed else "FAIL", message) for n, (passed, message) in enumerate(results, 1)]
    out += [(0, "WARN", message) for message in warn_unlinked_text(lines)]
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a newsletter draft before Bader uses it.")
    parser.add_argument("--draft", required=True, help="the draft (.md)")
    parser.add_argument("--verdicts", required=True, help="the JSON written by check_items.py --json")
    parser.add_argument("--dnf", required=True, help="do-not-feature.md")
    parser.add_argument("--last", required=True, help="last-newsletter.md")
    args = parser.parse_args(argv)

    try:
        draft_text = Path(args.draft).read_text(encoding="utf-8")
        verdicts = json.loads(Path(args.verdicts).read_text(encoding="utf-8"))
        dnf_names = read_dnf_names(args.dnf)
        last_urls = read_last_urls(args.last)
    except (OSError, ValueError) as error:
        print(f"Could not read one of the files: {error}", file=sys.stderr)
        return 2

    results = run_checks(draft_text, verdicts, dnf_names, last_urls)
    for _, _, message in results:
        print(message)
    return 1 if any(level == "FAIL" for _, level, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
