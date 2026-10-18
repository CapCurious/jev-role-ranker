# jev-role-ranker

Rank job postings against your profile with TypeSafe's Jev, flag the ones that refuse visa sponsorship, and never reject one.

![Terminal demo of jev-role-ranker ranking 80 postings](docs/demo.gif)

The explainer lives at [docs/index.html](https://capcurious.github.io/jev-role-ranker/) (GitHub Pages): move the thresholds and weights and watch the table re-rank.

Real output of `python3 jev_role_ranker.py --demo rank examples/postings --limit 5 --sort fit` (row 1 is flagged):

```
DEMO (recorded response)
rank  score   fit  sponsor  seniority  remote   title                                   company               
--------------------------------------------------------------------------------------------------------------
   1  0.663   4.6  FLAG     early      remote   Associate Product Manager, Growth       Hollowell Goods       
   2  0.850   4.5           early      onsite   Associate Product Manager, Platform     Brightmoor Cloud      
   3  0.864   4.2           early      remote   Associate Product Manager, Growth       Solstice Grid         
   4  0.814   4.2           mid        remote   Product Manager, Platform               Redwood Freight       
   5  0.846   4.2           early      hybrid   Associate Product Manager, Platform     Hollowell Goods       
calls 80 | input tokens 61961 | cost $0.00260 | showing 5 of 80
```

The score only sorts. It never rejects a posting, and a person reads the sponsorship flags.

## What Jev is

Jev is a hosted decision model from TypeSafe. You send it a JSON state and a few typed
questions (yes or no, pick one, a 1 to 5 score) and it returns probabilities, not prose.
One call with four questions takes about 0.2 seconds and costs about $0.00003 at the
published $0.042 per million input tokens. It is small, fast and cheap by design, which is
what makes it usable inside a loop over hundreds of items.

Because the output is numbers, the policy lives in your code. Weights, sort order and the
flag thresholds in this tool are plain parameters. Change a weight or a threshold and the
table re-sorts without a new model call, because the probabilities are already in hand.

## Install

Python 3.10 or newer, standard library only.

```
git clone https://github.com/CapCurious/jev-role-ranker
cd jev-role-ranker
python3 jev_role_ranker.py --demo rank
```

Or run live without cloning (the `--demo` data needs the clone):

```
uvx --from git+https://github.com/CapCurious/jev-role-ranker jev-role-ranker rank postings/
```

## Quickstart (60 seconds)

1. Offline, no key: `python3 jev_role_ranker.py --demo rank`. The first line says
   `DEMO (recorded response)`; the rows are real Jev answers recorded on 80 synthetic postings.
2. Live: create a key at https://console.typesafe.ai/keys, then

```
export JEV_API_KEY=YOUR_KEY          # TYPESAFE_API_KEY also works
python3 jev_role_ranker.py --model jev-1.13.0 rank examples/postings --limit 10
```

Your own postings: a folder of `.txt` files, or a text file of URLs, one per line (fetched
with the standard library, tags stripped, capped at 6,000 characters). Put your own
description in a text file and pass `--profile me.txt`. The bundled profile is
"an MBA graduate targeting technical product roles in the United States, open to relocation".

Options (they work before or after the subcommand):

| Flag | Meaning |
|---|---|
| `--demo` | replay `examples/recorded_rank.json`, no key, no network |
| `--model` | Jev model id; pin a versioned id, aliases move |
| `--profile` | path to your profile text |
| `--weights` | `fit=0.5,sponsorship=0.3,seniority=0.1,remote=0.1` |
| `--sort` | `score` (default) or one factor: `fit`, `sponsorship`, `seniority`, `remote` |
| `--limit N` | show the first N rows; the footer still counts every posting scored |
| `--record FILE` | save every exchange so `--demo` can replay a run of your own |

## The four questions

One Jev call per posting, state `{"profile": ..., "posting": {"title", "text"}}`:

| Question | Type | Answers |
|---|---|---|
| `no_sponsorship` | yes or no | does the posting refuse to sponsor visas or require citizenship or permanent work authorization |
| `fit` | 1 to 5 | match against the profile text |
| `seniority` | pick one | early, mid, lead |
| `remote` | pick one | remote, hybrid, onsite |

They are deliberately narrow. Each has one thing to find in the text. A broad question
("is this a good job?") would hide the reason behind one number.

The weighted score is `0.5*fit + 0.3*sponsorship + 0.1*seniority + 0.1*remote`, each factor
scaled 0 to 1 (fit is (level - 1) / 4, sponsorship is 1 minus the probability of a refusal,
seniority maps early 1.0, mid 0.6, lead 0.2, remote maps remote 1.0, hybrid 0.7, onsite 0.4;
for the two choices the probabilities are averaged, not just the top pick).

## Threshold policy

Three bands, named act, review and escalate, set by two cut points: act at 0.85 and review
at 0.60. In this table they show up as the sponsorship column:

| Band | Cut | Table cell | Meaning |
|---|---|---|---|
| act | at or above 0.85 | `FLAG` | Jev is confident the posting refuses sponsorship; read it before applying |
| review | at or above 0.60 | `REVIEW` | probably a refusal; a person decides |
| escalate (no flag) | below 0.60 | blank | no flag; either a confident "no refusal" or too unsure to call, so blank does not mean safe |

The rule. The number that is banded for a yes/no question is certainty = max(p, 1 - p),
where p is Jev's probability of yes. For sponsorship the table bands the refusal side: FLAG
when p(refusal) is at or above act (0.85), REVIEW when it is at or above review (0.60),
blank otherwise, so a confident "no refusal" (p near 0) stays blank instead of flagging.
Fit, seniority and remote are banded on their confidence, the probability of the top
answer. A flag is a prompt to read the posting, never a rejection. The cut points are
defaults: each question deserves bands sized to the cost of a wrong call (missing a refusal
costs a wasted application; a false flag costs a glance), and a threshold lab (a sibling kit that fits act and review cut points on your own labeled data) can refit
them on your labeled data. Changing a threshold needs no new inference.

## Cookbook: sort a week of postings, then re-sort by what you care about today

```
python3 jev_role_ranker.py --demo rank examples/postings --sort fit --limit 5
python3 jev_role_ranker.py --demo explain --limit 1
```

The first command is the demo block above: sorted by fit alone, the Hollowell Goods row
(fit 4.6, flagged) moves from rank 32 to rank 1, and the default score order puts it
back at 32. The score only sorts; the flag stays on the row wherever it lands. `explain`
shows the four raw answers behind one row:

```
DEMO (recorded response)
1. Associate Product Manager, Growth | Solstice Grid
   no_sponsorship  p(yes) = 0.140   flag: none
   fit             level = 4.25 of 5   1=0.00 2=0.00 3=0.02 4=0.69 5=0.29
   seniority       early (1.000)   early=1.00 lead=0.00 mid=0.00
   remote          remote (1.000)   hybrid=0.00 onsite=0.00 remote=1.00
   weighted score  0.864
calls 80 | input tokens 61961 | cost $0.00260 | showing 1 of 80
```

Measured on the 80 synthetic postings with model jev-1.13.0 (rank run 2026-10-18):

| Measure | Value |
|---|---|
| Spearman, Jev weighted score versus gold score | 0.863 |
| Top-10 overlap with the gold top 10 | 6 of 10 |
| Sponsorship, seniority, remote accuracy versus gold | 1.000 each |
| Spearman, fit alone versus gold fit | 0.665 (n=80) |
| Share flagged at defaults | 25 of 80 (31 percent) FLAG, 0 REVIEW; all 25 are true refusals in the gold labels |
| Cost of the whole run | $0.0026 |

On a stratified n=40, claude sonnet (claude-sonnet-5-5) via the claude CLI 2.1.286 tracks gold fit slightly better than Jev (Spearman
0.764 versus 0.709) at about 20 times the latency and more than 100 times the cost. Details and the
commands to reproduce are in [EVAL.md](EVAL.md).

## Limits and honesty

- Rank never rejects. Every posting you give it appears in the table, failures last with
  the flag `ERROR`. A human reads the flags and the postings.
- Numbers, all dated 2026-10-18 on model jev-1.13.0 and synthetic postings only: Spearman
  0.863 and top-10 overlap 6 of 10 against gold on n=80; fit Spearman 0.709 for Jev versus
  0.764 for claude sonnet (claude-sonnet-5-5) via the claude CLI 2.1.286 against gold on the stratified n=40; 25 of 80 postings (31
  percent) flagged at the defaults. They describe these fixtures, not your postings.
- The thresholds were fit on synthetic postings and do not transfer. Real postings bury
  the sponsorship sentence, mix levels and use vaguer remote language. Refit on your own
  labeled sample and pin a versioned model id.
- Calibration is a population property. A 0.9 means roughly nine in ten of such answers
  are right across many items, not that this one is.
- Text only. Images are in beta and are not used. The state is capped at 64k tokens and
  each string field at 6,000 characters here.
- The four questions are deliberately narrow. Jev gives probabilities and no explanation,
  so `explain` shows numbers, not reasons.
- All fixtures are synthetic and labeled by the generator rules in
  `examples/make_fixtures.py`, dated 2026-10-18. The company names are invented. The 1.000
  accuracies reflect templates that state each fact in one clear sentence.
- Model aliases (`jev-latest`) change under you. The numbers above are for `jev-1.13.0`.

## Development

```
python3 -m unittest discover -s tests          # no key needed
JEV_LIVE=1 python3 -m unittest discover -s tests   # adds a live class, needs a key
python3 examples/make_fixtures.py              # regenerate postings and gold labels
python3 tools/eval_rank.py                     # rerun the ranking numbers offline
```

Expected in a git clone: `OK (skipped=1)` without a key (the live class skips), `OK` with one. In a downloaded tree with no `.git` directory it prints `OK (skipped=2)` without a key (the live class and the fresh-tree test skip) and `OK (skipped=1)` with one.

An agent skill is at `.claude/skills/jev-role-ranker/SKILL.md`; how the kit was built is in `docs/HOW_IT_WAS_BUILT.md`.

## License

MIT. See LICENSE.
