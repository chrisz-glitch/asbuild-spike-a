"""The app's command-line surface. Stories register commands in COMMANDS."""
import sys

from app.scoring import cmd_score

COMMANDS = {"score": cmd_score}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        print(f"unknown command: {argv[:1]}", file=sys.stderr)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
