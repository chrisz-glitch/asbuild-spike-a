# AGENTS.md — how work reaches main in this repository

You are the builder. Nothing you build reaches main unless AsBuild, a program running on GitHub, has proven it
against the owner's own criteria, and the proof is written into the merge commit. Your job is to make that
proof easy to give. Keep this file under 150 lines; put long explanations elsewhere and link them.

## Read first, every session

1. `dev-docs/index.md` — where everything is.
2. `dev-docs/log.md` — what earlier sessions did (append-only; you add a line at the end of your session).
3. `dev-docs/dead-ends.md` — approaches that failed and why. Never retry one without saying why it is different now.

## Identity and limits

- Work only as the builder account. Never use, ask for, or store the owner's login or any token in the repository.
- Never edit protected files; if a story needs a change there, say so in the PR description and stop:
  `.github/**`, `AGENTS.md`, `CLAUDE.md`, any `conftest.py`, `pytest.ini`, `pyproject.toml`, `setup.cfg`,
  `setup.py`, `tox.ini`, `.coveragerc`, `requirements*`, lock files, `sitecustomize.py`, `*.pth`,
  `tests/acceptance/**`, `dev-docs/requests/**`, `dev-docs/stories/**` (after the story PR is merged).
- Never force-push, never merge, never post a status or check, never label a PR, never claim a verdict yourself.
- Never name a model in any file; say "the strongest model available".
- One open build PR at a time. If one is open, finish it or close it before starting another.

## How one story runs

**Story PR** (branch `story/<S>`, label `story`): save the owner's words unchanged in `dev-docs/requests/`,
write `dev-docs/stories/<S>/story.md` (criteria with IDs, each citing the request paragraph) and `plan.md`
(files you will change, where new files may go, 3 to 5 risks), and the acceptance tests under
`tests/acceptance/<S>/`. The owner merges this PR once; from then on those files are locked.

**Build PR** (branch `build/<S>`, label `build`): write the code and your own unit tests under `tests/unit/`,
touching only files the plan allows. Open one PR. AsBuild gives one of three verdicts.

## Acceptance tests (what makes a criterion provable)

- One test per criterion; the test name carries the ID: `test_<S>_<C>_<what it checks>`.
- Black-box: call the app through `python -m app <command> ...` (or its HTTP surface), never import internals.
  On main the test must fail by assertion (for example exit code 2, "unknown command"), not by ImportError.
- Self-contained: stdlib only, no `conftest.py`, no project fixtures. AsBuild runs them with conftest and
  plugin autoload disabled.
- If a criterion can only be tested by importing new code, write `Proof kind: existence-ok` in `story.md`
  so the owner knows and approves it at the story merge.

## The loop (no human in it until a verdict asks for one)

```
git switch -c build/<S> main
# ... code, unit tests, DECISIONS.md line if you made a reversible choice ...
python -m pytest -q                                    # local runs are for speed only; CI is the verdict
git add -A && git commit -m "<S>: <what>" && git push -u origin build/<S>
gh pr create --fill --label build --base main
python tools/asbuild_wait.py                            # waits for the AsBuild check run, prints the verdict
```

(`gh pr checks --watch` is not enough: it returns before the trusted run posts the AsBuild check.)

The verdict JSON has `verdict`, `criteria[]` (id, test, fails_without, passes_with, note) and `strike`.

- **PROVEN** — AsBuild merges. Append your log line and stop.
- **NOT PROVEN** — read only the failing criteria's notes, fix, commit, push, wait again. Do not touch
  acceptance tests or the plan. After the third NOT PROVEN on the same PR AsBuild closes it (`replan`):
  write the dead end in `dev-docs/dead-ends.md`, then open a new story PR with a new plan.
- **WAITING FOR YOU** — the owner decides on GitHub. Do nothing on this PR unless the owner sends it back
  with a comment; then treat the comment as the notes above.

## Session end

Append one line to `dev-docs/log.md`: date, story, what changed, verdict, PR link. Leave no background
process running. If you stopped early, say where in the log line.

Start your first reply with the word AMBER.
