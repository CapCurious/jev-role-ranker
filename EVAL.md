# EVAL: jev-role-ranker

Rank run 2026-10-18, n=80 synthetic postings, model jev-1.13.0.

Reproduce the ranking numbers offline (replays examples/recorded_rank.json, no key):

```
python3 tools/eval_rank.py
```

Reproduce from scratch with a key (about 16 seconds, about $0.003):

```
python3 examples/make_fixtures.py
python3 tools/eval_rank.py --live --model jev-1.13.0
```

Reproduce the Jev versus Claude comparison (needs the `claude` CLI and a key, about 3 minutes):

```
nohup python3 tools/compare_claude.py > tools/compare_claude.log 2>&1 &
```

## Ranking against the gold rank

Weights fit=0.5, sponsorship=0.3, seniority=0.1, remote=0.1. Gold is computed from the
generator's labels with the same weights, so it is exact by construction.

| Measure | Value |
|---|---|
| Spearman, Jev weighted score versus gold score | 0.863 |
| Top-10 overlap, strict (gold ties broken by posting id) | 6 of 10 |
| Top-10 overlap, tie-aware (gold score at or above the 10th best) | 6 of 10 |
| Spearman, Jev fit versus gold fit | 0.665 |
| Accuracy of no_sponsorship (p at least 0.5) versus gold | 1.000 |
| Accuracy of seniority versus gold | 1.000 |
| Accuracy of remote versus gold | 1.000 |

Read it plainly. The three narrow questions are right on every synthetic posting because
the templates state the answer in one sentence. The fit question is the soft one, and it
drives the gap between the ranking and gold: Jev rates fit on its own reading of the
profile, while the gold counts five signals. The 0.863 is a statement about these 80
generated postings, not about real listings. Real postings bury the sponsorship sentence,
mix levels and use vaguer remote language, so expect lower numbers.

Raw output of `python3 tools/eval_rank.py`:

```
n=80 postings
spearman (Jev weighted score vs gold score): 0.863
top-10 overlap strict (gold rank ties broken by id): 6/10
top-10 overlap tie-aware (gold score >= 10th best): 6/10
spearman (Jev fit vs gold fit): 0.665
accuracy no_sponsorship vs gold label: 1.000
accuracy seniority vs gold label: 1.000
accuracy remote vs gold label: 1.000
```

## Jev versus Claude on a stratified 40

<!-- COMPARE START -->
Run 2026-10-18 | n=40 of 40 stratified postings (up to 8 per gold fit level) | Jev jev-1.13.0 (live) | Claude claude-sonnet-5-5 via `claude -p --model sonnet`

| Measure | Jev | Claude (sonnet) |
|---|---|---|
| Spearman, fit versus gold fit | 0.709 | 0.764 |
| Exact match to gold fit (Jev rounded) | 0.300 | 0.475 |
| Spearman, Jev fit versus Claude fit | 0.838 | same |
| Agreement Jev (rounded) versus Claude, exact / within 1 | 0.525 / 0.925 | same |
| Median latency per item, seconds | 0.18 | 3.50 |
| Cost per 1,000 items, USD | 0.03 | 4.34 |

Cost for Jev is input tokens at $0.042 per million (output is free). Cost for Claude is the CLI's own `total_cost_usd` at list prices with settings, tools and slash commands switched off. Claude rates fit only, so the ranker comparison is on the fit factor, not on the four-factor weighted score. Gold labels come from the fixture generator rules, so neither side is graded by a model. Synthetic postings, one run, no confidence interval.
<!-- COMPARE END -->
