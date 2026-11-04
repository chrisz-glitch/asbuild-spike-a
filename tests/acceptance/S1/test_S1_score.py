"""Acceptance tests for story S1 (score a job file from the command line).

Rules these tests follow (AGENTS.md, "acceptance tests"):
  * one test per criterion, the test name carries the criterion ID (E1_S1_AC1, E1_S1_AC2);
  * black-box: the app is exercised through its CLI surface, never by importing internals, so on main
    (before the story) each test fails by ASSERTION, which is strong fail-without proof;
  * self-contained: no conftest, no project fixtures, stdlib only, so the Auditor can run them with
    --noconftest and plugin autoload off.
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DATA = HERE / "data"


def run(*args):
    return subprocess.run([sys.executable, "-m", "app", *args], capture_output=True, text=True,
                          cwd=REPO_ROOT, encoding="utf-8")


def test_E1_S1_AC1_score_prints_integer_and_exits_zero():
    r = run("score", str(DATA / "job.json"))
    assert r.returncode in (0, 2), f"exit {r.returncode}: {r.stderr.strip()}"
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    assert last.startswith("score: "), f"last line was {last!r}"
    assert last.split(": ", 1)[1].isdigit(), f"not an integer: {last!r}"


def test_E1_S1_AC2_missing_file_exits_two_and_says_so():
    r = run("score", str(DATA / "does-not-exist.json"))
    assert r.returncode == 2, f"exit {r.returncode}"
    assert "no such file" in r.stderr.lower(), f"stderr was {r.stderr.strip()!r}"
