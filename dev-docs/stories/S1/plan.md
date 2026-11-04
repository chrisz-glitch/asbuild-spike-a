# Plan S1

Read before planning: dev-docs/dead-ends.md (nothing recorded yet).

## Files the build PR may change

- app/scoring.py (new)
- app/__main__.py (edit: register the `score` command)
- tests/unit/test_scoring.py (new)
- DECISIONS.md (append one line: the scoring rule)

New files are allowed only under: app/, tests/unit/

## Tests (one per criterion, already in this PR, locked at merge)

- S1-C1 -> tests/acceptance/S1/test_S1_score.py::test_S1_C1_score_prints_integer_and_exits_zero
- S1-C2 -> tests/acceptance/S1/test_S1_score.py::test_S1_C2_missing_file_exits_two_and_says_so

## Premortem (3 to 5 risks)

1. The scoring rule is unspecified, so the build invents one and the owner dislikes it. Mitigation: simplest deterministic rule (count of keyword matches), one line in DECISIONS.md, easy to change in a later story.
2. Exit codes collide: Python's own errors also exit 1, and "unknown command" already uses 2. Mitigation: S1-C2 uses exit 2 deliberately (usage-style error); the mapping is explicit in `__main__.py`.
3. Windows: job.json read with the locale encoding breaks on non-ASCII. Mitigation: open with encoding="utf-8".
