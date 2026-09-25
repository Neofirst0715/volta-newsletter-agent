# Team news form

Team members drop news into a Google Form. The answers collect in a Google
Sheet. Bader exports the Sheet as CSV, and `scripts/intake_csv.py` turns each
row into one item in `inbox/`. Nothing connects to Google automatically.

## Setup (about 3 minutes)

1. In Google Forms, create a blank form called "Volta newsletter news".
2. Settings > Responses: limit the form to people in your Volta account
   (**Restrict to users in Volta**) and turn on **Collect email addresses**.
3. Add the questions below. Use these exact titles: the script finds the
   columns by words in the titles. Put the text in brackets into the question's
   description, not its title.
4. Responses tab > **Link to Sheets** > create a new spreadsheet.
5. In the Sheet, format the Timestamp column as yyyy-mm-dd (select the column,
   then **Format > Number > Custom date and time**). Otherwise many timestamps
   cannot be read for certain and those rows get no date.
6. Each month, export the answers (see "Export each month" at the end).

## Questions

Google adds the first two automatically.

| # | Title | Type | Notes |
|---|---|---|---|
| 1 | Timestamp | automatic | |
| 2 | Email Address | automatic | from "Collect email addresses" |
| 3 | What is this about? | short answer, required | (name of the company, person, event or program) |
| 4 | What kind of news is it? | multiple choice, required | options: Company or founder news / Event / Volta program or opportunity |
| 5 | What happened? | paragraph, required | (one or two sentences) |
| 6 | Link to the source | short answer | |
| 7 | Has the founder agreed to be featured? | multiple choice | (only for company or founder news) options: Yes / Not asked yet / Not sure |
| 8 | If they asked us to wait, until when? | date, optional | |
| 9 | Date of the event | date, optional | (only for events) |

## What happens to the answers

- **Company or founder news** is always saved as "not asked", even when the
  answer to question 7 is Yes. A team member's answer is not the founder's OK:
  Bader confirms it himself before anything is featured.
- **Events** are saved with the event date from question 9; an event with no
  date needs Bader's help before it can be used.
- **Links** are kept only if they start with `http://` or `https://`.
- **Dates** are read only when they are certain. A date such as 04/05/2026
  (April 5 or May 4?) is saved as "none".
- Rows without an answer to question 3 are skipped.
- Importing the same export twice does not create duplicates.

## Export each month

1. Open the form's responses Sheet.
2. **File > Download > Comma-separated values (.csv)**.
3. Move the downloaded file into the `intake` folder inside this project, then
   tell the assistant it is there. Do not attach it in the chat.
