---
name: story-intake
description: Structure raw material that Bader pastes in (chat logs, Slack messages, LinkedIn posts, verbal notes, etc.) into one candidate story and write it to the buffer pool at newsletter/memory/stories.md. Use when the user pastes raw text about a founder, event, hackathon, AI lab, fundraising, user growth, etc. and wants to record it, add it to the buffer pool, or consider it for a future newsletter issue.
---

# story-intake

> Execution logic below was written before any real pasted samples existed and
> was checked against a fictional test input only. Revise the extraction rules
> once real Slack / LinkedIn / verbal material comes in.

## What it does
- Turns one piece of raw material that Bader **actively pastes in** into a record in `stories.md`.
- Decides whether the material is a **new story** or an **update to an existing story**:
  - New story → append a new record.
  - Existing story → update the original record, refresh `last_updated_date`, and keep the existing content and history.

## What it does not do
- Doesn't proactively scrape, search for, or "discover" stories (chat / Slack / LinkedIn are off limits).
- Doesn't decide whether a story goes into the current issue, or into the main vs. secondary issue — that's Bader's editorial call.
- Doesn't judge whether a story is "interesting"; it records facts only.
- Doesn't invent, fill in, or polish missing fields.
- Doesn't assume the subject has given consent.

## Input
- A piece of raw text pasted by Bader (possibly with links and his verbal notes).

## Output
- One new or updated record in `newsletter/memory/stories.md` (fields and record format per that file's schema).
- A receipt for the user (format below).

## Files read / written
| File | Read / write | Purpose |
|---|---|---|
| `newsletter/memory/stories.md` | Read + write | Schema and existing records (dedup); write result |
| `newsletter/CLAUDE.md` | Read | Editorial leads, system defaults, open gaps |
| `memory/lessons.md` | Read | Known pitfalls |

## Execution steps

### Step 1 — Read the pool
Read `stories.md`. Collect every existing record's `id`, `subject`, `summary`,
`source_link` and `category` for the dedup check. Note the highest existing id.

### Step 2 — Separate the source text from Bader's own remarks
- **Source text**: the pasted post / message / chat content.
- **Bader's remarks**: text clearly marked as his own comment ("note:", "my
  thoughts:", text outside a quoted block, first-person remarks about the
  newsletter such as "maybe next month").
- If you can't tell which is which, don't guess: treat everything as source
  text, set `notes: none`, and ask in the receipt whether any part was his note.

### Step 3 — Extract fields (source text only, except `notes`)

**`subject`**
- The named person(s) or team the story is about. If a founder is named with
  their company, write `<Name> (<Company>)` — that is one subject.
- For hackathon / AI lab / event stories, the named team or entity is the subject.
- No name anywhere in the material → `missing`. Never derive a name from a URL
  slug, an email address, or outside knowledge.

**`summary`**
- 1–3 plain sentences stating only what the material says happened: who, what,
  and any numbers / names / dates exactly as written.
- No adjectives or framing the material doesn't contain ("impressive",
  "exciting"), no inferred causes or outcomes, no rounding of numbers.
- If the material doesn't describe an event (e.g. just "check out Jane's
  startup"), write `missing`.

**`source_link`**
- Every URL that appears in the pasted text. If there are several, list them all
  separated by `, ` — don't pick a "best" one.
- "I saw it on LinkedIn" without a URL → `missing`. Never build or look up a URL.

**`category`**
- Match on what the material explicitly states, using these cues:
  | Category | Cues in the material |
  |---|---|
  | fundraising | raised, round, pre-seed / seed / Series X, funding, investment led by, closed $ |
  | hackathon | hackathon, hack night, built at … hack |
  | AI lab | AI lab named explicitly |
  | event | event, meetup, workshop, demo day, talk, panel, conference |
  | user growth | users, customers, MAU / DAU, waitlist, downloads, revenue growth |
  | founder achievement | award, won, named to (list), accepted into (program), launched |
- More than one category matches → record all of them joined with ` + `
  (e.g. `hackathon + founder achievement`). Don't choose between them.
- Nothing matches → `other`.

