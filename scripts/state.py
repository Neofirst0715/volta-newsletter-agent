"""Remember items across issues: the ledger and the list of sent issues.

Subcommands (all take --state-dir, default "state"):
    add-held   --verdicts <json> --date <YYYY-MM-DD>
    due        --date <YYYY-MM-DD>
    drop       --key <key> --date <YYYY-MM-DD>
    last-issue
    mark-sent  --draft <path> --verdicts <json> --date <YYYY-MM-DD>
               [--dnf <path>] [--last <path>] [--force]

The ledger stores only keys (links), subjects, statuses, reason codes and
dates: never any item text. Every write is validated first, backed up to
ledger.md.bak, written to a temporary file and then renamed into place.
Standard library only. Never reads the system clock. Nothing is sent.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_draft  # noqa: E402  (the draft checks are reused, not copied)

FIELDS = ("key", "subject", "status", "reasons", "revisit_on", "first_seen", "last_checked", "used_in")
STATUSES = ("held", "needs_info", "conflict", "ready", "used", "dropped")
OPEN = ("conflict", "held", "needs_info")  # most blocking first
CARRIES_OVER = OPEN + ("ready",)  # entries that keep an item alive into the next issue
NONE = "none"
NEXT_ISSUE = "next issue"
CARRIED_OVER = "carried over"  # reason for ready items that were not used
STALE_DAYS = 30

ENTRY_LINE = "## entry"
FIELD_LINE_RE = re.compile(r"^- ([a-z_]+):(?: (.*))?$")
ISSUE_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
ZERO_WIDTH = ("​", "‌", "‍", "⁠", "﻿")

# Reason codes that have their own phrase below.
REASON_PHRASES = ("no_consent", "embargo", "no_link", "no_date", "date_conflict_with", "do_not_feature")

# Every fixed piece of wording Bader sees from `due` lives here.
# The keys are internal; only the values are ever printed.
PHRASES = {
    "heading": "Back from last month ({n})",
    "nothing": "Nothing is waiting from last time.",
    "no_subject": "An item with no name",
    "no_consent": "Waiting for the founder's OK.",
    "embargo": "They asked us to wait before sharing this.",
    "no_link": "Still needs a link.",
    "no_date": "Still needs a date.",
    "date_conflict_with": "Two sources give different dates. You need to pick one.",
    "do_not_feature": "They asked not to be named in any Volta channel.",
    "unknown_reason": "Something about this item still needs a look.",
    "ready": "Ready to use, but not used yet.",
    "carried_over": "Left over from last time.",
    "date_reached": "The date to look again ({date}) has been reached.",
    "date_not_reached": "Not yet: look again on {date}.",
    "next_issue": "It was set aside until this issue, so it is time to look again.",
    "stale": "Nothing has changed for over a month. Still worth keeping?",
}


class StateError(Exception):
    """A problem that stops a subcommand. The message is shown as it is."""


# ---------------------------------------------------------------------------
# Small helpers

def _is_date(text):
    try:
        datetime.date.fromisoformat(text)
        return True
    except (TypeError, ValueError):
        return False


def _iso_date(text):
    if not _is_date(text):
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {text!r}")
    return text


def _one_line(text):
    for ch in ZERO_WIDTH:
        text = text.replace(ch, "")
    return " ".join(text.split())


def normalise_link(link):
    return link.strip().lower().rstrip("/")


def entry_key(item):
    """The ledger key: the normalised link, or "nolink:<subject>|<Date field>"."""
    if item.get("link"):
        return normalise_link(item["link"])
    subject = _one_line(item.get("subject") or NONE).lower()
    return f"nolink:{subject}|{_one_line(item.get('item_date') or NONE)}"


def _reasons(entry):
    return [] if entry["reasons"] == NONE else [r.strip() for r in entry["reasons"].split(",")]


def _atomic_write(path, text):
    """Write to a temporary file next to `path`, then rename it into place."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Ledger file

