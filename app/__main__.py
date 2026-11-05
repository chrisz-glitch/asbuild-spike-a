"""The app's command-line surface. This file exists on main BEFORE any story is built, so every
acceptance test can call `python -m app <command> ...` and fail on main by ASSERTION (exit code 2,
"unknown command") rather than by ImportError. Stories register commands in COMMANDS."""
import sys

from app.scoring import score_command

COMMANDS = {"score": score_command}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(f"unknown command: {argv[:1]}", file=sys.stderr)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
