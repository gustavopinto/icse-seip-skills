# Data

The skills are proprietary and are not released. These files keep, for each of the 502 skills, the coded labels and the structural signals, under a pseudonymous ID (`S001`–`S502`, in random order). No name, description, tag, or text of a skill is included. The same ID refers to the same skill in every file.

| File | Rows | Content |
|---|---|---|
| `labels.csv` | 502 | Structural signals, the seven coded dimensions, and the matrix cell of each skill |
| `sensitive_programs.csv` | 502 | Output of the sensitive-program scan (RQ3) |
| `autonomous_review.csv` | 53 | Manual review of the skills the LLM coded as autonomous |
| `recoding/` | | Re-coding with five other models (see its README) |

## `labels.csv`

Column definitions are in [`../codebook/dimensions.md`](../codebook/dimensions.md). Booleans are `True`/`False`.

- `id`: pseudonymous skill ID.
- `has_references`, `has_shell_commands`, `has_sql_block`, `has_python_block`, `has_ask_user_tool`, `has_always_apply`, `has_argument_hint`, `solicits_input_structurally`, `word_count`, `entry_via_mdc`: structural signals.
- `functional_domain`, `input_artifact`, `output_artifact`, `delegation_intent`, `risk_impact`, `side_effect_scope`: D1–D4, D6, D7, as coded by GPT-4o-mini.
- `user_interaction_llm`: D5 as coded by GPT-4o-mini.
- `user_interaction`: D5 after the manual review; this is the label the paper uses.
- `matrix_cell`: Aligned-Assistive, Under-declared, Over-declared, or Aligned-Executive, computed from `delegation_intent`, `has_shell_commands`, and `user_interaction`.

## `sensitive_programs.csv`

- `id`: pseudonymous skill ID.
- `severity`, `severity_level`: none (0), low (1), medium (2), or high (3); the highest among the skill's programs.
- `sensitive_programs`: comma-separated categories (`db_client`, `remote_shell`, `git_mutate`, `infra_cloud`, `destructive_fs`).
- `programs`: comma-separated programs found.

## `autonomous_review.csv`

- `id`: pseudonymous skill ID.
- `delegation_intent`: D4 of the skill.
- `llm_label`: D5 as coded by GPT-4o-mini (always `autonomous`).
- `reviewed_label`: D5 after reading the full `SKILL.md`.
- `rationale`: a short reason for the reviewed label.
