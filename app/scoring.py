"""S1 scoring: count of job keywords found in the job description."""
import json, pathlib, sys

def score_job(path):
    job = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    text = str(job.get("description", "")).lower()
    return sum(1 for k in job.get("keywords", []) if str(k).lower() in text)

def cmd_score(argv):
    if len(argv) != 1:
        print("usage: python -m app score <file>", file=sys.stderr)
        return 2
    try:
        value = score_job(argv[0])
    except FileNotFoundError:
        print(f"no such file: {argv[0]}", file=sys.stderr)
        return 2
    print(f"score: {value}")
    return 0
