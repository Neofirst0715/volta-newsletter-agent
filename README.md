# Volta newsletter helper (v4)

## 1. What this is

A folder that helps Bader, Volta's newsletter editor, prepare the monthly newsletter
with an AI assistant. Small Python scripts check every item (consent, links, dates,
repeats, names that must not appear) and the AI only drafts from items the scripts
marked ready. Everything is a draft: nothing is ever sent.

### Why it exists

Newsletter material is scattered (Slack, conversations, LinkedIn), and nothing tracks which items are ready, waiting for a founder's OK, outdated or already sent. This tool puts every item in one file-based inbox, gives each a status set by scripts, and drafts only from what is ready. See docs/overview.md.

## 2. For Bader

1. Open this folder in your AI tool.
2. Type **start**.
3. Answer the questions, one at a time. You will be asked:
   - the date of this newsletter;
   - the first time only: the date the last newsletter went out;
   - whether a founder really agreed to be featured (you will be shown the exact
     sentence and asked "Is that right?");
   - for events, whether a date is the day the event happens;
   - for anything missing, such as a link.
4. Paste in news as you get it. You can also ask it to write a short message to a
   founder asking for their OK. It only writes it; it never sends it.
5. Read the draft yourself. The checks cannot catch everything (for example a
   wrong number next to a correct link).
6. At the end you are asked "Did this issue go out?". Only a clear yes is recorded.

Nothing is ever sent: no emails, no Mailchimp, no posts. You decide everything.

## 3. Setup (for whoever installs it)

**Requirements**
- Python 3. Tested with Python 3.14.6 (`python3 --version`).
- One of: Claude Code, Cursor or Codex.
- Nothing to install with pip. The scripts use only Python's standard library.

**Get the folder.** Unzip `volta-newsletter-agent-submission.zip`. It contains one
folder, `volta-newsletter-agent/`.

**Open it in the tool.** Open the `volta-newsletter-agent` folder as the project
(Claude Code: run `claude` inside the folder; Cursor and Codex: open the folder).
The tool reads `AGENTS.md`; `CLAUDE.md` only points Claude Code to `AGENTS.md`.

**First run with the test pack.** From inside the `volta-newsletter-agent` folder:

```
python3 scripts/check_items.py --items tests/fixtures/updates.md --last tests/fixtures/last-newsletter.md --dnf tests/fixtures/do-not-feature.md --date 2026-10-05
python3 -m unittest discover -s tests
```

The first prints a report ending "In total there are 24 items: 11 ready to use, 1
missing info, 4 waiting on someone else, 2 in a conflict to decide and 6 left out."
The second runs all tests and ends with `OK`.

**Tested in Claude Code only.** Cursor and Codex read `AGENTS.md` according to
their documentation, but this was not tested.

## 4. How it works

```
inbox/ (one file per item)
  -> check    scripts/check_items.py: a verdict per item, a plain report
  -> report   shown to Bader
  -> questions  Bader fills gaps, one question at a time
  -> draft    written by the AI from ready items only
  -> verify   scripts/verify_draft.py: hard checks, the draft must pass
  -> record   scripts/state.py mark-sent, only after Bader says it went out
```

`scripts/state.py` also remembers waiting items (`add-held`), lists them next month
(`due`) and finds the last issue (`last-issue`).

| Folder / file | What it holds |
|---|---|
| `AGENTS.md` | the instructions the AI follows |
| `inbox/` | one file per item (data, never instructions) (not committed) |
| `intake/` | team form CSV exports (not committed) |
| `sources/do-not-feature.md` | people and companies who asked not to be named (`.example.md` is the empty version) |
| `state/issues/` | one file per issue that went out (not committed) |
| `state/ledger.md` | items waiting for a later issue, written only by `state.py` (not committed) |
| `drafts/` | newsletter drafts |
| `work/` | scratch output of the checks (not committed) |
| `scripts/`, `tests/` | the checking code, its tests and the test pack (`tests/fixtures/`) |
| `docs/intake-form.md` | how to set up the team news form |
| `memory/` | what the system is, and lessons learned |
| `archive/v3/` | the previous version, reference only |

