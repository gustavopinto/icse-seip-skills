#!/usr/bin/env python3
"""Recomputes every number of the paper from the released data.

Reads data/labels.csv, data/sensitive_programs.csv, and
data/autonomous_review.csv. With --tex, also checks each value against the
macros defined in the paper's main.tex.

Usage:
  python3 scripts/numbers.py [--tex path/to/main.tex]
"""
import argparse
import csv
import re
import statistics
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
MISMATCHED = {"Over-declared", "Under-declared"}


def pct(k, n):
    return f"{100 * k / n:.0f}%"


def read(name):
    with open(DATA / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", help="main.tex of the paper, to check its macros")
    args = ap.parse_args()
    rows = read("labels.csv")
    n = len(rows)
    c = lambda key: Counter(r[key] for r in rows)
    dom, intent, inter, risk, scope, cell = (c("functional_domain"), c("delegation_intent"),
                                             c("user_interaction"), c("risk_impact"),
                                             c("side_effect_scope"), c("matrix_cell"))
    wc = [int(r["word_count"]) for r in rows]
    exp = {
        "corpusSize": n,
        "mdcFallback": sum(r["entry_via_mdc"] == "True" for r in rows),
        "inputLabels": len(c("input_artifact")), "outputLabels": len(c("output_artifact")),
        "dataML": dom["Data/ML"], "docSkills": dom["Documentation"], "processSkills": dom["Process/Planning"],
        "commSkills": dom["Communication/Collaboration"], "codeQSkills": dom["Code Quality"],
        "infraSkills": dom["Infrastructure/Deploy"], "obsSkills": dom["Observability/Debug"],
        "bizSkills": dom["Business Domain"], "vcsSkills": dom["Version Control"], "metaSkills": dom["Meta/Agent"],
        "assistiveSkills": intent["assistive"], "executiveSkills": intent["executive"],
        "interactiveSkills": inter["interactive"], "reactiveSkills": inter["reactive"],
        "autonomousSkills": inter["autonomous"],
        "interactiveAssistive": sum(r["user_interaction"] == "interactive" and r["delegation_intent"] == "assistive" for r in rows),
        "riskMedium": risk["medium"], "riskNone": risk["none"], "riskLow": risk["low"], "riskHigh": risk["high"],
        "scopeLocal": scope["local"], "scopeService": scope["service"], "scopeOrg": scope["org"],
        "alignedAssistive": cell["Aligned-Assistive"], "alignedExecutive": cell["Aligned-Executive"],
        "overDeclared": cell["Over-declared"], "underDeclared": cell["Under-declared"],
        "alignedSkills": cell["Aligned-Assistive"] + cell["Aligned-Executive"],
        "mismatchedSkills": cell["Over-declared"] + cell["Under-declared"],
        "autonomousExecutive": sum(r["user_interaction"] == "autonomous" and r["delegation_intent"] == "executive" for r in rows),
        "medianWords": int(statistics.median(wc)), "meanWords": f"{round(statistics.mean(wc)):,}",
        "minWords": min(wc), "maxWords": f"{max(wc):,}",
        "shellSkills": sum(r["has_shell_commands"] == "True" for r in rows),
    }

    review = read("autonomous_review.csv")
    moved = Counter(r["reviewed_label"] for r in review)
    exp.update(autonomousLLM=len(review), autonomousToReactive=moved["reactive"],
               autonomousToInteractive=moved["interactive"])

    sev = read("sensitive_programs.csv")
    cat = lambda k: sum(k in r["sensitive_programs"].split(",") for r in sev)
    lvl = Counter(r["severity"] for r in sev)
    cell_of = {r["id"]: r["matrix_cell"] for r in rows}
    sensitive = [r for r in sev if r["sensitive_programs"]]
    exp.update(dbClientSkills=cat("db_client"), infraCloudSkills=cat("infra_cloud"),
               gitMutateSkills=cat("git_mutate"), remoteShellSkills=cat("remote_shell"),
               sevLowSkills=lvl["low"], sevMediumSkills=lvl["medium"], sevHighSkills=lvl["high"],
               destructiveSkills=cat("destructive_fs"), sensitiveSkills=len(sensitive),
               sensitiveMismatched=sum(cell_of[r["id"]] in MISMATCHED for r in sensitive))

    macros = {}
    if args.tex:
        tex = open(args.tex, encoding="utf-8").read()
        macros = {m.group(1): m.group(2).replace("{,}", ",")
                  for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{(.*?)\\xspace\}", tex)}
        print(f"{'macro':24} {'paper':>8} {'data':>8}")
    bad = 0
    for k, v in exp.items():
        if not args.tex:
            print(f"{k:24} {str(v):>8}")
            continue
        p = macros.get(k)
        ok = p is not None and str(p) == str(v)
        bad += not ok and p is not None
        print(f"{k:24} {str(p):>8} {str(v):>8} {'' if ok else ('<-- differs' if p is not None else '(no macro)')}")
    if args.tex:
        print(f"\n{bad} macros differ from the data")

    print("\nOther numbers quoted in the text")
    ia, oa = c("input_artifact"), c("output_artifact")
    print("  input:", {k: ia[k] for k in ("conversation", "none", "code", "SQL", "ticket")})
    print("  output:", {k: oa[k] for k in ("analysis", "report", "summary", "code", "none")})
    ex = intent["executive"]
    print(f"  executive running reactively/autonomously: {cell['Aligned-Executive']} of {ex} ({pct(cell['Aligned-Executive'], ex)})")
    ask = sum(r["has_ask_user_tool"] == "True" for r in rows)
    print(f"  AskUserQuestion: {ask} ({pct(ask, n)})")
    under = [r for r in rows if r["matrix_cell"] == "Under-declared"]
    print(f"  under-declared that interact: {sum(r['user_interaction'] == 'interactive' for r in under)} of {len(under)}, "
          f"through AskUserQuestion: {sum(r['has_ask_user_tool'] == 'True' for r in under)}")
    by_cell = Counter(cell_of[r["id"]] for r in sensitive)
    print("  sensitive skills by cell:", dict(by_cell.most_common()))
    high = [r for r in sev if r["severity"] == "high"]
    print(f"  high severity under-declared: {sum(cell_of[r['id']] == 'Under-declared' for r in high)} of {len(high)}")
    for name, k in (("risk", risk), ("scope", scope), ("interaction", inter), ("cells", cell)):
        print(f"  {name}:", {a: f"{b} ({pct(b, n)})" for a, b in k.most_common()})
    print("  domains:", {a: f"{b} ({pct(b, n)})" for a, b in dom.most_common()})


if __name__ == "__main__":
    main()
