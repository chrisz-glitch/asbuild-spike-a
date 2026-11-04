#!/usr/bin/env python3
"""Wait for the AsBuild verdict on the current commit and print it. A program, no judgement.

Why this exists: `gh pr checks --watch` returns when the untrusted test workflow finishes, which is a few
seconds BEFORE the trusted workflow (started by workflow_run) posts the AsBuild check run. This script waits
for that check run specifically.

Usage (from the repository root, on the build branch, after `git push`):
  python tools/asbuild_wait.py [--timeout 1200] [--check-name AsBuild]

Prints the check run's summary (contains the verdict JSON block) and exits:
  0 = PROVEN (success)   4 = WAITING FOR YOU (action_required)   1 = NOT PROVEN (failure)   7 = timeout
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time


def sh(*cmd: str) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--check-name", default="AsBuild")
    ap.add_argument("--sha", help="defaults to git rev-parse HEAD")
    a = ap.parse_args(argv)
    gh = shutil.which("gh") or sys.exit("gh CLI not found")
    repo = sh(gh, "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    sha = a.sha or sh("git", "rev-parse", "HEAD")
    print(f"waiting for check '{a.check_name}' on {repo}@{sha[:10]} (up to {a.timeout}s)")
    deadline = time.time() + a.timeout
    while time.time() < deadline:
        data = json.loads(sh(gh, "api", f"repos/{repo}/commits/{sha}/check-runs?per_page=100"))
        runs = [r for r in data.get("check_runs", [])
                if r.get("name") == a.check_name and (r.get("app") or {}).get("slug") == "github-actions"]
        done = [r for r in runs if r.get("status") == "completed"]
        if done:
            r = sorted(done, key=lambda x: x.get("completed_at") or "")[-1]
            print(f"conclusion: {r.get('conclusion')}\n")
            print((r.get("output") or {}).get("summary") or "(no summary)")
            return {"success": 0, "action_required": 4}.get(r.get("conclusion"), 1)
        time.sleep(a.interval)
    print("timeout: no completed AsBuild check run; look at the Actions tab")
    return 7


if __name__ == "__main__":
    sys.exit(main())
