"""S1 scoring: count of `keywords` found in `description`, case-insensitive."""
import json, pathlib, sys


def score_job(path):
    job = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    text = str(job.get("description", "")).lower()
    return sum(1 for k in job.get("keywords", []) if str(k).lower() in text)


def cmd_score(argv):
    if not argv:
        print("usage: score <file>", file=sys.stderr)
        return 2
    try:
        n = score_job(argv[0])
    except FileNotFoundError:
        print(f"no such file: {argv[0]}", file=sys.stderr)
        return 2
    print(f"score: {n}")
    return 0
