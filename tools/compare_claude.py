"""Compare Jev fit scores with a Claude CLI fit rating on a stratified 40 of the 80 postings.

Both read the same profile and posting text and answer the same fit question (1 to 5).
Labels come from examples/gold.jsonl (rule-generated, never from a model), so neither
side is graded by a model. Claude is called as `claude -p --model sonnet` with settings,
tools and slash commands switched off so the call carries no local context.

  python3 tools/compare_claude.py                 # needs claude on PATH and, for live Jev, a key
  python3 tools/compare_claude.py --jev recorded  # Jev answers replayed from the recorded run

Writes tools/compare_claude_results.json and replaces the region between the COMPARE
markers in EVAL.md.
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import re
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import jev_client  # noqa: E402
import jev_role_ranker as rr  # noqa: E402
from eval_rank import load_gold, spearman  # noqa: E402

N_SAMPLE = 40
PER_LEVEL = 8
TIMEOUT_S = 60
START, END = "<!-- COMPARE START -->", "<!-- COMPARE END -->"
CLAUDE_CMD = ["claude", "-p", "--model", "sonnet", "--output-format", "json",
              "--setting-sources", "", "--tools", "", "--disable-slash-commands",
              "--strict-mcp-config", "--no-session-persistence",
              "--system-prompt", "You rate how well a job posting fits a profile. Reply with one digit from 1 to 5 and nothing else."]


def stratified(gold, n=N_SAMPLE):
    """Up to PER_LEVEL postings per gold fit level, then fill to n in id order. Deterministic."""
    by_level = {}
    for pid in sorted(gold):
        by_level.setdefault(gold[pid]["fit"], []).append(pid)
    chosen = []
    for level in sorted(by_level):
        chosen.extend(by_level[level][:PER_LEVEL])
    rest = [pid for pid in sorted(gold) if pid not in chosen]
    chosen.extend(rest[:max(0, n - len(chosen))])
    return sorted(chosen[:n])


def claude_prompt(profile, posting):
    return ("Profile: {}\n\nPosting title: {}\n\nPosting text: {}\n\n"
            "How well does this posting fit the profile, judging role type, level, skills and location? "
            "1 = almost no overlap, 2 = little overlap, 3 = some overlap, 4 = strong overlap, "
            "5 = near-perfect match. Reply with one integer from 1 to 5 and nothing else."
            ).format(profile, posting["title"], posting["text"])


def ask_claude(prompt):
    started = time.time()
    try:
        proc = subprocess.run(CLAUDE_CMD + [prompt], capture_output=True, text=True, timeout=TIMEOUT_S)
        doc = json.loads(proc.stdout)
        text = str(doc.get("result", ""))
        m = re.search(r"[1-5]", text)
        model = next(iter(doc.get("modelUsage", {})), "")
        return {"fit": int(m.group(0)) if m else None, "latency": time.time() - started,
                "cost": float(doc.get("total_cost_usd", 0.0)), "model": model, "raw": text.strip()[:20]}
    except Exception as exc:
        return {"fit": None, "latency": time.time() - started, "cost": 0.0, "model": "",
                "raw": "error: " + type(exc).__name__}


def ask_jev(mode, profile, postings, model):
    if mode == "live":
        client = jev_client.LiveClient(model=model)
    else:
        client = jev_client.RecordedClient(os.path.join(ROOT, "examples", "recorded_rank.json"))
    out = {}
    for p in postings:
        res = rr.score_posting(client, profile, p)
        if res["answers"] is None:
            out[p["id"]] = {"fit": None, "latency": 0.0, "tokens": 0}
            continue
        out[p["id"]] = {"fit": rr.fit_level(res["answers"]["fit"]),
                        "latency": client.last_latency_s,
                        "tokens": res["usage"].get("input_tokens", 0)}
    return out


def build_table(results, mode, model, claude_model):
    ids = [i for i in results["ids"] if results["claude"][i]["fit"] is not None
           and results["jev"][i]["fit"] is not None]
    c = [float(results["claude"][i]["fit"]) for i in ids]
    j = [results["jev"][i]["fit"] for i in ids]
    g = [float(results["gold_fit"][i]) for i in ids]
    exact = sum(1 for a, b in zip(c, j) if round(b) == a) / len(ids)
    within1 = sum(1 for a, b in zip(c, j) if abs(round(b) - a) <= 1) / len(ids)
    gexact_j = sum(1 for a, b in zip(g, j) if round(b) == a) / len(ids)
    gexact_c = sum(1 for a, b in zip(g, c) if b == a) / len(ids)
    jev_cost = sum(results["jev"][i]["tokens"] for i in ids) * jev_client.PRICE_PER_MILLION_INPUT / 1e6 / len(ids) * 1000
    claude_cost = sum(results["claude"][i]["cost"] for i in ids) / len(ids) * 1000
    med_j = statistics.median(results["jev"][i]["latency"] for i in ids)
    med_c = statistics.median(results["claude"][i]["latency"] for i in ids)
    lines = [
        "Run {} | n={} of {} stratified postings (up to {} per gold fit level) | Jev {} ({}) | Claude {} via `claude -p --model sonnet`".format(
            datetime.date.today().isoformat(), len(ids), len(results["ids"]), PER_LEVEL, model, mode, claude_model or "sonnet"),
        "",
        "| Measure | Jev | Claude (sonnet) |",
        "|---|---|---|",
        "| Spearman, fit versus gold fit | {:.3f} | {:.3f} |".format(spearman(j, g), spearman(c, g)),
        "| Exact match to gold fit (Jev rounded) | {:.3f} | {:.3f} |".format(gexact_j, gexact_c),
        "| Spearman, Jev fit versus Claude fit | {:.3f} | same |".format(spearman(j, c)),
        "| Agreement Jev (rounded) versus Claude, exact / within 1 | {:.3f} / {:.3f} | same |".format(exact, within1),
        "| Median latency per item, seconds | {:.2f} | {:.2f} |".format(med_j, med_c),
        "| Cost per 1,000 items, USD | {:.2f} | {:.2f} |".format(jev_cost, claude_cost),
        "",
        "Cost for Jev is input tokens at $0.042 per million (output is free). Cost for Claude is the CLI's own "
        "`total_cost_usd` at list prices with settings, tools and slash commands switched off. Claude rates fit only, "
        "so the ranker comparison is on the fit factor, not on the four-factor weighted score. Gold labels come from "
        "the fixture generator rules, so neither side is graded by a model. Synthetic postings, one run, "
        "no confidence interval.",
    ]
    return "\n".join(lines)


def write_eval(table):
    path = os.path.join(ROOT, "EVAL.md")
    with open(path, "r", encoding="utf-8") as fh:
        doc = fh.read()
    block = START + "\n" + table + "\n" + END
    if START in doc and END in doc:
        pre, rest = doc.split(START, 1)
        _, post = rest.split(END, 1)
        doc = pre + block + post
    else:
        doc = doc.rstrip("\n") + "\n\n" + block + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", choices=["live", "recorded"], default="live")
    ap.add_argument("--model", default="jev-1.13.0")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    gold = load_gold(os.path.join(ROOT, "examples", "gold.jsonl"))
    ids = stratified(gold)
    postings = {p["id"]: p for p in rr.load_postings(os.path.join(ROOT, "examples", "postings"))}
    chosen = [postings[i] for i in ids]
    profile = rr.load_profile(None)
    print("sample {} postings; asking Jev ({})".format(len(ids), args.jev), flush=True)
    jev = ask_jev(args.jev, profile, chosen, args.model)
    print("asking claude, {} workers".format(args.workers), flush=True)
    claude = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(ask_claude, claude_prompt(profile, postings[i])): i for i in ids}
        for fut in concurrent.futures.as_completed(futs):
            claude[futs[fut]] = fut.result()
            print("  claude {}/{} done".format(len(claude), len(ids)), flush=True)
    results = {"ids": ids, "jev": jev, "claude": claude,
               "gold_fit": {i: gold[i]["fit"] for i in ids}}
    with open(os.path.join(ROOT, "tools", "compare_claude_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
        fh.write("\n")
    claude_model = next((v["model"] for v in claude.values() if v["model"]), "")
    table = build_table(results, args.jev, args.model, claude_model)
    write_eval(table)
    print(table, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
