import contextlib
import io
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jev_role_ranker as rr


class InputValidationTests(unittest.TestCase):
    def test_missing_folder_is_one_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = rr.main(["--demo", "rank", "/no/such/postings"])
        self.assertEqual(code, 2)
        self.assertEqual(len(stderr.getvalue().splitlines()), 1)

    def test_empty_folder_is_one_error(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(io.StringIO()) as err:
            code = rr.main(["--demo", "rank", folder])
        self.assertEqual(code, 2)
        self.assertIn(folder, err.getvalue())

    def test_non_utf8_posting_is_one_error(self):
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(b"\xff")
            fh.flush()
            with contextlib.redirect_stderr(io.StringIO()) as err:
                code = rr.main(["--demo", "rank", fh.name])
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())


if __name__ == "__main__":
    unittest.main()
