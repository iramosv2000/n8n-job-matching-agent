# ADR-0007: Zero-cost, provider-agnostic LLM layer

- **Status:** Accepted, verified in M1-06/M1-07 (2026-10-15). Supersedes [ADR-0004](0004-llm-provider-and-model-selection.md)
- **Date:** 2026-10-14

## Context
ADR-0004 required a paid Claude API key from M3 onwards, at an estimated ~USD 20/month
for extraction. The project must be developed and operated at **zero additional cost**.
The candidate's available resources are:

- A Claude **Team** seat belonging to an organisation. Its API credits need an
  organisation administrator to link a Console organisation, and access ends with the
  employment relationship. The project must not depend on it.
- A personal Google consumer AI plan. It does **not** include Gemini API credit, but any
  Google account can use the Gemini API **free tier**.
- An Apple M4 laptop with 16 GB of unified memory, which can run small open-weight models
  locally.

Two constraints from primary sources shape the design:

1. **Gemini API free tier:** limits are per project, shown in AI Studio, and "not
   guaranteed" ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), updated
   2026-10-13). Under the unpaid-service terms, Google may use inputs and outputs to
   improve its products, human reviewers may read them, and users must not submit
   personal information ([Gemini API terms](https://ai.google.dev/gemini-api/terms)).
2. **Local inference on macOS:** Docker containers on macOS cannot use the Apple GPU. A
   local model runtime must therefore run **natively on the host** to be usable.

## Decision
1. **Provider-agnostic LLM layer.** Every LLM task goes through a provider router
   (implemented as an n8n sub-workflow). The router applies a per-task policy, emits
   JSON-schema-constrained output, and logs each call to `llm_calls` (provider, model,
   tokens, latency).
2. **Task policies:**

   | Task | Data class | Primary | Fallback | Never |
   |---|---|---|---|---|
   | Requirement extraction | Public offer text, contact data redacted | Gemini API free tier (Flash-class model) | Local model | — |
   | CV adaptation | **Personal** (CV, confirmed skills) | Local model (Ollama) | Manual mode: prompt bundle delivered to the candidate | Gemini free tier, or any unpaid service |
   | Evaluation runs | Public offer text | Same as extraction | Local model | — |

3. **Local runtime:** [Ollama](https://ollama.com), running natively on macOS and reached
   from n8n at `host.docker.internal:11434`. The candidates are open-weight instruction
   models of 7–12B parameters at 4-bit quantisation. The model is selected in M1-07 on
   memory use, throughput and JSON-schema adherence, with the Docker stack running.
4. **Quota handling:** the router counts daily calls per provider. It routes to the local
   fallback on HTTP 429/5xx, or pre-emptively once 80 % of the observed daily quota is
   used. The initial backfill (~665 offers) is processed locally or spread over several
   days.
5. **Claude API stays an optional provider** (configuration only) for anyone with their
   own API key, and as a quality reference in M6 if such access exists. It is **not**
   required by any milestone.
6. **Policy enforcement is tested.** A unit test asserts that the CV-adaptation route can
   never select an unpaid external provider, and the M5 acceptance criteria include an
   egress check.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Paid Claude API (ADR-0004) | Highest quality; structured outputs; usage reporting | Recurring cost; violates the zero-cost constraint |
| Claude via `claude -p` on the organisation's Team seat | No marginal cost | Consumes the employer's plan; access ends with the job; terms and policy exposure |
| Local models only | Full privacy; no quotas | Lower extraction quality; heavier load on a 16 GB machine |
| **Gemini free tier for public data + local for personal data** | Zero cost; personal data never leaves the machine; better extraction quality than local alone | Free quota can change without notice; dependence on Google's unpaid terms for public data |

## Consequences
- **Operating cost:** USD 0, with infrastructure as in ADR-0001/0002 (n8n Community
  Edition, PostgreSQL, Docker Desktop for personal use or Colima, GitHub Actions on a
  public repository).
- The evaluation compares **rules vs Gemini (free) vs local** on quality, latency, quota
  use and privacy class, which makes it more informative than a single-provider study.
- CV generation quality and speed depend on the local model. The guardrail (ADR-0005)
  and the M6 audit carry the factual-safety burden.
- The free-tier quota and available models are re-checked in AI Studio before M3 and
  recorded with dates. If the free tier disappears, extraction degrades to local-only
  without code changes.
- The ~2,000-token offer prompts and ~8,000-token CV prompts must fit the local model's
  context window; this is verified in M1-07.

## Verification (M1-06, M1-07; 2026-10-15)

Evidence: [`spikes/M1-06-n8n-capabilities.md`](../spikes/M1-06-n8n-capabilities.md) and
[`spikes/M1-07-local-llm-benchmark.md`](../spikes/M1-07-local-llm-benchmark.md).

| Item | Result |
|---|---|
| Local model | **`qwen3.5:9b`** is primary (Apache 2.0; 8.5 GB resident; 6.3 s per extraction; 51 s per CV; 0 fabrications). `granite4.2:8b` is the light fallback (6.6 GB resident). `gemma4:12b` is rejected (runaway generation on the CV task) |
| Context fit | Verified up to ~10k tokens with explicit `num_ctx` |
| Integration path | n8n's built-in Gemini and Ollama nodes offer JSON *mode* only, with no schema. WF-10 therefore calls the **native APIs through the HTTP Request node** (Ollama `format` schema; Gemini response schema, to verify in M3-04) and validates every response in matcher-service |
| Required router settings | Per-task output cap (`num_predict`), request timeout, and `done_reason: "length"` treated as failure → fallback |
| Runtime | The **official Ollama build** is required. The Homebrew formula lacks `xgrammar`, so MLX-engine models return HTTP 501 to schema requests |
| Networking | n8n → `host.docker.internal:11434` works on Colima with Ollama bound to `127.0.0.1` |
| Per-source restriction (ADR-0008) | Offers from sources with `external_llm_allowed: false` (Chiletrabajos) are routed to the **local model only**, for extraction too |
