# Re-coding with other models

To check that the results do not depend on one model, the full corpus was re-coded with five models from three other families (Claude Opus 5.5, Sonnet 5.5, and Haiku 5.5; DeepSeek V4 Pro; Qwen 3.8 Max), with the same prompt and the same inputs as the original coding (`../../codebook/coding_prompt.md`). The Claude models ran at their default sampling and the others at temperature 0.1.

This directory holds the per-model labels, keyed by the same pseudonymous IDs as `../labels.csv`, and the script that computes the agreement reported in Table I of the paper.

## Files

| Path | Content |
|---|---|
| `exact/<model>.csv` | 502 skills coded from the same inputs as the original coding (metadata, structural signals, and the first 600 characters of the body). Table I uses this variant. |
| `full/<model>.csv` | 502 skills coded from the same inputs, but with the complete `SKILL.md` body. Not reported in the paper. |
| `agreement.py` | Computes the agreement with the GPT-4o-mini labels and writes `agreement.json` and `summary.md`. |
| `agreement.json`, `summary.md` | Cohen's kappa against GPT-4o-mini, pairwise kappa, Fleiss' kappa, Krippendorff's alpha, and the matrix per model. |

The models are `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `deepseek-v4-pro`, and `qwen3.8-max-0902`.

Each label file has the columns `id`, `functional_domain`, `delegation_intent`, `user_interaction`, `risk_impact`, `side_effect_scope`, and `matrix_cell`, with the same value sets as `../labels.csv`; `matrix_cell` is computed from the model's own `delegation_intent` and `user_interaction`. The open-ended artifact labels (D2 and D3) and the evidence phrases are not included, because they name the organization and its internal products.

## Running

```
python3 data/recoding/agreement.py
```

The baseline is `../labels.csv`, whose `user_interaction` column holds the interaction mode after the manual review of the autonomous labels; the paper reports the agreement with these reviewed labels.
