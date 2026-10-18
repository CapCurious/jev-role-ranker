"""Tests for jev-role-ranker. Run: python3 -m unittest discover -s tests

No key is needed. LiveTests run only with JEV_LIVE=1 and a key in JEV_API_KEY or TYPESAFE_API_KEY.
"""
import contextlib
import filecmp
import io
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "examples"))

import jev_client  # noqa: E402
import jev_role_ranker as rr  # noqa: E402
import make_fixtures  # noqa: E402


def answers(p_no=0.1, fit_score=3.0, seniority="mid", remote="hybrid"):
    """Hand-made raw answers in the shape the API returns."""
    return {
        "no_sponsorship": {"type": "noul", "noul": p_no},
        "fit": {"type": "score", "score": fit_score, "confidence": 0.8,
                "probabilities": {"0": 0.0, "1": 0.0, "2": 0.0, "3": 1.0, "4": 0.0}},
        "seniority": {"type": "choice", "choice": seniority, "confidence": 1.0,
                      "probabilities": {k: (1.0 if k == seniority else 0.0) for k in rr.SENIORITY_W}},
        "remote": {"type": "choice", "choice": remote, "confidence": 1.0,
                   "probabilities": {k: (1.0 if k == remote else 0.0) for k in rr.REMOTE_W}},
    }


def make_rows(specs):
    postings = [{"id": "x{}".format(i), "title": "Role {}".format(i), "company": "Co {}".format(i), "text": "t"}
                for i in range(len(specs))]
    results = [{"answers": a, "usage": {}, "error": None} for a in specs]
    return rr.build_rows(postings, results, dict(rr.DEFAULT_WEIGHTS))


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = rr.main(argv)
    return code, buf.getvalue()


