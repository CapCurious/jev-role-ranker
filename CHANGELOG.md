# Changelog

## Unreleased, 2026-10-18 (iteration 2 of the quality loop)

- Input validation: a missing file, a non-UTF8 file, a malformed JSONL line or a record missing a field ends in one "error: <path>:<line>: <what>" line and exit 2, never a traceback.
- Range checks: thresholds, costs, steps and limits outside their range end in one line naming the flag and the allowed range, exit 2.
- Fail fast: 10 s HTTP timeout; after 3 consecutive failed calls the run stops with the last cause.
- A posting whose URL fetch fails is an ERROR row carrying the cause, never scored as text; `--record` is checked writable before the first paid call and written via a temp file.
- README: cost in short dated sentences, "no key, offline" on the demo line.

## Unreleased, 2026-10-18 (iteration 1 of the quality loop)

- README cut from 1,620 to about 1,090 words: framed as rank plus flag, never reject; the hero shows the default `--demo rank` output in descending score; cost per 1,000 and 100,000 postings and a "nothing to host" line; a Limits bullet on live score drift of about 0.02 between identical runs; the Jev section is shared word for word with the sibling kits.
- jev_client: HTTP 401 or 403 raises one clear line naming JEV_API_KEY and the console URL; `rank` and `explain` stop on the first auth error with exit 2.
- `rank` exits 1 and names the first cause when every posting fails; `--demo` with no subcommand runs `rank`.
- Demo mode no longer answers a posting that has no recording; it exits 2 with one line and no table.
- Explainer: a "Repo on GitHub" link in the rail; the localhost line in this file replaced by the live page.
- Gate: tests `OK (skipped=1)`, demo byte-identical, privacy grep all classes zero except the public origin remote, leakage scan 0 findings, scorecard 14 of 15 on the working tree.

## v5 (2026-10-18)

Docs glosses from cold reads. No code changed. "System One" does not appear in this README, so that gloss was skipped.

What changed:
- README: first mention of a threshold lab says it is a sibling kit that fits act and review cut points on your own labeled data.
- README: the model label "Claude (sonnet)" is now "claude sonnet via the claude CLI 2.1.286" in both places.

Gates (2026-10-18):
- tests: Ran 22 tests, OK (skipped=1)
- privacy scan: 0 findings
- name, path and secret grep: pass
- Em dashes across the folder: 0 files
- README.md: 196 lines
- Tag: v0.1.0

## v4 (2026-10-18)

Changed
- `tests/test_fresh_tree.py` skips unless a `.git` directory exists at the kit root ("needs git history; downloaded trees skip this"), so a downloaded tree no longer fails it.
- README: the expected test output line now says what each case prints; the band table reads "escalate (no flag)"; the fit Spearman 0.665 is labeled n=80 and 0.709 and 0.764 are labeled stratified n=40 (dates and model id kept).

Not changed: `jev_role_ranker.py` and `jev_client.py`. No remote.

Gates (run 2026-10-18)
- tests in the repo: `OK (skipped=1)`
- tests in a `git archive` tree with env limited to PATH and HOME: `OK (skipped=2)`
- privacy scan: 0 findings
- name, path and secret grep: pass
- em dash count: 0

## v3 (2026-10-18)

Changed (README only, from a cold read: 60 seconds on the README, then the quickstart)
- Line 3 now names Jev and says what the tool does: "Rank job postings against your profile with TypeSafe's Jev, flag the ones that refuse visa sponsorship, and never reject one."
- The demo block now shows a real FLAG row: `--demo rank examples/postings --limit 5 --sort fit` puts Hollowell Goods (row 32 by score) at rank 1 with FLAG. Output pasted from the real run.
- Threshold policy names act, review and escalate, maps them to FLAG, REVIEW and blank in a table, and states the banding rule (certainty = max(p, 1 - p); the sponsorship column bands the refusal side, so a confident "no refusal" stays blank).
- Limits carries the dated numbers with n and model id, plus the share flagged (25 of 80, 31 percent, all true refusals in gold).
- Cookbook shows the `--sort fit` reordering and the `explain` output as printed (with the DEMO label).
- Checked: docs/demo.gif exists (192,456 bytes) and the GIF line path is right; the explainer line and the skill pointer line are present and the paths exist.

Added
- `tests/test_fresh_tree.py`: exports tracked files with `git archive HEAD` into a temp directory and runs `--demo rank examples/postings --limit 3` there with env limited to PATH and HOME; asserts the DEMO label and three rows.

Not changed: `jev_role_ranker.py` and `jev_client.py`. Tag v0.1.0 set locally; no remote.

Gates (run 2026-10-18)
- tests: Ran 22 tests in 0.212s, OK (skipped=1)
- privacy scan: 0 findings
- name, path and secret grep: pass
- em dash count: 0 (every text file in the kit)
- README line count: 196 (limit 250)

## v2 (2026-10-18)

