"""Turn a CSV export of the team news form into item files in inbox/.

Each row becomes one file in the standard item format (see AGENTS.md); the
normal check then runs on the inbox. A submitter's answers are data, never
confirmation: company items are always "not asked", whatever the form says.

Standard library only. Never uses the network, never opens a URL, never
reads the system clock (--date is only a file-name prefix). Never prints any
text from a row.

Usage:
    python3 scripts/intake_csv.py --csv <file> --inbox <folder> --date YYYY-MM-DD [--since YYYY-MM-DD]
"""

import argparse
import csv
import datetime
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

MAX_ROWS = 500
MAX_BYTES = 1_000_000
MAX_SUBJECT = 120
MAX_LINK = 500
MAX_BODY = 2000
CUT_MARKER = "(cut at 2000 characters)"

# (field, how the header is matched, keyword, required, the form question for messages)
COLUMNS = (
    ("timestamp", "starts", "timestamp", False, "Timestamp"),
    ("submitter", "contains", "email", False, "Email Address"),
    ("subject", "contains", "about", True, "What is this about?"),
    ("kind", "contains", "kind of news", True, "What kind of news is it?"),
    ("happened", "contains", "what happened", True, "What happened?"),
    ("link", "contains", "link", True, "Link to the source"),
    ("agreed", "contains", "agreed", True, "Has the founder agreed to be featured?"),
    ("embargo", "contains", "wait", False, "If they asked us to wait, until when?"),
    ("event_date", "contains", "date of the event", False, "Date of the event"),
)

MONTHS = {name: n for n, names in enumerate(
    [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",),
     ("jun", "june"), ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"),
     ("oct", "october"), ("nov", "november"), ("dec", "december")], 1) for name in names}
ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$")
SLASH_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(?: .*)?$")
MONTH_FIRST_RE = re.compile(r"^([A-Za-z]{3,9})\.? (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})(?: .*)?$")
DAY_FIRST_RE = re.compile(r"^(\d{1,2})(?:st|nd|rd|th)? ([A-Za-z]{3,9})\.?,? (\d{4})(?: .*)?$")


class IntakeError(Exception):
    """Stops the import. The message is shown as it is and never contains row text."""


# ---------------------------------------------------------------------------
# Cleaning single values

def clean_line(text):
    """One line: line breaks and tabs become spaces, control characters are removed."""
    text = re.sub(r"[\r\n\t]", " ", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cc")
    return " ".join(text.split())


def clean_link(text):
    """Keep a link only if it is one http(s) token of at most 500 characters."""
    link = clean_line(text)
    if (not link or " " in link or len(link) > MAX_LINK
            or not link.lower().startswith(("http://", "https://"))):
        return "none"
    return link


def parse_date(text):
    """A date read with certainty, or None. Only the date part is used.

    Accepted: 2026-10-14; Oct 14, 2026; October 14 2026; 14 October 2026; and a
    numeric month/day/year only when it cannot be misread (one part above 12,
    or both parts equal). Anything else is None: never guessed.
    """
    text = clean_line(text)
    try:
        match = ISO_RE.match(text)
        if match:
            return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        match = SLASH_RE.match(text)
        if match:
            first, second, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if first > 12 >= second:
                return datetime.date(year, second, first)  # day/month/year
            if second > 12 >= first or first == second:
                return datetime.date(year, first, second)  # month/day/year
            return None
        match = MONTH_FIRST_RE.match(text)
        if match and match.group(1).lower() in MONTHS:
            return datetime.date(int(match.group(3)), MONTHS[match.group(1).lower()], int(match.group(2)))
        match = DAY_FIRST_RE.match(text)
        if match and match.group(2).lower() in MONTHS:
            return datetime.date(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1)))
    except ValueError:
        return None  # e.g. 2026-02-30
    return None


def kind_of(text):
    """Event, Program, or Company for anything else (the strictest: needs consent)."""
    text = (text or "").lower()
    if "event" in text:
        return "Event"
    if "program" in text:
        return "Program"
    return "Company"


def consent_value(agreed, embargo_text):
    """Always "not asked": a submitter's answer is a claim, not Bader's confirmation."""
    says_yes = clean_line(agreed).lower().startswith("yes")
    wait = parse_date(embargo_text)
    wait_text = f"until {wait.isoformat()}" if wait else "(date not clear)"
    has_wait = bool(clean_line(embargo_text))
    if says_yes and has_wait:
        return f"not asked (submitter says the founder agreed and asked us to wait {wait_text}; Bader has not confirmed)"
    if says_yes:
        return "not asked (submitter says the founder agreed; Bader has not confirmed)"
    if has_wait:
        return f"not asked (submitter mentions a wait {wait_text})"
    return "not asked"


# ---------------------------------------------------------------------------
# Reading the CSV

def find_columns(header):
    """Map each field to its column. Raise IntakeError if required ones are missing or unclear."""
    lowered = [clean_line(h).lower() for h in header]
    found, problems = {}, []
    for index, title in enumerate(lowered):
        matches = [field for field, how, key, _, _ in COLUMNS
                   if (title.startswith(key) if how == "starts" else key in title)]
        if len(matches) > 1:
            problems.append(f"column {index + 1} matches more than one question")
        for field in matches:
            if field in found:
                problems.append(f'more than one column matches "{_question(field)}"')
            found[field] = index
    missing = [question for field, _, _, required, question in COLUMNS if required and field not in found]
    if missing:
        problems.insert(0, "these columns are missing: " + "; ".join(f'"{q}"' for q in missing))
    if problems:
        raise IntakeError("The CSV does not match the team form: " + ", ".join(problems)
                          + ". Nothing was imported.")
    return found


