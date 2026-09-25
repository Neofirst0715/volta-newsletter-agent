---
name: click-conversion
description: Cross-reference a manually exported Mailchimp click CSV with an Eventbrite registration CSV to estimate a newsletter issue's click-to-event-registration conversion rate, and write the result to newsletter/memory/conversion-log.md. Use when the user provides these two CSVs, or wants to know how many event registrations an issue drove or how well it converted.
---

# click-conversion

> Only the boundaries are defined for now. Concrete CSV parsing and matching logic
> will be added once real CSV samples exist — don't invent column names or matching rules.

## What it does
- Reads the two manually exported CSVs provided by the user:
  - Mailchimp: click data for a given newsletter issue
  - Eventbrite: event registration data for the matching period
- Cross-references them to **estimate** the issue's click → registration conversion rate.
- Appends the result as a record to `newsletter/memory/conversion-log.md`.

## What it does not do
- Doesn't connect to the Eventbrite / Volta back end or any API (no access — see `memory/lessons.md`, 2026-09-17).
  Don't quietly switch back to relying on back-end data in later iterations.
- Doesn't present the estimate as precise user-level conversion tracking.
- Doesn't count attendance (the CSVs don't contain it).
- Doesn't draw conclusions about newsletter content or send frequency; it only provides data.
- Doesn't modify or write back to the original CSVs.

## Input
- Mailchimp click CSV (manual export)
- Eventbrite registration CSV (manual export)
- The matching issue and time window (if the CSVs don't make it clear, ask the user — don't guess)

## Output
- One record appended to `newsletter/memory/conversion-log.md` (fields per that file's schema).
- A short conclusion for the user: the estimate, the matching method used, and a confidence note.

## Files read / written
| File | Read / write | Purpose |
|---|---|---|
| The two CSVs provided by the user | Read | Raw data |
| `newsletter/memory/conversion-log.md` | Read + write | Schema and history; append result |
| `memory/lessons.md` | Read | Known pitfalls such as access limits |

## Must follow
1. `confidence_note` must state that this is an indirect estimate and explain the sources of error.
2. `matching_method` records the matching approach actually used (by email / by time window / by name, etc.).
3. If data is missing or columns don't line up, stop and ask the user — don't invent numbers or guess column names.
4. The CSVs contain personal information (emails, names): use it only for matching, never write it to `conversion-log.md` — record aggregate numbers only.

## To be added (pending real CSV samples)
- Actual column names and format of both CSVs
- Concrete matching rules and their priority
- How the rate is calculated (e.g. denominator: unique clickers vs. total clicks)
