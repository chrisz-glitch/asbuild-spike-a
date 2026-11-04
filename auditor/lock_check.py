#!/usr/bin/env python3
"""AsBuild T21 — the test lock (C4), file level, language-agnostic.

Two commands:

  baseline  Record the "first seen" state of every locked test file: a hash of its NORMALISED content
            (CRLF -> LF, trailing spaces stripped, exactly one trailing newline) plus the test IDs found
            in it (Python: `def test_*`). In v0.1 proper this baseline comes from main's merge commits;
            in step 0 the JSON file stands in for that record.

  verify    Recompute and compare. Any CHANGED or DELETED locked file -> WAITING FOR YOU.
            With --junit: every baseline test ID must appear in the run and must not be skipped;
            MISSING (renamed/deleted) or SKIPPED -> WAITING FOR YOU. New files are allowed (listed).

The program never runs project code. The JUnit XML it reads comes from the untrusted run and is parsed only.

Usage:
  python lock_check.py baseline --paths tests/acceptance --out locks.json
  python lock_check.py verify   --baseline locks.json --paths tests/acceptance [--junit acceptance.xml]

Exit codes: 0 = all locked tests intact; 4 = WAITING FOR YOU (something changed/missing/skipped); 2 = bad input
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from defusedxml import ElementTree as ET  # type: ignore
except Exception:  # pragma: no cover
    import xml.etree.ElementTree as ET

TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(", re.M)


def normalised(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="surrogateescape")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip(" \t") for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return ("\n".join(lines) + "\n").encode("utf-8", errors="surrogateescape")


def scan(paths: list[Path]) -> dict[str, dict]:
    files: dict[str, dict] = {}
    for base in paths:
        if base.is_file():
            candidates = [base]
        else:
            candidates = sorted(p for p in base.rglob("*.py") if p.is_file())
        for p in candidates:
            raw = p.read_bytes()
            key = p.as_posix()
            files[key] = {
                "sha256": hashlib.sha256(normalised(raw)).hexdigest(),
                "tests": TEST_DEF.findall(raw.decode("utf-8", errors="replace")),
            }
    return files


def junit_status(xml_path: Path) -> dict[tuple[str, str], str]:
    """(module basename, test name) -> passed|failed|error|skipped."""
    root = ET.parse(str(xml_path)).getroot()
    out: dict[tuple[str, str], str] = {}
    for tc in root.iter("testcase"):
        name = tc.get("name") or ""
        module = (tc.get("classname") or "").split(".")[-1]  # tests.acceptance.S1.test_S1_score -> test_S1_score
        kids = [k.tag for k in tc if k.tag in ("failure", "error", "skipped")]
        out[(module, name)] = kids[0] if kids else "passed"
    return out


def cmd_baseline(a) -> int:
    files = scan(a.paths)
    if not files:
        print("no locked files found under " + ", ".join(p.as_posix() for p in a.paths), file=sys.stderr)
        return 2
    doc = {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": files}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"baseline: {len(files)} file(s), {sum(len(f['tests']) for f in files.values())} test(s) -> {a.out}")
    return 0


def cmd_verify(a) -> int:
    base = json.loads(a.baseline.read_text(encoding="utf-8"))["files"]
    now = scan(a.paths)
    problems: list[str] = []
    for path, rec in base.items():
        cur = now.get(path)
        if cur is None:
            problems.append(f"DELETED  {path}")
        elif cur["sha256"] != rec["sha256"]:
            problems.append(f"CHANGED  {path}")
    for path in now:
        if path not in base:
            print(f"new (allowed)  {path}")

    if a.junit:
        if not a.junit.is_file():
            print(f"junit file not found: {a.junit}", file=sys.stderr)
            return 2
        status = junit_status(a.junit)
        for path, rec in base.items():
            module = Path(path).stem
            for test in rec["tests"]:
                st = status.get((module, test))
                if st is None:
                    problems.append(f"MISSING  {path}::{test} (not in the run: renamed, deleted or not collected)")
                elif st == "skipped":
                    problems.append(f"SKIPPED  {path}::{test}")
                else:
                    print(f"ok       {path}::{test} -> {st}")

    if problems:
        print("\n".join(problems))
        print("--\nverdict: WAITING FOR YOU (locked test changed, missing or skipped)")
        return 4
    print("--\nverdict: locked tests intact")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("baseline")
    b.add_argument("--paths", nargs="+", type=Path, default=[Path("tests/acceptance")])
    b.add_argument("--out", type=Path, default=Path("locks.json"))
    v = sub.add_parser("verify")
    v.add_argument("--baseline", type=Path, required=True)
    v.add_argument("--paths", nargs="+", type=Path, default=[Path("tests/acceptance")])
    v.add_argument("--junit", type=Path)
    a = ap.parse_args(argv)
    return cmd_baseline(a) if a.cmd == "baseline" else cmd_verify(a)


if __name__ == "__main__":
    sys.exit(main())
