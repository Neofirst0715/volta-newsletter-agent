"""Read Volta newsletter items and reference lists.

Parsing (step 3a), rules via evaluate() (step 3b), JSON and report (step 3c).
Standard library only. Never reads the system clock: the newsletter date
is always passed in with --date. Nothing is sent anywhere.

Usage:
    python3 scripts/check_items.py --items <file-or-folder> --last <file> \
        --dnf <file> --date YYYY-MM-DD [--json <path>] [--report <path>]
        [--ledger <state/ledger.md>] [--dump]
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state  # noqa: E402  (the ledger is read with state.py's own code, never a copy)

# Only these bullet names count as fields. Anything else is body text.
KNOWN_FIELDS = ("Source", "Date", "Company", "Person", "Event", "Program", "Link", "Consent")

SECTION_RE = re.compile(r"^## (\S+)\s*$")
FIELD_RE = re.compile(r"^- ([A-Za-z]+): ")
COMMENT_RE = re.compile(r"<!--.*?(-->|\Z)", re.DOTALL)  # an unclosed comment runs to the end
URL_RE = re.compile(r"https?://\S+")
SENT_RE = re.compile(r"\bsent (\d{4}-\d{2}-\d{2})\b")
DNF_RE = re.compile(r"^- (.+?) - asked")
# The start of a Consent value. Only this part is used; anything after it
# (such as evidence in brackets) is kept as written but never read by the rules.
CONSENT_KEYWORD_RE = re.compile(
    r"^(yes|not\s+asked|embargoed\s+until(?:\s+\d{4}-\d{2}-\d{2})?)(?![\w-])", re.IGNORECASE)


def _item_type(fields):
    if "Company" in fields or "Person" in fields:
        return "story"
    if "Event" in fields:
        return "event"
    if "Program" in fields:
        return "program"
    return None  # unknown: left for later checks to report, not guessed


def _consent_keyword(value):
    """The keyword at the start of a Consent value, or "" if there is none.

    "yes (Bader confirmed ...)"            -> "yes"
    "embargoed until 2026-10-20 (... 2026-09-01 ...)" -> "embargoed until 2026-10-20"
    "embargoed until Oct 20"               -> "embargoed until" (no usable date)
    "maybe", "yesterday someone said so"   -> "" (not consent)
    """
    match = CONSENT_KEYWORD_RE.match(value.strip())
    return " ".join(match.group(1).split()) if match else ""


def _blank_comments(text):
    """Remove HTML comments but keep their line breaks, so line numbers still match."""
    return COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _parse_section(item_id, lines):
    """Turn the lines of one item into a dict.

    HTML comments are removed first, so nothing inside a comment can become
    a field. Fields come only from the unbroken block of known "- Field: value"
    lines at the top. The first other line (including a blank one) ends the
    block; everything after it is body text, even if it looks like a field.
    """
    clean_lines = _blank_comments("\n".join(lines)).split("\n")

    i = 0
    while i < len(clean_lines) and not clean_lines[i].strip():
        i += 1  # skip blank lines before the field block
    fields = {}
    field_rows = set()
    while i < len(clean_lines):
        match = FIELD_RE.match(clean_lines[i])
        if not match or match.group(1) not in KNOWN_FIELDS:
            break
        name, value = clean_lines[i][2:].split(": ", 1)  # first ": " only
        fields.setdefault(name, value.strip())
        if clean_lines[i] == lines[i]:
            field_rows.add(i)  # a field line that had a comment stays visible in raw_text
        i += 1

    # Rules only ever see the consent keyword; the full value is kept as written.
    consent_as_written = fields.get("Consent")
    if consent_as_written is not None:
        fields["Consent"] = _consent_keyword(consent_as_written)

    # raw_text is everything as written except the plain field lines.
    raw_text = "\n".join(l for n, l in enumerate(lines) if n not in field_rows).strip("\n")
    clean_text = "\n".join(clean_lines[i:]).strip()
    return {
        "id": item_id,
        "fields": fields,
        "consent_as_written": consent_as_written,
        "raw_text": raw_text,
        "clean_text": clean_text,
        "type": _item_type(fields),
    }


def _parse_items_file(path):
    items = []
    current_id, current_lines = None, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = SECTION_RE.match(line)
        if match:
            if current_id is not None:
                items.append(_parse_section(current_id, current_lines))
            current_id, current_lines = match.group(1), []
        elif current_id is not None:
            current_lines.append(line)
    if current_id is not None:
        items.append(_parse_section(current_id, current_lines))
    return items


def parse_items(path):
    """Read one items file, or a folder where each .md file is one item.

    In a folder, other files and hidden files (names starting with ".", such
    as .gitkeep or macOS "._" copies) are ignored.
    """
    path = Path(path)
    if path.is_dir():
        return [
            _parse_section(f.stem, f.read_text(encoding="utf-8").splitlines())
            for f in sorted(path.glob("*.md"))
            if f.is_file() and not f.name.startswith(".")
        ]
    return _parse_items_file(path)


def parse_last_newsletter(path):
    """Return {"sent": "YYYY-MM-DD" or None, "urls": [...]}."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    header = next((l for l in lines if l.startswith("# ")), "")
    sent = SENT_RE.search(header)
    urls = [u for l in lines for u in URL_RE.findall(l)]
    return {"sent": sent.group(1) if sent else None, "urls": urls}


