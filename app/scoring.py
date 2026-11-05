"""S1 scoring (seeded WRONG on purpose for T24a)."""
import json, pathlib, sys

def score_job(path):
    job = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))   # FileNotFoundError escapes -> traceback, exit 1
    text = str(job.get("description", "")).lower()
    return sum(1 for k in job.get("keywords", []) if str(k).lower() in text)

def cmd_score(argv):
    print(f"Score={score_job(argv[0])}")                                # wrong format for S1-C1
    return 0
