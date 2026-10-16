# evals/

Evaluation assets for the research questions in
[`docs/evaluation-plan.md`](../docs/evaluation-plan.md).

Planned layout:

```
evals/
├── LABELING.md              Labelling guide (frozen before labelling starts)
├── skills_vocabulary.yaml   Controlled vocabulary (also used by the guardrail)
├── labels/                  Offer IDs + manual labels (no offer texts)
├── synthetic/               Small synthetic set for CI
├── harness/                 Metrics, bootstrap CIs, paired tests
└── results/REPORT.md        Published results
```

Offer texts are third-party content and are **never** committed. They are rebuilt
locally from IDs ([`docs/data-governance.md`](../docs/data-governance.md)).

## Available now (M1-07)

| Path | Content |
|---|---|
| `synthetic/offers.json` | 6 fictitious offers with hand labels (CI and benchmarks) |
| `synthetic/cv_example.tex` | Fictitious CV in the master-CV LaTeX format |
| `synthetic/protocol_example.md` | Generic tailoring protocol of realistic length |
| `schemas/requirements.v0.json` | Draft extraction schema (finalised in M3-03) |
| `results/m1-07-local-llm-bench.json` | Local-model benchmark results ([report](../docs/spikes/M1-07-local-llm-benchmark.md)) |

The labelled real-offer dataset and the evaluation harness arrive in M6.
