# jev-role-ranker
Rank plus flag, never reject: a pattern on TypeSafe's Jev, with job postings as the worked example. It sorts by profile fit, flags visa-sponsorship refusals and drops none.
Measured: Spearman 0.863 against the gold rank on synthetic postings (n=80, 2026-10-18, jev-1.13.0), $0.0026 for the run.

![Terminal demo of jev-role-ranker ranking 80 postings](docs/demo.gif)
### Quickstart (60 seconds)
```
git clone https://github.com/CapCurious/jev-role-ranker && cd jev-role-ranker
python3 jev_role_ranker.py --demo          # no key, offline
python3 jev_role_ranker.py --model jev-1.13.0 rank examples/postings --limit 10   # live: export JEV_API_KEY=YOUR_KEY first
```
## Cost and hosting

Cost, measured 2026-10-18 on jev-1.13.0 at the published $0.042 per million input tokens: one four-question call takes about 0.2 seconds and $0.00003. So 1,000 postings cost about $0.033 and 3.3 minutes serial on the fixture postings, about $0.088 on real postings at the 6,000-character cap. 100,000 cost about $3.30 to $8.80 and 5.5 hours. Demo mode is free and offline. Live mode sends each posting's text to TypeSafe.

Nothing to host: the explainer is a static page on GitHub Pages and the kit runs locally; there is no browser playground because the Jev API rejects browser origins (a preflight from github.io answered 400 Disallowed CORS origin on 2026-10-18).

## Output

Real output of `python3 jev_role_ranker.py --demo rank --limit 5` (recorded answers, 80 synthetic postings):

```
DEMO (recorded response)
rank  score   fit  sponsor  seniority  remote   title                                   company               
--------------------------------------------------------------------------------------------------------------
   1  0.864   4.2           early      remote   Associate Product Manager, Growth       Solstice Grid         
   2  0.850   4.5           early      onsite   Associate Product Manager, Platform     Brightmoor Cloud      
   3  0.846   4.2           early      hybrid   Associate Product Manager, Platform     Hollowell Goods       
   4  0.844   4.2           early      hybrid   Associate Product Manager, Data         Copperline Automation 
   5  0.826   4.0           mid        remote   Product Manager, Platform               Copperline Automation 
calls 80 | input tokens 61961 | cost $0.00260 | showing 5 of 80
```

