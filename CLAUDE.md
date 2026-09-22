# CLAUDE.md — Project entry point

This is a folder-based agent system that supports Volta's newsletter workflow.
There is no UI; everything happens from a folder. When you open this project,
read the files in the order below instead of exploring the directory on your own.

## Read these first to understand the system
1. `memory/manifest.md` — what the system is, why it exists, directory overview
2. `memory/lessons.md` — known pitfalls (e.g. missing access permissions), so they aren't repeated
3. `newsletter/CLAUDE.md` — domain context: Bader's editorial judgment criteria
   (two layers: leads extracted from interviews but not yet confirmed / true
   unknowns that must be flagged to Bader)

## Rules
- `.claude/rules/brand-voice.md` — writing voice rules. **Out of scope for this
  iteration**: no past newsletter issues from Bader yet, so voice rules can't be
  derived. This doesn't block the system — the secondary-issue draft only stitches
  existing `summary` fields together, with no rewriting or tone polishing.

## Three skills
- `.claude/skills/story-intake/` — structure raw material that Bader pastes in
- `.claude/skills/buffer-audit/` — audit the buffer pool and check whether information is complete
- `.claude/skills/click-conversion/` — cross-reference Mailchimp × Eventbrite CSVs
  to estimate conversion rate. **Out of scope for this iteration**: no real
  Mailchimp / Eventbrite CSV samples yet, so execution logic can't be written
  without real data; to be completed once real samples are available.

`story-intake` and `buffer-audit` have execution logic, running on the system
defaults in `newsletter/CLAUDE.md` (pending Bader's confirmation).
`click-conversion` keeps only its boundary definition (see above).

## Data
- `newsletter/memory/stories.md` — the buffer pool (digitized pool of candidate
  stories); schema only, no data yet
- `newsletter/memory/conversion-log.md` — history of conversion-rate estimates;
  schema only, no data yet

## Raw research material
- `research/` — raw interview transcripts and other primary material. Reference
  only; not part of the system and must not be treated as a runtime input.

## Core principles (see manifest.md for details)
1. Don't reinvent Bader's information-gathering process, which already works well
2. Only structure material he actively provides; don't "discover" stories for him
3. When judging completeness, never fill in missing fields — mark them missing
   and leave them for Bader to confirm
4. The buffer pool is a living record, not an archive
