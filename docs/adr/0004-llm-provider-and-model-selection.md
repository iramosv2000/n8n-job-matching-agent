# ADR-0004: LLM provider, integration path and model per task

- **Status:** Accepted for provider and integration; **model per task pending M6 evidence**
- **Date:** 2026-10-14

## Context
The system has two LLM tasks with different profiles:

| Task | Volume | Input / output (estimate) | Quality sensitivity |
|---|---|---|---|
| Requirement extraction (WF-02) | Every new offer that passes the rule pre-filter | ~2.1k input tokens (system prompt + schema ≈ 1.5k, cacheable; offer ≈ 0.6k) / ~0.4k output, plus thinking tokens | Moderate; measurable against labels |
| CV adaptation (WF-05) | On demand (a few per week) | ~8k input (master CV + protocol ≈ 7k, cacheable) / ~3k output | High; factual safety is guarded by ADR-0005 |

The As-Is calls Claude through the Claude Code CLI (`claude -p`), authenticated with the
candidate's subscription. That path is not portable to a containerised n8n deployment.

## Decision
1. **Provider:** Claude via the **Messages API**, authenticated with an API key stored in
   n8n's credential store.
2. **Structured output:** use JSON-schema structured outputs (`output_config.format`) so
   that responses are schema-valid. Current Claude models reject forced `tool_choice`
   (`any`/`tool`) with HTTP 400 and do not accept assistant prefill. If n8n's Anthropic
   node implements structured output through either mechanism, call the Messages API
   from an **HTTP Request node** instead (verified in spike M1-06).
3. **Models (initial configuration, all configurable per task):**
   - CV adaptation: `claude-sonnet-5-5`, which keeps the As-Is choice (`cv.modelo: "sonnet"`).
   - Requirement extraction: `claude-opus-5-5` (provider default), with `effort: "low"`.
   - Lower-cost candidates (for example `claude-haiku-5-5`) are evaluated in M6. A switch
     is the candidate's decision, made against the pre-registered rule in
     [`../evaluation-plan.md`](../evaluation-plan.md) §6.
4. **Prompt caching** on the static prefix (system prompt, schema, master CV).

## Cost model (order of magnitude; to be replaced by measured values)
List prices per million tokens, input / output, as of 2026-10-06:

| Model | Input | Output |
|---|---|---|
| `claude-opus-5-5` | $4.00 | $20.00 |
| `claude-sonnet-5-5` | $2.00 | $10.00 |
| `claude-haiku-5-5` | $0.10 | $0.50 |

Estimated cost per unit, excluding caching discounts and thinking tokens:

| Unit | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|
| Extraction, per offer | ≈ $0.016 | ≈ $0.008 | ≈ $0.0004 |
| CV adaptation, per CV | ≈ $0.09 | ≈ $0.05 | ≈ $0.002 |

**Volume assumption:** 121 new offers were observed on the single As-Is day available, of
which about 47 % pass the pre-filter, giving about 57 extractions per day. With Opus 5.5
for extraction, this is about $0.9/day, or about $20/month over 22 working days. This
rests on **one observation**; it is re-estimated in M2-06 and replaced by measured costs
in M6.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Keep `claude -p` via an Execute Command node | No API billing | Not containerisable; depends on an interactive login; not reproducible by a reviewer |
| Other providers via n8n nodes | Comparable features | Breaks continuity with the As-Is prompts and evaluation baseline |
| **Claude Messages API** | Portable; structured outputs; usage reported per call | API billing separate from the subscription |

## Consequences
- An Anthropic API key with billing is a prerequisite from M3 onwards.
- `llm_calls` records tokens (including cached), latency, `request_id` and cost per call.
- Model IDs and prices live in configuration and a versioned price table, not in
  workflow nodes.
