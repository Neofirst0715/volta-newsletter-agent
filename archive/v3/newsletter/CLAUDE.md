# Newsletter — Domain context

This file holds Bader's editorial judgment criteria. Because follow-up interviews
with Bader / Rishabh are no longer possible, it has two layers: layer 1 is leads
that can be extracted from the existing transcripts (sourced, but not confirmed by
Bader himself); layer 2 is the remaining unknowns, to be confirmed with Bader when
real cases come up while the system is running.

---

## Layer 1: Judgment leads extracted from interviews (unconfirmed; cold-start reference only)

1. **Information completeness is a hard gate**
   > "if there's not much information to include, I don't see a reason
   > to include it now" — Bader, 2026-09-17 interview (17:08)
   - Exactly which fields make information "enough" is unclear; see the gaps below.

2. **"Interesting / engagement value" is a soft filter, independent of completeness**
   > "if it's something that's fresh and has not much engagement value,
   > I wouldn't include it now" — Bader (17:55)
   - Note: not enough information ≠ not interesting enough. These are two
     independent reasons to hold a story; don't merge them.

3. **Deferring is active tracking, not giving up**
   > "I keep notes... maybe I should revisit this the next month and see
   > if there has been any updates" — Bader (17:35)

4. **Every story must have a traceable source link**
   > "I link everything. That's really important." — Bader (2:59)

5. **A founder's consent is required before using their story**
   — Bader (around 15:47)

6. **The opening slot (founder highlight) is filtered more strictly than later sections**
   — Bader (7:29): doesn't want to put up things that aren't interesting

7. **Content categories go beyond "individual founder achievements"**
   > Hackathon output, AI lab stories, user growth, fundraising progress, etc.
   > can all be material — Matt, 2026-09-17 interview (around 9:26–9:43)
   - But final prioritization is still decided by Bader (possibly with Laura
     and Amy), not Matt.

---

## System defaults (pending Bader confirmation)

These are **defaults we set so the system can actually run**. They are NOT
criteria Bader has confirmed. Anything produced using them must say so
(e.g. "default rule, pending Bader confirmation"). Replace each one as soon as
Bader gives a real answer, and log the change in `memory/lessons.md`.

1. **Information completeness**: a story is `completeness_status = complete`
   only when all three are present: **founder name** (`subject`) + **event
   description** (`summary`) + **source link** (`source_link`). Missing any one
   → `incomplete`. (Permission is tracked separately in `permission_status`
   and is not part of completeness.)
2. **Stale-story reminder threshold**: if more than **30 days** have passed
   since `last_updated_date`, buffer-audit flags the story as
   "suggest re-evaluating". This is a reminder only, never a drop decision.
3. **"Engagement value / is it interesting"**: **no default**. The system only
   presents facts (e.g. whether an award was won, the funding amount) and never
   judges whether a story is interesting.
4. **Summary cadence**: story-intake's receipt covers only the record just
   processed. Only when a new record brings the number of `candidate` stories
   to a multiple of 5 does it append "Current buffer pool: N candidate
   stories"; otherwise it never mentions counts or progress.

## Out of scope for this iteration

- **click-conversion**: no real Mailchimp / Eventbrite CSV samples yet, so its
  execution logic can't be written without inventing column names and matching
  rules. The skill keeps its boundary definition and will be completed once real
  samples are available.
- **brand-voice**: no past newsletter issues from Bader yet, so voice rules
  can't be derived. This does **not** block the system: the secondary-issue
  draft (buffer-audit) only stitches together existing `summary` fields from
  `memory/stories.md`, with no rewriting or tone polishing, so the system runs
  end to end without brand-voice rules.

---

## Layer 2: Gaps to confirm (don't guess; flag to Bader when they come up at runtime)

- [ ] Concrete criteria for "enough information": which fields (founder name?
      achievement description? source link? permission status?) make a story
      complete? Still unconfirmed — the system runs on system default #1 above
      until Bader answers.
- [ ] How is "interesting / engagement value" judged? Are there past examples to reference?
- [ ] How long can a story in the buffer pool go without updates before Bader
      should be prompted to reconsider it? (Bader never gave a threshold;
      "revisit next month" is the only lead.) Still unconfirmed — the system
      runs on system default #2 (30 days) until Bader answers.
- [ ] Main issue vs. secondary issue allocation rules are undefined: which
      stories are suitable to go out alone as a secondary issue, and which need
      to be arranged alongside other stories in the main issue? Needs Bader's
      confirmation. Until then the system only records an objective structural
      marker (`standalone_ready` in `memory/stories.md`) and never makes the
      allocation call itself.
- [ ] What roles do Laura / Amy play in the judgment process? (Matt mentioned
      them; in Bader's interview Laura is mainly one of the information sources.
      Role boundaries are unclear.)

**Principle**: If any of the items above is needed while the system is running,
always mark it as "Needs Bader confirmation" and record the specific question.
Never substitute a guessed value. The only exceptions are the explicitly listed
system defaults above, and output that relies on them must be labeled as such.
