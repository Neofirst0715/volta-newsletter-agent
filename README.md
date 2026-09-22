# volta-newsletter-agent

A folder-based [Claude Code](https://claude.com/claude-code) agent system that supports
Volta's monthly newsletter workflow. There is no UI — everything happens from a folder.

## Why

The newsletter's real bottleneck isn't gathering information; it's **editorial judgment**:
which candidate stories go into this issue, and which should wait until more information
comes in. That "wait a bit" pool has only ever lived in the editor's head and notes.

This project turns it into a **buffer pool**: a traceable record of candidate stories that
doesn't depend on one person's memory. The existing information-gathering process (chat,
Slack, LinkedIn) stays as it is.

Secondary goal: **estimate** how well newsletter clicks convert into event registrations,
using manually exported CSVs (there is no back-end access for precise tracking).

## Skills

| Skill | What it does | Use when |
|---|---|---|
| `story-intake` | Structures pasted raw material into one candidate story in the buffer pool | You paste text about a founder, event, hackathon, fundraising, etc. |
| `buffer-audit` | Reports where each candidate story stands: missing info, permission status, days on hold, and which stories meet the secondary-issue conditions. On explicit instruction only, marks a story as used or assembles a short secondary-issue draft | Before drafting the next issue, to see which stories are worth another look, or after a story has gone out |
| `click-conversion` | Cross-references a Mailchimp click CSV with an Eventbrite registration CSV to estimate conversion | You have both CSV exports for an issue |

> **Status:**
> - `story-intake` and `buffer-audit` have execution logic (field extraction, dedup, ids,
>   receipts; audit report, mark-as-used, secondary-issue draft). It runs on **system
>   defaults** listed in `newsletter/CLAUDE.md` (e.g. the completeness rule and the 30-day
>   reminder) that are pending the editor's confirmation, and has only been checked against a
>   fictional test input so far.
> - `click-conversion` still defines only its boundaries. **To be added** once real CSV
>   exports are available: column names, matching rules, and how the rate is calculated.
> - `.claude/rules/brand-voice.md` is still TODO, pending past newsletter issues.

## Repository layout

```
CLAUDE.md                     Entry point — reading order for the agent
.claude/
  rules/brand-voice.md        Writing voice rules (TODO)
  skills/
    story-intake/             Raw material → structured story
    buffer-audit/             Audit the buffer pool
    click-conversion/         Estimate click → registration conversion
memory/
  manifest.md                 What the system is, why it exists, core principles
  lessons.md                  Pitfalls log
newsletter/
  CLAUDE.md                   Editorial judgment criteria (confirmed vs. open questions)
  memory/
    stories.md                The buffer pool (schema only for now)
    conversion-log.md         Conversion estimates (schema only for now)
```

## Getting started

1. Install [Claude Code](https://docs.claude.com/en/docs/claude-code/overview).
2. Clone this repo and start Claude Code from the repo root:
   ```bash
   git clone https://github.com/Neofirst0715/volta-newsletter-agent.git
   cd volta-newsletter-agent
   claude
   ```
3. Claude Code picks up `CLAUDE.md` and the skills automatically. Examples:
   - Paste a Slack message about a founder's milestone → `story-intake` adds it to the buffer pool.
   - "What's in the buffer pool right now?" → `buffer-audit`.
   - Attach the Mailchimp and Eventbrite CSVs for an issue → `click-conversion`.

## Core principles

1. **Don't reinvent what already works.** No scraping or push features.
2. **Only structure material that's actively provided**; don't go looking for stories.
3. **Never fill in missing information.** Mark it `missing` and flag it for the editor to confirm.
4. **Consent first.** A story's `permission_status` defaults to `not_asked`; nothing is used without the subject's consent.
5. **The buffer pool is a living record, not an archive.**
6. **Conversion numbers are estimates**, never presented as precise user-level tracking.

## Privacy

Raw research material (interview transcripts) lives in a local `research/` folder that is
git-ignored and never committed. Personal data from CSV exports is used only for matching;
only aggregate numbers are recorded.
