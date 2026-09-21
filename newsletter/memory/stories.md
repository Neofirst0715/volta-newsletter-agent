# Stories (buffer pool)

The digitized pool of candidate stories. Each record is a "candidate story that
might go into some newsletter issue", whether it was just structured by
story-intake or is on hold waiting for more information.

This file currently defines only the field structure (schema) and contains no real
data — data is written by story-intake / buffer-audit at runtime.

## Field structure (draft; iterate with real material)

Each story record should include:

- `id`: unique identifier
- `subject`: who / which team the story is about (founder or other entity)
- `summary`: story summary (from the raw material; nothing invented)
- `source_link`: traceable source link (Bader stresses "I link everything")
- `permission_status`: `not_asked` / `asked_pending` / `granted` / `declined`
  (default must be `not_asked`; never assume consent)
- `completeness_status`: `complete` / `incomplete` / `needs_bader_confirmation`
  (criteria: see the layer-2 gaps in `newsletter/CLAUDE.md`)
- `missing_fields`: if `completeness_status` is not `complete`, list exactly what is missing
- `first_seen_date`: date first recorded in the buffer pool
- `last_updated_date`: date of the most recent new information
- `status`: `candidate` / `used (issue: YYYY-MM)` / `on_hold`
- `category`: story type (founder achievement / event / hackathon / AI lab /
  user growth / fundraising / other — categories taken from the content scope
  mentioned in Matt's interview)
- `notes`: Bader's verbal notes verbatim (if any); don't paraphrase or summarize

## Usage principles

- When a field has no real value, write `unknown` or `missing`. Don't leave it
  blank and don't invent a value.
- `completeness_status` is not decided by story-intake or buffer-audit on their
  own; it must follow confirmed criteria in `newsletter/CLAUDE.md`. Until those
  criteria are confirmed, always mark it `needs_bader_confirmation`.

---

(Records start here; append at runtime)
