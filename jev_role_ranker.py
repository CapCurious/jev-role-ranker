"""jev-role-ranker: rank job postings against a reader profile with four typed Jev questions each.

One Jev call per posting. The four questions are deliberately narrow:
  no_sponsorship  noul    does the posting refuse to sponsor work visas
  fit             score   1 to 5 match against the profile text
  seniority       choice  early | mid | lead
  remote          choice  remote | hybrid | onsite

The weighted score only sorts. It never rejects: every posting you give it appears in
the output, and a human reads the sponsorship flag column.

Usage:
  python3 jev_role_ranker.py --demo rank
  python3 jev_role_ranker.py --model jev-1.13.0 rank examples/postings
  python3 jev_role_ranker.py rank urls.txt --sort fit --limit 10
  python3 jev_role_ranker.py explain examples/postings --limit 3

Python 3.10 or newer, standard library only, plus the bundled jev_client.py.
"""
import argparse
import datetime
import html
import html.parser
import json
import os
import re
import sys
import urllib.request

import jev_client

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILE = ("an MBA graduate targeting technical product roles in the United States, "
                   "open to relocation")
DEFAULT_WEIGHTS = {"fit": 0.5, "sponsorship": 0.3, "seniority": 0.1, "remote": 0.1}
SENIORITY_W = {"early": 1.0, "mid": 0.6, "lead": 0.2}
REMOTE_W = {"remote": 1.0, "hybrid": 0.7, "onsite": 0.4}
SORT_KEYS = ("score", "fit", "sponsorship", "seniority", "remote")
FLAG_AT = 0.85
REVIEW_AT = 0.60
TEXT_CAP = 6000

QUESTIONS = {
    "no_sponsorship": {
        "type": "noul",
        "instructions": ("The posting says the employer will not sponsor work visas, or requires "
                         "citizenship, permanent residency, or work authorization without "
                         "sponsorship"),
    },
    "fit": {
        "type": "score",
        "instructions": ("How well this posting matches the reader described in the profile, "
                         "judging role type, level, skills and location"),
        "criteria": [
            "1: almost no overlap with the profile",
            "2: little overlap, a stretch in role or level",
            "3: some overlap, several things do not line up",
            "4: strong overlap, one or two things do not line up",
            "5: near-perfect match on role, level, skills and location",
        ],
    },
    "seniority": {
        "type": "choice",
        "instructions": "The experience level the posting asks for",
        "criteria": {
            "early": "Entry level or early career, roughly 0 to 2 years of experience",
            "mid": "Mid level, roughly 3 to 7 years of experience",
            "lead": "Senior, lead or manager level, 8 or more years or leads people",
        },
    },
    "remote": {
        "type": "choice",
        "instructions": "Where the work is done",
        "criteria": {
            "remote": "Fully remote",
            "hybrid": "Part of the week in an office, part remote",
            "onsite": "Fully onsite at an office or facility",
        },
    },
}


# ---------------------------------------------------------------- input

