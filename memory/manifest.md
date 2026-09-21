# System manifest

## What this is
A folder-based Claude Code agent system that supports Volta's newsletter workflow.
There is no UI; everything happens from a folder.

## Why it exists
Volta's monthly newsletter is produced by Bader alone. He doesn't see obvious pain
points in his current process (Mailchimp works well; one issue takes 3–4 hours).
The real bottleneck is **editorial judgment**, not information gathering:
- which candidate stories go into the current issue
- which should "wait a bit" until the information is complete next month

This "wait a bit" candidate pool (the buffer pool) is completely informal. It has
never been digitized and exists only in Bader's memory and verbal notes. The core
value of this system is turning that implicit buffer pool into a traceable system
that doesn't depend on one person's memory — without disrupting his existing
information-gathering process (chat / Slack / LinkedIn), which already works well.

Secondary goal: estimate the conversion rate from newsletter clicks to event
registrations (currently impossible to measure, because there is no access to the
Eventbrite / Volta back end).

## Directory structure
```
.claude/
  rules/brand-voice.md         System-wide writing voice rules
  skills/
    story-intake/               Structure raw material that Bader pastes in
    buffer-audit/               Audit the buffer pool; check whether information is complete
    click-conversion/           Cross-reference Mailchimp × Eventbrite CSVs to estimate conversion
memory/
  manifest.md                   This file
  lessons.md                    Pitfalls log
newsletter/
  CLAUDE.md                     Bader's editorial judgment criteria (domain context)
  memory/
    stories.md                  The digitized buffer pool
    conversion-log.md           History of conversion-rate estimates
```

## Core principles
1. **Don't reinvent the process that already works for him.** Bader gathers
   information through chat, Slack and LinkedIn; that needs no tooling. Don't
   build scraping or push features.
2. **Only structure material he actively provides**; don't "discover" stories for him.
3. **When judging completeness, never fill in missing fields.** If information is
   missing, mark it missing and leave it for Bader to confirm. Never assume or invent.
4. **The buffer pool is a living record, not an archive.** Every story should be
   traceable: when it was put on hold, what was missing at the time, and whether
   it has been updated since.

## Known hard information gaps
The editorial criteria in `newsletter/CLAUDE.md` are currently only speculative
leads extracted from two interview transcripts, not yet confirmed by Bader. When
the system hits a judgment call it can't make, it should record the open question
for Bader to confirm later, rather than guessing the criteria.