class GeneratorTests(unittest.TestCase):
    def test_deterministic(self):
        a, b = make_fixtures.generate(), make_fixtures.generate()
        self.assertEqual([t for t, _ in a], [t for t, _ in b])
        self.assertEqual([l for _, l in a], [l for _, l in b])

    def test_written_files_identical_and_match_shipped(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            make_fixtures.write(d1)
            make_fixtures.write(d2)
            cmp = filecmp.dircmp(os.path.join(d1, "postings"), os.path.join(d2, "postings"))
            self.assertEqual(cmp.diff_files, [])
            self.assertEqual(len(os.listdir(os.path.join(d1, "postings"))), 80)
            shipped = os.path.join(ROOT, "examples")
            self.assertTrue(filecmp.cmp(os.path.join(d1, "gold.jsonl"), os.path.join(shipped, "gold.jsonl"),
                                        shallow=False))

    def test_labels_by_construction(self):
        for text, labels in make_fixtures.generate():
            refuses = any(s in text for s in make_fixtures.NO_SPONSOR)
            self.assertEqual(labels["no_sponsorship"], refuses)
            self.assertTrue(6 <= text.split("\n\n", 1)[1].count(". ") + 1 <= 10)
            self.assertTrue(1 <= labels["fit"] <= 5)

    def test_gold_rank_is_a_strict_order(self):
        ranks = sorted(l["gold_rank"] for _, l in make_fixtures.generate())
        self.assertEqual(ranks, list(range(1, 81)))


class ScoreTests(unittest.TestCase):
    def test_weighted_score_math(self):
        # fit 4 -> 0.75; sponsorship 1 - 0.2 = 0.8; early 1.0; remote 1.0
        f = rr.factors_from_answers(answers(p_no=0.2, fit_score=3.0, seniority="early", remote="remote"))
        self.assertAlmostEqual(f["fit"], 0.75)
        self.assertAlmostEqual(f["sponsorship"], 0.8)
        score = rr.weighted_score(f, rr.DEFAULT_WEIGHTS)
        self.assertAlmostEqual(score, 0.5 * 0.75 + 0.3 * 0.8 + 0.1 * 1.0 + 0.1 * 1.0)

    def test_custom_weights(self):
        w = rr.parse_weights("fit=1,sponsorship=0,seniority=0,remote=0")
        f = rr.factors_from_answers(answers(fit_score=4.0))
        self.assertAlmostEqual(rr.weighted_score(f, w), 1.0)

    def test_bad_weight_name_exits(self):
        with self.assertRaises(SystemExit):
            rr.parse_weights("luck=1")

    def test_flag_thresholds(self):
        self.assertEqual(rr.sponsorship_flag(0.85), "FLAG")
        self.assertEqual(rr.sponsorship_flag(0.99), "FLAG")
        self.assertEqual(rr.sponsorship_flag(0.84), "REVIEW")
        self.assertEqual(rr.sponsorship_flag(0.60), "REVIEW")
        self.assertEqual(rr.sponsorship_flag(0.59), "")
        self.assertEqual(rr.sponsorship_flag(0.0), "")

    def test_sort_reorders(self):
        rows = make_rows([
            answers(p_no=0.9, fit_score=4.0, seniority="early", remote="remote"),   # high fit, flagged
            answers(p_no=0.0, fit_score=1.0, seniority="lead", remote="onsite"),    # low fit, clean
            answers(p_no=0.0, fit_score=2.0, seniority="mid", remote="hybrid"),
        ])
        by_score = [r["id"] for r in rr.sort_rows(rows, "score")]
        by_fit = [r["id"] for r in rr.sort_rows(rows, "fit")]
        by_spons = [r["id"] for r in rr.sort_rows(rows, "sponsorship")]
        self.assertEqual(by_fit[0], "x0")
        self.assertNotEqual(by_fit, by_spons)
        self.assertEqual(by_spons[-1], "x0")
        self.assertEqual(len(by_score), 3)
        with self.assertRaises(SystemExit):
            rr.sort_rows(rows, "vibes")

    def test_failed_posting_is_kept_and_listed_last(self):
        class Broken(object):
            total_calls = total_input_tokens = 0
            total_cost_usd = 0.0

            def ask(self, state, questions):
                raise jev_client.JevError("boom")

        postings = [{"id": "a", "title": "A", "company": "-", "text": "t"}]
        res = [rr.score_posting(Broken(), "profile", postings[0])]
        rows = rr.sort_rows(rr.build_rows(postings, res, dict(rr.DEFAULT_WEIGHTS)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["flag"], "ERROR")
        self.assertIn("ERROR", rr.format_table(rows))


class InputTests(unittest.TestCase):
    def test_html_stripping(self):
        raw = ("<html><head><title>Product Manager at Example</title><style>p{color:red}</style></head>"
               "<body><script>var secret = 1;</script><h1>Product Manager</h1>"
               "<p>Build &amp; ship things.</p><ul><li>Roadmap</li><li>Specs</li></ul></body></html>")
        title, text = rr.strip_html(raw)
        self.assertEqual(title, "Product Manager at Example")
        self.assertNotIn("<", text)
        self.assertNotIn("secret", text)
        self.assertNotIn("color:red", text)
        self.assertIn("Build & ship things.", text)
        self.assertIn("Roadmap Specs", text)

    def test_text_cap(self):
        _, text = rr.strip_html("<p>" + "word " * 5000 + "</p>")
        self.assertLessEqual(len(text), 6000)

    def test_folder_and_header_parse(self):
        postings = rr.load_postings(os.path.join(ROOT, "examples", "postings"))
        self.assertEqual(len(postings), 80)
        self.assertTrue(postings[0]["title"])
        self.assertNotEqual(postings[0]["company"], "-")

    def test_default_profile_text(self):
        self.assertEqual(rr.load_profile(None),
                         "an MBA graduate targeting technical product roles in the United States, "
                         "open to relocation")


class DemoTests(unittest.TestCase):
    def test_demo_prints_label_and_80_rows(self):
        code, out = run_cli(["--demo", "rank"])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], jev_client.DEMO_LABEL)
        body = lines[3:-1]
        self.assertEqual(len(body), 80)
        self.assertIn("calls 80", lines[-1])
        self.assertTrue(body[0].split()[0] == "1")

    def test_demo_flags_match_gold_and_nothing_dropped(self):
        _, out = run_cli(["--demo", "rank"])
        body = out.splitlines()[3:-1]
        self.assertEqual(len(body), 80)
        flagged = sum(1 for ln in body if " FLAG " in ln)
        gold = make_fixtures.generate()
        self.assertEqual(flagged, sum(1 for _, l in gold if l["no_sponsorship"]))

    def test_demo_sort_and_limit(self):
        _, out = run_cli(["--demo", "rank", "--sort", "sponsorship", "--limit", "5"])
        lines = out.splitlines()
        self.assertEqual(len(lines), 1 + 2 + 5 + 1)
        self.assertIn("showing 5 of 80", lines[-1])
        _, base = run_cli(["--demo", "rank", "--limit", "5"])
        self.assertNotEqual(lines[3:8], base.splitlines()[3:8])

    def test_flags_work_before_or_after_subcommand(self):
        _, a = run_cli(["--demo", "--limit", "2", "rank"])
        _, b = run_cli(["rank", "--demo", "--limit", "2"])
        self.assertEqual(a, b)

    def test_explain_prints_four_probabilities(self):
        _, out = run_cli(["--demo", "explain", "--limit", "2"])
        for word in ("no_sponsorship", "fit", "seniority", "remote"):
            self.assertIn(word, out)

    def test_record_roundtrip(self):
        # RecordingClient keeps what it was given and RecordedClient replays it
        class Fake(object):
            total_calls = total_input_tokens = 0
            total_cost_usd = 0.0

            def ask(self, state, questions):
                return {"q": {"type": "noul", "noul": 0.5}}, {"input_tokens": 7}

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "rec.json")
            rec = rr.RecordingClient(Fake(), path, "jev-test")
            rec.ask({"a": 1}, {"q": {"type": "noul", "instructions": "x"}})
            rec.save()
            back = jev_client.RecordedClient(path)
            answers_back, usage = back.ask({"a": 1}, {"q": {"type": "noul", "instructions": "x"}})
            self.assertEqual(answers_back["q"]["noul"], 0.5)
            self.assertEqual(usage["input_tokens"], 7)


def _have_key():
    return bool(os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY"))


@unittest.skipUnless(os.environ.get("JEV_LIVE") == "1" and _have_key(), "set JEV_LIVE=1 and a key to run")
class LiveTests(unittest.TestCase):
    def test_rank_five_postings(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(ROOT, "examples", "postings")
            for name in sorted(os.listdir(src))[:5]:
                shutil.copy(os.path.join(src, name), d)
            code, out = run_cli(["--model", "jev-1.13.0", "rank", d])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(len(lines[2:-1]), 5)
        self.assertIn("calls 5", lines[-1])
        self.assertNotIn(jev_client.DEMO_LABEL, out)


if __name__ == "__main__":
    unittest.main()
