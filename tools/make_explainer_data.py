"""Embed the fixture data into docs/index.html as one JS constant.

Reads examples/recorded_rank.json (real Jev answers) and examples/gold.jsonl (labels by
construction), joins them by posting order (the recording follows sorted file names), and
rewrites the block between the DATA markers in docs/index.html. Offline, standard library only.

  python3 tools/make_explainer_data.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "docs", "index.html")
START, END = "/*DATA START*/", "/*DATA END*/"


def build():
    with open(os.path.join(ROOT, "examples", "recorded_rank.json"), "r", encoding="utf-8") as fh:
        rec = json.load(fh)
    with open(os.path.join(ROOT, "examples", "gold.jsonl"), "r", encoding="utf-8") as fh:
        gold = [json.loads(line) for line in fh if line.strip()]
    gold.sort(key=lambda g: g["id"])
    records = rec["records"]
    if len(records) != len(gold):
        raise SystemExit("records {} and gold {} differ".format(len(records), len(gold)))
    rows, tokens = [], 0
    for g, r in zip(gold, records):
        title = r["state"]["posting"]["title"]
        if title != g["title"]:
            raise SystemExit("order mismatch at {}: {!r} vs {!r}".format(g["id"], title, g["title"]))
        a = r["answers"]
        sen, rem = a["seniority"]["probabilities"], a["remote"]["probabilities"]
        tokens += r["usage"]["input_tokens"]
        rows.append([
            g["title"], g["company"],
            round(float(a["no_sponsorship"]["noul"]), 4),
            round(float(a["fit"]["score"]), 3),
            [sen["early"], sen["mid"], sen["lead"]],
            [rem["remote"], rem["hybrid"], rem["onsite"]],
            g["fit"], g["gold_score"], g["gold_rank"],
        ])
    return {"model": rec["meta"]["model"], "recorded": rec["meta"]["recorded"],
            "inputTokens": tokens, "pricePerMillion": 0.042, "rows": rows}


def main():
    data = build()
    block = "{}\nconst DATA = {};\n{}".format(START, json.dumps(data, separators=(",", ":")), END)
    with open(PAGE, "r", encoding="utf-8") as fh:
        page = fh.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(page):
        raise SystemExit("DATA markers not found in docs/index.html")
    page = pattern.sub(lambda m: block, page)
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote {} rows, {} input tokens, {} bytes of page".format(
        len(data["rows"]), data["inputTokens"], len(page.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
