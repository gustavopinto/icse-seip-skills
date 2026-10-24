#!/usr/bin/env python3
"""Result figures (domain, interaction x intent, domain x interaction, matrix), in grayscale."""

import csv
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / "data" / "labels.csv"
IMAGES = BASE / "figures"
IMAGES.mkdir(exist_ok=True)

records = list(csv.DictReader(CORPUS.open(encoding="utf-8")))
N = len(records)

# Paleta preto-e-branco (tons de cinza consistentes em todas as figuras)
GRAY_BLACK = "#1A1A1A"
GRAY_DARK  = "#595959"
GRAY_MID   = "#969696"
GRAY_LIGHT = "#D9D9D9"
INK        = "#1A1A1A"   # texto sobre fundo claro


def text_color(hexcolor):
    r = int(hexcolor[1:3], 16)
    g = int(hexcolor[3:5], 16)
    b = int(hexcolor[5:7], 16)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "white" if lum < 140 else INK


plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.grid.axis": "x",
    "grid.color": GRAY_MID,
    "grid.alpha": 0.4,
})


def fig_domain():
    domain_counts = Counter(r["functional_domain"] for r in records)
    labels, values = zip(*domain_counts.most_common())

    fig, ax = plt.subplots(figsize=(7, max(3.0, 0.35 * len(labels))))
    bars = ax.barh(labels[::-1], values[::-1], color=GRAY_DARK, height=0.6)
    for bar, val in zip(bars, values[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8, color=INK)
    ax.set_xlabel("Number of skills")
    ax.set_xlim(0, max(values) + 5)
    fig.tight_layout()
    fig.savefig(IMAGES / "fig1_domain.pdf", bbox_inches="tight")
    fig.savefig(IMAGES / "fig1_domain.png", dpi=150, bbox_inches="tight")
    print("Saved fig1_domain")


def fig_interaction_intent():
    interaction_labels = ["interactive", "reactive", "autonomous"]
    intent_labels = ["assistive", "executive"]
    colors = {"assistive": GRAY_LIGHT, "executive": GRAY_DARK}
    data = {
        intent: [sum(1 for r in records if r["user_interaction"] == il and r["delegation_intent"] == intent)
                 for il in interaction_labels]
        for intent in intent_labels
    }

    fig, ax = plt.subplots(figsize=(6, 3.5))
    bottoms = [0] * len(interaction_labels)
    for intent in intent_labels:
        vals = data[intent]
        c = colors[intent]
        bars = ax.barh(interaction_labels, vals, left=bottoms,
                       color=c, height=0.5, label=intent.capitalize())
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_y() + bar.get_height() / 2,
                        str(val), ha="center", va="center",
                        color=text_color(c), fontsize=8, fontweight="bold")
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_xlabel("Number of skills")
    ax.set_xlim(0, max(bottoms) + 5)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(IMAGES / "fig2_interaction_intent.pdf", bbox_inches="tight")
    fig.savefig(IMAGES / "fig2_interaction_intent.png", dpi=150, bbox_inches="tight")
    print("Saved fig2_interaction_intent")


def fig_domain_interaction():
    domain_order = [l for l, _ in Counter(r["functional_domain"] for r in records).most_common()]
    colors = {"interactive": GRAY_DARK, "reactive": GRAY_MID, "autonomous": GRAY_LIGHT}
    data = {
        mode: [sum(1 for r in records if r["functional_domain"] == d and r["user_interaction"] == mode)
               for d in domain_order]
        for mode in ["interactive", "reactive", "autonomous"]
    }

    fig, ax = plt.subplots(figsize=(7, max(3.0, 0.35 * len(domain_order))))
    bottoms = [0] * len(domain_order)
    for mode in ["interactive", "reactive", "autonomous"]:
        vals = data[mode]
        c = colors[mode]
        bars = ax.barh(domain_order[::-1], vals[::-1], left=bottoms[::-1],
                       color=c, height=0.6, label=mode.capitalize())
        for bar, val in zip(bars, vals[::-1]):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_y() + bar.get_height() / 2,
                        str(val), ha="center", va="center",
                        color=text_color(c), fontsize=8, fontweight="bold")
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_xlabel("Number of skills")
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(IMAGES / "fig3_domain_interaction.pdf", bbox_inches="tight")
    fig.savefig(IMAGES / "fig3_domain_interaction.png", dpi=150, bbox_inches="tight")
    print("Saved fig3_domain_interaction")


def fig_matrix():
    cells = Counter(r["matrix_cell"] for r in records)
    grid = [
        [("Aligned-Assistive", cells["Aligned-Assistive"]),
         ("Under-declared", cells["Under-declared"])],
        [("Over-declared", cells["Over-declared"]),
         ("Aligned-Executive", cells["Aligned-Executive"])],
    ]
    palette = {
        "Aligned-Assistive": GRAY_LIGHT,
        "Aligned-Executive": GRAY_LIGHT,
        "Under-declared": GRAY_BLACK,
        "Over-declared": GRAY_DARK,
    }
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    for i, row in enumerate(grid):
        for j, (label, n) in enumerate(row):
            c = palette[label]
            ax.add_patch(mpatches.Rectangle(
                (j, 1 - i), 1, 1, facecolor=c,
                edgecolor="white", linewidth=3, alpha=0.9))
            pct = 100 * n / max(sum(cells.values()), 1)
            tc = text_color(c)
            ax.text(j + 0.5, 1 - i + 0.62, label,
                    ha="center", va="center", fontsize=8,
                    color=tc, fontweight="bold")
            ax.text(j + 0.5, 1 - i + 0.35, f"{n} skills ({pct:.0f}%)",
                    ha="center", va="center", fontsize=10,
                    color=tc, fontweight="bold")
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5])
    ax.set_yticks([0.5, 1.5])
    ax.set_xticklabels(["Operationally constrained\n(no shell, interactive)",
                        "Operationally capable\n(shell / reactive)"], fontsize=8)
    ax.set_yticklabels(["Executive\n(declared)", "Assistive\n(declared)"], fontsize=8)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(IMAGES / "fig_matrix_declared_encoded.pdf", bbox_inches="tight")
    fig.savefig(IMAGES / "fig_matrix_declared_encoded.png", dpi=150,
                bbox_inches="tight")
    print("Saved fig_matrix_declared_encoded")


if __name__ == "__main__":
    fig_domain()
    fig_interaction_intent()
    fig_domain_interaction()
    fig_matrix()
    print("All figures saved to figures/")
