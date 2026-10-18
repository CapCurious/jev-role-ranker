import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAS_GIT = os.path.isdir(os.path.join(ROOT, ".git"))


@unittest.skipUnless(HAS_GIT, "needs git history; downloaded trees skip this")
class FreshTreeTest(unittest.TestCase):
    """The tracked files alone must run the quickstart: no untracked or ignored file may be needed."""

    def test_demo_runs_from_git_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tar_path = os.path.join(tmp, "tree.tar")
            subprocess.run(["git", "archive", "--format=tar", "-o", tar_path, "HEAD"],
                           cwd=ROOT, check=True)
            dest = os.path.join(tmp, "tree")
            os.mkdir(dest)
            subprocess.run(["tar", "-xf", tar_path, "-C", dest], check=True)
            env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}
            out = subprocess.run(
                [sys.executable, "jev_role_ranker.py", "--demo", "rank", "examples/postings", "--limit", "3"],
                cwd=dest, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("DEMO (recorded response)", out.stdout)
            rows = [ln for ln in out.stdout.splitlines() if ln.strip()[:1].isdigit() and ln.split()[0].isdigit()]
            self.assertEqual(len(rows), 3, out.stdout)


if __name__ == "__main__":
    unittest.main()
