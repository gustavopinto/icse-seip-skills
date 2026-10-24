#!/usr/bin/env python3
"""Agreement between the original coding and the re-coding with five models.

Compares the GPT-4o-mini labels in data/labels.csv (interaction mode after the
manual review) with the labels of each re-coding model in
data/recoding/<variant>/<model>.csv, and writes agreement.json and summary.md
next to this script. Table I of the paper uses the `exact` variant.

Usage:
  python3 data/recoding/agreement.py
"""
import json
from collections import Counter
from pathlib import Path

import krippendorff
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

HERE = Path(__file__).resolve().parent
LABELS = HERE.parent / "labels.csv"

BASELINE = "gpt-4o-mini"
CLAUDE = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]
OTHERS = ["deepseek-v4-pro", "qwen3.8-max-0902"]
MODELS = CLAUDE + OTHERS
VARIANTS = ["exact", "full"]
DIMS = ["functional_domain", "delegation_intent", "user_interaction",
        "risk_impact", "side_effect_scope"]
RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
CELLS = ["Aligned-Assistive", "Aligned-Executive", "Over-declared", "Under-declared"]
MISMATCHED = {"Over-declared", "Under-declared"}

labels = pd.read_csv(LABELS, dtype=str).set_index("id")
N = len(labels)
SHELL = labels["has_shell_commands"] == "True"


def load_codings(variant):
    codings = {BASELINE: labels[DIMS + ["matrix_cell"]]}
    for m in MODELS:
        p = HERE / variant / f"{m}.csv"
        if p.exists():
            codings[m] = pd.read_csv(p, dtype=str).set_index("id")[DIMS + ["matrix_cell"]]
    return codings


def kappa(a, b, ordinal=False):
    idx = a.index.intersection(b.index)
    x, y = a[idx], b[idx]
    if ordinal:
        return cohen_kappa_score(x.map(RISK_ORDER), y.map(RISK_ORDER), weights="linear")
    return cohen_kappa_score(x, y)


def fleiss(table):
    """Fleiss' kappa; table = skills x raters, no missing values."""
    cats = sorted(set(table.values.ravel()))
    counts = np.array([[(row == c).sum() for c in cats] for row in table.values])
    n = table.shape[1]
    p_j = counts.sum(axis=0) / counts.sum()
    p_i = ((counts ** 2).sum(axis=1) - n) / (n * (n - 1))
    p_bar, p_e = p_i.mean(), (p_j ** 2).sum()
    return (p_bar - p_e) / (1 - p_e)


def alpha_ordinal(codings, dim):
    data = pd.DataFrame({m: df[dim] for m, df in codings.items()}).reindex(labels.index)
    values = data.apply(lambda s: s.map(RISK_ORDER)).T.to_numpy(dtype=float)
    return krippendorff.alpha(reliability_data=values, level_of_measurement="ordinal")


def cell_dist(cells):
    c = Counter(cells)
    n = len(cells)
    mism = sum(c[k] for k in MISMATCHED)
    return {
        "n": n,
        **{k: c[k] for k in CELLS},
        "mismatched": mism,
        "mismatched_pct": round(100 * mism / n, 1),
        "over_pct": round(100 * c["Over-declared"] / n, 1),
        "under_pct": round(100 * c["Under-declared"] / n, 1),
    }


def majority_cells(codings):
    """matrix_cell from the majority label of intent and interaction mode."""
    need = len(codings) // 2 + 1

    def maj(dim):
        votes = pd.DataFrame({m: df[dim] for m, df in codings.items()}).reindex(labels.index)
        top = votes.apply(lambda r: r.value_counts().idxmax() if r.notna().any() else None, axis=1)
        cnt = votes.apply(lambda r: r.value_counts().max() if r.notna().any() else 0, axis=1)
        return top.where(cnt >= need)

    intent, inter = maj("delegation_intent"), maj("user_interaction")
    ok = intent.notna() & ((intent == "assistive") | inter.notna())
    cells = pd.Series(np.where(
        intent == "assistive",
        np.where(SHELL, "Under-declared", "Aligned-Assistive"),
        np.where(inter == "interactive", "Over-declared", "Aligned-Executive"),
    ), index=labels.index)[ok]
    return cells, int((~ok).sum())


