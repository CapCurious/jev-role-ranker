# How EVAL.md was produced

Date 2026-10-18, model jev-1.13.0, 80 synthetic postings. The full tables are in EVAL.md at the
repository root. This note is the method.

1. Fixtures. `python3 examples/make_fixtures.py` writes 80 postings and `examples/gold.jsonl`
   from a seeded generator. Labels (fit, seniority, remote, sponsorship) come from the
   generator's rules, never from a model, so no model grades another model. The gold score uses
   the same weights as the ranker (fit 0.5, sponsorship 0.3, seniority 0.1, remote 0.1).
2. Live run. One Jev call per posting (80 calls, 61,961 input tokens, $0.0026) recorded to
   `examples/recorded_rank.json`, which `--demo` and the tests replay.
3. Ranking numbers. `python3 tools/eval_rank.py` replays the recording offline and prints
   Spearman against the gold score (0.863), top-10 overlap with the gold top 10 (6 of 10, strict
   and tie-aware), fit alone against gold fit (0.665), and accuracy of the three narrow
   questions (1.000 each).
4. Claude comparison. `python3 tools/compare_claude.py` asks `claude -p --model sonnet` to rate
   fit only on a stratified 40 (up to 8 per gold fit level): Spearman against gold fit 0.764
   for Claude versus 0.709 for Jev, median latency 3.50 s versus 0.18 s, cost per 1,000 items
   $4.34 versus $0.03.

What this cannot see: real postings, which are vaguer than the templates; more than one run;
confidence intervals. To reproduce, follow the commands at the top of EVAL.md.