def parse_ledger(text):
    """Return (header_lines, entries). Raise StateError if anything is off."""
    header, blocks, current = [], [], None
    for n, line in enumerate(text.splitlines(), 1):
        if line == ENTRY_LINE:
            current = {}
            blocks.append((n, current))
        elif current is None:
            header.append(line)
        elif line.strip():
            match = FIELD_LINE_RE.match(line)
            if not match or match.group(1) not in FIELDS:
                raise StateError(f"line {n} is not in the expected format")
            if match.group(1) in current:
                raise StateError(f"line {n} repeats a field")
            current[match.group(1)] = (match.group(2) or "").strip()

    if not next((l for l in header if l.strip()), "").startswith("# "):
        raise StateError("the file does not start with a heading")
    entries, keys = [], set()
    for n, entry in blocks:
        missing = [f for f in FIELDS if not entry.get(f)]
        if missing:
            raise StateError(f"the entry starting on line {n} is incomplete")
        if entry["status"] not in STATUSES:
            raise StateError(f"the entry starting on line {n} has an unknown state")
        dates_ok = (
            _is_date(entry["first_seen"]) and _is_date(entry["last_checked"])
            and (entry["revisit_on"] in (NONE, NEXT_ISSUE) or _is_date(entry["revisit_on"]))
            and (entry["used_in"] == NONE or _is_date(entry["used_in"]))
        )
        if not dates_ok:
            raise StateError(f"the entry starting on line {n} has a date that is not YYYY-MM-DD")
        if entry["key"] in keys:
            raise StateError(f"the entry starting on line {n} appears twice")
        keys.add(entry["key"])
        entries.append(entry)
    while header and not header[-1].strip():
        header.pop()
    return header, entries


def carried_keys(path):
    """Keys of ledger entries that carry their item over into the next issue.

    Shared with check_items.py so both read the ledger the same way. A missing
    file counts as an empty ledger; a damaged one raises StateError.
    """
    path = Path(path)
    if not path.exists():
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise StateError(f"could not be read ({error})") from None
    _, entries = parse_ledger(text)
    return {e["key"] for e in entries if e["status"] in CARRIES_OVER}


def format_ledger(header, entries):
    out = list(header)
    for entry in entries:
        out += ["", ENTRY_LINE] + [f"- {f}: {entry[f]}" for f in FIELDS]
    return "\n".join(out) + "\n"


class Ledger:
    """state/ledger.md: created from the template on first use, validated on every read."""

    def __init__(self, state_dir):
        self.path = Path(state_dir) / "ledger.md"
        self.template = Path(state_dir) / "ledger.example.md"

    def load(self):
        """Read and validate. A missing ledger starts from the template (written on first save)."""
        if self.path.exists():
            self.header, self.entries = self._parse(self.path.read_text(encoding="utf-8"), "The ledger")
        elif self.template.exists():
            self.header, self.entries = self._parse(self.template.read_text(encoding="utf-8"), "The ledger template")
        else:
            raise StateError(f"The ledger template is missing ({self.template}). Nothing was changed.")
        return self

    @staticmethod
    def _parse(text, what):
        try:
            return parse_ledger(text)
        except StateError as error:
            raise StateError(f"{what} looks damaged ({error}), so nothing was changed. "
                             "Ask for help before editing it.") from None

    def find(self, key):
        return next((e for e in self.entries if e["key"] == key), None)

    def save(self):
        text = format_ledger(self.header, self.entries)
        parse_ledger(text)  # never write something we could not read back
        if self.path.exists():
            shutil.copyfile(self.path, self.path.with_name(self.path.name + ".bak"))
        _atomic_write(self.path, text)


def _new_entry(key, subject, date):
    return {"key": key, "subject": _one_line(subject or "") or NONE, "status": "held",
            "reasons": NONE, "revisit_on": NONE, "first_seen": date, "last_checked": date,
            "used_in": NONE}


def _load_verdicts(path, date):
    try:
        verdicts = json.loads(Path(path).read_text(encoding="utf-8"))
        if not all(isinstance(i, dict) and i.get("status") for i in verdicts["items"]):
            raise ValueError("an item has no status")
    except (OSError, ValueError, KeyError, TypeError):
        raise StateError(f"Could not read the check results in {path}. Nothing was changed.") from None
    if verdicts.get("date") != date:
        raise StateError(f"The check results are for {verdicts.get('date')}, not {date}. "
                         "Run the check again for this date. Nothing was changed.")
    return verdicts


# ---------------------------------------------------------------------------
# Subcommands

