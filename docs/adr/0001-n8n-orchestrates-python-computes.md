# ADR-0001: n8n orchestrates, Python computes

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
The As-Is tool mixes orchestration (looping over sources, retries, scheduling), I/O and
domain logic (parsing, scoring) in the same modules, and has no tests. The project's goal
is to show AI process automation with a workflow orchestrator, but logic that must stay
correct (scoring, the fabrication guardrail) needs unit tests, versioned diffs and parity
checks. Large visual workflows and inline Code nodes do not provide these well.

## Decision
Use **n8n** for orchestration only: triggers, control flow, retries, integrations,
human-in-the-loop and error handling. Put all deterministic domain logic in a **Python
FastAPI service** (`matcher-service`) with typed Pydantic contracts and pytest. n8n calls
the service over HTTP inside a private Docker network.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Everything in n8n (Code nodes) | One runtime; fastest to start | Logic hard to unit-test and review; tied to the n8n sandbox; poor diffs |
| Everything in Python (keep the As-Is, add cron) | Simple; already works | No orchestration evidence; notifications, retries and human approval would all need custom code |
| Python orchestration framework (Prefect, Airflow) | Strong scheduling and lineage | Heavier; does not show the low-code automation skills the target roles ask for |
| **n8n + Python service** | Each tool used where it is strongest; testable core; reusable logic | Two runtimes; HTTP contract to maintain |

## Consequences
- The service's OpenAPI schema is the contract; breaking changes need a version bump.
- Logic ported from the As-Is must pass parity tests before it replaces the original (M3).
- n8n workflows stay thin, which makes their exported JSON reviewable in pull requests.