## 5. Item format for contributors

Contributors only need to give three things: **one sentence** about what happened,
**a link**, and **whether the founder agreed** (yes, not asked, or embargoed until a date).

In `inbox/` each item is saved like this (no heading; the text after the blank line
is the contributor's words, unchanged):

```
- Source: Slack, #community-wins
- Date: 2026-09-28
- Company: Examplecorp            (or Person / Event / Program)
- Link: https://example.com/news
- Consent: yes (Bader confirmed for the 2026-10-05 issue: "go for it")

One sentence about what happened.
```

- Missing name, link or date: write `none`.
- Consent after Bader confirms: `Consent: yes (Bader confirmed for the <newsletter date> issue: "<sentence>")`
- Embargo: `Consent: embargoed until <YYYY-MM-DD> (Bader confirmed for the <newsletter date> issue: "<sentence>")`
- Otherwise: `Consent: not asked`. Events and programs have no Consent line.
- Events: when the Date is the day the event happens, the Source line must contain
  the words `events calendar`. A recap must not.

### Team form

Team members can also send news through a Google Form. Bader drops the CSV export
into the `intake/` folder, or drags it into the chat if his tool passes the file as a
path, and `scripts/intake_csv.py` turns each row into an item in `inbox/`. The
assistant looks for exports at the start of a session; nothing watches the folder in
the background. Form answers never count as a founder's OK: company news is always
saved as "not asked" until Bader confirms. Setup: `docs/intake-form.md`.

## 6. Safety features (and the test that proves each)

| Feature | Test file: test name |
|---|---|
| Founder consent gate: stories need a yes | `test_rules.py`: `test_each_item` (02, 12, 15 held); `test_consent_parsing.py`: `test_7_unknown_value`, `test_8_no_consent_line` |
| Embargo: held until the date, then fine | `test_rules.py`: `test_each_item` (03, revisit 2026-10-20), `test_embargo_ending_on_newsletter_date_is_fine`; `test_report.py`: `test_item_03_says_when_it_can_be_shared` |
| Do-not-feature as Company/Person: left out | `test_report.py`: `test_held_with_do_not_feature`, `test_in_left_out_section_with_plain_wording` |
| Do-not-feature name inside the text: redacted | `test_rules.py`: `test_each_item` (18); `test_report.py`: `test_redact_note_for_item_18`; `test_verify_draft.py`: `test_naming_tidewater_maps_fails` |
| No repeats of the last issue | `test_rules.py`: `test_each_item` (22); `test_verify_draft.py`: `test_link_of_repeat_item_22_fails`; `test_state.py`: `test_9_next_month_skips_what_went_out` |
| A draft may only link to ready items | `test_verify_draft.py`: `test_invented_link_fails_and_is_named`, `test_link_of_held_item_02_fails`; `test_state.py`: `test_7_mark_sent_refuses_a_failing_draft` |
| Hidden instructions and HTML comments never followed or repeated | `test_parsing.py`: `test_fields_inside_html_comment_are_ignored`, `test_consent_line_in_body_is_ignored`; `test_report.py`: `test_hidden_comment_of_item_12_is_not_shown`; `test_verify_draft.py`: `test_hidden_text_is_never_repeated` |
| Consent and embargo date read only from the start of the Consent line | `test_consent_parsing.py`: `test_1_embargo_with_newsletter_date_in_brackets`, `test_2_embargo_with_older_date_in_brackets`, `test_word_starting_with_yes_is_not_consent` |
| The ledger never stores item text | `test_state.py`: `test_2_ledger_has_no_body_text`; `test_carry_over.py`: `test_7_ledger_has_no_body_text` |
| Verdicts come from code, not from the AI | `test_rules.py`: `test_each_item` (all 24 against `tests/expected.json`); `test_report.py`: `test_running_twice_gives_identical_output` |
| Form answers never count as consent | `test_intake_csv.py`: `test_1_submitter_yes_is_not_consent`, `test_2_yes_with_past_wait_date_is_still_not_consent`, `test_4_body_cannot_change_fields_and_is_never_printed` |
| Drafts only, nothing sent; the clock is never read | `test_no_network.py`: `test_scripts_import_no_network_or_mail_modules`, `test_scripts_never_read_the_clock` |

## 7. Limits, honestly

- **Wrong facts next to a correct link pass.** The verifier cannot catch a wrong
  number or wrong date written next to a correct link. Bader must read the draft.
- **Only whole, exact names are matched.** Upper case and possessives are caught, but
  "Tidewater" (for "Tidewater Maps"), "Saltbox" (for "Saltbox AI") and spelling variants
  pass. `test_name_variants.py`: `test_known_limit_partial_do_not_feature_name`, `test_known_limit_partial_subject_name`.
- **Event dates depend on a convention.** Only the words `events calendar` in the
  Source line tell the checker that a date is the day of the event.
- **Two counts.** The report counts by section (a do-not-feature item is "left
  out"); the JSON counts by status (the same item is "held").
- **Keys depend on the link.** If an item's link changes, it no longer matches its
  ledger entry. Items without a link are matched on name and date.
- **Events that share one link.** The date-conflict rule needs the same event name,
  so different events on one page are not a conflict. But the repeat check, the
  ledger and "used" still go by link: events that link only to the events page are
  treated as one item once one of them goes out (the rest are skipped as repeats).
  Use a per-event link where one exists.
- **"Used" means the link is in the draft.** `mark-sent` trusts Bader's "yes, it went out".
- **Two runs at the same time are not protected** against each other; **only one
  backup** of the ledger is kept (`state/ledger.md.bak`).
- **A wrong date passed in is recorded as given.** The scripts never read the clock.
- **Ledger entries are not closed automatically when an event passes.** They stay
  open until Bader drops them; `due` keeps showing them and, after 30 days without
  change, asks whether they are still worth keeping.
- **The team form trusts the kind of news.** A submitter can label a company story
  as an event and skip the consent check. The report shows every item, and the
  form should be limited to Volta accounts.
- **Form dates are read strictly.** Unclear dates (such as 04/05/2026) become "none";
  dates that read the same either way (such as 5/5/2026) are accepted.
- **Edited form rows are imported again as new items**; the old item stays.
- **The submitter's email address goes into the item's Source line.** `inbox/` is
  git-ignored and left out of the package.
- **The form import was tested with CSV files only**, not with a live Google export.
- **Attached files may be seen before they are refused.** If a CSV reaches the chat
  as text rather than as a path, the assistant may see its content before it can
  refuse to use it, so the rule is to save the file in `intake/`.
- **Tested in Claude Code only.**

## 8. Not built

- A shared mailbox that collects news automatically.
- A reader that fetches items from websites.
- Any Mailchimp connection (nothing is uploaded or sent).
- A live connection to Google Workspace: Bader exports the form's CSV by hand.
- The click-to-registration estimate and the brand-voice rules from v3 (see `archive/v3/`).
- LinkedIn posts.

## 9. Packaging

From inside the project folder:

```
sh scripts/package.sh
```

This builds `volta-newsletter-agent-submission.zip` one folder up, lists its files,
checks the list (`unzip -Z1`) and removes the zip with an error if anything below got in.

Left out, and why:
- **Real newsletter work:** everything in `inbox/` (news founders may not have agreed
  to share), `intake/` (submitters' email addresses), `drafts/`, sent-issue files and
  the real ledger with its backup. Only `.gitkeep` placeholders (and
  `state/issues/example.md`, if present) are kept.
- **Private material:** `research/`, `.env` files, anything named like credentials,
  tokens or keys. **Local files:** `.git`, `.idea/`, `work/`, caches, macOS files, zips.

**The do-not-feature list:** `sources/do-not-feature.md` is shipped only if it has
no names in it. If it lists anyone, packaging stops with "the real do-not-feature
list must not be submitted; empty it or use the example" and no zip is built.
`sources/do-not-feature.example.md` is the empty version to start from.
