# Spike M1-07: local LLM runtime benchmark

- **Issue:** #42 · **Date:** 2026-10-15 · **Decision feeds:** [ADR-0007](../adr/0007-zero-cost-provider-agnostic-llm.md)
- **Machine:** Apple M4, 16 GB unified memory, macOS 27.0.1. The Docker stack (n8n +
  PostgreSQL in a 4 GB Colima VM) was running throughout, as in real use.
- **Runtime:** Ollama 0.40.4, **official build** (`brew install --cask ollama-binary`), served
  natively on the host.
- **Harness:** [`scripts/bench_local_llm.py`](../../scripts/bench_local_llm.py). Raw results:
  [`evals/results/m1-07-local-llm-bench.json`](../../evals/results/m1-07-local-llm-bench.json).
- **Data:** synthetic only: 6 fictitious labelled offers, a fictitious LaTeX CV and a
  generic protocol of realistic length ([`evals/synthetic/`](../../evals/synthetic/)).

## Candidates

| Model | Params | Quantisation | Engine in Ollama | Download | Licence |
|---|---|---|---|---|---|
| `granite4.2:8b` | 8.8 B | Q4_K_M | llama.cpp | 5.3 GB | Apache 2.0 |
| `qwen3.5:9b` | 9.7 B | NVFP4 | MLX | 7.6 GB | Apache 2.0 |
| `gemma4:12b` | 12.4 B | NVFP4 | MLX | 7.7 GB | Apache 2.0 |

Settings: temperature 0, seed 7, thinking off, schema-constrained decoding through the
native `/api/chat` `format` parameter. Output caps: 768 tokens (extraction), 4,096 (CV),
64 (probe). Context: 8,192 tokens (extraction), 16,384 (CV and probe).

## Results

| Metric | granite4.2:8b | **qwen3.5:9b** | gemma4:12b |
|---|---|---|---|
| **Extraction**: schema-valid outputs | 6/6 | 6/6 | 6/6 |
| Field accuracy (7 scalar fields × 6 offers) | 41/42 (97.6 %) | 41/42 (97.6 %) | 41/42 (97.6 %) |
| Skill recall vs labels | 93 % | 97 % | 100 % |
| Latency per offer, mean / max | 10.2 s / 16.2 s | **6.3 s / 11.1 s** | 7.3 s / 13.7 s |
| Generation speed | 18.7 tok/s | **36.0 tok/s** | 32.2 tok/s |
| **CV adaptation** (prompt ≈ 3.4–3.9k tokens) | Valid, 117 s | **Valid, 51 s** | **Failed**: hit the 4,096-token cap, invalid JSON (157 s) |
| Fabricated skills / gap leaks in CV sections | 0 / 0 | 0 / 0 | n/a |
| Gaps correctly reported (offer skills absent from CV) | 8/8 | 8/8 | n/a |
| **Context probe** (code at start of a ~10k-token prompt) | Recovered (10,884 tok, 77 s) | Recovered (9,958 tok, 50 s) | Recovered (9,591 tok, 78 s) |
| Resident size in memory (`ollama ps`) | 6.6 GB, 100 % GPU | 8.5 GB, 100 % GPU | 9.8 GB, 100 % GPU |

**Stability:** `granite4.2:8b` ran three times (two trials plus the final run) and
`qwen3.5:9b` twice. Their accuracy figures were identical across runs, and latencies varied
by less than 10 %.

**The only extraction error** was on the same offer for all models (`syn-02`, "Experiencia
deseable: 2 años"). The models disagreed on whether desirable experience counts as
`years_required`. This points to an under-specified schema rule, not a model failure. It
will be fixed in the schema/prompt v1 (M3-03).

## Findings that change the design

1. **Ollama build matters.** The Homebrew *formula* `ollama` 0.40.4 ships without
   `libollama_xgrammar.dylib`. Models on the MLX engine (`qwen3.5`, `gemma4`) then return
   HTTP 501 to schema-constrained requests, and the log reports "Structured output is
   unavailable". The official build includes the library. → Documented in
   [`infra/README.md`](../../infra/README.md).
2. **Runaway generation is real.** Without an output cap, `gemma4:12b` generated for
   15 minutes on the CV task until the client timed out. With a 4,096-token cap it stopped,
   but with invalid JSON. → WF-10 must always set `num_predict` per task and a request
   timeout, and must treat `done_reason: "length"` as a failure that triggers fallback.
3. **The protocol's explicit "never mention gaps in the CV" rule is load-bearing.** In a
   trial with a shorter prompt that lacked this rule, `granite4.2:8b` wrote "No cuenta con
   experiencia directa en PLC Rockwell, …" inside the CV summary. That is not a fabricated
   claim, but it would harm the candidate. With the full protocol, no model leaked gaps.
   → The M5 guardrail must detect **negated mentions** as well as fabricated claims; plain
   keyword matching cannot tell them apart.
4. **Long context works when `num_ctx` is set explicitly.** All models recovered a code
   placed at the start of a ~10k-token prompt.
5. **Memory is tight but workable on 16 GB.** The model runs fully on the GPU (unified
   memory). macOS swap stayed in use during the session (5.6–8.4 GB, cumulative across
   runs with other applications open), but throughput did not degrade between repeated
   runs. The 4 GB Docker VM uses ~0.7 GB at idle, so it could be reduced if needed.

## Decision

| Role | Model | Rationale |
|---|---|---|
| **Primary local model** (extraction fallback and CV adaptation) | **`qwen3.5:9b`** | Fastest (≈ 2× `granite` on both tasks), top-tier accuracy, valid CV output with no fabrication or leaks, long context verified |
| Light fallback (memory pressure) | `granite4.2:8b` | Smallest footprint (6.6 GB), equally accurate on extraction, valid CV output; slower |
| Rejected | `gemma4:12b` | Failed the CV task (runaway generation under constrained decoding) and has the largest footprint. Can be removed with `ollama rm gemma4:12b` |

## Limitations

- **Small synthetic sample** (6 offers, 1 CV task). This is a feasibility and selection
  spike, not a quality evaluation. Real-offer accuracy with confidence intervals is M6's
  job ([`evaluation-plan.md`](../evaluation-plan.md)).
- The synthetic offers were written by the author and may be cleaner than real postings.
- The fabrication and gap-leak detector is a heuristic (keywords plus negation cues),
  backed by manual inspection here. The production guardrail is designed in M5-02.
- The real CV prompt is estimated at ~5k tokens, larger than the 3.4–3.9k tested. The
  ~10k-token probe covers the context requirement but not output quality at that size.
- Swap figures are cumulative system-wide and cannot be attributed to a single model.