def parse_do_not_feature(path):
    """Return the names on the do-not-feature list."""
    names = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = DNF_RE.match(line)
        if match:
            names.append(match.group(1).strip())
    return names


# ---------------------------------------------------------------------------
# Rules (Step 3b). Each rule looks only at structured fields and returns what
# it found. Body text is only ever searched (names, suspicious phrases); it can
# never make an item "more ready".

# Most blocking first.
STATUS_ORDER = ("skip", "conflict", "held", "needs_info", "ready")

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
EMBARGO_RE = re.compile(r"^embargoed until\b(.*)$", re.IGNORECASE)
ZERO_WIDTH = ("​", "‌", "‍", "⁠", "﻿")
INSTRUCTION_RES = (
    re.compile(r"ignore (all |your )?previous", re.IGNORECASE),
    re.compile(r"note to the ai", re.IGNORECASE),
    re.compile(r"mark its consent", re.IGNORECASE),
    re.compile(r"\bmake\b.{0,60}\bthe lead\b", re.IGNORECASE | re.DOTALL),
)


def _last_date(text):
    """Last YYYY-MM-DD in the text as a date (the end of a range), or None."""
    found = DATE_RE.findall(text or "")
    if not found:
        return None
    try:
        return datetime.date.fromisoformat(found[-1])
    except ValueError:
        return None


def _link(item):
    """The item's link, or None if it is missing, empty or "none"."""
    link = item["fields"].get("Link", "").strip()
    if not link or link.lower() == "none":
        return None
    return link.rstrip("/")


def _consent_kind(item):
    """"yes", "embargoed" or "not_asked" (anything else counts as not asked)."""
    consent = item["fields"].get("Consent", "").strip().lower()
    if consent.startswith("yes"):
        return "yes"
    if EMBARGO_RE.match(consent):
        return "embargoed"
    return "not_asked"


def rule_no_link(item):
    """Rule 1: no usable link means Bader needs to find one."""
    if _link(item) is None:
        return [("needs_info", "no_link")]
    return []


def rule_consent(item, newsletter_date):
    """Rule 2: stories need the founder's OK. Events and programs do not.

    Returns (findings, revisit_on).
    """
    if item["type"] != "story":
        return [], None
    kind = _consent_kind(item)
    if kind == "yes":
        return [], None
    if kind == "embargoed":
        until = _last_date(item["fields"]["Consent"])
        if until is None:
            return [("held", "embargo")], None  # embargo with no readable date: wait for Bader
        if until > newsletter_date:
            return [("held", "embargo")], until.isoformat()
        return [], None
    return [("held", "no_consent")], None


def rule_dates(item, newsletter_date, last_date, carried_over=False):
    """Rule 3: past events and news from before the last newsletter are skipped.

    For calendar items the Date is when the event happens. For everything
    else it is when the news was posted or sent. A missing date is reported,
    never guessed: a calendar event without a date needs info; for anything
    else it is only noted and the status is unchanged.

    carried_over (only ever set from the ledger file, never from item text)
    exempts the item from the old-news check and nothing else.
    """
    when = _last_date(item["fields"].get("Date"))
    calendar = "events calendar" in item["fields"].get("Source", "").lower()
    if when is None:
        return [("needs_info" if calendar else "ready", "no_date")]
    if calendar:
        if when < newsletter_date:
            return [("skip", "past_event")]
    elif when < last_date and not carried_over:
        return [("skip", "old_news")]
    return []


