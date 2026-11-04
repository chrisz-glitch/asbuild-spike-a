"""Story S1: score a job file. Reference implementation for variant v1 (expected PROVEN).

Scoring rule (DECISIONS.md): the number of keywords in the job's `keywords` list that also appear in its
description, counted case-insensitively. Deterministic, an integer, trivially explainable.
"""
import json
import pathlib
import sys


def score_job(path: str) -> int:
    p = pathlib.Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    job = json.loads(p.read_text(encoding="utf-8"))
    text = str(job.get("description", "")).lower()
    return sum(1 for k in job.get("keywords", []) if str(k).lower() in text)


def cmd_score(argv) -> int:
    if len(argv) != 1:
        print("usage: python -m app score <job.json>", file=sys.stderr)
        return 2
    try:
        print(f"score: {score_job(argv[0])}")
        return 0
    except FileNotFoundError:
        print(f"no such file: {argv[0]}", file=sys.stderr)
        return 2
