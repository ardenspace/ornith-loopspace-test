#!/usr/bin/env python3
"""Trajectory grader for Experiment W (multi-session drift).

Walks every commit of an arm's repo (first-parent, oldest first), runs
the held-out oracle against each snapshot, and emits one CSV row per
(commit, R-group): passed, failed. A drift event is an R-group that
passed at snapshot t and fails at some t+k — compute it from the CSV.

Usage:
    python3 grade_trajectory.py <arm-repo-path> [--branch BRANCH]
        [--out trajectory.csv]
"""
import argparse
import csv
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

GRADING_DIR = Path(__file__).resolve().parent
ORACLE = GRADING_DIR / "gridcalc_oracle.py"
RGROUP = re.compile(r"test_(r\d\d)")


def sh(*cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True,
                          text=True)


def commits(repo, branch):
    out = sh("git", "rev-list", "--reverse", "--first-parent", branch,
             cwd=repo).stdout.split()
    return out


def grade_snapshot(clone, junit_path):
    sh("python3", "-m", "pytest", str(ORACLE), "-q", "--tb=no",
       "-p", "no:cacheprovider", f"--junitxml={junit_path}",
       cwd=str(GRADING_DIR), check=False)
    import xml.etree.ElementTree as ET
    counts = defaultdict(lambda: [0, 0])  # rgroup -> [passed, failed]
    try:
        root = ET.parse(junit_path).getroot()
    except Exception:
        return counts  # no report: treat as zero rows (import crash)
    for case in root.iter("testcase"):
        m = RGROUP.search(case.get("name", ""))
        group = m.group(1) if m else "other"
        failed = case.find("failure") is not None or \
            case.find("error") is not None
        counts[group][1 if failed else 0] += 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--branch", default="HEAD")
    ap.add_argument("--out", default="trajectory.csv")
    args = ap.parse_args()

    repo = str(Path(args.repo).resolve())
    shas = commits(repo, args.branch)
    if not shas:
        sys.exit("no commits found")

    rows = []
    with tempfile.TemporaryDirectory() as td:
        clone = str(Path(td) / "snap")
        sh("git", "clone", "--quiet", "--no-hardlinks", repo, clone)
        for idx, sha in enumerate(shas):
            sh("git", "checkout", "--quiet", "--force", sha, cwd=clone)
            subject = sh("git", "log", "-1", "--format=%s", cwd=clone
                         ).stdout.strip()
            date = sh("git", "log", "-1", "--format=%cI", cwd=clone
                      ).stdout.strip()
            import os
            os.environ["PYTHONPATH"] = clone
            counts = grade_snapshot(clone, str(Path(td) / "junit.xml"))
            if not counts:  # collection failed: no gridcalc package yet
                counts["import"] = [0, 1]
            total_pass = sum(p for p, _ in counts.values())
            total_fail = sum(f for _, f in counts.values())
            print(f"[{idx:>3}] {sha[:8]} pass={total_pass:<4} "
                  f"fail={total_fail:<4} {subject[:60]}")
            for group in sorted(counts):
                p, f = counts[group]
                rows.append({"idx": idx, "commit": sha[:8], "date": date,
                             "subject": subject, "rgroup": group,
                             "passed": p, "failed": f})

    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["idx", "commit", "date",
                                           "subject", "rgroup", "passed",
                                           "failed"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} rows)")

    # drift events: rgroup fully green at some idx, then any failure later
    best = {}
    events = []
    for r in rows:
        g = r["rgroup"]
        green = r["failed"] == 0 and r["passed"] > 0
        if green and g not in best:
            best[g] = r["idx"]
        if not green and g in best and r["idx"] > best[g]:
            events.append((g, best[g], r["idx"]))
    if events:
        print("DRIFT EVENTS (rgroup, first-green idx, regressed idx):")
        for e in events:
            print(f"  {e}")
    else:
        print("no drift events")


if __name__ == "__main__":
    main()
