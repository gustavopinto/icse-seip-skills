# Re-coding with other models

To check that the results do not depend on one model, the full corpus was re-coded with five models from three other families (Claude Opus 5.5, Sonnet 5.5, and Haiku 5.5; DeepSeek V4 Pro; Qwen 3.8 Max), with the same prompt and the same inputs as the original coding (`../../codebook/coding_prompt.md`). The Claude models ran at their default sampling and the others at temperature 0.1.

This directory holds the per-model labels, keyed by the same pseudonymous IDs as `../labels.csv`, and the script that computes the agreement reported in Table 2 of the paper.

<!-- TODO: add the per-model label files and the agreement script. -->
