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

(Add further pitfalls below)
