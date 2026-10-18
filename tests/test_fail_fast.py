import contextlib
import io
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jev_client
import jev_role_ranker as rr


class Broken(object):
    total_calls = total_input_tokens = 0
    total_cost_usd = 0.0

    def ask(self, state, questions):
        self.total_calls += 1
        raise jev_client.JevError("failure {}".format(self.total_calls))


class FailFastTests(unittest.TestCase):
    def test_default_timeout_is_ten_seconds(self):
        self.assertEqual(jev_client.LiveClient(key="x").timeout, 10)

    def test_stops_after_three_consecutive_failures(self):
        client = Broken()
        with mock.patch.object(rr, "make_client", return_value=client), \
                contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            code = rr.main(["rank", os.path.join(ROOT, "examples", "postings")])
        self.assertEqual(code, 1)
        self.assertEqual(client.total_calls, 3)
        self.assertIn("failure 3", err.getvalue())
        self.assertEqual(len(err.getvalue().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