class _TextExtractor(html.parser.HTMLParser):
    SKIP = ("script", "style", "noscript", "template")

    def __init__(self):
        html.parser.HTMLParser.__init__(self, convert_charrefs=True)
        self.parts = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in ("p", "br", "li", "div", "h1", "h2", "h3", "tr"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.parts.append(data)


def strip_html(raw):
    """Return (title, text) from an HTML string. Tags and scripts removed, whitespace collapsed."""
    parser = _TextExtractor()
    parser.feed(raw)
    parser.close()
    text = re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()
    return re.sub(r"\s+", " ", parser.title).strip(), text[:TEXT_CAP]


def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "jev-role-ranker/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(500000).decode("utf-8", "replace")
    return strip_html(raw)


def parse_posting_text(name, raw):
    """Split an optional Title:/Company: header from the body. Returns a posting dict."""
    title, company = "", ""
    lines = raw.splitlines()
    body_start = 0
    for i, line in enumerate(lines[:4]):
        m = re.match(r"^(Title|Company|Location):\s*(.*)$", line)
        if not m:
            break
        if m.group(1) == "Title":
            title = m.group(2).strip()
        elif m.group(1) == "Company":
            company = m.group(2).strip()
        body_start = i + 1
    if not title:
        first = next((ln.strip() for ln in lines if ln.strip()), name)
        title = first[:80]
    return {"id": name, "title": title, "company": company or "-", "text": raw.strip()[:TEXT_CAP]}


def load_postings(source):
    """Folder of .txt files, a file of URLs (one per line), or a single text file."""
    if os.path.isdir(source):
        names = sorted(n for n in os.listdir(source) if n.endswith(".txt"))
        if not names:
            raise SystemExit("no .txt files in {}".format(source))
        out = []
        for n in names:
            with open(os.path.join(source, n), "r", encoding="utf-8") as fh:
                out.append(parse_posting_text(n[:-4], fh.read()))
        return out
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as fh:
            raw = fh.read()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if lines and all(re.match(r"^https?://", ln) for ln in lines):
            out = []
            for i, url in enumerate(lines, start=1):
                try:
                    title, text = fetch_url(url)
                except Exception as exc:  # a failed fetch still appears in the table
                    title, text = "", "[fetch failed: {}]".format(type(exc).__name__)
                out.append({"id": "u{:03d}".format(i), "title": title or url[:80],
                            "company": "-", "text": text})
            return out
        return [parse_posting_text(os.path.basename(source), raw)]
    raise SystemExit("input not found: {}".format(source))


def load_profile(path):
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    local = os.path.join(HERE, "profile.txt")
    if os.path.isfile(local):
        with open(local, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    return DEFAULT_PROFILE


# ---------------------------------------------------------------- scoring

def parse_weights(text):
    weights = dict(DEFAULT_WEIGHTS)
    if not text:
        return weights
    for part in text.split(","):
        key, _, val = part.partition("=")
        key = key.strip()
        if key not in DEFAULT_WEIGHTS:
            raise SystemExit("unknown weight {!r}; use {}".format(key, ",".join(DEFAULT_WEIGHTS)))
        try:
            weights[key] = float(val)
        except ValueError:
            raise SystemExit("weight {} needs a number, got {!r}".format(key, val))
    return weights


def _expected(answer, table):
    probs = answer.get("probabilities") or {}
    total = sum(probs.get(k, 0.0) for k in table)
    if total > 0:
        return sum(probs.get(k, 0.0) * w for k, w in table.items()) / total
    return table.get(answer.get("choice"), 0.0)


def fit_level(answer):
    """Fit on the 1 to 5 scale. The API returns the expected 0-based index into the criteria
    list (checked live 2026-10-18: five criteria give scores between 0 and 4), so add one."""
    return float(answer["score"]) + 1.0


def factors_from_answers(answers):
    """Map the four raw answers to factor values, each in 0..1 (higher is better for the reader)."""
    p_no = float(answers["no_sponsorship"]["noul"])
    fit = min(1.0, max(0.0, fit_level(answers["fit"]) - 1.0) / 4.0)
    return {
        "fit": fit,
        "sponsorship": 1.0 - p_no,
        "seniority": _expected(answers["seniority"], SENIORITY_W),
        "remote": _expected(answers["remote"], REMOTE_W),
    }


def weighted_score(factors, weights):
    return sum(weights[k] * factors[k] for k in DEFAULT_WEIGHTS)


def sponsorship_flag(p_no):
    """FLAG when the probability of a no-sponsorship statement is >= 0.85, REVIEW >= 0.60, else blank."""
    kind = jev_client.band(p_no, act=FLAG_AT, review=REVIEW_AT)
    return {"act": "FLAG", "review": "REVIEW"}.get(kind, "")


def score_posting(client, profile, posting):
    state = {"profile": profile, "posting": {"title": posting["title"], "text": posting["text"]}}
    last = None
    for _ in range(2):
        try:
            answers, usage = client.ask(state, QUESTIONS)
            return {"answers": answers, "usage": usage, "error": None}
        except jev_client.JevError as exc:
            last = exc
    return {"answers": None, "usage": {}, "error": str(last)}


def build_rows(postings, results, weights):
    rows = []
    for post, res in zip(postings, results):
        row = {"id": post["id"], "title": post["title"], "company": post["company"],
               "error": res["error"], "answers": res["answers"]}
        if res["answers"] is None:
            row.update(score=None, factors=None, flag="ERROR", seniority="", remote="", p_no=None)
        else:
            f = factors_from_answers(res["answers"])
            row.update(
                factors=f,
                score=weighted_score(f, weights),
                p_no=float(res["answers"]["no_sponsorship"]["noul"]),
                flag=sponsorship_flag(float(res["answers"]["no_sponsorship"]["noul"])),
                seniority=res["answers"]["seniority"]["choice"],
                remote=res["answers"]["remote"]["choice"],
            )
        rows.append(row)
    return rows


def sort_rows(rows, key="score"):
    """Sort best first by weighted score or by one factor. Failed rows go last; nothing is dropped."""
    if key not in SORT_KEYS:
        raise SystemExit("--sort must be one of {}".format(", ".join(SORT_KEYS)))

    def value(row):
        if row["factors"] is None:
            return (1, 0.0, 0.0)
        main = row["score"] if key == "score" else row["factors"][key]
        return (0, -main, -row["score"])

    return sorted(rows, key=value)


# ---------------------------------------------------------------- output

def _clip(text, width):
    text = text or ""
    return text if len(text) <= width else text[:width - 1] + "~"


def format_table(rows, limit=None):
    head = "{:>4}  {:>5}  {:>4}  {:<7}  {:<9}  {:<7}  {:<38}  {:<22}".format(
        "rank", "score", "fit", "sponsor", "seniority", "remote", "title", "company")
    lines = [head, "-" * len(head)]
    shown = rows if limit is None else rows[:limit]
    for pos, row in enumerate(shown, start=1):
        if row["factors"] is None:
            score, fit = "  n/a", " n/a"
        else:
            score = "{:5.3f}".format(row["score"])
            fit = "{:4.1f}".format(fit_level(row["answers"]["fit"]))
        lines.append("{:>4}  {:>5}  {:>4}  {:<7}  {:<9}  {:<7}  {:<38}  {:<22}".format(
            pos, score, fit, row["flag"], row["seniority"], row["remote"],
            _clip(row["title"], 38), _clip(row["company"], 22)))
    return "\n".join(lines)


def format_footer(client, shown, total):
    return "calls {} | input tokens {} | cost ${:.5f} | showing {} of {}".format(
        client.total_calls, client.total_input_tokens, client.total_cost_usd, shown, total)


def format_explain(rows, limit=None):
    out = []
    shown = rows if limit is None else rows[:limit]
    for pos, row in enumerate(shown, start=1):
        out.append("{}. {} | {}".format(pos, row["title"], row["company"]))
        if row["answers"] is None:
            out.append("   error: {}".format(row["error"]))
            continue
        a = row["answers"]
        out.append("   no_sponsorship  p(yes) = {:.3f}   flag: {}".format(
            float(a["no_sponsorship"]["noul"]), row["flag"] or "none"))
        out.append("   fit             level = {:.2f} of 5   {}".format(
            fit_level(a["fit"]), _probs(a["fit"].get("probabilities"), shift=1)))
        out.append("   seniority       {} ({:.3f})   {}".format(
            a["seniority"]["choice"], float(a["seniority"]["confidence"]),
            _probs(a["seniority"].get("probabilities"))))
        out.append("   remote          {} ({:.3f})   {}".format(
            a["remote"]["choice"], float(a["remote"]["confidence"]),
            _probs(a["remote"].get("probabilities"))))
        out.append("   weighted score  {:.3f}".format(row["score"]))
    return "\n".join(out)


def _probs(probs, shift=0):
    if not probs:
        return ""
    return " ".join("{}={:.2f}".format(int(k) + shift if shift else k, float(v))
                    for k, v in sorted(probs.items()))


# ---------------------------------------------------------------- recording

class RecordingClient(object):
    """Wraps a live client and keeps every exchange so --demo can replay it later."""

    def __init__(self, inner, path, model):
        self.inner = inner
        self.path = path
        self.model = model
        self.records = []

    def ask(self, state, questions):
        answers, usage = self.inner.ask(state, questions)
        self.records.append({"questions": questions, "state": state,
                             "answers": answers, "usage": usage})
        return answers, usage

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def save(self):
        doc = {"meta": {"model": self.model, "recorded": datetime.date.today().isoformat(),
                        "note": "synthetic postings; recorded by jev_role_ranker.py --record"},
               "records": self.records}
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
            fh.write("\n")


# ---------------------------------------------------------------- cli

def _common(parser, suppress):
    """Global flags. The subparsers repeat them with SUPPRESS so they work before or after the command."""
    def opt(*names, **kw):
        if suppress:
            kw["default"] = argparse.SUPPRESS
        parser.add_argument(*names, **kw)

    opt("--demo", action="store_true", default=False,
        help="replay examples/recorded_rank.json, no key and no network")
    opt("--model", default="jev-latest",
        help="Jev model id; pin a versioned id such as jev-1.13.0")
    opt("--profile", default=None, help="path to a profile text file (default: bundled profile.txt)")
    opt("--weights", default=None, help="fit=0.5,sponsorship=0.3,seniority=0.1,remote=0.1")
    opt("--sort", default="score", help="score or one factor: " + ", ".join(SORT_KEYS[1:]))
    opt("--limit", type=int, default=None, help="show only the first N rows")
    opt("--record", default=None, help="write every exchange to this JSON file for later --demo")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="jev-role-ranker",
        description="Rank job postings against a reader profile. The score only sorts; it never rejects.")
    _common(parser, suppress=False)
    sub = parser.add_subparsers(dest="command")
    for name, text in (("rank", "print the ranked table"),
                       ("explain", "print the four raw answers per posting")):
        p = sub.add_parser(name, help=text)
        p.add_argument("input", nargs="?", help="folder of .txt files, or a file of URLs")
        _common(p, suppress=True)
    return parser


def make_client(args):
    demo_path = os.path.join(HERE, "examples", "recorded_rank.json")
    if args.demo:
        if not os.path.isfile(demo_path):
            raise SystemExit("demo data not found at {}; --demo needs a git clone of the repository "
                             "(examples/ is not part of the installed package)".format(demo_path))
        return jev_client.RecordedClient(demo_path)
    return jev_client.client_from_env(model=args.model)


def run(args, out=None):
    out = out or sys.stdout
    source = args.input
    if not source:
        if args.demo:
            source = os.path.join(HERE, "examples", "postings")
        else:
            raise SystemExit("give a folder of .txt files or a file of URLs")
    weights = parse_weights(args.weights)
    profile = load_profile(args.profile)
    postings = load_postings(source)
    try:
        client = make_client(args)
    except jev_client.JevKeyMissing as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.record and not args.demo:
        client = RecordingClient(client, args.record, args.model)
    if args.demo:
        print(jev_client.DEMO_LABEL, file=out)
    results = [score_posting(client, profile, p) for p in postings]
    rows = sort_rows(build_rows(postings, results, weights), args.sort)
    if args.command == "explain":
        print(format_explain(rows, args.limit), file=out)
    else:
        print(format_table(rows, args.limit), file=out)
    shown = len(rows) if args.limit is None else min(args.limit, len(rows))
    print(format_footer(client, shown, len(rows)), file=out)
    if isinstance(client, RecordingClient):
        client.save()
    failed = sum(1 for r in rows if r["error"])
    if failed:
        print("{} posting(s) failed and are listed last with flag ERROR".format(failed), file=sys.stderr)
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