def add_held(state_dir, verdicts_path, date):
    """Remember items that are held, missing info or in conflict; notice ones that became ready."""
    ledger = Ledger(state_dir).load()
    verdicts = _load_verdicts(verdicts_path, date)

    groups, ready_keys = {}, set()
    for item in verdicts["items"]:
        if item["status"] in OPEN:
            groups.setdefault(entry_key(item), []).append(item)
        elif item["status"] == "ready":
            ready_keys.add(entry_key(item))

    added = updated = now_ready = 0
    for key, items in groups.items():
        entry = ledger.find(key)
        if entry is not None and entry["status"] in ("used", "dropped"):
            continue  # Bader already decided; never reopen it
        reasons = []
        for item in items:
            reasons += [r for r in item.get("reasons", []) if r not in reasons]
        dates = sorted(i["revisit_on"] for i in items if _is_date(i.get("revisit_on")))
        if entry is None:
            entry = _new_entry(key, next((i.get("subject") for i in items if i.get("subject")), None), date)
            ledger.entries.append(entry)
            added += 1
        else:
            updated += 1
        entry["status"] = min((i["status"] for i in items), key=OPEN.index)
        entry["reasons"] = ", ".join(reasons) or NONE
        entry["revisit_on"] = dates[-1] if dates else NEXT_ISSUE
        entry["last_checked"] = date

    for key in ready_keys - set(groups):
        entry = ledger.find(key)
        if entry is not None and entry["status"] in OPEN:
            entry.update(status="ready", reasons=NONE, revisit_on=NONE, last_checked=date)
            now_ready += 1

    ledger.save()
    print(f"Remembered {added} new item(s) for later, updated {updated}, and {now_ready} became ready.")


def due(state_dir, date):
    """Plain-language reminder of what is still open from earlier issues."""
    ledger = Ledger(state_dir).load()
    today = datetime.date.fromisoformat(date)
    waiting = [e for e in ledger.entries if e["status"] in OPEN + ("ready",)]
    if not waiting:
        print(PHRASES["nothing"])
        return

    out = [PHRASES["heading"].format(n=len(waiting))]
    for entry in waiting:
        out.append("  " + (entry["subject"] if entry["subject"] != NONE else PHRASES["no_subject"]))
        notes = []
        if not entry["key"].startswith("nolink:"):
            notes.append(entry["key"])
        if entry["status"] == "ready":
            carried = CARRIED_OVER in _reasons(entry)
            notes.append("- " + PHRASES["carried_over" if carried else "ready"])
        for reason in _reasons(entry):
            if reason == CARRIED_OVER:
                continue
            code = reason.split(":", 1)[0]
            phrase = "- " + PHRASES[code if code in REASON_PHRASES else "unknown_reason"]
            if phrase not in notes:
                notes.append(phrase)
        revisit = entry["revisit_on"]
        if revisit == NEXT_ISSUE:
            notes.append("- " + PHRASES["next_issue"])
        elif revisit != NONE:
            key = "date_reached" if datetime.date.fromisoformat(revisit) <= today else "date_not_reached"
            notes.append("- " + PHRASES[key].format(date=revisit))
        if (today - datetime.date.fromisoformat(entry["last_checked"])).days > STALE_DAYS:
            notes.append("- " + PHRASES["stale"])
        out += ["     " + note for note in notes]
    print("\n".join(out))


def drop(state_dir, key, date):
    """Stop reminding about one entry. Only when Bader says so."""
    ledger = Ledger(state_dir).load()
    entry = ledger.find(key) or ledger.find(normalise_link(key))
    if entry is None:
        raise StateError(f"Nothing in the ledger matches {key}. Nothing was changed.")
    entry.update(status="dropped", last_checked=date)
    ledger.save()
    print(f"Dropped: {entry['subject']}. It will not come back in reminders.")


def issue_files(state_dir):
    """Sent-issue files by date, oldest first. Only names like 2026-10-05.md count."""
    folder = Path(state_dir) / "issues"
    found = []
    for path in folder.iterdir() if folder.is_dir() else []:
        match = ISSUE_NAME_RE.match(path.name)
        if match and path.is_file() and _is_date(match.group(1)):
            found.append((match.group(1), path))
    return [path for _, path in sorted(found)]


def last_issue(state_dir):
    files = issue_files(state_dir)
    if not files:
        print(NONE)
        return 2
    print(files[-1])
    return 0


