"""S1 scoring: `python -m app score <job.json>` prints `score: N`."""
import json
import pathlib
import sys


def score_job(path):
    job = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    text = str(job.get("description", "")).lower()
    return sum(1 for k in job.get("keywords", []) if str(k).lower() in text)


def cmd_score(argv):
    if len(argv) != 1:
        print("usage: python -m app score <job.json>", file=sys.stderr)
        return 2
    path = argv[0]
    if not pathlib.Path(path).is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    print(f"score: {score_job(path)}")
    return 0
