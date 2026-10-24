# Robustness of the LLM coding: GPT-4o-mini vs. Claude, DeepSeek, and Qwen

Table I of the paper reports the `exact` variant. The `full` variant is not reported in the paper.


## Variant `exact`

Coded: gpt-4o-mini 502, claude-opus-5-5 502, claude-sonnet-5-5 502, claude-haiku-5-5 502, deepseek-v4-pro 502, qwen3.8-max-0902 502

### Kappa vs. GPT-4o-mini (risk: linearly weighted)

| model | functional_domain | delegation_intent | user_interaction | risk_impact | side_effect_scope |
|---|---|---|---|---|---|
| claude-opus-5-5 | 0.652 | 0.615 | 0.868 | 0.498 | 0.363 |
| claude-sonnet-5-5 | 0.606 | 0.578 | 0.864 | 0.488 | 0.418 |
| claude-haiku-5-5 | 0.695 | 0.574 | 0.883 | 0.469 | 0.368 |
| deepseek-v4-pro | 0.665 | 0.572 | 0.833 | 0.46 | 0.369 |
| qwen3.8-max-0902 | 0.703 | 0.609 | 0.712 | 0.473 | 0.411 |

Fleiss' kappa (6 models, n=502): functional_domain 0.756, delegation_intent 0.751, user_interaction 0.858, risk_impact 0.629, side_effect_scope 0.607

Krippendorff's alpha, ordinal (risk): 0.761

### Declared--encoded matrix per model

| model | Aligned-Assistive | Aligned-Executive | Over-declared | Under-declared | mismatched | % | autonomous |
|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 262 | 67 | 107 | 66 | 173 | 34.5% | 5 |
| claude-opus-5-5 | 214 | 82 | 164 | 42 | 206 | 41.0% | 8 |
| claude-sonnet-5-5 | 217 | 83 | 160 | 42 | 202 | 40.2% | 8 |
| claude-haiku-5-5 | 221 | 79 | 158 | 44 | 202 | 40.2% | 8 |
| deepseek-v4-pro | 217 | 86 | 154 | 45 | 199 | 39.6% | 5 |
| qwen3.8-max-0902 | 227 | 101 | 124 | 50 | 174 | 34.7% | 8 |
| majority (13 undecided) | 214 | 77 | 154 | 44 | 198 | 40.5% |  |

Of the 173 skills mismatched for GPT-4o-mini, still mismatched for: >=1 coders: 173, >=2 coders: 165, >=3 coders: 164, >=4 coders: 162, >=5 coders: 152, >=6 coders: 137

### Values cited in the text

- mismatched_gpt4omini: 173
- kept_by_all_three_claude: 157
- kept_by_all_five: 137
- pairwise_kappa_intent_range: [0.77, 0.93]
- assistive_to_executive: {'claude-opus-5-5': 84, 'claude-sonnet-5-5': 87, 'claude-haiku-5-5': 84, 'deepseek-v4-pro': 86, 'qwen3.8-max-0902': 73}
- autonomous_llm: 53
- autonomous_llm_reactive_for_all_five: 43
- autonomous_per_model_max: 8

## Variant `full`

Coded: gpt-4o-mini 502, claude-opus-5-5 502, claude-sonnet-5-5 502, claude-haiku-5-5 502, deepseek-v4-pro 502, qwen3.8-max-0902 502

### Kappa vs. GPT-4o-mini (risk: linearly weighted)

| model | functional_domain | delegation_intent | user_interaction | risk_impact | side_effect_scope |
|---|---|---|---|---|---|
| claude-opus-5-5 | 0.662 | 0.523 | 0.594 | 0.424 | 0.308 |
| claude-sonnet-5-5 | 0.616 | 0.503 | 0.63 | 0.459 | 0.356 |
| claude-haiku-5-5 | 0.65 | 0.517 | 0.724 | 0.438 | 0.303 |
| deepseek-v4-pro | 0.631 | 0.496 | 0.667 | 0.413 | 0.343 |
| qwen3.8-max-0902 | 0.691 | 0.545 | 0.621 | 0.463 | 0.365 |

Fleiss' kappa (6 models, n=502): functional_domain 0.74, delegation_intent 0.731, user_interaction 0.723, risk_impact 0.615, side_effect_scope 0.574

Krippendorff's alpha, ordinal (risk): 0.735

### Declared--encoded matrix per model

| model | Aligned-Assistive | Aligned-Executive | Over-declared | Under-declared | mismatched | % | autonomous |
|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 262 | 67 | 107 | 66 | 173 | 34.5% | 5 |
| claude-opus-5-5 | 197 | 105 | 168 | 32 | 200 | 39.8% | 10 |
| claude-sonnet-5-5 | 206 | 99 | 166 | 31 | 197 | 39.2% | 9 |
| claude-haiku-5-5 | 212 | 75 | 181 | 34 | 215 | 42.8% | 8 |
| deepseek-v4-pro | 212 | 80 | 168 | 42 | 210 | 41.8% | 7 |
| qwen3.8-max-0902 | 211 | 104 | 153 | 34 | 187 | 37.3% | 7 |
| majority (17 undecided) | 208 | 80 | 164 | 33 | 197 | 40.6% |  |

Of the 173 skills mismatched for GPT-4o-mini, still mismatched for: >=1 coders: 173, >=2 coders: 163, >=3 coders: 157, >=4 coders: 151, >=5 coders: 136, >=6 coders: 123

### Values cited in the text

- mismatched_gpt4omini: 173
- kept_by_all_three_claude: 134
- kept_by_all_five: 123
- pairwise_kappa_intent_range: [0.76, 0.91]
- assistive_to_executive: {'claude-opus-5-5': 111, 'claude-sonnet-5-5': 109, 'claude-haiku-5-5': 102, 'deepseek-v4-pro': 100, 'qwen3.8-max-0902': 99}
- autonomous_llm: 53
- autonomous_llm_reactive_for_all_five: 34
- autonomous_per_model_max: 10

## exact vs. full (same model)

| model | κ functional_domain | κ delegation_intent | κ user_interaction | κ risk_impact | κ side_effect_scope | % mism. exact | % mism. full |
|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 0.938 | 0.837 | 0.65 | 0.792 | 0.739 | 41.0 | 39.8 |
| claude-sonnet-5-5 | 0.865 | 0.785 | 0.662 | 0.834 | 0.792 | 40.2 | 39.2 |
| claude-haiku-5-5 | 0.819 | 0.749 | 0.748 | 0.722 | 0.635 | 40.2 | 42.8 |
| deepseek-v4-pro | 0.81 | 0.745 | 0.689 | 0.684 | 0.665 | 39.6 | 41.8 |
| qwen3.8-max-0902 | 0.897 | 0.769 | 0.708 | 0.754 | 0.727 | 34.7 | 37.3 |
