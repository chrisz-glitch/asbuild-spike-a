#!/usr/bin/env python3
"""AsBuild verdict for one pull request. Trusted side: runs from main, reads the evidence artifact as data and
the PR through the API; it never imports or runs pull-request code.

Thin wrapper over the spike (common.CRITERION, auditor.matches) and the kit (junit_classify, lock_check):
  C1   every test in evidence/pr.xml passes (acceptance tests of OTHER stories that also fail on main are
       listed, not counted: they are unbuilt stories, not breakage)
  C3   each criterion's acceptance test fails on main by assertion (evidence/c3/*.xml) and passes at the head
       (evidence/acceptance.xml, the hardened run)
  C4   the locked acceptance files at the head match locks.json on main, none missing or skipped
  protected files from the PR's file list against the list in AGENTS.md -> WAITING FOR YOU
Verdicts: PROVEN | NOT PROVEN | WAITING FOR YOU (the spike's PROVEN WITH LIMITS). WAITING wins over NOT PROVEN:
a protected or locked file changed means the owner looks first; the NOT PROVEN reasons stay in the summary.

Usage: verdict.py --evidence evidence/ --head SHA --pr N --owners a,b --out verdict.json --summary summary.md
                  --record record.md      (env: GH_TOKEN, REPO, RUN_URL)
"""
import argparse
import base64
import fnmatch
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from auditor import matches  # noqa: E402
from common import CRITERION, gh, gh_paged, is_protected  # noqa: E402
from junit_classify import ET, MAX_BYTES, classify  # noqa: E402
from lock_check import normalised  # noqa: E402

REPO = os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY", "")
RUN_URL = os.environ.get("RUN_URL", "")
CHECK_NAME = os.environ.get("CHECK_NAME", "AsBuild")
FAILED = ("strong", "existence-only")


def load_junit(path):
    """{(classname, name): kind} via junit_classify; None if the file is missing or unreadable."""
    if not os.path.isfile(path) or os.path.getsize(path) > MAX_BYTES:
        return None
    try:
        root = ET.parse(path).getroot()
    except Exception:  # noqa: BLE001
        return None
    return {(tc.get("classname") or "", tc.get("name") or ""): classify(tc)[0] for tc in root.iter("testcase")}


def story_of(classname):
    parts = classname.split(".")
    return parts[2] if len(parts) > 3 and parts[:2] == ["tests", "acceptance"] else None


def protected_patterns(agents_md):
    """Backticked paths in the 'Never edit protected files' bullet of AGENTS.md."""
    lines, grab = [], False
    for line in open(agents_md, encoding="utf-8").read().splitlines():
        if "Never edit protected files" in line:
            grab = True
        elif grab and line.lstrip().startswith("- "):
            break
        if grab:
            lines.append(line)
    return re.findall(r"`([^`]+)`", "\n".join(lines))


def is_listed(path, patterns):
    for pat in patterns:
        if "/" in pat:
            if pat.endswith("/**") and path.startswith(pat[:-2]) or fnmatch.fnmatch(path, pat):
                return True
        elif fnmatch.fnmatch(path.rsplit("/", 1)[-1], pat):
            return True
    return is_protected(path)


