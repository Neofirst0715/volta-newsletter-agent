---
name: buffer-audit
description: Audit the newsletter buffer pool at newsletter/memory/stories.md and report where each candidate story stands — what information is missing, whether permission has been granted, how long it has been on hold, and whether there's new progress — plus a list of questions that need Bader's confirmation. Use when the user wants to see the state of the buffer pool, review candidate stories before the next issue, or asks which stories are worth another look.
---

# buffer-audit

> Only the boundaries are defined for now. Concrete audit steps and report format
> will be added once the buffer pool has real records — don't invent logic without data.

## What it does
- Reads every record whose `status` is `candidate` / `on_hold` and reports, per record:
  - Missing fields (`missing_fields`, and fields whose value is `missing` / `unknown`)
  - Whether `permission_status` is anything other than `granted`
  - How long it has been since `first_seen_date` / `last_updated_date`
- Lists "not enough information" and "questionable engagement value" as **two independent reasons to hold**, without merging them.
- Compiles a list of questions that need Bader's confirmation.

## What it does not do
- Doesn't decide for Bader which stories go into the current issue or get dropped.
- Doesn't judge on its own whether information is "enough" or a story is "interesting"; until the criteria are confirmed, it describes facts only, without verdicts.
- Doesn't set its own "time to revisit" threshold (the only lead so far is "revisit next month"); it only reports the actual number of days.
- Doesn't search externally to fill in missing information.
- Read-only by default: doesn't modify `stories.md` unless the user explicitly asks.

## Input
- The current contents of `newsletter/memory/stories.md`.
- (Optional) A scope from the user, e.g. "founder stories only", "only ones on hold for over a month".

## Output
- An audit report for the user (in the conversation, not saved to a file):
  - Current state of each candidate story: what's missing, permission status, days on hold
  - List of questions that need Bader's confirmation
- No files are modified unless the user asks.

## Files read / written
| File | Read / write | Purpose |
|---|---|---|
| `newsletter/memory/stories.md` | Read (write only on request) | Buffer pool data |
| `newsletter/CLAUDE.md` | Read | Editorial judgment leads and open gaps |
| `memory/lessons.md` | Read | Known pitfalls |

## Must follow
1. If information is missing, mark it `missing` as is — no guessing, no inference.
2. Any judgment that touches a layer-2 gap in `newsletter/CLAUDE.md` is written as "Needs Bader confirmation: <specific question>".
3. The opening slot (founder highlight) is held to a stricter standard than other sections, but that standard is unknown, so it can only be flagged — never scored on its own.
4. Any story whose `permission_status` is not `granted` must be clearly marked "not usable as is" in the report.

## To be added (pending real data)
- Exact report format and sort order
- Time threshold for prompting Bader to reconsider a story (add once Bader confirms)
- Fields that define "complete information" (add once Bader confirms)
