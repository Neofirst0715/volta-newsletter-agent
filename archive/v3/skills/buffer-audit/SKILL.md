---
name: buffer-audit
description: Audit the newsletter buffer pool at newsletter/memory/stories.md and report where each candidate story stands — what information is missing, whether permission has been granted, how long it has been on hold, and whether there's new progress — plus a list of questions that need Bader's confirmation and the stories that already meet the objective secondary-issue conditions. Also, only on explicit instruction, marks a story as used ("use story-XXX for the secondary/main issue") or assembles a short secondary-issue draft from 1–2 named stories' summaries. Use when the user wants to see the state of the buffer pool, review candidate stories before the next issue, asks which stories are worth another look, says a story was used, or asks for a secondary-issue draft.
---

# buffer-audit

> Execution logic below was written before the buffer pool had real records.
> Revise the report format once real records exist.

## What it does
1. **Audit (default, read-only)**: reports per-story missing information,
   permission status, days on hold, a stale-story reminder, the two independent
   hold reasons, questions for Bader, and the stories that objectively meet the
   secondary-issue conditions.
2. **Mark as used (write, explicit instruction only)**: changes the named
   stories' `status` to `used_secondary` / `used_main`, and confirms with each
   story's verbatim summary.
3. **Secondary-issue draft (explicit request only)**: stitches the `summary` of
   1–2 named stories into a short plain-text draft for Bader to paste into
   Mailchimp himself.

## What it does not do
- Doesn't decide for Bader which stories go into the current issue, get dropped,
  or go to the main vs. secondary issue.
- Doesn't rank, score or recommend stories. Lists are in `id` order, which
  carries no meaning.
- Doesn't judge whether a story is "interesting".
- Doesn't search externally to fill in missing information.
- Never marks a story as used, or generates a draft, just because the user looked
  at a report or said something like "story-003 looks good".
- Doesn't rewrite, re-voice or add to summaries in a draft.
- Doesn't connect to Mailchimp or any sending API; never sends anything.

## Input
- The current contents of `newsletter/memory/stories.md`.
- (Optional) A scope from the user, e.g. "founder stories only", "only ones on hold for over a month".
- For mark-as-used / draft: the user's explicit instruction naming the story id(s).

## Files read / written
| File | Read / write | Purpose |
|---|---|---|
| `newsletter/memory/stories.md` | Read; write only in the mark-as-used action | Buffer pool data |
| `newsletter/CLAUDE.md` | Read | Editorial leads, system defaults, open gaps |
| `memory/lessons.md` | Read | Known pitfalls |

---

## Action 1 — Audit (read-only)

### Steps
1. Read `stories.md` and parse all records. If there are none, reply
   "The buffer pool is empty." and stop.
2. Apply the user's scope filter, if any.
3. Split records into **active** (`candidate`, `on_hold`) and **used**
   (`used_secondary`, `used_main`). Only active records are audited in detail;
   used records appear only in the counts.