**`permission_status`** — look for explicit statements only:
- `granted`: the material says the subject agreed to be featured ("she's happy
  to be featured", "he said OK to share", "gave permission").
- `asked_pending`: Bader says he has asked and has no answer yet ("I asked him,
  waiting to hear back").
- `declined`: the subject said no ("doesn't want it shared", "asked us not to").
- `not_asked`: everything else — including a **public post** (a public LinkedIn
  post is not consent to be in the newsletter) and a stated **intention** to ask
  ("I'll ask her").
- When not `not_asked`, quote the sentence it's based on in the receipt.

**`notes`**: Bader's remarks from Step 2, verbatim. None → `none`.

**`first_seen_date` / `last_updated_date`**: today's date (the date of intake,
not the date of the event in the story).

**`status`**: `candidate` for new records. Never set `on_hold` or any `used_*`
value during intake unless the user explicitly says so.

### Step 4 — Completeness (system default #1, pending Bader confirmation)
- Required: `subject`, `summary`, `source_link`.
- All three present → `complete`, `missing_fields: none`.
- Any one is `missing` → `incomplete`, and `missing_fields` lists exactly which.
- `needs_bader_confirmation` only when the default can't be applied
  mechanically — specifically: a founder-type story (fundraising / founder
  achievement / user growth) names a company but no person, so it's unclear
  whether "founder name" is satisfied. List `subject (founder name?)` in
  `missing_fields` and add the question to the receipt.
- Permission is **not** part of completeness; it is tracked on its own.

### Step 5 — `standalone_ready` (structural, not editorial)
- `unknown` if `subject` or `summary` is `missing`.
- `true` only if **both**:
  1. **Single subject**: exactly one person, or one founder + their company, or
     one team — counted as one entity.
  2. **Single event**: the summary describes one occurrence (one round, one
     award, one launch, one event appearance), not a list of updates.
- `false` if any of:
  - two or more independent subjects (e.g. "three teams won prizes"),
  - two or more distinct events (e.g. "raised a seed round and hit 10k users"),
  - the summary only makes sense alongside another story or a roundup
    (e.g. "also among this month's demo day speakers").
- This never judges quality or suitability for a secondary issue.

### Step 6 — Dedup: new story or update?
Compare against every existing record:
1. **Same subject** — same person / team after ignoring case, extra spaces,
   titles ("Dr.", "CEO") and whether the company name is attached.
2. **Same event** — same category **and** the material refers to the same
   occurrence (same round, same award, same event / hackathon name), or shares a
   `source_link` with the existing record.

| Result | Action |
|---|---|
| Same subject + same event | **Update** the existing record (Step 7) |
| Same subject, clearly different event (e.g. earlier fundraising, now an award) | **New** record |
| Same subject, can't tell if the event is the same | **Stop and ask** the user: update `story-XXX` or create new? Don't write until answered |
| Different subject | **New** record |

### Step 7 — Write
- **New**: id = highest existing id + 1, zero-padded (`story-001`, `story-002`, …;
  first record is `story-001`). Append the record at the end in the schema's
  record format.
- **Update**:
  - Fill fields that were `missing` / `unknown` if the new material provides them.
  - Append new facts to `summary` as a new sentence; don't delete earlier facts.
  - Add any new URL to `source_link` (keep the old ones).
  - Upgrade `permission_status` only on an explicit statement (per Step 3).
  - Append new Bader remarks to `notes` prefixed with today's date; keep old notes.
  - Re-run Steps 4–5, set `last_updated_date` to today. Never change `id`,
    `first_seen_date` or `status`.

### Step 8 — Receipt
The receipt has two layers, written in English. By default output **only the
short receipt**; this is the only thing Bader sees after an intake.

**Short receipt (default)** — fixed format, 1–2 lines:
```
✅ Recorded — <one sentence: subject + event + key result>
Missing: <item>, <item>
```
- No field names anywhere (`subject:`, `category:`, `source_link:` …) and no
  bullet list or field-style layout. The first line is one natural-language
  sentence built only from facts in the record.
- `Missing:` lists only what Bader has to act on or may need to supply later,
  in plain words, comma-separated:
  - a required field that is `missing` → "founder name", "what happened",
    "source link"
  - `needs_bader_confirmation` on the founder name → "founder name (only the
    company is named)"
  - `permission_status` is `not_asked` → "consent"; `asked_pending` → "consent
    (asked, awaiting reply)"; `declined` → "consent (declined)"
  - an open question the intake couldn't resolve (e.g. which part of the text
    was Bader's note) → a short question
- Internal results Bader doesn't need to handle (category, standalone_ready,
  that a link *was* found, completeness bookkeeping) never appear.
- If nothing is missing and consent is `granted`, omit the `Missing:` line
  entirely (don't write "Missing: none").
- For an update, start with `✅ Updated story-XXX — <sentence>`; otherwise the
  same rules apply.

Example (fictional input — a LinkedIn post with no URL, note "I'll ask her"):
```
✅ Recorded — Jane Doe's Acme Robotics closed a $1.5M pre-seed round led by Example Ventures.
Missing: source link, consent
```

**Full record (only on request)** — only when the user asks about a specific
record ("what did you record for story-XXX?", "show me the full record").
Still natural-language prose, not a field list, covering:
- the full story as recorded
- the source link(s), if any
- what is missing and why, citing what the original material did or didn't say
  (no inference)
- the consent status and the sentence it's based on (or that none was found)
- Bader's verbatim note, if any

The receipt reports **only this record**. It never mentions the pool size, the
record's position in the pool, or how many records remain until the next summary.

**Summary line (conditional)** — only after a **new** record is created, count
the records in `stories.md` whose `status` is `candidate`. If that count N is a
multiple of 5, append one final line to the receipt:
`Current buffer pool: N candidate stories.`
Otherwise (and always after an update) add nothing about counts or progress.

## Must follow
1. `permission_status` defaults to `not_asked` unless the material explicitly says the subject has consented.
2. `source_link` must come from the material itself; if the material has no link, write `missing` — don't look one up or make one up.
3. `notes` keeps Bader's verbal notes verbatim — no paraphrasing, no summarizing.
4. Fields without a real value get `unknown` or `missing`, never blank.
5. `completeness_status` follows system default #1 mechanically and the receipt always labels it as a default pending Bader's confirmation.
6. Layer-1 leads in `newsletter/CLAUDE.md` are reference only, not confirmed rules.
7. No ranking, no "this one is better" — facts only.
