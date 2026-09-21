# Conversion Log (history of click-conversion estimates)

Written by the click-conversion skill. Each record is an estimate derived from
cross-referencing manually exported Mailchimp + Eventbrite CSVs. These are
estimates, not precise tracking (there is no direct user-level link between the
two data sources).

This file currently defines only the field structure and contains no data.

## Field structure (draft; refine the matching logic once real CSV samples exist)

- `newsletter_issue`: which newsletter issue
- `date_range`: the time window analyzed
- `mailchimp_clicks`: click count from the Mailchimp export
- `eventbrite_signups`: registrations in the matching period from the Eventbrite export
- `estimated_conversion_rate`: the estimated value
- `matching_method`: how the cross-reference was done (by email / by time window /
  by name, etc. — exact method to be decided once real CSV samples exist)
- `confidence_note`: confidence statement; must state explicitly that this is an
  indirect estimate, not precise user-level conversion tracking
- `run_date`: date this estimate was run

---

(Records start here; append at runtime)
