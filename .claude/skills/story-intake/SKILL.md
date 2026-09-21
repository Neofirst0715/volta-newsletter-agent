---
name: story-intake
description: Structure raw material that Bader pastes in (chat logs, Slack messages, LinkedIn posts, verbal notes, etc.) into one candidate story and write it to the buffer pool at newsletter/memory/stories.md. Use when the user pastes raw text about a founder, event, hackathon, AI lab, fundraising, user growth, etc. and wants to record it, add it to the buffer pool, or consider it for a future newsletter issue.
---

# story-intake

> Only the boundaries are defined for now. Concrete parsing / extraction steps
> will be added once real pasted samples exist — don't invent logic without samples.

## What it does
- Turns one piece of raw material that Bader **actively pastes in** into a record in `stories.md`.
- Decides whether the material is a **new story** or an **update to an existing story**:
  - New story → append a new record.
  - Existing story → update the original record, refresh `last_updated_date`, and keep the existing content and history.

## What it does not do
- Doesn't proactively scrape, search for, or "discover" stories (chat / Slack / LinkedIn are off limits).
- Doesn't decide whether a story goes into the current issue — that's Bader's editorial call.
- Doesn't judge on its own whether information is "complete" or "interesting"; until the criteria are confirmed, always mark `needs_bader_confirmation`.
- Doesn't invent, fill in, or polish missing fields.
- Doesn't assume the subject has given consent.

## Input
- A piece of raw text pasted by Bader (possibly with links and his verbal notes).

## Output
- One new or updated record in `newsletter/memory/stories.md` (fields per that file's schema).
- A short receipt for the user: which record was written, which fields are marked `missing` / `unknown`, and which questions need Bader's confirmation.

## Files read / written
| File | Read / write | Purpose |
|---|---|---|
| `newsletter/memory/stories.md` | Read + write | Schema and existing records (dedup); write result |
| `newsletter/CLAUDE.md` | Read | Editorial judgment leads and open gaps |
| `memory/lessons.md` | Read | Known pitfalls |

## Must follow
1. `permission_status` defaults to `not_asked` unless the material explicitly says the subject has consented.
2. `source_link` must come from the material itself; if the material has no link, write `missing` — don't look one up or make one up.
3. `notes` keeps Bader's verbal notes verbatim — no paraphrasing, no summarizing.
4. Fields without a real value get `unknown` or `missing`, never blank.
5. Until the criteria are confirmed, `completeness_status` is `needs_bader_confirmation`, and `missing_fields` lists information that is clearly absent.
6. Layer-1 leads in `newsletter/CLAUDE.md` are reference only, not confirmed rules.

## To be added (pending real samples)
- How to extract fields from different sources (Slack / LinkedIn / verbal)
- Dedup rule: what counts as "the same story"
- `id` format
