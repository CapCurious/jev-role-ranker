# The four questions

One Jev call per posting. The state is `{"profile": <text>, "posting": {"title": ..., "text": ...}}`.
The texts below are the ones in `jev_role_ranker.py` (`QUESTIONS`), verbatim.

## no_sponsorship (yes or no)

> The posting says the employer will not sponsor work visas, or requires citizenship, permanent
> residency, or work authorization without sponsorship

Narrow because there is one sentence to find. The answer is a probability of "yes", so the
ranker bands the raw probability: FLAG at or above 0.85, REVIEW at or above 0.60, blank below.
A confident "no refusal" must stay blank, which is why it does not use max(p, 1 - p).

## fit (score, 1 to 5)

> How well this posting matches the reader described in the profile, judging role type, level,
> skills and location

Criteria: 1 almost no overlap with the profile; 2 little overlap, a stretch in role or level;
3 some overlap, several things do not line up; 4 strong overlap, one or two things do not line
up; 5 near-perfect match on role, level, skills and location.

This is the soft question and the only one that depends on the profile text. The API returns
the expected 0-based index into the criteria, so the ranker adds 1 to report the 1 to 5 level.
It is kept to one profile and one posting, with the scale spelled out, so the number means the
same thing on every call.

## seniority (pick one)

> The experience level the posting asks for

Options: early (0 to 2 years), mid (3 to 7 years), lead (8 or more years, or leads people).
Narrow because the years requirement is stated in the text, so there is little to interpret.

## remote (pick one)

> Where the work is done

Options: remote (fully remote), hybrid (part of the week in an office), onsite (fully onsite).

## Why narrow

A broad question such as "is this a good job?" would fold the reason into one number and could
not be re-weighted. Four questions, each with one thing to find, give four numbers the reader
can weight and sort by in code. Changing a weight needs no new inference.
