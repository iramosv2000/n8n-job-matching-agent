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

*Populated in M6.*
