# Spike M1-06: n8n capabilities for the pinned version

- **Issue:** #8 · **Date:** 2026-10-15 · **n8n:** 2.42.7 (Community Edition, self-hosted)
- **Method:** inspection of the node and server code shipped in the pinned image (`docker
  compose exec n8n …`), plus official documentation where available. Code inspection was
  preferred because the documentation pages consulted do not state edition availability
  for these features.

## Questions and findings

### 1. MCP Server Trigger: transports, auth, licensing

| Aspect | Finding | Evidence |
|---|---|---|
| Nodes present | `McpTrigger` (server), `McpClientTool`, `McpClient`, `McpRegistryClientTool` | `@n8n/n8n-nodes-langchain/dist/nodes/mcp/` |
| Server transports | **SSE** and **streamable HTTP**; no stdio | `McpServer.js`: `transportFactory.createSSE(...)`, `handleStreamableHttpSetup(...)` |
| Server authentication | None, **bearer** or **header** auth | `bearerAuth` / `headerAuth` options in the trigger |
| Client transports | SSE and streamable HTTP | `McpClientTool` options |
| Licence gating | **None found** in the MCP node code (no `isLicensed`/`feat:` checks) | `grep` over `nodes/mcp` |

**Implication:** WF-06 (M7) can use the MCP Server Trigger in Community Edition, with
bearer auth. stdio-only clients need a bridge (for example `mcp-remote`), to be verified
end-to-end in M7-02.

### 2. Evaluations in Community Edition

| Aspect | Finding | Evidence |
|---|---|---|
| Nodes present | `Evaluation` and `EvaluationTrigger` | `n8n-nodes-base/dist/nodes/Evaluation/` |
| Backend | Lives under `dist/evaluation.ee/`. The `.ee` suffix marks code under n8n's enterprise licence terms | Directory listing |
| Tier defaults | Concurrency defaults `{ Community: 1, Pro: 1, Business: 3, Enterprise: 5 }` | `evaluation-concurrency.helper.js` |
| Workflow quota | A quota `quota:evaluations:maxWorkflows` exists. Its value for an unlicensed instance could not be determined from the code inspected | `@n8n/constants` |
| Documentation | The official overview does not state edition availability | docs.n8n.io/advanced-ai/evaluations/overview |

**Implication:** n8n Evaluations are **not** a dependency. The evaluation harness stays in
Python (M6-03), as planned in [`evaluation-plan.md`](../evaluation-plan.md). n8n
Evaluations may be used for an optional, light in-editor check if they work in the
instance.

### 3. Structured (JSON-schema) output from the LLM nodes

| Node | Structured-output support in 2.42.7 | Evidence |
|---|---|---|
| Google Gemini (vendor node, *Message a model*) | **JSON mode only** (`jsonOutput` → `responseMimeType: application/json`); no response schema | `vendors/GoogleGemini/.../message.operation.js` |
| Google Gemini Chat Model (LangChain sub-node) | No schema option; structure only through the *Structured Output Parser*, which adds format instructions to the prompt and parses the result | `llms/LmChatGoogleGemini`, `output_parser/OutputParserStructured` |
| Ollama Chat Model | **Output Format: Default \| JSON** (JSON mode); no schema | `LmChatOllama/description.js`: `format` options `default`, `json` |
| Ollama (vendor node) | No `format`/schema parameter (JSON Schema is only used to describe tools) | `vendors/Ollama/.../message.operation.js` |

**Implication (decision input for ADR-0007):** none of the built-in LLM nodes can
*constrain* output to our JSON Schema. WF-10 (`llm-router`) will therefore call the
providers' native APIs through the **HTTP Request node**:

- **Ollama:** `POST /api/chat` with `format: <JSON Schema>`. This was validated
  empirically in M1-07, with 100 % schema-valid outputs.
- **Gemini:** `generateContent` with `responseMimeType: application/json` plus a response
  schema. To be verified with a free-tier key at the start of M3.

Every response is also validated against the schema by matcher-service before it is used
(defence in depth).

### 4. Container → host networking (Ollama)

From inside the n8n container, `wget http://host.docker.internal:11434/api/version` returns
`{"version":"0.40.4"}` on Colima 0.10.3, with Ollama bound to `127.0.0.1` only. No LAN
exposure is needed. The image has no `getent`, so name resolution was verified through the
HTTP call itself.

## Decisions and follow-ups

| Decision | Recorded in |
|---|---|
| LLM calls with a schema go through the HTTP Request node to native APIs, not the built-in LLM nodes | ADR-0007 (verification note) |
| Evaluation harness in Python; n8n Evaluations optional | Evaluation plan (unchanged) |
| MCP Server Trigger with bearer auth for WF-06 | Architecture (unchanged) |
| Verify Gemini response-schema support with a real free-tier key | M3-04 |

## Limitations

- The code inspection covers one version (2.42.7). Node options change between releases,
  so this spike must be repeated when n8n is upgraded across minor versions.
- The evaluation workflow quota for unlicensed instances remains unknown. The design does
  not depend on it.
