import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jev_role_ranker as rr


class CountingClient(object):
    total_calls = total_input_tokens = 0
    total_cost_usd = 0.0

    def ask(self, state, questions):
        self.total_calls += 1
        raise AssertionError("fetch failures must not be scored")


class ErrorsNotResultsTests(unittest.TestCase):
    def test_failed_fetch_is_not_scored(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as fh:
            fh.write("https://example.invalid/job\n")
            fh.flush()
            with mock.patch.object(rr, "fetch_url", side_effect=urllib.error.URLError("x")):
                postings = rr.load_postings(fh.name)
        result = rr.score_posting(CountingClient(), "profile", postings[0])
        row = rr.build_rows(postings, [result], rr.DEFAULT_WEIGHTS)[0]
        self.assertEqual(row["flag"], "ERROR")
        self.assertIn("URLError", row["error"])

    def test_empty_posting_is_error_row(self):
        with tempfile.NamedTemporaryFile() as fh:
            postings = rr.load_postings(fh.name)
        result = rr.score_posting(CountingClient(), "profile", postings[0])
        self.assertEqual(rr.build_rows(postings, [result], rr.DEFAULT_WEIGHTS)[0]["flag"], "ERROR")


if __name__ == "__main__":
    unittest.main()