A flagged row stays in the table at its score rank, marked `FLAG` (the Hollowell Goods growth role, fit 4.6, is rank 32). [Explainer](https://capcurious.github.io/jev-role-ranker/): drag thresholds and weights; the table re-ranks.

## What Jev is

Jev is a hosted decision model from TypeSafe. You send it a text and one or more typed questions (yes or no, pick one from a list, or a score from 1 to 5) and it returns a probability for each answer, with no prose.

The probability is the interface. Your code sets the threshold, so the same answer can mean act, review or escalate depending on what a wrong call costs you. Calibration is a property of a population of answers, measured on a dated sample, not a guarantee on any single answer.

## Install and inputs

Python 3.10 or newer, standard library only. Key: https://console.typesafe.ai/keys (`TYPESAFE_API_KEY` also works). Live without cloning (`--demo` needs the clone):

```
uvx --from git+https://github.com/CapCurious/jev-role-ranker jev-role-ranker rank postings/
```

Pass a folder of `.txt` files or a file of URLs, one per line (tags stripped, capped at 6,000 characters), and your description with `--profile me.txt`. Flags (before or after the subcommand): `--weights fit=0.5,sponsorship=0.3,seniority=0.1,remote=0.1`, `--sort score|fit|sponsorship|seniority|remote`, `--limit N` (the footer counts every posting), `--record FILE` (saves exchanges for `--demo` to replay).

## The four questions

One Jev call per posting, state `{"profile": ..., "posting": {"title", "text"}}`:

- `no_sponsorship`, yes or no: does the posting refuse to sponsor visas or require citizenship or permanent work authorization?
- `fit`, 1 to 5: match against the profile.
- `seniority`, pick one: early, mid, lead.
- `remote`, pick one: remote, hybrid, onsite.

Score = `0.5*fit + 0.3*sponsorship + 0.1*seniority + 0.1*remote`, each factor 0 to 1.
Fit is (level - 1) / 4; sponsorship 1 minus p(refusal); seniority early 1.0, mid 0.6, lead 0.2; remote remote 1.0, hybrid 0.7, onsite 0.4; choices probability-averaged.

## Threshold policy

Two cut points, three bands, in the sponsorship column:

- act, at or above 0.85: `FLAG`, confident refusal; read before applying.
- review, at or above 0.60: `REVIEW`, probable refusal; a person decides.
- escalate (no flag), below 0.60: blank, confident "no refusal" or too unsure to call; blank does not mean safe.

Sponsorship bands p(refusal), the one exception to the usual yes/no rule of certainty, max(p, 1 - p), so a confident "no refusal" stays blank; the others band the top answer's probability. The cuts are defaults: size them to the cost of a wrong call and refit with a threshold lab (a sibling kit that fits act and review cut points on your own labeled data), with no new inference.

## Cookbook: re-sort by today's priority

```
python3 jev_role_ranker.py --demo rank examples/postings --sort fit --limit 5
python3 jev_role_ranker.py --demo explain --limit 1
```

By fit alone the flagged Hollowell Goods row moves from rank 32 to rank 1, flag attached; `explain` prints a row's four raw answers.

## Limits

- Rank never rejects: every posting appears, failures last as `ERROR`; a human reads the flags.
- Numbers (2026-10-18, jev-1.13.0, synthetic only): n=80, Spearman 0.863, top-10 overlap 6 of 10, fit alone 0.665, sponsorship, seniority and remote accuracy 1.000 each, 25 of 80 (31 percent) FLAG and 0 REVIEW at defaults, all true refusals; stratified n=40, fit Spearman 0.709 for Jev versus 0.764 for claude sonnet (claude-sonnet-5-5) via the claude CLI 2.1.286, at about 20 times the latency and more than 100 times the cost. They describe these fixtures, not your postings; details in [EVAL.md](EVAL.md).
- Live scores can differ by about 0.02 between runs, so neighbouring ranks can swap while flags stay put; `--record` replays a run exactly.
- Thresholds fit on synthetic postings do not transfer; real postings bury the sponsorship sentence, mix levels, blur remote language. Refit on your labeled sample; pin a versioned model id.
- Calibration is a population property: a 0.9 means roughly nine in ten such answers are right, not this one.
- Text only (images are beta, unused); state capped at 64k tokens, string fields at 6,000 characters.
- Questions are deliberately narrow; Jev gives no explanation, so `explain` shows numbers, not reasons.
- Fixtures are synthetic, labeled by `examples/make_fixtures.py` rules (2026-10-18), company names invented; the 1.000 accuracies reflect one-sentence templates.
- Aliases (`jev-latest`) change under you; numbers are for `jev-1.13.0`.

## Development

```
python3 -m unittest discover -s tests          # no key needed
JEV_LIVE=1 python3 -m unittest discover -s tests   # adds a live class, needs a key
python3 examples/make_fixtures.py              # regenerate postings and gold labels
python3 tools/eval_rank.py                     # rerun the ranking numbers offline
```

Expected: `OK (skipped=1)` without a key, `OK` with one; a tree without `.git` prints `OK (skipped=2)` and `OK (skipped=1)`. Skill: `.claude/skills/jev-role-ranker/SKILL.md`; build notes: `docs/HOW_IT_WAS_BUILT.md`.

Jev kits: [jev-threshold-lab](https://github.com/CapCurious/jev-threshold-lab) fits cut points; [jev-cascade](https://github.com/CapCurious/jev-cascade) escalates Jev's unsure band.

## License

MIT, see LICENSE.