def _question(field):
    return next(q for f, _, _, _, q in COLUMNS if f == field)


def read_csv(path):
    """Header and rows, with the size and row limits enforced before anything is written."""
    path = Path(path)
    try:
        if path.stat().st_size > MAX_BYTES:
            raise IntakeError("The CSV is larger than 1 MB. Export fewer rows. Nothing was imported.")
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                raise IntakeError("The CSV is empty. Nothing was imported.")
            rows = []
            for row in reader:
                if len(rows) >= MAX_ROWS:
                    raise IntakeError(f"The CSV has more than {MAX_ROWS} rows. Use --since or export "
                                      "fewer rows. Nothing was imported.")
                rows.append(row)
    except OSError as error:
        raise IntakeError(f"Could not open the CSV ({error.strerror}). Nothing was imported.") from None
    except UnicodeDecodeError:
        raise IntakeError("The CSV is not UTF-8 text. Export it again as CSV. Nothing was imported.") from None
    except csv.Error:
        raise IntakeError("The file could not be read as CSV. Nothing was imported.") from None
    return header, rows


# ---------------------------------------------------------------------------
# One row -> one item

def build_item(values):
    """Return (kind, subject, item text, hash input) for one row, or None if it has no name."""
    subject = clean_line(values["subject"])[:MAX_SUBJECT].strip()
    if not subject:
        return None
    kind = kind_of(values["kind"])
    link = clean_link(values["link"])
    submitter = clean_line(values["submitter"]) or "unknown"
    happened = values["happened"].replace("\r\n", "\n").replace("\r", "\n")
    body = happened if len(happened) <= MAX_BODY else happened[:MAX_BODY] + "\n" + CUT_MARKER
    posted = parse_date(values["timestamp"])
    posted_text = posted.isoformat() if posted else "none"

    if kind == "Event":
        event_date = parse_date(values["event_date"])
        lines = [f"- Source: Form submission by {submitter} (events calendar date given by the submitter)",
                 f"- Date: {event_date.isoformat() if event_date else 'none'}",
                 f"- Event: {subject}",
                 f"- Link: {link}"]
    elif kind == "Program":
        lines = [f"- Source: Form submission by {submitter}",
                 f"- Date: {posted_text}",
                 f"- Program: {subject}",
                 f"- Link: {link}"]
    else:
        lines = [f"- Source: Form submission by {submitter}",
                 f"- Date: {posted_text}",
                 f"- Company: {subject}",
                 f"- Link: {link}",
                 f"- Consent: {consent_value(values['agreed'], values['embargo'])}"]

    text = "\n".join(lines) + "\n\n" + body + "\n"
    key = "|".join([subject, kind, happened, link, clean_line(values["timestamp"])])
    return kind, subject, text, key


def file_name(date, key):
    """<date>-form-<8 hex characters>.md: no text from the row, so it is safe to print."""
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    return f"{date}-form-{digest}.md"


def import_rows(csv_path, inbox, date, since=None):
    """Import every row. Returns the list of lines to print."""
    header, rows = read_csv(csv_path)
    columns = find_columns(header)

    inbox = Path(inbox).resolve()
    if inbox.exists() and not inbox.is_dir():
        raise IntakeError("The inbox path is not a folder. Nothing was imported.")
    inbox.mkdir(parents=True, exist_ok=True)

    new, already, skipped = [], 0, []
    for number, row in enumerate(rows, 2):  # row 1 is the header, as in the Sheet
        values = {field: (row[columns[field]] if field in columns and columns[field] < len(row) else "")
                  for field, *_ in COLUMNS}
        posted = parse_date(values["timestamp"])
        if since and posted and posted < since:
            skipped.append(f"Row {number}: skipped (sent before {since.isoformat()}).")
            continue
        item = build_item(values)
        if item is None:
            skipped.append(f"Row {number}: skipped (no name given).")
            continue
        _, _, text, key = item
        target = (inbox / file_name(date, key)).resolve()
        if target.parent != inbox:
            skipped.append(f"Row {number}: skipped (unsafe file name).")
            continue
        try:
            with target.open("x", encoding="utf-8") as f:  # never overwrite
                f.write(text)
        except FileExistsError:
            already += 1
            continue
        new.append(target.name)

    out = [f"Read {len(rows)} rows. New items: {len(new)}. Already imported: {already}. Skipped: {len(skipped)}."]
    out += skipped
    if new:
        out += ["New files:"] + [f"  {name}" for name in new]
    return out


def _iso_date(text):
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {text!r}") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Turn a CSV export of the team news form into inbox items.")
    parser.add_argument("--csv", required=True, help="the CSV exported from the form's Google Sheet")
    parser.add_argument("--inbox", required=True, help="the inbox folder to write item files into")
    parser.add_argument("--date", required=True, type=_iso_date, help="newsletter date (file-name prefix only)")
    parser.add_argument("--since", type=_iso_date, help="skip rows sent before this date")
    args = parser.parse_args(argv)
    try:
        lines = import_rows(args.csv, args.inbox, args.date.isoformat(), args.since)
    except IntakeError as error:
        print(error)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