def kept_by_all(codings, models):
    """Skills mismatched for GPT-4o-mini that every model in `models` also places in a mismatched cell."""
    base = codings[BASELINE]["matrix_cell"].isin(MISMATCHED)
    keep = base.copy()
    for m in models:
        keep &= codings[m]["matrix_cell"].reindex(labels.index).isin(MISMATCHED)
    return int(keep.sum())


def paper_numbers(codings):
    """Values cited in the text of the paper (Section III, Robustness of the coding)."""
    base = codings[BASELINE]
    pair_intent = [kappa(codings[a]["delegation_intent"], codings[b]["delegation_intent"])
                   for i, a in enumerate(MODELS) for b in MODELS[i + 1:]]
    assist_to_exec = {m: int(((base["delegation_intent"] == "assistive")
                              & (codings[m]["delegation_intent"] == "executive")).sum())
                      for m in MODELS}
    autonomous_llm = labels.index[labels["user_interaction_llm"] == "autonomous"]
    all_reactive = pd.concat([codings[m].loc[autonomous_llm, "user_interaction"] == "reactive"
                              for m in MODELS], axis=1).all(axis=1)
    return {
        "mismatched_gpt4omini": int(base["matrix_cell"].isin(MISMATCHED).sum()),
        "kept_by_all_three_claude": kept_by_all(codings, CLAUDE),
        "kept_by_all_five": kept_by_all(codings, MODELS),
        "pairwise_kappa_intent_range": [round(min(pair_intent), 2), round(max(pair_intent), 2)],
        "assistive_to_executive": assist_to_exec,
        "autonomous_llm": len(autonomous_llm),
        "autonomous_llm_reactive_for_all_five": int(all_reactive.sum()),
        "autonomous_per_model_max": max(int((codings[m]["user_interaction"] == "autonomous").sum())
                                        for m in MODELS),
    }


def analyze(variant):
    codings = load_codings(variant)
    models = [m for m in MODELS if m in codings]
    if not models:
        return None
    base = codings[BASELINE]
    res = {"models": list(codings), "coded": {m: len(df) for m, df in codings.items()}}

    res["kappa_vs_baseline"] = {
        m: {d: round(kappa(base[d], codings[m][d], ordinal=(d == "risk_impact")), 3) for d in DIMS}
        for m in models
    }
    res["kappa_pairwise"] = {
        f"{a} | {b}": {d: round(kappa(codings[a][d], codings[b][d], ordinal=(d == "risk_impact")), 3)
                       for d in DIMS}
        for i, a in enumerate(codings) for b in list(codings)[i + 1:]
    }
    common = labels.index
    for df in codings.values():
        common = common.intersection(df.index)
    res["fleiss_all_models"] = {
        d: round(fleiss(pd.DataFrame({m: df.loc[common, d] for m, df in codings.items()})), 3)
        for d in DIMS
    }
    res["fleiss_n"] = len(common)
    res["alpha_ordinal_risk"] = round(alpha_ordinal(codings, "risk_impact"), 3)

    res["confusion_vs_baseline"] = {
        m: {d: pd.crosstab(base[d], codings[m][d]).to_dict()
            for d in ["delegation_intent", "user_interaction"]}
        for m in models
    }
    res["matrix"] = {m: cell_dist(df["matrix_cell"]) for m, df in codings.items()}
    res["autonomous"] = {m: int((df["user_interaction"] == "autonomous").sum())
                         for m, df in codings.items()}

    maj, undecided = majority_cells(codings)
    res["majority"] = {**cell_dist(maj), "undecided": undecided}

    # how many coders (GPT-4o-mini included) place each skill in a mismatched cell
    votes = pd.DataFrame({m: df["matrix_cell"].isin(MISMATCHED) for m, df in codings.items()})
    votes = votes.reindex(labels.index)
    n_mism = votes.sum(axis=1)
    base_mism = base["matrix_cell"].isin(MISMATCHED)
    res["mismatch_votes_all"] = {int(k): int(v) for k, v in n_mism.value_counts().sort_index().items()}
    res["baseline_mismatched_kept_by"] = {
        f">={k}": int((n_mism[base_mism] >= k).sum()) for k in range(1, len(codings) + 1)
    }
    if len(models) == len(MODELS):
        res["paper"] = paper_numbers(codings)
    return res


