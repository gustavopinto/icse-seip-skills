# Coding scheme

Each skill was coded along seven dimensions plus one derived structural label, the declared–encoded matrix cell. D1–D3 characterize what is delegated (RQ1), D4 and D5 feed the matrix (RQ2), and D6 and D7 estimate the cost of an error and how far it propagates. D1 and D4–D7 use closed value sets; D2 and D3 are open-ended.

All seven dimensions were coded by an LLM (`coding_prompt.md`). The interaction mode (D5) of the 53 skills the model coded as autonomous was then reviewed by hand with the definitions below (`../data/autonomous_review.csv`).

| ID | Dimension | Column in `labels.csv` | Values |
|---|---|---|---|
| D1 | Functional domain | `functional_domain` | Data/ML, Documentation, Process/Planning, Communication/Collaboration, Code Quality, Infrastructure/Deploy, Observability/Debug, Business Domain, Version Control, Meta/Agent |
| D2 | Input artifact | `input_artifact` | Open-ended (73 distinct labels), e.g., conversation, code, SQL, ticket, none |
| D3 | Output artifact | `output_artifact` | Open-ended (126 distinct labels), e.g., analysis, report, code, YAML, PPTX, PR |
| D4 | Delegation intent | `delegation_intent` | assistive, executive |
| D5 | User interaction mode | `user_interaction` (reviewed), `user_interaction_llm` (LLM) | interactive, reactive, autonomous |
| D6 | Risk/impact | `risk_impact` | none, low, medium, high |
| D7 | Side-effect scope | `side_effect_scope` | local, service, org, external |

## Definitions

- **D1, functional domain.** The software engineering or business area the skill supports, from ten categories derived from a pilot read of the corpus. The prompt gives a one-line description of each category.
- **D2–D3, input and output artifacts.** What the skill consumes and produces, as open-ended labels.
- **D4, delegation intent.** The intent the skill's description communicates, inferred from it, since the catalog has no field for it. *Assistive* skills give guidance or analysis without irreversible actions; *executive* skills produce real side effects, such as writing files, opening merge requests, or running deployments.
- **D5, user interaction mode.** How much human involvement the skill requires once invoked. *Interactive* skills solicit input before or during execution, *reactive* skills run to completion once triggered, and *autonomous* skills fire without human initiation (a schedule, an event, or continuous monitoring).
- **D6, risk/impact.** The worst-case consequence of the skill running end-to-end without a human, on an ordinal scale: *none* (read or analysis only), *low* (local files or reversible artifacts, e.g., PPTX, CSV), *medium* (opens a merge request or issue, sends a message, incurs metered cost, or mutates service-scoped state such as a Jira ticket or Databricks table), and *high* (production change, ML training on shared infrastructure, or writes to org-wide regulated systems).
- **D7, side-effect scope.** Where side effects land: *local* (developer filesystem), *service* (bounded service state), *org* (shared organizational asset), or *external* (third-party service).

## Manual review of the autonomous labels

A skill stayed autonomous only if it is designed to fire on a schedule, an event, or continuous monitoring. Otherwise it became interactive if its body instructs the agent to ask the user for input or confirmation during execution, and reactive if not. The review kept 5 skills as autonomous and reassigned 41 to reactive and 7 to interactive.

## Declared–encoded matrix

`matrix_cell` is computed deterministically from D4, D5, and the structural signal `has_shell_commands`:

| Cell | Rule |
|---|---|
| Aligned-Assistive | assistive intent, no shell command blocks in the body |
| Under-declared | assistive intent, shell command blocks in the body |
| Over-declared | executive intent, interactive mode |
| Aligned-Executive | executive intent, reactive or autonomous mode |

The rule is asymmetric by design: an assistive skill is tested for capability (does its body let the agent act through shell?), and an executive skill for containment (does it stop for a human?). The `AskUserQuestion` signal does not enter the rule.

## Structural signals

Extracted from each `SKILL.md` without an LLM (`scripts/build_corpus.py`, `extract_one`):

| Column | Signal |
|---|---|
| `has_shell_commands` | a fenced code block tagged `bash`, `sh`, `shell`, or `zsh` |
| `has_sql_block` | a fenced code block tagged `sql`, `postgres`, or `mysql` |
| `has_python_block` | a fenced code block tagged `python` or `py` |
| `has_ask_user_tool` | the file mentions the `AskUserQuestion` tool |
| `solicits_input_structurally` | the body asks the agent to prompt the user (regular expression in `extract_one`) |
| `has_references` | the package has a `references/` directory |
| `has_always_apply`, `has_argument_hint` | the file has the `alwaysApply` or `argument-hint` key |
| `word_count` | words in the body, frontmatter excluded |
| `entry_via_mdc` | the package has only a `SKILL.mdc` entry file |

## Sensitive programs (RQ3)

`scripts/sensitive_scan.py` holds the patterns. A program counts only when invoked as a command, in a code block or inline code, on a line that does not forbid it or quote it as an example.

| Category | Programs | Severity |
|---|---|---|
| `db_client` | `databricks`, `dbt`, `bq`, Athena, `snowsql` | low (1) |
| `db_client` | `psql`, `mysql`, `mongosh`, `redis-cli`, `sqlite3` | medium (2) |
| `remote_shell` | `ssh`, `scp`, `sudo` | medium (2) |
| `destructive_fs` | `rm -rf`, `dd`, `shred` | high (3) |
| `infra_cloud` | `kubectl`, `helm`, `terraform`, `aws`, `gcloud`, `docker` | does not raise severity |
| `git_mutate` | `git push`/`commit`/`merge`/`rebase`/`reset --hard`/`tag`/`cherry-pick`; `gh`/`glab` creating or merging requests | does not raise severity |

Each skill receives the highest severity among its programs.
