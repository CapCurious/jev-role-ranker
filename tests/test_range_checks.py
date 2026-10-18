import contextlib
import io
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jev_role_ranker as rr


class RangeCheckTests(unittest.TestCase):
    def test_nan_weight_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = rr.main(["--demo", "--weights", "fit=nan", "rank"])
        self.assertEqual(code, 2)
        self.assertIn("--weights", err.getvalue())

    def test_zero_weight_sum_rejected(self):
        weights = "fit=0,sponsorship=0,seniority=0,remote=0"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(rr.main(["--demo", "--weights", weights, "rank"]), 2)

    def test_limit_must_be_positive(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = rr.main(["--demo", "--limit", "0", "rank"])
        self.assertEqual(code, 2)
        self.assertIn("--limit", err.getvalue())

    def test_thresholds_are_checked(self):
        with mock.patch.object(rr, "FLAG_AT", 2.0), contextlib.redirect_stderr(io.StringIO()) as err:
            code = rr.main(["--demo", "rank"])
        self.assertEqual(code, 2)
        self.assertIn("0 to 1", err.getvalue())


if __name__ == "__main__":
    unittest.main()