def rule_repeat_of_last_issue(item, last_urls):
    """Rules 4 and 8: skip only if this exact link already went out.

    Matching is on the link (the same news), not the company, so a new
    milestone from a company in the last issue is not a repeat.
    """
    link = _link(item)
    if link is not None and link in last_urls:
        return [("skip", "repeat_of_last_issue")]
    return []


def _event_name(item):
    """The Event name for comparing: lower case, no text in brackets, no
    punctuation, single spaces. "Build Weekend (hackathon)" -> "build weekend"."""
    name = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", item["fields"].get("Event", "").lower())
    name = re.sub(r"[^\w\s]", " ", name)
    return " ".join(name.split())


def rule_same_link_in_batch(items):
    """Rule 5: items in this batch that share a link.

    Stories: keep the one with the best consent (yes > embargoed > not asked,
    tie goes to the first) and skip the others as duplicates.
    Events: two items are a conflict for Bader to resolve only if they have the
    same link, the same event name (see _event_name) and different Source text.
    Different events that merely share a page link (such as an events calendar
    page) are not a conflict.
    Returns {item id: [findings]}.
    """
    rank = {"yes": 0, "embargoed": 1, "not_asked": 2}
    groups = {}
    for item in items:
        link = _link(item)
        if link is not None:
            groups.setdefault(link, []).append(item)

    findings = {}
    for group in groups.values():
        stories = [i for i in group if i["type"] == "story"]
        if len(stories) > 1:
            keep = min(stories, key=lambda i: rank[_consent_kind(i)])  # min keeps the first on a tie
            for other in stories:
                if other is not keep:
                    findings.setdefault(other["id"], []).append(("skip", f"duplicate_of:{keep['id']}"))

        events = [i for i in group if i["type"] == "event"]
        for a in events:
            for b in events:
                if (a is not b and _event_name(a) == _event_name(b)
                        and a["fields"].get("Source") != b["fields"].get("Source")):
                    findings.setdefault(a["id"], []).append(("conflict", f"date_conflict_with:{b['id']}"))
    return findings


def rule_do_not_feature(item, dnf_names):
    """Rule 6: people and companies who asked not to be named.

    Named in Company or Person: held. Named anywhere else (other fields or
    the body): status unchanged, but the names must be removed from the text.
    Returns (findings, names_to_redact).
    """
    subject = " ".join(item["fields"].get(f, "") for f in ("Company", "Person")).lower()
    elsewhere = " ".join(
        [v for f, v in item["fields"].items() if f not in ("Company", "Person")] + [item["raw_text"]]
    ).lower()

    findings, redact = [], []
    for name in dnf_names:
        if name.lower() in subject:
            findings.append(("held", "do_not_feature"))
        elif name.lower() in elsewhere:
            redact.append(name)
    return findings, redact


def rule_possible_instruction(item):
    """Rule 7: text that looks like it is talking to the AI.

    Only raises a flag for Bader. It never changes the status.
    """
    text = item["raw_text"] + "\n" + "\n".join(item["fields"].values())
    if "<!--" in text or any(ch in text for ch in ZERO_WIDTH):
        return True
    return any(r.search(text) for r in INSTRUCTION_RES)


def ledger_key(item):
    """The item's ledger key, made by state.py's own function."""
    return state.entry_key({"link": _given_link(item), "subject": _subject(item),
                            "item_date": item["fields"].get("Date", "").strip() or None})


