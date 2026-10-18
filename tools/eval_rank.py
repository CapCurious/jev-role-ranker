"""Compare the Jev ranking with the gold rank from examples/gold.jsonl.

Offline by default: it replays examples/recorded_rank.json (the real responses from the
live run), so the numbers reproduce without a key. Pass --live to ask Jev again.

  python3 tools/eval_rank.py
  python3 tools/eval_rank.py --live --model jev-1.13.0
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jev_client  # noqa: E402
import jev_role_ranker as rr  # noqa: E402


def average_ranks(values):
    """1-based ranks, higher value gets rank 1; ties share the mean rank."""
    order = sorted(range(len(values)), key=lambda i: -values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = mean
        i = j + 1
    return ranks


def spearman(a, b):
    ra, rb = average_ranks(a), average_ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((y - mb) ** 2 for y in rb)
    return cov / (va * vb) ** 0.5 if va and vb else 0.0


def top_k_overlap(pred_scores, gold_scores, gold_rank, k=10):
    """Return (strict, tie_aware) overlap counts out of k.
    strict: Jev top k versus the k lowest gold_rank values (ties already broken by posting id).
    tie_aware: Jev top-k items whose gold score is at least the k-th best gold score."""
    n = len(pred_scores)
    jev_top = sorted(range(n), key=lambda i: -pred_scores[i])[:k]
    strict = sum(1 for i in jev_top if gold_rank[i] <= k)
    cut = sorted(gold_scores, reverse=True)[k - 1]
    tie_aware = sum(1 for i in jev_top if gold_scores[i] >= cut)
    return strict, tie_aware


def load_gold(path):
    with open(path, "r", encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    return {r["id"]: r for r in rows}


def jev_rows(live=False, model="jev-1.13.0"):
    postings = rr.load_postings(os.path.join(ROOT, "examples", "postings"))
    profile = rr.load_profile(None)
    if live:
        client = jev_client.LiveClient(model=model)
    else:
        client = jev_client.RecordedClient(os.path.join(ROOT, "examples", "recorded_rank.json"))
    results = [rr.score_posting(client, profile, p) for p in postings]
    return postings, rr.build_rows(postings, results, dict(rr.DEFAULT_WEIGHTS)), client


def metrics(postings, rows, gold):
    by_id = {r["id"]: r for r in rows}
    ids = [p["id"] for p in postings]
    pred = [by_id[i]["score"] for i in ids]
    g_score = [gold[i]["gold_score"] for i in ids]
    g_rank = [gold[i]["gold_rank"] for i in ids]
    g_fit = [gold[i]["fit"] for i in ids]
    j_fit = [rr.fit_level(by_id[i]["answers"]["fit"]) for i in ids]
    strict, tie = top_k_overlap(pred, g_score, g_rank, 10)
    acc = {
        "no_sponsorship": sum(1 for i in ids if (by_id[i]["p_no"] >= 0.5) == gold[i]["no_sponsorship"]) / len(ids),
        "seniority": sum(1 for i in ids if by_id[i]["seniority"] == gold[i]["seniority"]) / len(ids),
        "remote": sum(1 for i in ids if by_id[i]["remote"] == gold[i]["remote"]) / len(ids),
    }
    return {
        "accuracy": acc,
        "n": len(ids),
        "spearman_rank": spearman(pred, g_score),
        "top10_strict": strict,
        "top10_tie_aware": tie,
        "spearman_fit": spearman(j_fit, g_fit),
        "jev_scores": dict(zip(ids, pred)),
        "jev_fit": dict(zip(ids, j_fit)),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--model", default="jev-1.13.0")
    args = ap.parse_args(argv)
    gold = load_gold(os.path.join(ROOT, "examples", "gold.jsonl"))
    postings, rows, client = jev_rows(args.live, args.model)
    m = metrics(postings, rows, gold)
    print("n={} postings".format(m["n"]))
    print("spearman (Jev weighted score vs gold score): {:.3f}".format(m["spearman_rank"]))
    print("top-10 overlap strict (gold rank ties broken by id): {}/10".format(m["top10_strict"]))
    print("top-10 overlap tie-aware (gold score >= 10th best): {}/10".format(m["top10_tie_aware"]))
    print("spearman (Jev fit vs gold fit): {:.3f}".format(m["spearman_fit"]))
    for k, v in m["accuracy"].items():
        print("accuracy {} vs gold label: {:.3f}".format(k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
