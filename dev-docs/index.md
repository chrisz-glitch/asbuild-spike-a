# Where everything is

- AGENTS.md — the rules every agent follows (read first)
- dev-docs/log.md — append-only record of each session (read second)
- dev-docs/dead-ends.md — approaches that failed and why (read before planning)
- dev-docs/requests/ — the owner's words, saved unchanged (protected)
- dev-docs/stories/<S>/story.md and plan.md — criteria, proof map, files, premortem (protected after merge)
- tests/acceptance/<S>/ — the locked acceptance tests, one per criterion (protected after merge)
- tests/unit/ — the builder's own tests (free)
- app/ — the application; app/__main__.py is the CLI surface every story registers into
- DECISIONS.md — one line per reversible decision
- tools/asbuild_wait.py — waits for the AsBuild verdict on the current commit and prints it
