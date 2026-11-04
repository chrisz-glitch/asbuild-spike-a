#!/usr/bin/env python3
"""AsBuild C3 fail-without, the spike's G3 overlay (auditor.py) applied to story-owned acceptance tests.

Each acceptance test file at the head is laid over the base unchanged, one file at a time, and run with the
hardened flags (no conftest, no plugin autoload). One JUnit XML per file goes into --out; the trusted side
classifies them with junit_classify.py. A test that passes here proves nothing.

Usage: c3_overlay.py --base origin/main [--head HEAD] [--paths tests/acceptance] --out out/c3
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auditor import TEST_FILE, sh  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--paths", default="tests/acceptance")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    repo = "."
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    head = sh(["git", "rev-parse", args.head], repo).stdout.strip()
    base = sh(["git", "merge-base", args.base, head], repo).stdout.strip() or args.base
    files = [p for p in sh(["git", "ls-tree", "-r", "--name-only", head, "--", args.paths], repo).stdout.split()
             if TEST_FILE.search(p)]
    print(f"base {base[:10]}  head {head[:10]}  acceptance files: {len(files)}")
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    tmp = tempfile.mkdtemp(prefix="c3-")
    try:
        for path in files:
            slug = re.sub(r"[^a-z0-9]", "_", path.lower())
            one = os.path.join(tmp, slug)
            sh(["git", "worktree", "add", "--detach", one, base], repo)
            sh(["git", "checkout", head, "--", path], one)
            proc = subprocess.run([sys.executable, "-m", "pytest", path, "--noconftest", "-p", "no:cacheprovider",
                                   "--continue-on-collection-errors", "-o", "junit_family=xunit2",
                                   f"--junitxml={os.path.join(out, slug + '.xml')}"],
                                  cwd=one, env=env, capture_output=True, text=True)
            print(f"== {path} over base: pytest exit {proc.returncode}\n" + proc.stdout[-600:])
            sh(["git", "worktree", "remove", "--force", one], repo)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
