# Two challenges, and how the system answers them

## The two challenges

Based on the interviews with Bader and Matt, the newsletter process has two key problems:

1. **Content is captured in scattered places.** Updates arrive through Slack, conversations and LinkedIn, and there is no single place where they are logged and structured.
2. **Nothing tracks the status of each item.** It is hard to manage founder approvals and to avoid repeated or outdated stories.

## What we built

1. **One file-based inbox.** Whether Bader pastes a Slack message, a note from a conversation or a LinkedIn post, or drops in the CSV export of the team form, each update becomes one standard markdown file. The original wording and the link are kept. If a detail is missing, it is flagged and the user is reminded.
2. **A status for every item, set by scripts (not by the AI):** ready; waiting on a founder's OK (or held until a date the founder asked for, or asked not to be named); missing information; conflict (two sources disagree about the same event); or left out (already happened, older than the last issue, already in the last issue, or the same news as another item). Text inside an item that looks like instructions to the AI is flagged and ignored: it can never change a status.
3. **A team form as a second door.** Team members send news through a Google Form. Bader downloads the answers as a CSV and saves the file in the intake folder; the tool turns each row into an item. A "Yes" on the form is only a claim: those items wait until Bader confirms the founder's OK himself.

## How it works

**Saving news.** Paste the text into the chat. The assistant saves it in the inbox folder with the name of the company, person, event or program, the original wording and the link, and flags anything incomplete or missing. It never invents facts: a missing date or link is saved as "none" and pointed out. A founder's approval is recorded only after the assistant quotes the sentence back and the user explicitly confirms it. A "Yes" on the team form never counts as approval.

**Making an issue.** With items in the inbox, say "start" and give the issue date. The system checks the items and shows what is ready. Before drafting, it tells the user about missing details, reminds them about founder approvals (it only reminds; the user decides), and lists what was left out and why. The AI drafts only from items marked ready, in their original wording, each with its source link. Bader chooses which items go in, how many and what opens the issue; a small issue is fine. A second script then verifies the draft, and the user reads it, because the checks cannot catch a wrong date or number next to a correct link. When the user confirms the issue went out, it is recorded, so the same links are not repeated next time. Items that were not used, and items still waiting, come back the next time.

**Nothing is moved.** All files stay in the inbox. Deleting a draft changes nothing: every item is still there with its status. Nothing is ever sent.