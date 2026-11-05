import json
import subprocess
import sys


def run(*args):
    return subprocess.run([sys.executable, "-m", "app", *args], capture_output=True, text=True, encoding="utf-8")


def test_score_counts_keywords_case_insensitively(tmp_path):
    f = tmp_path / "j.json"
    f.write_text(json.dumps({"description": "Python and LLM", "keywords": ["python", "llm", "go"]}), encoding="utf-8")
    r = run("score", str(f))
    assert r.returncode == 0
    assert r.stdout.strip().splitlines()[-1] == "score: 2"


def test_score_missing_file_exits_two(tmp_path):
    r = run("score", str(tmp_path / "nope.json"))
    assert r.returncode == 2
    assert "no such file" in r.stderr
