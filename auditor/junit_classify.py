#!/usr/bin/env python3
"""AsBuild T18 — classify how each test behaved, from a pytest JUnit XML file.

Trusted-side program: it reads XML and nothing else. It never imports or runs project code.

Per test it answers one question the Auditor needs for C3 ("fails without the change"):
  passed          the test passed
  strong          the test ran the code path and an assertion failed  -> real fail-without proof
  existence-only  the test failed only because something does not exist yet:
                  ImportError / ModuleNotFoundError / AttributeError / NameError inside the test,
                  or the file could not be collected at all (<error> element)
  skipped         the test was skipped (a locked test that is skipped is a weakened test)

Verified on pytest 9.1.1 with `-o junit_family=xunit2`:
  * assertion failures      -> <failure message="AssertionError: ..."> or <failure message="assert ...">
  * import/attribute errors -> <failure message="ModuleNotFoundError: ..."> / "AttributeError: ..."
  * collection errors       -> <error message="collection failure"> on a testcase with no test name
  * skips                   -> <skipped type="pytest.skip" message="...">
  * the `type` attribute of <failure> is EMPTY under xunit2, so the rule keys on the message prefix.
  * a collection error ABORTS the whole run unless pytest gets --continue-on-collection-errors.

Usage:
  python junit_classify.py JUNIT.xml [--json out.json] [--require-all-fail]

Exit codes: 0 = parsed; 2 = bad input; 5 = --require-all-fail given and some test did not fail/err
            (use 5 on the fail-on-main run: a test that PASSES on main proves nothing)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:  # XML comes from the untrusted test run: prefer the hardened parser when it is installed
    from defusedxml import ElementTree as ET  # type: ignore
except Exception:  # pragma: no cover
    import xml.etree.ElementTree as ET  # stdlib fallback; the size cap below limits blow-up attacks

MAX_BYTES = 20 * 1024 * 1024
EXISTENCE = re.compile(r"^(ImportError|ModuleNotFoundError|AttributeError|NameError)\b")


def classify(tc) -> tuple[str, str]:
    kids = [k for k in tc if k.tag in ("failure", "error", "skipped")]
    if not kids:
        return "passed", ""
    k = kids[0]
    msg = (k.get("message") or "").strip()
    first = msg.split("\n", 1)[0]
    if k.tag == "skipped":
        return "skipped", first
    if k.tag == "error":  # collection or setup error: nothing in the test body ran
        return "existence-only", f"error: {first}"
    if EXISTENCE.match(msg):
        return "existence-only", first
    return "strong", first


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xml", type=Path)
    ap.add_argument("--json", type=Path, help="write the per-test rows and summary here")
    ap.add_argument("--require-all-fail", action="store_true",
                    help="exit 5 if any test passed (for the fail-on-main run)")
    a = ap.parse_args(argv)

    if not a.xml.is_file():
        print(f"not a file: {a.xml}", file=sys.stderr)
        return 2
    if a.xml.stat().st_size > MAX_BYTES:
        print(f"refusing to parse {a.xml}: larger than {MAX_BYTES} bytes", file=sys.stderr)
        return 2
    try:
        root = ET.parse(str(a.xml)).getroot()
    except Exception as e:  # noqa: BLE001
        print(f"cannot parse {a.xml}: {e}", file=sys.stderr)
        return 2

    rows = []
    for tc in root.iter("testcase"):
        kind, detail = classify(tc)
        rows.append({
            "classname": tc.get("classname") or "",
            "name": tc.get("name") or "",
            "kind": kind,
            "detail": detail[:200],
        })
    summary = Counter(r["kind"] for r in rows)

    width = max([len(r["name"] or r["classname"]) for r in rows] + [10])
    for r in rows:
        label = r["name"] or r["classname"]
        print(f"{label:<{width}}  {r['kind']:<15}  {r['detail']}")
    print("--")
    print("summary: " + ", ".join(f"{k}={v}" for k, v in sorted(summary.items())) + f", total={len(rows)}")

    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"rows": rows, "summary": dict(summary)}, indent=2), encoding="utf-8")

    if a.require_all_fail and summary.get("passed", 0):
        print("FAIL-ON-MAIN VIOLATION: at least one test passed on main; it proves nothing", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
