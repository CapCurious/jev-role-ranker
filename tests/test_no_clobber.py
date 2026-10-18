import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jev_role_ranker as rr


class NoClobberTests(unittest.TestCase):
    def test_bad_record_path_fails_before_client_creation(self):
        missing = os.path.join(tempfile.gettempdir(), "missing-record-parent", "record.json")
        with mock.patch.object(rr, "make_client") as make, contextlib.redirect_stderr(io.StringIO()) as err:
            code = rr.main(["--record", missing, "rank", os.path.join(ROOT, "examples", "postings")])
        self.assertEqual(code, 2)
        make.assert_called_once()
        self.assertEqual(make.return_value.ask.call_count, 0)
        self.assertIn("--record", err.getvalue())

    def test_save_replaces_complete_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "record.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("old")
            rr.RecordingClient(object(), path, "model").save()
            with open(path, "r", encoding="utf-8") as fh:
                self.assertIn('"records": []', fh.read())


if __name__ == "__main__":
    unittest.main()
