# Session log (append-only)

Format: `- YYYY-MM-DD HH:MM | story | what changed | verdict | links`

- 2026-11-04 | S1 | fixed score output format ("score: N") and missing-file handling (exit 2, "no such file") in app/scoring.py, added unit tests | PROVEN after one NOT PROVEN (strike 1) | https://github.com/chrisz-glitch/asbuild-spike-a/pull/26
- 2026-11-04 | S1 | app/scoring.py: print "score: N", exit 2 with "no such file: <path>" for a missing file (and usage error for no argument); added tests/unit/test_scoring.py | PROVEN after one NOT PROVEN (strike 1) | https://github.com/chrisz-glitch/asbuild-spike-a/pull/30
- 2026-11-04 | S1 | app/scoring.py + score command registered in app/__main__.py, unit tests in tests/unit/test_scoring.py (rule in DECISIONS.md) | see PR | build/S1-b2
- 2026-11-04 | S1 | app/scoring.py (score command: keyword count, "score: N", exit 2 + "no such file" for a missing file, usage error for wrong args), registered in app/__main__.py, tests/unit/test_scoring.py; rule already in DECISIONS.md | see PR | build/S1-c
