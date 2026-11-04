# S1 — Score a job file from the command line

Request: dev-docs/requests/R1.md
Status: story PR (owner merges once) -> build PR -> verdict
Proof kind: strong (every criterion fails on main by assertion; see plan.md)

## Criteria

| ID | Criterion | Cites |
| --- | --- | --- |
| E1-S1-AC1 | `python -m app score <file>` prints `score: <integer>` as its last line and exits 0 for a valid job file | R1 ¶2 |
| E1-S1-AC2 | For a file that does not exist it exits 2 and stderr contains "no such file" | R1 ¶3 |

## Proof map (locked once this PR is merged)

| ID | Acceptance test |
| --- | --- |
| E1-S1-AC1 | tests/acceptance/S1/test_S1_score.py::test_E1_S1_AC1_score_prints_integer_and_exits_zero |
| E1-S1-AC2 | tests/acceptance/S1/test_S1_score.py::test_E1_S1_AC2_missing_file_exits_two_and_says_so |

## Not in this story

The scoring rule itself is not specified by the owner; any deterministic rule that returns an integer satisfies E1-S1-AC1. The rule chosen is recorded in DECISIONS.md by the build.