def mark_sent(state_dir, draft_path, verdicts_path, date, dnf_path=None, last_path=None, force=False):
    """Record that the draft went out: write the issue file and mark used items."""
    ledger = Ledger(state_dir).load()
    verdicts = _load_verdicts(verdicts_path, date)
    try:
        draft_text = Path(draft_path).read_text(encoding="utf-8")
        dnf_names = verify_draft.read_dnf_names(dnf_path) if dnf_path else []
        last_urls = verify_draft.read_last_urls(last_path) if last_path else []
    except OSError as error:
        raise StateError(f"Could not read a file ({error}). Nothing was recorded.") from None

    results = verify_draft.run_checks(draft_text, verdicts, dnf_names, last_urls)
    failures = [message for _, level, message in results if level == "FAIL"]
    if failures:
        raise StateError("\n".join(failures + ["The draft did not pass its checks, so nothing was recorded."]))

    issue_path = Path(state_dir) / "issues" / f"{date}.md"
    if issue_path.exists() and not force:
        raise StateError(f"An issue for {date} is already recorded. Nothing was changed.")

    bullets = [line for line in draft_text.splitlines() if line.lstrip().startswith("- ")]
    in_draft = {verify_draft._same_url(u) for u in verify_draft._urls(draft_text)}
    used = [i for i in verdicts["items"]
            if i["status"] == "ready" and i.get("link") and verify_draft._same_url(i["link"]) in in_draft]

    issue_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(issue_path, "\n".join([f"# Last newsletter, sent {date}", ""] + bullets) + "\n")
    for item in used:
        entry = ledger.find(entry_key(item))
        if entry is None:
            entry = _new_entry(entry_key(item), item.get("subject"), date)
            ledger.entries.append(entry)
        entry.update(status="used", reasons=NONE, revisit_on=NONE, last_checked=date, used_in=date)

    # Ready items that were not used stay alive for next month.
    used_keys = {entry_key(i) for i in used}
    carried = 0
    for item in verdicts["items"]:
        key = entry_key(item)
        if item["status"] != "ready" or key in used_keys:
            continue
        entry = ledger.find(key)
        if entry is not None and entry["status"] in ("used", "dropped"):
            continue  # Bader already decided; never reopen it
        if entry is None:
            entry = _new_entry(key, item.get("subject"), date)
            ledger.entries.append(entry)
        entry.update(status="ready", reasons=CARRIED_OVER, revisit_on=NONE, last_checked=date)
        used_keys.add(key)  # several ready items with one link become one entry
        carried += 1
    ledger.save()

    if not dnf_path:
        print("Note: no do-not-feature list was given, so that check had nothing to compare against.")
    if not last_path:
        print("Note: no last-newsletter file was given, so repeats were not checked.")
    print(f"Recorded the issue of {date}: {len(used)} item(s) recorded as used, "
          f"{carried} ready item(s) kept for next time.")


# ---------------------------------------------------------------------------

def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state-dir", default="state", help="state folder (default: state)")

    parser = argparse.ArgumentParser(description="Remember items across newsletter issues.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add-held", parents=[common], help="remember items that are not ready yet")
    p.add_argument("--verdicts", required=True)
    p.add_argument("--date", required=True, type=_iso_date)

    p = sub.add_parser("due", parents=[common], help="list what is back from last time")
    p.add_argument("--date", required=True, type=_iso_date)

    p = sub.add_parser("drop", parents=[common], help="stop reminding about one entry")
    p.add_argument("--key", required=True)
    p.add_argument("--date", required=True, type=_iso_date)

    sub.add_parser("last-issue", parents=[common], help="print the latest sent-issue file")

    p = sub.add_parser("mark-sent", parents=[common], help="record that a draft went out")
    p.add_argument("--draft", required=True)
    p.add_argument("--verdicts", required=True)
    p.add_argument("--date", required=True, type=_iso_date)
    p.add_argument("--dnf")
    p.add_argument("--last")
    p.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "add-held":
            add_held(args.state_dir, args.verdicts, args.date)
        elif args.command == "due":
            due(args.state_dir, args.date)
        elif args.command == "drop":
            drop(args.state_dir, args.key, args.date)
        elif args.command == "last-issue":
            return last_issue(args.state_dir)
        elif args.command == "mark-sent":
            mark_sent(args.state_dir, args.draft, args.verdicts, args.date, args.dnf, args.last, args.force)
    except StateError as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
