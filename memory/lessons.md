# Lessons (pitfalls log)

Pitfalls worth remembering from designing or running the system. Format for each entry:
date + what happened + how we worked around it / how to avoid it.

---

## 2026-09-17 · No access to the Eventbrite / Volta back end

**Situation**: The original plan was to calculate the newsletter click → event
registration conversion rate directly from Eventbrite / Volta back-end data, but
we have no back-end access, so the data can't be retrieved.

**Workaround**: Cross-reference two manually exported CSVs (Mailchimp click data +
Eventbrite registration data) to *estimate* the conversion rate instead of
calculating it precisely.

**Lesson**: Before designing any feature that depends on third-party back-end data,
confirm that access actually exists — don't assume it "should be available". The
`click-conversion` skill is designed on the premise that access is unavailable;
don't quietly switch back to relying on back-end APIs in later iterations.

---

## 2026-09-23 · Consent note with a date released an embargoed item

**What happened**: A Consent line with a bracketed note that contained a date
(`embargoed until 2026-10-20 (Bader confirmed for the 2026-10-05 issue ...)`)
made an embargoed item come out ready, because the embargo date was read from
the last date on the line.
**How it was found**: By adding consent-parsing tests before shipping.
**What we did**: The parser now reads only the keyword at the start of the
Consent line; the rest is kept as written but never used by the rules.

---

## 2026-09-23 · Held items died as old news the next month

**What happened**: Items held in one issue were dated before that issue went
out, so the next month the old-news rule threw them all out.
**How it was found**: The end-to-end next-month test.
**What we did**: check_items.py --ledger exempts items that are still open or
ready in the ledger from the old-news rule, and from nothing else.

---

## 2026-09-23 · Unused ready items would have been forgotten

**What happened**: Items that were ready but not used in the draft had no
ledger entry, so next month they would have become old news.
**How it was found**: While fixing the carry-over problem above.
**What we did**: state.py mark-sent records them as ready, "carried over".

---

## 2026-09-23 · Blog dates one day off

**What happened**: Dates in a blog page saved from the browser were one day
earlier than in the fetched text of the same page; most likely time zones.
**How it was found**: Comparing the two versions of the page.
**What we did**: Rule: never slice date strings; read the date as a date.

---

## 2026-09-23 · PDF text drops "ff" ligatures

**What happened**: PDF text extraction dropped the "ff" ligature:
voltaeffect.com came out as voltaefect.com.
**How it was found**: The extracted address did not match the original.
**What we did**: Rule: never copy names or email addresses from PDF text.

---

## 2026-09-23 · The verifier repeated hidden text

**What happened**: verify_draft.py once printed a line containing hidden text
(an HTML comment) back in its messages.
**How it was found**: Reviewing the verifier's output.
**What we did**: Lines with hidden text are now never shown; the verifier
only says which line numbers contain hidden text.

---

(Add further pitfalls below)
