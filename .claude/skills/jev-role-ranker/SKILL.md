---
name: jev-role-ranker
description: Rank a folder of job postings against a profile with Jev, a hosted decision model, and flag postings that refuse visa sponsorship. Use when the user says "rank these postings", "which of these jobs fit", or "flag sponsorship risk in these roles". Not for summarizing documents or writing text.
---

# jev-role-ranker

Ranks job postings with four typed Jev questions per posting and prints one table: weighted
score, fit (1 to 5), a sponsorship flag, seniority, remote. Output is numbers only, so it is
fast (about 0.2 seconds a posting) and cheap (about $0.03 per 1,000 postings).

## When to use

- The user has several postings (a folder of .txt files, or a text file of URLs) and wants
  them ordered against a short profile.
- The user wants a quick screen for postings that say they will not sponsor a visa.
- The user wants to re-weight or re-sort without paying for new model calls.

## When not to use

- One posting that needs a written assessment, a summary, or a tailored cover letter. Jev
  returns probabilities and no prose.
- Anything that must reject a posting automatically. The score only sorts, and a blank
  sponsorship cell does not mean safe. A person reads the flags.
- Images, or more than 64k tokens of state per call.

## Commands

Run from the kit directory. Python 3.10 or newer, standard library only.

```
python3 jev_role_ranker.py --demo rank examples/postings --limit 8
export JEV_API_KEY=YOUR_KEY    # TYPESAFE_API_KEY also works
python3 jev_role_ranker.py --model jev-1.13.0 rank POSTINGS_DIR --profile me.txt --sort fit
python3 jev_role_ranker.py --demo explain --limit 1
```

- `--demo` replays recorded answers, needs no key and no network, and prints
  `DEMO (recorded response)` on the first line. Offer it first.
- `--weights fit=0.5,sponsorship=0.3,seniority=0.1,remote=0.1` and `--sort` change the order
  without a new call when replaying; live runs call Jev once per posting.
- Pin a versioned model id; aliases move. Never print or log the key.

## Reading the result

- Sponsorship column: FLAG at or above 0.85 refusal probability, REVIEW from 0.60, blank below.
- A failed posting stays in the table with flag ERROR, last. Nothing is dropped.
- Thresholds were fit on synthetic postings and do not transfer. Say so when reporting.

Questions and why each is narrow: references/questions.md. How the numbers were measured: references/eval.md.