def evaluate(items, last_info, dnf_names, newsletter_date, last_date, carried_keys=frozenset()):
    """Run every rule on every item and return {id: verdict}.

    A verdict is {status, reasons, flags, revisit_on, carried_over}. The most
    blocking status wins; every reason is kept. Dates are datetime.date values
    passed in by the caller; the system clock is never read. carried_keys come
    only from the ledger file (see state.carried_keys); empty means no ledger.
    """
    last_urls = {u.rstrip("/") for u in last_info["urls"]}
    batch = rule_same_link_in_batch(items)

    verdicts = {}
    for item in items:
        carried_over = bool(carried_keys) and ledger_key(item) in carried_keys
        consent, revisit_on = rule_consent(item, newsletter_date)
        dnf, redact = rule_do_not_feature(item, dnf_names)
        findings = (
            rule_no_link(item)
            + consent
            + rule_dates(item, newsletter_date, last_date, carried_over)
            + rule_repeat_of_last_issue(item, last_urls)
            + batch.get(item["id"], [])
            + dnf
        )

        statuses = [s for s, _ in findings] + ["ready"]
        reasons = []
        for _, reason in findings:
            if reason not in reasons:
                reasons.append(reason)
        flags = {}
        if redact:
            flags["redact"] = redact
        if rule_possible_instruction(item):
            flags["possible_instruction"] = True

        verdicts[item["id"]] = {
            "status": min(statuses, key=STATUS_ORDER.index),
            "reasons": reasons,
            "flags": flags,
            "revisit_on": revisit_on,
            "carried_over": carried_over,
        }
    return verdicts


# ---------------------------------------------------------------------------
# Outputs (Step 3c): machine-readable JSON and a plain-language report.
# The report never shows field names, reason codes or hidden (comment) text.

# Every fixed piece of report wording lives here, so it can be checked in
# one place. The keys are internal; only the values are ever printed.
PHRASES = {
    "title": "Newsletter check for {date}",
    "compared": "Compared with the last newsletter from {date}.",
    "heading_ready": "Ready to use",
    "heading_needs_info": "Needs you: missing info",
    "heading_waiting": "Waiting on someone else",
    "heading_conflict": "Conflicts to decide",
    "heading_left_out": "Left out for this issue, and why",
    "total": "In total there are {count} items: {parts} and {last}.",
    "total_ready": "{n} ready to use",
    "total_needs_info": "{n} missing info",
    "total_waiting": "{n} waiting on someone else",
    "total_conflict": "{n} in a conflict to decide",
    "total_left_out": "{n} left out",
    "no_link": "No link yet.",
    "no_date": "No date yet.",
    "no_consent": "Nobody has asked them for their OK yet.",
    "embargo": "They asked us not to share this until {date}.",
    "embargo_no_date": "They asked us to wait before sharing this, but gave no date.",
    "past_event": "Already happened ({date}).",
    "old_news": "Older than the last newsletter (posted {date}).",
    "repeat_of_last_issue": "Already in the last newsletter.",
    "duplicate_of": "Same news as [{id}].",
    "date_conflict_with": "Another source gives a different date, see [{id}].",
    "do_not_feature": "They asked not to be named in any Volta channel.",
    "unknown_reason": "Something about this item needs a look.",
    "redact": "Leave out the name of {name} (they asked not to be named).",
    "possible_instruction": "This item contained text that looks like instructions to an AI. It was ignored.",
    "conflict_heading": "{name}: the sources give different dates. Check which one is right.",
    "conflict_calendar": "[{id}] {source}: {date}",
    "conflict_quote": '[{id}] {source} ({date}) says: "{quote}"',
    "unknown_source": "Unknown source",
    "unknown_date": "no date",
    "event_fallback": "Event",
    "no_description": "No description given.",
    "nothing_to_check": "Nothing to check: there are no items in the inbox yet.",
}

# Report sections in order: (section key, heading phrase, total phrase).
SECTIONS = (
    ("ready", "heading_ready", "total_ready"),
    ("needs_info", "heading_needs_info", "total_needs_info"),
    ("waiting", "heading_waiting", "total_waiting"),
    ("conflict", "heading_conflict", "total_conflict"),
    ("left_out", "heading_left_out", "total_left_out"),
)

# The reasons that explain why an item is left out. In the Left-out section
# only these are shown.
LEFT_OUT_REASONS = ("past_event", "old_news", "repeat_of_last_issue", "duplicate_of:", "do_not_feature")

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
INDENT_ITEM, INDENT_NOTE = "  ", "       "


def _section(verdict):
    """Which report section an item goes in.

    Follows the status, except that do-not-feature items go to Left out:
    nobody is going to change their mind for this issue.
    """
    status = verdict["status"]
    if status == "skip" or (status == "held" and "do_not_feature" in verdict["reasons"]):
        return "left_out"
    return {"held": "waiting"}.get(status, status)


def _one_line(text):
    """Text on a single line, without invisible characters."""
    for ch in ZERO_WIDTH:
        text = text.replace(ch, "")
    return " ".join(text.split())


