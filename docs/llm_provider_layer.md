# LLM Provider Layer

## 1. Purpose

The LLM Provider Layer isolates model vendors from Ask SocTrace. It gives the Municipal Intelligence Agent one stable contract for planning analytical tool calls and synthesizing natural answers.

The provider never executes SQL, reads the database, or bypasses the Universal Tool Layer. It only plans and writes.

## 2. Provider-Agnostic Design

SocTrace needs to test cheaply during MVP and keep the option to switch providers later. The code now depends on `LLMProvider`, not directly on Gemini or OpenAI SDKs.

Supported provider names are:

- `mock`
- `gemini`
- `openai`

`mock` and `gemini` are implemented. `openai` remains reserved for a later phase.

## 3. Gemini for MVP

Gemini is the MVP provider because it can reduce iteration cost while the analytical architecture stabilizes.

The adapter still lives behind `LLMProvider`, so Ask SocTrace does not call Gemini from random service code.

## 4. OpenAI Later

OpenAI can be plugged in later by implementing the same `LLMProvider` contract. Ask SocTrace will not need to call OpenAI-specific code from service files.

## 5. Provider Interface

`backend/app/ask/llm/provider.py` defines:

```py
class LLMProvider(ABC):
    async def plan(self, request: LLMPlanRequest) -> LLMPlanResponse:
        ...

    async def synthesize(self, request: LLMSynthesisRequest) -> LLMSynthesisResponse:
        ...

    def healthcheck(self) -> dict[str, Any]:
        ...
```

`plan()` selects a tool call. `synthesize()` turns a `ToolResult` payload into a human answer. `healthcheck()` reports readiness without external API calls.

## 6. Request And Response Schemas

Schemas live in `backend/app/ask/llm/schemas.py`.

Core models:

- `LLMMessage`
- `LLMToolSchema`
- `LLMToolCall`
- `LLMPlanRequest`
- `LLMPlanResponse`
- `LLMSynthesisRequest`
- `LLMSynthesisResponse`

The tool schema is intentionally generic so Gemini and OpenAI adapters can translate it into their provider-specific function/tool formats.

## 7. Environment Variables

```env
LLM_PROVIDER=mock

GEMINI_API_KEY=
GEMINI_FAST_MODEL=gemini-2.5-flash-lite
GEMINI_DEFAULT_MODEL=gemini-2.5-flash
GEMINI_PRO_MODEL=gemini-2.5-pro

OPENAI_API_KEY=
OPENAI_DEFAULT_MODEL=gpt-4.1-mini
OPENAI_PRO_MODEL=gpt-4.1
```

API keys are backend-only. They must not be exposed to the frontend.

## 8. Adding Gemini Next

Gemini is implemented in `backend/app/ask/llm/gemini_provider.py`.

It supports planning through function calling and synthesis from backend `ToolResult` payloads. The provider does not execute SQL or tools.

## 9. Adding OpenAI Later

To add OpenAI:

1. Create `openai_provider.py`.
2. Convert `LLMToolSchema` into OpenAI-compatible tool schemas.
3. Parse OpenAI tool calls into `LLMToolCall`.
4. Keep database and SQL access outside the provider.
5. Add tests using mocked client responses.

## 10. Security Notes

- Providers must not execute SQL.
- Providers must not access the database.
- Providers must not receive raw API keys in frontend responses.
- Unknown or not-yet-implemented providers raise explicit errors.
- User-facing errors should stay clean; implementation details are for logs.

## Complexity Router

`backend/app/ask/llm/complexity_router.py` classifies questions into provider-agnostic levels:

- `simple`
- `semi_complex`
- `complex`

The router exists to control cost and latency. Most MVP questions are direct rankings, totals or section lookups and should use the cheapest capable model. More involved temporal comparisons and deterministic multi-step analyses use the middle tier. Open-ended strategy, correlation, clustering, prediction and causal interpretation use the highest tier.

The router returns only complexity, score and reasons. It never returns Gemini model names, calls Gemini, executes tools or generates answers.

Provider model mapping happens inside each provider. For Gemini:

| Complexity | Gemini model setting |
|---|---|
| `simple` | `GEMINI_FAST_MODEL` |
| `semi_complex` | `GEMINI_DEFAULT_MODEL` |
| `complex` | `GEMINI_PRO_MODEL` |

Examples:

| Question | Complexity |
|---|---|
| `¿Cuál es la sección con mayor población?` | `simple` |
| `¿Qué sección ha rejuvenecido más desde 2021?` | `semi_complex` |
| `¿Existe relación entre renta y participación electoral?` | `complex` |

To add a rule, update the deterministic patterns in `ComplexityRouter`. Prefer adding a reason string alongside the score change so debug logs explain the decision.
