"""S1: `python -m app score <file>` - score a job file.

Rule (see DECISIONS.md): count of `keywords` found in `description`, case-insensitive.
Exit codes: 0 ok, 2 usage error or missing file.
"""
import json
import sys


def score_job(job):
    description = str(job.get("description", "")).lower()
    return sum(1 for k in job.get("keywords", []) if str(k).lower() in description)


def score_command(args):
    if len(args) != 1:
        print("usage: python -m app score <file>", file=sys.stderr)
        return 2
    path = args[0]
    try:
        with open(path, encoding="utf-8") as f:
            job = json.load(f)
    except FileNotFoundError:
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    print(f"score: {score_job(job)}")
    return 0