def lock_check(head, junit, tmp):
    """Write the head's acceptance files (from the API, as data) into tmp and run lock_check.py verify."""
    tree = gh(f"repos/{REPO}/git/trees/{head}?recursive=1") or {}
    hashes = {}
    for e in tree.get("tree", []):
        if e["type"] == "blob" and e["path"].startswith("tests/acceptance/") and e["path"].endswith(".py"):
            raw = base64.b64decode(gh(f"repos/{REPO}/git/blobs/{e['sha']}")["content"])
            dest = os.path.join(tmp, *e["path"].split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(raw)
            hashes[e["path"]] = hashlib.sha256(normalised(raw)).hexdigest()
    os.makedirs(os.path.join(tmp, "tests", "acceptance"), exist_ok=True)
    cmd = [sys.executable, os.path.join(HERE, "lock_check.py"), "verify", "--baseline",
           os.path.abspath("locks.json"), "--paths", "tests/acceptance"]
    if os.path.isfile(junit):
        cmd += ["--junit", os.path.abspath(junit)]
    p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    problems = [ln for ln in p.stdout.splitlines() if ln.split(" ", 1)[0] in ("DELETED", "CHANGED", "MISSING", "SKIPPED")]
    if p.returncode not in (0, 4):
        problems.append(f"lock check could not run (exit {p.returncode}): {(p.stderr or p.stdout).strip()[:200]}")
    return problems, hashes


def strikes_before(pr, head):
    n = 0
    for c in gh_paged(f"repos/{REPO}/pulls/{pr}/commits"):
        if c["sha"] == head:
            continue
        runs = (gh(f"repos/{REPO}/commits/{c['sha']}/check-runs?per_page=100", check=False) or {}).get("check_runs", [])
        if any(r.get("name") == CHECK_NAME and (r.get("app") or {}).get("slug") == "github-actions"
               and r.get("conclusion") == "failure" for r in runs):
            n += 1
    return n


def judge(a):
    ev = a.evidence
    pr = gh(f"repos/{REPO}/pulls/{a.pr}")
    branch = pr["head"]["ref"]
    m = re.match(r"build/(S\d+)", branch)
    story = m.group(1) if m else None
    story_md = f"dev-docs/stories/{story}/story.md" if story else ""
    story_text = open(story_md, encoding="utf-8").read() if story and os.path.isfile(story_md) else ""
    criteria = list(dict.fromkeys(CRITERION.findall(story_text)))
    existence_ok = "Proof kind: existence-ok" in story_text

    pr_res = load_junit(os.path.join(ev, "pr.xml"))
    acc = load_junit(os.path.join(ev, "acceptance.xml")) or {}
    c3 = {}
    for x in sorted(glob.glob(os.path.join(ev, "c3", "*.xml"))):
        c3.update(load_junit(x) or {})

    not_proven, waiting, notes = [], [], []
    checks = {"author": "builder"}

    # C1
    if pr_res is None:
        not_proven.append("C1: evidence/pr.xml missing or unreadable")
        checks["C1"] = "fail"
    else:
        failing = [k for k, kind in pr_res.items() if kind in FAILED]
        excused = [k for k in failing if story_of(k[0]) not in (None, story) and c3.get(k) in FAILED]
        broken = [k for k in failing if k not in excused]
        checks["C1"] = "fail" if broken else "pass"
        for k in broken:
            not_proven.append(f"C1: {k[0]}::{k[1]} fails")
        for k in excused:
            notes.append(f"C1: {k[0]}::{k[1]} fails here and on main (story {story_of(k[0])} not built): not counted")

    # C3
    rows = []
    for c in criteria:
        with_ = {k: v for k, v in acc.items() if matches(k[1], c)}
        without = {k: c3.get(k) for k in with_}
        test = ", ".join(f"{k[0].replace('.', '/')}.py::{k[1]}" for k in with_) or "(none)"
        if not with_:
            passes, fails, note = "no", "no", "no acceptance test carries this criterion ID"
        else:
            passes = "yes" if all(v == "passed" for v in with_.values()) else (
                "skipped" if any(v == "skipped" for v in with_.values()) else "no")
            if all(v == "strong" for v in without.values()):
                fails = "strong"
            elif all(v in FAILED for v in without.values()):
                fails = "existence-only"
            else:
                fails = "no"
            if passes != "yes":
                note = "fails even with the change" if passes == "no" else "skipped with the change"
            elif fails == "no":
                note = "passes on main too (or not run there): proves nothing about this change"
            elif fails == "existence-only":
                note = "fails on main only because something does not exist yet"
            else:
                note = "fails on main by assertion, passes with the change"
        rows.append({"id": c, "test": test, "fails_without": fails, "passes_with": passes, "note": note})
        if passes != "yes" or fails == "no":
            not_proven.append(f"{c}: {note}")
        elif fails == "existence-only" and not existence_ok:
            waiting.append(f"{c}: existence-only proof and story.md does not say 'Proof kind: existence-ok'")
    checks["C3"] = "vacuous" if not criteria else (
        "pass" if all(r["passes_with"] == "yes" and r["fails_without"] == "strong" for r in rows) else "fail")
    checks["c3_tests"] = {f"{k[0]}::{k[1]}": v for k, v in sorted(c3.items())}

    # C4
    with tempfile.TemporaryDirectory(prefix="lock-") as tmp:
        problems, hashes = lock_check(a.head, os.path.join(ev, "acceptance.xml"), tmp)
    checks["C4"] = "waiting" if problems else "pass"
    waiting += [f"C4: {p}" for p in problems]

    # protected files
    patterns = protected_patterns("AGENTS.md")
    files = [f["filename"] for f in gh_paged(f"repos/{REPO}/pulls/{a.pr}/files")]
    hit = sorted(p for p in files if is_listed(p, patterns))
    checks["protected"] = hit or "none"
    if hit:
        waiting.append("protected files changed: " + ", ".join(hit))

    verdict = "WAITING FOR YOU" if waiting else ("NOT PROVEN" if not_proven else "PROVEN")
    strike = strikes_before(a.pr, a.head) + (1 if verdict == "NOT PROVEN" else 0)
    return {"verdict": verdict, "pr": a.pr, "head_sha": a.head, "branch": branch, "story": story,
            "strike": strike, "criteria": rows, "checks": checks,
            "reasons": waiting + not_proven, "notes": notes, "locked_files": hashes, "run_url": RUN_URL}


def write_outputs(v, a):
    json.dump(v, open(a.out, "w", encoding="utf-8"), indent=2)
    lines = [f"AsBuild: {v['verdict']} for PR #{v['pr']} at {v['head_sha'][:10]} (story {v.get('story') or 'none'})", ""]
    for r in v.get("criteria", []):
        lines.append(f"- {r['id']}: fails without = {r['fails_without']}, passes with = {r['passes_with']}. {r['note']}")
    if not v.get("criteria"):
        lines.append("- No story criteria for this branch (C3 vacuous).")
    for r in v.get("reasons", []):
        lines.append(f"- {r}")
    for n in v.get("notes", []):
        lines.append(f"- note: {n}")
    lines += ["", "```json", json.dumps(v, indent=2), "```", ""]
    open(a.summary, "w", encoding="utf-8").write("\n".join(lines))
    rec = [f"Verdict: {v['verdict']} (AsBuild) for PR #{v['pr']}, commit {v['head_sha']}",
           f"Story: {v.get('story') or 'none'}. Verdict run: {v.get('run_url', '')}", ""]
    for r in v.get("criteria", []):
        rec.append(f"{r['id']}: fails without {r['fails_without']}, passes with {r['passes_with']} - {r['test']}")
    if not v.get("criteria"):
        rec.append("No story criteria on this branch (C3 vacuous).")
    c = v.get("checks", {})
    rec += ["", f"Checks: C1 {c.get('C1')}, C3 {c.get('C3')}, C4 {c.get('C4')}, protected {c.get('protected')}", "",
            "Locked files (sha256 of normalised content):"]
    rec += [f"  {p}  {h}" for p, h in sorted(v.get("locked_files", {}).items())] or ["  (none)"]
    open(a.record, "w", encoding="utf-8").write("\n".join(rec) + "\n")


def main():
    ap = argparse.ArgumentParser()
    for name in ("--evidence", "--head", "--pr", "--out", "--summary", "--record"):
        ap.add_argument(name, required=True)
    ap.add_argument("--owners", default="")
    a = ap.parse_args()
    a.pr = int(a.pr)
    try:
        v = judge(a)
    except Exception as e:  # noqa: BLE001  a crash must still give a verdict, never a silent pass
        v = {"verdict": "NOT PROVEN", "pr": a.pr, "head_sha": a.head, "strike": 0, "criteria": [], "checks": {},
             "reasons": [f"AsBuild could not compute the verdict: {type(e).__name__}: {str(e)[:300]}"], "run_url": RUN_URL}
    write_outputs(v, a)
    print(open(a.summary, encoding="utf-8").read())


if __name__ == "__main__":
    main()
