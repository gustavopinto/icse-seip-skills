#!/usr/bin/env python3
"""Word-count histogram of the corpus (Figure 1), in grayscale."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / "data" / "labels.csv"
IMAGES = BASE / "figures"
IMAGES.mkdir(exist_ok=True)

with CORPUS.open(encoding="utf-8") as f:
    reader = csv.DictReader(f)
    word_counts = sorted(int(r["word_count"]) for r in reader if r["word_count"].strip())

median = np.median(word_counts)
mean = np.mean(word_counts)
print(f"N={len(word_counts)}  min={min(word_counts)}  max={max(word_counts)}  "
      f"median={median:.0f}  mean={mean:.0f}")

fig, ax = plt.subplots(figsize=(6.5, 3.2))
sns.histplot(word_counts, bins=30, color="#595959", edgecolor="white",
             linewidth=0.5, alpha=0.8, kde=False)
sns.rugplot(word_counts, color="#1A1A1A", alpha=0.6, height=0.06)
ax.axvline(median, color="#1A1A1A", linewidth=1.2, linestyle="--", label="Median")
ax.set_xlabel("Word count (SKILL.md body)", fontsize=10)
ax.set_ylabel("Number of skills", fontsize=10)
ax.legend(fontsize=8, loc="upper right")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(labelsize=8)

plt.tight_layout(pad=0.5)
plt.savefig(IMAGES / "fig_wordcount.pdf", dpi=300, bbox_inches="tight")
plt.savefig(IMAGES / "fig_wordcount.png", dpi=300, bbox_inches="tight")
print("Saved figures/fig_wordcount.pdf and .png")