Added
- `docs/index.html`: single-file explainer (inline CSS and JS, no CDN, `color-scheme` light and dark). First viewport is the interactive: act and review threshold sliders, four weight sliders, a sort selector and a live table of the 80 fixture postings that re-sorts on every change, with the sponsorship flag moving between FLAG, REVIEW and blank. Stats recomputed live: Spearman against gold, top-10 overlap, share flagged, Jev cost per 1,000 postings. Three panels below: what Jev is, the band rule, the limits.
- `tools/make_explainer_data.py`: embeds `examples/recorded_rank.json` and `examples/gold.jsonl` into the page as one JS constant. At default settings the page reproduces 0.863 and 6 of 10, and all 80 scores and flags match the Python ranker.
- `docs/demo.tape` and `docs/demo.gif` (vhs, `--demo` only, no key on screen). The tape is 1100 by 540 pixels, about 112 columns by 28 rows, not 100 columns, because the table lines are 110 characters and wrap below that.
- `.claude/skills/jev-role-ranker/SKILL.md` (50 lines) with `references/questions.md` and `references/eval.md`.
- `.github/workflows/test.yml`: Python 3.11 and 3.13, `python3 -m unittest discover -s tests`.
- `docs/HOW_IT_WAS_BUILT.md`: the shared method page plus a kit section on what was and was not measured.
- README: two pointer lines only (explainer, skill and build page).

Not changed: `jev_role_ranker.py` and `jev_client.py` (sha256 unchanged).

Notes
- The "under 600 words on screen" bar is met by the prose, 494 words; the 80-row table adds about 600 more words of data.
- Sponsorship probabilities on these postings are bimodal (under 0.26 or over 0.91), so the flag only moves when a threshold crosses those edges. The page says so.
- The skill description itself says "Not for summarizing documents or writing text", which tells the decoys apart more easily than a description that omitted it. Treat the trigger test as an easy case.

Gates (run 2026-10-18)
- tests: Ran 21 tests in 0.135s, OK (skipped=1)
- privacy scan: 0 findings
- name, path and secret grep: pass
- em dash count: 0 (every text file in the kit)
- docs/index.html: 25,022 bytes (limit 150 KB)
- docs/demo.gif: 192,456 bytes (limit 2 MB), 12.76 s (limit 25 s); text checked legible on extracted frames at 5 s and 12 s
- console: built-in browser on the live page at https://capcurious.github.io/jev-role-ranker/ at 1280 light, 1280 dark and 375 mobile, no console messages and no errors; no horizontal page scroll at 375
- skill trigger test, a small model via `claude -p`, one call per phrase, 60 s timeout: "rank these postings" yes; "which of these jobs fit" yes; "flag sponsorship risk in these roles" yes; decoy "summarize this PDF" no; decoy "write a cover letter" no (5 of 5 as intended)

## v1 (2026-10-18)

Added
- `jev_role_ranker.py` with `rank` and `explain`, global flags `--demo --model --profile --weights --sort --limit --record`.
- Four typed questions per posting in one call: no_sponsorship (noul), fit (score), seniority (choice), remote (choice).
- `examples/make_fixtures.py`: 80 seeded synthetic postings and `examples/gold.jsonl` with labels by construction and a gold rank.
- `examples/recorded_rank.json`: real responses from a live run with jev-1.13.0 (80 calls, 61,961 input tokens, $0.0026), replayed by `--demo`.
- `tools/eval_rank.py` (ranking numbers offline) and `tools/compare_claude.py` (Jev versus `claude -p --model sonnet` on a stratified 40).
- 21 unittest tests plus a live class gated by JEV_LIVE=1.

Results (details in EVAL.md): Spearman 0.863 and top-10 overlap 6 of 10 against the gold rank; fit alone 0.665.

Decisions
- The API returns a fit `score` as the expected 0-based index into the criteria list (five criteria give 0 to 4, verified live 2026-10-18). The ranker adds 1 to report fit on the 1 to 5 scale and scales the factor as (level - 1) / 4. This is worth knowing for any kit that uses score questions.
- Sponsorship flag uses the raw probability of a refusal (FLAG at or above 0.85, REVIEW at or above 0.60), not max(p, 1 - p), because a confident "no refusal" must stay blank.
- A posting whose call fails twice stays in the table with flag ERROR and sorts last; rank never drops a posting.
- `--demo` needs a git clone (examples/ is not in the installed package); the message says so.
- Top-10 overlap is reported strict (gold ties broken by posting id) and tie-aware, because the gold has only 41 distinct scores.
- Not yet in v1: docs/index.html, docs/demo.gif, the skill, the CI workflow, docs/HOW_IT_WAS_BUILT.md. The README omits pointers to them until they exist.

Gates (run 2026-10-18)
- tests: Ran 21 tests in 0.113s, OK (skipped=1); with JEV_LIVE=1: Ran 21 tests in 1.053s, OK
- privacy scan: 0 findings
- name, path and secret grep: pass
- Python 3.10 parse: `ast.parse(feature_version=(3,10))` OK on every .py file
- em dash count: 0
