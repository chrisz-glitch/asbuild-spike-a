#!/usr/bin/env python3
"""T1 prototype of check G3: does each criterion test fail without the change and pass with it?

Method (proofcheck's idea, generalised): run the tests at the head; then take the base,
lay the head's test files over it unchanged, and run again. The test files are byte for
byte the same in both runs, so a fail-then-pass can only come from the code change.

Usage: failfirst.py <repo> <base-ref> <head-ref> <python|node|go> <criterion-id> [...]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

TEST_FILES = {
    "python": re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py)$"),
    "node": re.compile(r"\.(test|spec)\.(c|m)?(j|t)s$"),
    "go": re.compile(r"_test\.go$"),
}
NODE_MODULES = os.environ.get("T1_NODE_MODULES", "")


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def matches(test_name, criterion):
    return re.search(re.escape(norm(criterion)) + r"(?![0-9])", norm(test_name)) is not None


def parse_junit(path):
    """Return ({test name: status}, load_errors) from a JUnit XML file."""
    results, load_errors = {}, []
    if not os.path.exists(path):
        return results, ["no report written"]
    for case in ET.parse(path).getroot().iter("testcase"):
        name = case.get("name") or ""
        status = "pass"
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                status = {"failure": "fail", "error": "error", "skipped": "skip"}[child.tag]
                break
        if status == "error" and (not name or name == case.get("classname")):
            load_errors.append((case.get("classname") or name or "?") + " could not load")
        results[name] = status
    return results, load_errors


def run_python(wt):
    proc = sh([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml=_junit.xml"], wt)
    results, load_errors = parse_junit(os.path.join(wt, "_junit.xml"))
    if "errors during collection" in proc.stdout or "ERROR collecting" in proc.stdout:
        load_errors.append("pytest collection error")
    return results, load_errors, proc


def run_node(wt):
    if NODE_MODULES and not os.path.exists(os.path.join(wt, "node_modules")):
        os.symlink(NODE_MODULES, os.path.join(wt, "node_modules"))
    proc = sh(["npx", "--no-install", "vitest", "run", "--reporter=junit", "--outputFile=_junit.xml"], wt)
    results, load_errors = parse_junit(os.path.join(wt, "_junit.xml"))
    text = proc.stdout + proc.stderr
    if "Failed to load" in text or "does not provide an export" in text or "SyntaxError" in text:
        load_errors.append("vitest could not load a test file")
    return results, load_errors, proc


def run_go(wt):
    proc = sh(["go", "test", "-json", "./..."], wt)
    results, saw_tests = {}, False
    for line in proc.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("Test") and ev.get("Action") in ("pass", "fail", "skip"):
            results[ev["Test"]] = ev["Action"]
            saw_tests = True
    load_errors = []
    if proc.returncode != 0 and not saw_tests:
        load_errors.append("package did not compile")
    if "[build failed]" in proc.stdout + proc.stderr or "build-fail" in proc.stdout:
        load_errors.append("go build failed")
    return results, load_errors, proc


RUNNERS = {"python": run_python, "node": run_node, "go": run_go}


def find(results, criterion):
    return {name: st for name, st in results.items() if matches(name, criterion)}


def verdict(head_hits, base_hits, base_load_errors):
    if not head_hits:
        return "NOT PROVEN", "no test carries this criterion ID"
    if any(st != "pass" for st in head_hits.values()):
        return "NOT PROVEN", "fails even with the change"
    if base_hits:
        if all(st in ("fail", "error") for st in base_hits.values()):
            return "PROVEN", "fails without the change, passes with it (same test file)"
        if any(st == "pass" for st in base_hits.values()):
            return "NOT EVIDENCE OF THIS CHANGE", "passes without the change too"
        return "NOT PROVEN", "skipped without the change"
    if base_load_errors:
        return ("PROVEN WITH LIMITS",
                "the test file could not load or compile without the change; "
                "its own result without the change is unknown")
    return "NOT PROVEN", "test not found without the change"


def main():
    repo, base, head, lang = sys.argv[1:5]
    criteria = sys.argv[5:]
    changed = [p for p in sh(["git", "diff", "--name-only", base, head], repo).stdout.split()
               if TEST_FILES[lang].search(p)]
    tmp = tempfile.mkdtemp(prefix="t1-")
    head_wt, base_wt = os.path.join(tmp, "head"), os.path.join(tmp, "base")
    sh(["git", "worktree", "add", "--detach", head_wt, head], repo)
    sh(["git", "worktree", "add", "--detach", base_wt, base], repo)
    try:
        head_res, head_err, head_proc = RUNNERS[lang](head_wt)
        if os.environ.get("T1_PER_FILE") and len(changed) > 1:
            # One changed test file at a time over the base, so one file that cannot
            # load does not hide the results of the others.
            base_res, base_err, outputs = {}, [], []
            for path in changed:
                one = os.path.join(tmp, "base-" + re.sub(r"[^a-z0-9]", "_", path.lower()))
                sh(["git", "worktree", "add", "--detach", one, base], repo)
                sh(["git", "checkout", head, "--", path], one)
                res, err, proc = RUNNERS[lang](one)
                outputs.append(proc.stdout + proc.stderr)
                for name, st in res.items():
                    base_res.setdefault(name, st)
                base_err += [path + ": " + e for e in err]
                sh(["git", "worktree", "remove", "--force", one], repo)

            class P:  # minimal stand-in for the combined run
                returncode = 0
                stdout = "\n".join(outputs)
                stderr = ""
            base_proc = P()
        else:
            # Base plus the head's test files, unchanged.
            if changed:
                sh(["git", "checkout", head, "--", *changed], base_wt)
            base_res, base_err, base_proc = RUNNERS[lang](base_wt)
        rows = []
        for c in criteria:
            v, why = verdict(find(head_res, c), find(base_res, c), base_err)
            rows.append({"criterion": c, "verdict": v, "why": why,
                         "with_change": find(head_res, c), "without_change": find(base_res, c)})
        out = {"repo": os.path.basename(repo), "language": lang, "test_files_overlaid": changed,
               "load_errors_without_change": base_err, "rows": rows,
               "head_exit": head_proc.returncode, "base_exit": base_proc.returncode,
               "base_output_tail": (base_proc.stdout + base_proc.stderr)[-1500:]}
        print(json.dumps(out, indent=2))
    finally:
        sh(["git", "worktree", "remove", "--force", head_wt], repo)
        sh(["git", "worktree", "remove", "--force", base_wt], repo)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
