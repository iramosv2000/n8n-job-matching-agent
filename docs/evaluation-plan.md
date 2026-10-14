# Evaluation Plan

The migration is justified only if it is measured. This plan fixes the questions,
dataset, metrics and decision rules **before** any implementation, so that the results
cannot be tuned after the fact.

## 1. Research questions

| ID | Question | Why it matters |
|---|---|---|
| RQ1 | Does LLM structured extraction beat the As-Is rules on field accuracy, and does a hybrid (rules first, LLM for fields the rules leave empty or ambiguous) beat both? | Decides whether the LLM step pays for its cost |
| RQ2 | Does the To-Be ranking surface relevant offers better than the As-Is score? | The digest shows only the top N, so ranking quality is what the user experiences |
| RQ3 | How often does the CV agent produce claims that are not supported by the master CV or the confirmed skills, before and after the guardrail? | Factual safety is a hard requirement |
| RQ4 | What do the extraction and CV paths cost in money and latency, per offer and per CV, for each candidate model? | Informs the model-per-task decision ([ADR-0004](adr/0004-llm-provider-and-model-selection.md)) |

## 2. Dataset

- **Sampling frame:** offers collected by WF-01 over at least 3 weeks.
- **Sample:** 150 offers, **stratified** by source and by As-Is score band (< 40, 40–69,
  ≥ 70), so that the result is not driven only by easy, high-scoring cases. The random
  seed is recorded.
- **Split:** 50 offers for development (prompt iteration allowed) and 100 for a held-out
  test set (run once per frozen configuration). Results are reported on the test set.
- **Storage:** labels and offer IDs are committed to `evals/labels/`. Offer texts are
  **not** committed (third-party content). They stay in the local database, and a script
  rebuilds the evaluation set from the IDs. CI uses a small synthetic set.

## 3. Labelling protocol

Each sampled offer is labelled by hand, following a written guide (`evals/LABELING.md`,
M6), on these fields:

| Field | Values |
|---|---|
| `years_required` | integer, or `null` if not stated; "deseable" (desirable) is recorded separately |
| `contract` | `indefinido` (permanent) / `plazo_fijo` (fixed-term) / `plazo_fijo_a_indefinido` / `honorarios` (freelance invoice) / `no_indicado` (not stated) |
| `modality` | `presencial` (on-site) / `hibrido` (hybrid) / `remoto` (remote) / `no_indicado` |
| `salary_min_clp`, `salary_max_clp`, `salary_is_net` | numbers / boolean / `null` |
| `key_skills` | list taken from a controlled vocabulary (`evals/skills_vocabulary.yaml`) |
| `relevance` | 0 = not relevant, 1 = plausible, 2 = would apply |

**Reliability:** a random 20 % subset is relabelled by the same annotator after at least
7 days, and intra-annotator agreement is reported (Cohen's κ for categorical fields).
A second annotator is optional; if one participates, inter-annotator κ is reported. With
a single annotator, the labels measure fit to *this* candidate's judgement, not general
relevance. This is stated as a limitation.

## 4. Metrics

| RQ | Metric | Notes |
|---|---|---|
| RQ1 | Per-field accuracy (categorical), exact match and absolute error (numeric), micro-F1 for `key_skills` | 95 % CIs by bootstrap over offers (10,000 resamples). Paired comparison between systems on the same offers (McNemar for categorical fields) |
| RQ2 | nDCG@10 and precision@10 using `relevance` as the gain | Computed per daily batch, then averaged; CIs by bootstrap over days |
| RQ3 | Unsupported-claim rate = outputs with ≥ 1 untraceable claim / outputs | Measured by the validator and by a manual audit of 30 outputs (validator recall). Reported before and after the guardrail |
| RQ4 | Cost per offer and per CV (USD), p50/p95 latency | From `llm_calls`. Includes cached-token pricing and thinking/output tokens |

**LLM non-determinism:** every LLM configuration is run 3 times on the test set. Mean and
range are reported, and conclusions must hold across runs.

## 5. Systems compared

1. **As-Is rules:** ported logic, verified for parity with the original tool.
2. **LLM-only:** structured extraction from the description alone.
3. **Hybrid:** rules first; the LLM fills fields that are `null` or flagged ambiguous, and
   always extracts `key_skills`.

Each LLM system is evaluated with the default model and with any lower-cost model the
candidate chooses to test ([ADR-0004](adr/0004-llm-provider-and-model-selection.md)).

## 6. Decision rules (pre-registered)

- **Adopt LLM extraction (hybrid) for a field** only if it improves accuracy on that field
  and the 95 % CI of the paired difference excludes 0. Otherwise keep the rules for that
  field.
- **Adopt a lower-cost model** only if every field's accuracy stays within 2 percentage
  points of the default model and the guardrail violation rate does not increase.
- **Ship the CV agent** only if the unsupported-claim rate delivered to the user (after the
  guardrail) is 0 in the audit sample and the validator's recall in the manual audit is
  ≥ 0.9.

## 7. Threats to validity

| Threat | Mitigation |
|---|---|
| Single annotator; labels reflect one candidate's preferences | Declared as a limitation; intra-annotator κ; optional second annotator |
| Prompt overfitting to the evaluation set | Development/test split; the test set is touched only for frozen configurations |
| Source mix changes over time | Stratified sampling; results reported per source |
| Small n for rare categories (e.g. `honorarios`) | Per-class counts reported; no claims drawn from cells with n < 10 |
| Ported rules diverge from the As-Is | Parity tests on archived inputs before any comparison |

## 8. Reporting

Results are published in `evals/results/REPORT.md` (M6). The report contains tables with
CIs, configuration hashes, model IDs, dates, costs and a limitations section. Negative
results (for example, "LLM extraction did not beat rules on contract type") are reported,
not omitted.