4. For each active record compute:
   - **Missing**: everything in `missing_fields`, plus any field whose value is
     `missing` / `unknown`.
   - **Permission**: `permission_status`; anything other than `granted` →
     "not usable as is".
   - **Days in pool** = today − `first_seen_date`; **days since update** =
     today − `last_updated_date`.
   - **Stale reminder**: days since update > 30 → "suggest re-evaluating"
     (system default #2, pending Bader confirmation). This is a reminder, not a
     drop decision.
5. Sort the two hold reasons **independently**:
   - **Information insufficient**: `completeness_status` is `incomplete` or
     `needs_bader_confirmation`.
   - **Engagement value questioned**: only when Bader's own `notes` say so —
     quote the note verbatim. The system never adds a story to this list by its
     own judgment. A story may appear on both lists, or on neither.
6. Build the questions for Bader: every `needs_bader_confirmation` item, every
   open question from the records, and any layer-2 gap in
   `newsletter/CLAUDE.md` that this audit ran into, written as
   "Needs Bader confirmation: <specific question>".
7. Build the **secondary-issue conditions** list: active records where
   `completeness_status = complete` **and** `permission_status = granted`
   **and** `standalone_ready = true`. Pure filter; `id` order; no ranking.

### Summary line format
Whenever the report lists stories, each story is one line:
```
story-XXX — <subject> @ <event or context> (<key result>, <link marker>)
```
- `<subject>`, `<event or context>` and `<key result>` come from the record's
  `subject` / `summary` wording — no rephrasing into claims the record doesn't
  make. Drop `@ <event or context>` if the record names none; write `unknown
  subject` if `subject` is `missing`.
- `<key result>` is the concrete fact (award name, amount, number); omit it if
  the record has none.
- `<link marker>`: `✅ link` if `source_link` has a value, `❌ no link` if it's
  `missing`.
- Example: `story-004 — God's Plan @ Hack the North (Best Use of Devin, ✅ link)`
- Sections may append a short suffix after the line (e.g. `— 34 days since
  last update`, `— "<verbatim note>"`).

### Report format (in the conversation, not saved to a file)
```
## Buffer pool audit — YYYY-MM-DD
Pool: N records — candidate a · on_hold b · used_secondary c · used_main d
(Scope: <user's filter, or all>)

### Summary (id order, one summary line per active story)
- <summary line>

### Per-story status (id order)
| id | subject | category | completeness | missing | permission | days in pool | days since update | standalone_ready |
|---|---|---|---|---|---|---|---|---|
(permission ≠ granted → add "— not usable as is" in the permission cell)

### Suggest re-evaluating (> 30 days since last update · system default, pending Bader confirmation)
- <summary line> — N days since last update
(or: none)

### Hold reason A — information insufficient
- <summary line> — missing: <fields>

### Hold reason B — engagement value questioned (Bader's own notes only)
- <summary line> — "<verbatim note>"
(or: none recorded)

### Needs Bader confirmation
- Needs Bader confirmation: <question>

### Stories meeting secondary-issue conditions
Objective filter only (complete + permission granted + standalone_ready = true);
not a recommendation, not ranked.
- <summary line>
(or: none)
```

---

## Confirmation format (shared by Actions 2 and 3)

Every confirmation — marking stories as main issue, marking as secondary issue,
and the confirmation part of a secondary-issue draft — uses the same shape:
```
<header line>

- story-XXX — <title>: <summary, quoted verbatim from stories.md>
- story-YYY — <title>: <summary, quoted verbatim from stories.md>

⚠️ <combined warnings>
```
- `<title>` = the record's `subject`, plus ` @ <event or context>` if the
  record names one — same wording as the summary line format. No invented titles.
- The summary is copied exactly as stored in `stories.md`. Never search for,
  infer or add information the record doesn't contain. If the stored summary is
  short or incomplete, show it as is — don't expand it to make the confirmation
  look complete. If `summary` is `missing`, write `summary missing`.
- `⚠️` line: one combined line listing facts that still need attention, grouped
  by issue, e.g. `⚠️ No consent yet: story-003, story-005 · No source link:
  story-004`. Cover consent not `granted`, `source_link` missing, and
  `completeness_status` not `complete`. If nothing applies, omit the line.
- Header lines:
  - Main issue: `Stories 003, 004, 005 marked as main issue content, issue <YYYY-MM or unknown>.`
  - Secondary issue: `Story 006 marked as secondary issue content, issue <YYYY-MM-DD or unknown>.`
  - Draft: `Secondary-issue draft assembled from stories 006, 007 (not saved, not sent, not marked as used).`
  (Use `Story` / `Stories` to match the count.)

---

## Action 2 — Mark as used (write; explicit instruction only)

**Trigger**: only an explicit instruction that names the id(s) and the issue type,
e.g. "use story-004 for the secondary issue", "story-002 went out in the main
issue". Anything vaguer ("story-004 seems good for a secondary", "let's think
about story-004") is **not** a trigger — ask instead of writing.

**Steps** (one instruction may name several stories; apply each step per story)
1. Find the record. Not found → say so and stop.
2. If its `status` is already `used_secondary` or `used_main` → stop and tell the
   user (this is what prevents one story being consumed by both issues). Change
   it only if the user explicitly confirms the overwrite.
3. If `permission_status ≠ granted` or `completeness_status ≠ complete`, show
   the fact ("permission_status is not_asked") and ask the user to confirm once
   before writing. Don't block beyond that — the call is Bader's.
4. Set `status` to `used_secondary (issue: <date the user gave, or unknown>)` or
   `used_main (issue: <YYYY-MM the user gave, or unknown>)`. Set
   `last_updated_date` to today. Change no other field.
5. Reply with the shared confirmation format above (main or secondary header),
   listing every story just marked with its verbatim summary.

---

## Action 3 — Secondary-issue draft (explicit request only)

**Trigger**: the user explicitly asks for a draft and names 1–2 story ids.
More than 2 → ask which 1–2. No ids named → ask; don't pick stories yourself.

**Steps**
1. Read the named records. If a `summary` is `missing`, that story can't be
   drafted — say so and draft only the others (or nothing).
2. Before the draft, output the shared confirmation format above (draft
   header, each story with its verbatim summary, `⚠️` line). This stays
   **outside** the draft block — never put warnings inside the copyable text.
   Don't refuse because of warnings.
3. Assemble the draft by stitching only — `summary` copied **verbatim**, with
   its `source_link`. No headline, intro, outro, transitions or rewording
   (brand voice rules in `.claude/rules/brand-voice.md` are out of scope for
   this iteration — no past newsletter issues to derive them from. This doesn't
   block drafting, since the draft only stitches existing `summary` fields;
   Bader adds his own framing in Mailchimp).
4. Output as a plain-text code block so it copies cleanly:
   ```
   <summary of story A, verbatim>
   Source: <source_link of story A>

   ---

   <summary of story B, verbatim>
   Source: <source_link of story B>
   ```
   (If a `source_link` is `missing`, write `Source: missing` — never omit or invent.)
5. After the draft, state: "To mark them as used, say 'use story-XXX for the
   secondary issue'."

---

## Must follow
1. If information is missing, mark it `missing` as is — no guessing, no inference.
2. Any judgment that touches a layer-2 gap in `newsletter/CLAUDE.md` is written as "Needs Bader confirmation: <specific question>".
3. Anything based on a system default (completeness rule, 30-day reminder) is labeled "system default, pending Bader confirmation".
4. The opening slot (founder highlight) is held to a stricter standard than other sections, but that standard is unknown, so it can only be flagged — never scored on its own.
5. Any story whose `permission_status` is not `granted` must be clearly marked "not usable as is" in the report.
6. No ranking or "which is better" judgments — objective facts only.
7. Writes happen only in Action 2, and only on explicit instruction. Drafts are never sent anywhere.
