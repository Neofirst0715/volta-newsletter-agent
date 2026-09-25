# System manifest (v4)

## What this is
A folder that helps Bader, Volta's newsletter editor, prepare the monthly
newsletter with an AI tool (Claude Code, Cursor or Codex). The AI follows
AGENTS.md; three Python scripts (standard library only) do all the deciding.
Everything is a draft. Nothing is ever sent.

## The flow
inbox items -> scripts/check_items.py (verdict per item + plain report)
-> Bader answers what is missing, one question at a time
-> the AI drafts only from items the check marked ready
-> scripts/verify_draft.py (hard checks on the draft)
-> Bader reads it and says whether it went out
-> scripts/state.py mark-sent (issue file + ledger for next month)

## Principle
Code decides, the AI only drafts, Bader decides what happens. Verdicts come
from structured fields and code, never from what item text says. The v3
version is kept under archive/v3/ for reference only.
