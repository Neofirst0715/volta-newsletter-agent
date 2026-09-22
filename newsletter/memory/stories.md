# Stories (buffer pool)

The digitized pool of candidate stories. Each record is a "candidate story that
might go into some newsletter issue", whether it was just structured by
story-intake or is on hold waiting for more information.

This file currently defines only the field structure (schema) and contains no real
data — data is written by story-intake / buffer-audit at runtime.

## Field structure (draft; iterate with real material)

Each story record should include:

- `id`: unique identifier, format `story-XXX` (three digits, incrementing from
  `story-001`; never reused, even if a story is later dropped)
- `subject`: who / which team the story is about (founder or other entity)
- `summary`: story summary (from the raw material; nothing invented)
- `source_link`: traceable source link (Bader stresses "I link everything")
- `permission_status`: `not_asked` / `asked_pending` / `granted` / `declined`
  (default must be `not_asked`; never assume consent)
- `completeness_status`: `complete` / `incomplete` / `needs_bader_confirmation`
  (criteria: system default #1 in `newsletter/CLAUDE.md` — `subject` + `summary`
  + `source_link` all present → `complete`; any one missing → `incomplete`)
- `missing_fields`: if `completeness_status` is not `complete`, list exactly what is missing
- `standalone_ready`: `true` / `false` / `unknown` — a **structural** marker,
  not an editorial one. `true` only means "this story involves a single subject
  and a single event, so in principle it could stand alone as a short item
  without being paired with other stories". It says nothing about whether the
  story is good, and does not decide main vs. secondary issue allocation (see the
  layer-2 gap in `newsletter/CLAUDE.md`). `unknown` when `subject` or `summary`
  is missing, so the structure can't be determined. Rules: story-intake SKILL.md.
- `first_seen_date`: date first recorded in the buffer pool
- `last_updated_date`: date of the most recent new information or status change
- `status`: one of
  - `candidate` — in the pool, not yet used
  - `on_hold` — deliberately set aside for now
  - `used_secondary (issue: <YYYY-MM-DD or unknown>)` — used in a secondary issue
  - `used_main (issue: <YYYY-MM or unknown>)` — used in the main issue
  (The old single `used` value is split in two so the same story isn't consumed
  by both a main and a secondary issue. Only the user's explicit instruction
  changes a story to a `used_*` status — see buffer-audit SKILL.md.)
- `category`: story type (founder achievement / event / hackathon / AI lab /
  user growth / fundraising / other — categories taken from the content scope
  mentioned in Matt's interview)
- `notes`: Bader's verbal notes verbatim (if any); don't paraphrase or summarize

## Record format

Each record is a level-3 heading with the id, followed by one bullet per field,
in schema order. Records are appended in id order.

```
### story-001
- subject: <value>
- summary: <value>
- source_link: <value>
- permission_status: <value>
- completeness_status: <value>
- missing_fields: <comma-separated list, or none>
- standalone_ready: <true / false / unknown>
- first_seen_date: YYYY-MM-DD
- last_updated_date: YYYY-MM-DD
- status: <value>
- category: <value>
- notes: <verbatim, or none>
```

## Usage principles

- When a field has no real value, write `unknown` or `missing`. Don't leave it
  blank and don't invent a value.
- `completeness_status` follows system default #1 in `newsletter/CLAUDE.md`
  (pending Bader's confirmation), applied mechanically — never by judging
  whether the story is "enough" in an editorial sense. Use
  `needs_bader_confirmation` only when the default can't be applied
  mechanically (see story-intake SKILL.md).

---

(Records start here; append at runtime)
