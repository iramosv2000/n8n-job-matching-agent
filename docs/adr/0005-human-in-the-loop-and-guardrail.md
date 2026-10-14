# ADR-0005: Human-in-the-loop and a deterministic fabrication guardrail

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
An LLM that tailors a CV can introduce skills or achievements the candidate does not
have. Prompt instructions reduce this risk but do not eliminate it. Misrepresentation in
an application is a serious harm to the candidate.

## Decision
1. The system **never applies on the candidate's behalf**. It produces material and
   records decisions, and the candidate sends every application.
2. Every CV output passes a **deterministic validator** (`/validate/cv`) that traces each
   skill and claim to the master CV or to `confirmed_skills`. On violation, the workflow
   retries once with the violations as feedback. If violations remain, the output is
   delivered **flagged**, with the offending lines listed.
3. Gaps can be added only through an explicit confirmation with free-text evidence.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Prompt-only constraint | Simple | Unverifiable; fails silently |
| LLM-as-judge validator | Catches paraphrased claims | Non-deterministic; one LLM checking another |
| **Deterministic validator (+ optional LLM judge in M6 as a second signal)** | Testable, auditable, reproducible | Must handle synonyms; recall is measured in the M6 audit |

## Consequences
- The validator's recall is a reported metric, not an assumption ([`../evaluation-plan.md`](../evaluation-plan.md), RQ3).
- The skills vocabulary (M6-01) doubles as the synonym map for the validator.