def _shorten(text, limit):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _own_words(text, min_len=30, limit=160):
    """The first sentence (or two, if the first is very short) of the item's own text."""
    words = ""
    for sentence in SENTENCE_RE.split(_one_line(text)):
        words = f"{words} {sentence}".strip()
        if len(words) >= min_len:
            break
    return _shorten(words, limit)


def _given_link(item):
    """The link exactly as written, or None when there is no usable link."""
    return item["fields"]["Link"].strip() if _link(item) else None


def describe(item):
    """A short description from the item's own words: never invented."""
    fields = item["fields"]
    if item["type"] == "event":
        name = _one_line(fields.get("Event", "")) or PHRASES["event_fallback"]
        when = _one_line(fields.get("Date", ""))
        return f"{name} ({when})" if when else name
    words = _own_words(item["clean_text"])
    name = _one_line(fields.get("Program") or fields.get("Company") or fields.get("Person") or "")
    if name.lower().startswith("none"):
        name = ""
    if name and name.lower() not in words.lower():
        return f"{name}: {words}" if words else name
    return words or name or PHRASES["no_description"]


def _plain_reason(reason, item, verdict):
    """One reason code in plain words for Bader."""
    code, _, other_id = reason.partition(":")
    when = _last_date(item["fields"].get("Date"))
    if code == "embargo" and verdict["revisit_on"]:
        return PHRASES["embargo"].format(date=verdict["revisit_on"])
    if code == "embargo":
        return PHRASES["embargo_no_date"]
    if code in ("past_event", "old_news"):
        return PHRASES[code].format(date=when.isoformat())
    if code in ("duplicate_of", "date_conflict_with"):
        return PHRASES[code].format(id=other_id)
    if code in ("no_link", "no_date", "no_consent", "repeat_of_last_issue", "do_not_feature"):
        return PHRASES[code]
    return PHRASES["unknown_reason"]


def _notes(item, verdict, section):
    """The indented lines under an item: link, reasons in plain words, flags.

    Left-out items only say why they are left out. Conflict items leave out
    the conflict itself, because their group heading already says it.
    """
    lines = []
    link = _given_link(item)
    if link:
        lines.append(link)
    for reason in verdict["reasons"]:
        if section == "left_out" and not reason.startswith(LEFT_OUT_REASONS):
            continue
        if section == "conflict" and reason.startswith("date_conflict_with:"):
            continue
        lines.append("- " + _plain_reason(reason, item, verdict))
    if section != "left_out":
        for name in verdict["flags"].get("redact", []):
            lines.append("- " + PHRASES["redact"].format(name=name))
    if verdict["flags"].get("possible_instruction"):
        lines.append("- " + PHRASES["possible_instruction"])
    return [INDENT_NOTE + line for line in lines]


def _conflict_lines(conflict_ids, by_id, verdicts):
    """Group items that conflict with each other and show their dates side by side."""
    lines, seen = [], set()
    for first in conflict_ids:
        if first in seen:
            continue
        group, todo = [], [first]
        while todo:  # collect everything linked to `first`
            item_id = todo.pop()
            if item_id in seen or item_id not in by_id:
                continue
            seen.add(item_id)
            group.append(item_id)
            todo += [r.split(":", 1)[1] for r in verdicts[item_id]["reasons"]
                     if r.startswith("date_conflict_with:")]
        group.sort()

        name = _one_line(by_id[group[0]]["fields"].get("Event", "")) or describe(by_id[group[0]])
        lines.append(INDENT_ITEM + PHRASES["conflict_heading"].format(name=name))
        for item_id in group:
            item = by_id[item_id]
            source = _one_line(item["fields"].get("Source", "")) or PHRASES["unknown_source"]
            date = _one_line(item["fields"].get("Date", "")) or PHRASES["unknown_date"]
            if "events calendar" in source.lower():
                line = PHRASES["conflict_calendar"].format(id=item_id, source=source, date=date)
            else:
                quote = _shorten(_one_line(item["clean_text"]), 200)
                line = PHRASES["conflict_quote"].format(id=item_id, source=source, date=date, quote=quote)
            lines.append(INDENT_ITEM * 2 + line)
            lines += _notes(item, verdicts[item_id], "conflict")
    return lines