def compare_variants():
    out = {}
    exact, full = load_codings("exact"), load_codings("full")
    for m in MODELS:
        a, b = exact.get(m), full.get(m)
        if a is None or b is None:
            continue
        out[m] = {
            **{f"kappa_{d}": round(kappa(a[d], b[d], ordinal=(d == "risk_impact")), 3) for d in DIMS},
            "mismatched_pct_exact": cell_dist(a["matrix_cell"])["mismatched_pct"],
            "mismatched_pct_full": cell_dist(b["matrix_cell"])["mismatched_pct"],
        }
    return out


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return lines


def report(results, variants):
    lines = ["# Robustness of the LLM coding: GPT-4o-mini vs. Claude, DeepSeek, and Qwen\n",
             "Table I of the paper reports the `exact` variant. The `full` variant is not reported in the paper.\n"]
    for v, res in results.items():
        if res is None:
            continue
        lines.append(f"\n## Variant `{v}`\n")
        lines.append("Coded: " + ", ".join(f"{m} {n}" for m, n in res["coded"].items()) + "\n")
        lines.append("### Kappa vs. GPT-4o-mini (risk: linearly weighted)\n")
        lines += md_table(["model"] + DIMS,
                          [[m] + [k[d] for d in DIMS] for m, k in res["kappa_vs_baseline"].items()])
        lines.append(f"\nFleiss' kappa ({len(res['models'])} models, n={res['fleiss_n']}): "
                     + ", ".join(f"{d} {k}" for d, k in res["fleiss_all_models"].items()))
        lines.append(f"\nKrippendorff's alpha, ordinal (risk): {res['alpha_ordinal_risk']}\n")
        lines.append("### Declared--encoded matrix per model\n")
        rows = [[m] + [d[c] for c in CELLS] + [d["mismatched"], f"{d['mismatched_pct']}%",
                                                res["autonomous"][m]]
                for m, d in res["matrix"].items()]
        mj = res["majority"]
        rows.append([f"majority ({mj['undecided']} undecided)"] + [mj[c] for c in CELLS]
                    + [mj["mismatched"], f"{mj['mismatched_pct']}%", ""])
        lines += md_table(["model"] + CELLS + ["mismatched", "%", "autonomous"], rows)
        n_base = res["matrix"][BASELINE]["mismatched"]
        lines.append(f"\nOf the {n_base} skills mismatched for GPT-4o-mini, still mismatched for: "
                     + ", ".join(f"{k} coders: {n}" for k, n in res["baseline_mismatched_kept_by"].items()))
        if "paper" in res:
            lines.append("\n### Values cited in the text\n")
            lines += [f"- {k}: {val}" for k, val in res["paper"].items()]
    if variants:
        lines.append("\n## exact vs. full (same model)\n")
        lines += md_table(["model"] + [f"κ {d}" for d in DIMS] + ["% mism. exact", "% mism. full"],
                          [[m] + [c[f"kappa_{d}"] for d in DIMS]
                           + [c["mismatched_pct_exact"], c["mismatched_pct_full"]]
                           for m, c in variants.items()])
    return "\n".join(lines) + "\n"


def main():
    results = {v: analyze(v) for v in VARIANTS}
    variants = compare_variants()
    out = {"models": MODELS, "variants": results, "exact_vs_full": variants}
    text = report(results, variants)
    (HERE / "agreement.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    (HERE / "summary.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
