#!/usr/bin/env python3
"""Applies the manual review of the skills the LLM coded as autonomous.

The coding prompt defined `autonomous` as "acts on its own without requiring
user input", which overlaps with `reactive`; the paper defines autonomous as
firing without human initiation (schedule, event, or continuous monitoring).
data/autonomous_review.csv holds the reviewed label of each of the 53 skills.
This script writes it to the `user_interaction` column of data/labels.csv
(the LLM label stays in `user_interaction_llm`) and recomputes `matrix_cell`.
data/labels.csv already ships with the review applied; the script is
idempotent and documents the step.

Usage:
  python3 scripts/apply_autonomous_review.py
"""
import csv
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LABELS = BASE / "data" / "labels.csv"
REVIEW = BASE / "data" / "autonomous_review.csv"


def matrix_cell(intent: str, has_shell: bool, interaction: str) -> str:
    # same rule as build_corpus.matrix_cell
    if intent == "assistive":
        return "Under-declared" if has_shell else "Aligned-Assistive"
    if intent == "executive":
        return "Over-declared" if interaction == "interactive" else "Aligned-Executive"
    return "UNCODED"


def main():
    review = {r["id"]: r["reviewed_label"] for r in csv.DictReader(open(REVIEW, encoding="utf-8"))}
    rows = list(csv.DictReader(open(LABELS, encoding="utf-8")))
    for r in rows:
        r["user_interaction"] = review.get(r["id"], r["user_interaction_llm"])
        r["matrix_cell"] = matrix_cell(r["delegation_intent"], r["has_shell_commands"] == "True",
                                       r["user_interaction"])
    with open(LABELS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("interaction:", dict(Counter(r["user_interaction"] for r in rows).most_common()))
    print("cells:", dict(Counter(r["matrix_cell"] for r in rows).most_common()))


if __name__ == "__main__":
    main()