def build_report(items, verdicts, newsletter_date, last_date):
    """The plain-language report for Bader, as one string."""
    by_id = {item["id"]: item for item in items}
    ids = sorted(by_id)
    out = [
        PHRASES["title"].format(date=newsletter_date.isoformat()),
        PHRASES["compared"].format(date=last_date.isoformat()),
    ]
    if not ids:
        return "\n".join(out + ["", PHRASES["nothing_to_check"]]) + "\n"
    totals = []
    for section, heading, total in SECTIONS:
        section_ids = [i for i in ids if _section(verdicts[i]) == section]
        totals.append(PHRASES[total].format(n=len(section_ids)))
        if not section_ids:
            continue
        out += ["", f"{PHRASES[heading]} ({len(section_ids)})"]
        if section == "conflict":
            out += _conflict_lines(section_ids, by_id, verdicts)
            continue
        for item_id in section_ids:
            out.append(f"{INDENT_ITEM}[{item_id}] {describe(by_id[item_id])}")
            out += _notes(by_id[item_id], verdicts[item_id], section)

    out += ["", PHRASES["total"].format(count=len(ids), parts=", ".join(totals[:-1]), last=totals[-1])]
    return "\n".join(out) + "\n"


def _subject(item):
    """Who or what the item is about, exactly as written, or None."""
    for field in ("Company", "Person", "Event", "Program"):
        value = item["fields"].get(field, "").strip()
        if value:
            return value
    return None


def build_json(items, verdicts, newsletter_date, last_date):
    """Machine-readable results, sorted by id."""
    counts = {status: 0 for status in STATUS_ORDER}
    entries = []
    for item in sorted(items, key=lambda i: i["id"]):
        verdict = verdicts[item["id"]]
        counts[verdict["status"]] += 1
        entries.append({
            "id": item["id"],
            "type": item["type"],
            "subject": _subject(item),
            "item_date": item["fields"].get("Date", "").strip() or None,
            "status": verdict["status"],
            "reasons": verdict["reasons"],
            "flags": sorted(verdict["flags"]),
            "redact": verdict["flags"].get("redact", []),
            "link": _given_link(item),
            "revisit_on": verdict["revisit_on"],
            "clean_text": item["clean_text"],
        })
        if verdict.get("carried_over"):
            entries[-1]["carried_over"] = True
    return {
        "date": newsletter_date.isoformat(),
        "last_date": last_date.isoformat(),
        "counts": counts,
        "items": entries,
    }


def _iso_date(text):
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {text!r}")
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check newsletter items and write a report for Bader.")
    parser.add_argument("--items", required=True, help="items file or folder of item files")
    parser.add_argument("--last", required=True, help="last-newsletter.md")
    parser.add_argument("--dnf", required=True, help="do-not-feature.md")
    parser.add_argument("--date", required=True, type=_iso_date, help="newsletter date, YYYY-MM-DD")
    parser.add_argument("--dump", action="store_true", help="print the parsed data as JSON and stop")
    parser.add_argument("--json", help="write the machine-readable results to this path")
    parser.add_argument("--report", help="write the report to this path (default: print it)")
    parser.add_argument("--ledger", help="state/ledger.md: items carried over from earlier issues (optional)")
    args = parser.parse_args(argv)

    items = parse_items(args.items)
    last = parse_last_newsletter(args.last)
    dnf_names = parse_do_not_feature(args.dnf)

    if args.dump:
        data = {"items": items, "last_newsletter": last, "do_not_feature": dnf_names}
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    if last["sent"] is None:
        print(f'The "sent YYYY-MM-DD" date is missing from the title of {args.last}. '
              "Add it and run again.", file=sys.stderr)
        return 2

    carried_keys = frozenset()
    if args.ledger:
        try:
            carried_keys = frozenset(state.carried_keys(args.ledger))
        except state.StateError as error:
            print(f"The ledger {args.ledger} looks damaged ({error}), so nothing was checked. "
                  "Ask for help before editing it.", file=sys.stderr)
            return 2

    newsletter_date = datetime.date.fromisoformat(args.date)
    last_date = datetime.date.fromisoformat(last["sent"])
    verdicts = evaluate(items, last, dnf_names, newsletter_date, last_date, carried_keys)

    if args.json:
        results = build_json(items, verdicts, newsletter_date, last_date)
        Path(args.json).write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = build_report(items, verdicts, newsletter_date, last_date)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
