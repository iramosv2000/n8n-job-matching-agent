# services/matcher/

`matcher-service`: a Python 3.12 FastAPI service holding all deterministic domain logic
([ADR-0001](../../docs/adr/0001-n8n-orchestrates-python-computes.md)).

Planned endpoints: `/health`, `/normalize`, `/dedupe`, `/extract/rules`, `/score`,
`/validate/cv`, `/sources/{name}/fetch`. See
[`docs/architecture.md`](../../docs/architecture.md#4-matcher-service-api-planned).

Planned layout:

```
services/matcher/
├── pyproject.toml
├── src/matcher/
│   ├── api.py           FastAPI app and routes
│   ├── models.py        Pydantic contracts (canonical offer, features, score)
│   ├── normalize.py     HTML stripping, region mapping, PII redaction
│   ├── extract_rules.py Years, contract, schedule, modality, salary
│   ├── score.py         Scoring and discard rules
│   ├── dedupe.py        Cross-source deduplication
│   ├── guardrail.py     CV claim traceability validator
│   └── sources/         Optional adapters (disabled by default)
└── tests/               pytest; synthetic fixtures only
```

*Implemented from M2.*
