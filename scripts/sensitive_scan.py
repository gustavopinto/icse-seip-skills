#!/usr/bin/env python3
"""Sensitive-program scan (RQ3).

Scans the body of each <skills>/<slug>/SKILL.md (frontmatter excluded) for
programs of five categories, in code blocks and in prose, since skills often
instruct the agent in prose to run a command. A line that forbids the program
(never, do not, nunca, não, proibido, ...) is not counted.

Severity of a skill = the highest severity among the programs it uses:
  high   (3) destructive filesystem command
  medium (2) raw database REPL, remote shell, or privilege escalation
  low    (1) managed data-access client (CLI or connector of a data platform)
  none   (0) otherwise; infrastructure tooling and git mutations are reported
             as categories but do not raise severity (see the paper)

The skills are proprietary and not released, so this script documents the
patterns behind data/sensitive_programs.csv; running it needs a directory of
skills laid out as <skills>/<slug>/SKILL.md.

Usage:
  python3 sensitive_scan.py --skills DIR [--out FILE] [--mode command|mention]
"""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path


# (category, program label, regex, severity)
PROGRAMS = [
    ("db_client", "databricks", r"\bdatabricks\s+[a-z]", 1),
    ("db_client", "dbt", r"\bdbt\s+(run|build|test|compile|seed|ls|show|docs)\b", 1),
    ("db_client", "bq", r"\bbq\s+(query|ls|show|head)\b", 1),
    ("db_client", "athena", r"\baws\s+athena\b", 1),
    ("db_client", "snowsql", r"\bsnowsql\b", 1),
    ("db_client", "psql", r"\bpsql\b", 2),
    ("db_client", "mysql", r"\bmysql\s+-", 2),
    ("db_client", "mongosh", r"\bmongosh\s+|\bmongo\s+(--|mongodb://)", 2),
    ("db_client", "redis-cli", r"\bredis-cli\b", 2),
    ("db_client", "sqlite3", r"\bsqlite3\s+", 2),
    ("infra_cloud", "kubectl", r"\bkubectl\s+", 0),
    ("infra_cloud", "helm", r"\bhelm\s+", 0),
    ("infra_cloud", "terraform", r"\bterraform\s+(init|plan|apply|destroy|import)\b", 0),
    ("infra_cloud", "aws", r"\baws\s+[a-z0-9-]+", 0),
    ("infra_cloud", "gcloud", r"\bgcloud\s+", 0),
    ("infra_cloud", "docker", r"\bdocker\s+(run|exec|build|push|compose)\b", 0),
    ("git_mutate", "git", r"\bgit\s+(push|commit|merge(?!-)|rebase|reset\s+--hard|tag|cherry-pick)\b", 0),
    ("git_mutate", "glab/gh", r"\b(glab|gh)\s+(mr|pr)\s+(create|merge)\b", 0),
    ("remote_shell", "ssh", r"\bssh\s+", 2),
    ("remote_shell", "scp", r"\bscp\s+", 2),
    ("remote_shell", "sudo", r"\bsudo\s+", 2),
    ("destructive_fs", "rm -rf", r"\brm\s+-(rf|fr|Rf)\b", 3),
    ("destructive_fs", "dd", r"\bdd\s+if=", 3),
    ("destructive_fs", "shred", r"\bshred\s+", 3),
]
NEGATION = re.compile(r"(\bexamples?:|\b(never|do not|don't|must not|nunca|não|nao|proibid[oa]s?|jamais|evite|avoid)\b)", re.I)
# Mention mode: the program or platform is named anywhere in the body
MENTIONS = [
    ("db_client", "databricks", r"\bdatabricks\b", 1),
    ("db_client", "dbt", r"\bdbt\b", 1),
    ("db_client", "bigquery", r"\b(bq|bigquery)\b", 1),
    ("db_client", "athena", r"\bathena\b", 1),
    ("db_client", "snowflake", r"\b(snowsql|snowflake)\b", 1),
    ("db_client", "psql", r"\bpsql\b", 2),
    ("db_client", "mysql", r"\bmysql\b", 2),
    ("db_client", "mongo", r"\bmongo(sh|db)?\b", 2),
    ("db_client", "redis-cli", r"\bredis-cli\b", 2),
    ("db_client", "sqlite3", r"\bsqlite3\b", 2),
    ("infra_cloud", "kubectl", r"\bkubectl\b", 0),
    ("infra_cloud", "helm", r"\bhelm\b", 0),
    ("infra_cloud", "terraform", r"\bterraform\b", 0),
    ("infra_cloud", "aws", r"\baws\b", 0),
    ("infra_cloud", "gcloud", r"\bgcloud\b", 0),
    ("infra_cloud", "docker", r"\bdocker\b", 0),
] + [p for p in PROGRAMS if p[0] in ("git_mutate", "remote_shell", "destructive_fs")]
LEVEL = {0: "none", 1: "low", 2: "medium", 3: "high"}
ORDER = ["db_client", "remote_shell", "git_mutate", "infra_cloud", "destructive_fs"]


def body(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def command_lines(text):
    """Lines inside fenced code blocks, plus inline code spans elsewhere."""
    lines, in_block = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if in_block:
            lines.append(line)
        else:
            lines += [m for m in re.findall(r"`([^`]+)`", line)
                      if not NEGATION.search(line)]
    return lines


def scan(text, mode="mention"):
    found = {}
    lines = body(text).splitlines() if mode == "mention" else command_lines(body(text))
    table = MENTIONS if mode == "mention" else PROGRAMS
    for line in lines:
        if NEGATION.search(line) or line.lstrip().startswith("#") and NEGATION.search(line):
            continue
        for cat, label, rx, sev in table:
            if re.search(rx, line, re.I if mode == "mention" and cat in ("db_client", "infra_cloud") else 0):
                found.setdefault(label, (cat, sev))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", required=True, type=Path, help="directory with <slug>/SKILL.md")
    ap.add_argument("--out", default="sensitive_programs_scan.csv", type=Path)
    ap.add_argument("--mode", choices=["mention", "command"], default="command",
                    help="mention: programs named anywhere in the body; command: only in code")
    args = ap.parse_args()
    rows = []
    for d in sorted(args.skills.iterdir()):
        f = d / "SKILL.md"
        if not f.exists():
            f = d / "SKILL.mdc"
        found = scan(f.read_text(encoding="utf-8", errors="ignore"), args.mode) if f.exists() else {}
        cats = sorted({c for c, _ in found.values()}, key=ORDER.index)
        level = max([s for _, s in found.values()], default=0)
        rows.append(dict(skill=d.name, severity=LEVEL[level], severity_level=level,
                         sensitive_programs=",".join(cats), programs=",".join(sorted(found))))
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n = len(rows)
    print(f"skills: {n}")
    for cat in ORDER:
        k = sum(cat in r["sensitive_programs"].split(",") for r in rows)
        print(f"  {cat:15} {k:4} ({100 * k / n:.0f}%)")
    sev = Counter(r["severity"] for r in rows)
    print("severity:", {k: f"{v} ({100 * v / n:.0f}%)" for k, v in sev.items()})

if __name__ == "__main__":
    main()
