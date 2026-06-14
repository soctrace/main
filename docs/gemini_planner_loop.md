# Gemini Planner Loop

## Architecture

Fase 4.5 connects Gemini as a planner behind the provider-agnostic Ask SocTrace backend.

```txt
User question
-> Follow-up Resolver
-> Complexity Router
-> GeminiProvider.plan()
-> Tool Layer v2
-> AnswerGuard
-> GeminiProvider.synthesize()
-> AskResponse
-> Conversation Memory
```

Gemini plans and explains. SocTrace calculates.

## Planner Loop

The loop lives in `backend/app/ask/planner_loop.py`.

It is enabled only when:

```env
ASK_USE_LLM_PLANNER=true
LLM_PROVIDER=gemini
```

When disabled, deterministic Semantic Layer v2 and legacy flows continue to run.

## Why Gemini Does Not Access SQL

Gemini receives only:

- the user question
- compact conversation context
- compact semantic context
- provider-agnostic Tool v2 schemas

It does not receive SQL, database credentials, table dumps, `marts.*` view names or raw internal schemas.

## Tool Selection

Gemini selects exactly one Tool v2 through function calling.

The backend validates:

- tool name exists
- arguments match the Pydantic input schema
- tool status is `supported` or `beta`

Invalid tool calls are retried once, then fall back to deterministic paths.

## Tool Execution Layer

Fase 4.6 makes Tool Layer v2 execution explicit:

```py
tool_result = await tool_executor.execute(
    tool_name=plan.tool_call.tool_name,
    arguments=plan.tool_call.arguments,
    context=ToolContext(...),
)
```

The executor validates the registry entry and Pydantic input model, runs the selected backend tool, validates generated SQL through `SqlValidator`, executes it with `QueryExecutor`, and normalizes the output to `ToolResult`.

Planner-loop status handling:

- `ok`: pass through `AnswerGuard`, then Gemini synthesis.
- `empty`: return a clean no-data response without synthesis.
- `unsupported`: return a clean unsupported response when safe.
- `error`: log internally and allow deterministic fallback from the service.

User-facing responses never expose SQL, database errors, Python exceptions or internal schema names.

`ToolResult.metadata` carries municipality, years, metric labels, party/election context and sections so conversation memory can answer follow-ups without asking Gemini to recalculate.

## Fallback Order

The service preserves this order:

1. Follow-up resolver.
2. Gemini planner loop when enabled.
3. Semantic Layer v2 deterministic path.
4. Tool Layer v2 direct execution from semantic interpretation.
5. Legacy Ask handlers.
6. Clean unsupported response.

Gemini free text is never returned for numerical or analytical questions without tool execution.

## Safety Guards

`backend/app/ask/answer_guard.py` validates:

- tool result status
- expected section rows
- year or period context
- party context
- correlation coefficient for correlation questions
- synthesis does not expose SQL or internal table names
- synthesis does not contradict the top row in obvious cases

If synthesis fails, SocTrace uses a deterministic renderer from `ToolResult`.

## Gemini Renderer

Fase 4.7 moves final wording into `backend/app/ask/rendering/`.

Purpose:

- turn a validated `ToolResult` into a natural Spanish answer;
- keep Gemini inside the provider abstraction through `provider.synthesize()`;
- preserve numerical consistency with backend-calculated values;
- preserve `chartSpec`, table rows and entities for the dashboard;
- return suggested follow-ups separately for frontend CTAs.

Renderer flow:

```txt
ToolResult ok
-> compress_tool_result_for_llm()
-> GeminiRenderer provider.synthesize()
-> RenderAnswerGuard
-> AskRenderedAnswer
-> AskResponse
```

If Gemini is unavailable, exposes forbidden content, changes the top section/value/year/party, or omits short entity lists, SocTrace falls back to `DeterministicRenderer`.

### Synthesis Prompt

The renderer prompt tells Gemini:

- use only `ToolResult`;
- do not invent figures, sections, parties or years;
- do not show SQL, internal views, raw JSON or technical errors;
- show concrete sections for lists/rankings;
- explain estimates and caveats in plain Spanish.

Preferred Gemini output is structured JSON:

```json
{
  "answer": "...",
  "methodology": "...",
  "caveats": ["..."],
  "suggested_followups": ["¿...?", "¿...?"],
  "short_caveat": "..."
}
```

Plain text synthesis is also accepted; methodology, caveats and follow-ups then come from `ToolResult`.

### ToolResult Compression

`compress_tool_result_for_llm(tool_result, max_rows=10)` sends only:

- summary;
- first/top rows;
- safe metadata;
- methodology;
- caveats;
- suggested follow-ups;
- chart summary;
- row truncation metadata.

It does not send SQL or raw debug payloads.

### ChartSpec Preservation

Gemini never edits chart configuration. The returned `AskRenderedAnswer.chart_spec` is always the backend-calculated `tool_result.chart_spec`, so the right-side dashboard remains deterministic.

## Conversation Memory

Successful planner answers update:

- last tool
- operation
- metric
- year/start/end year
- party
- rows
- chart spec
- methodology
- provider
- model

This supports follow-ups such as:

- `¿Son datos de 2025?`
- `¿Y en 2023?`
- `¿Cómo lo has calculado?`
- `¿Puedes mostrar la tabla?`

## Persistent Conversation Memory

Fase 4.8 persists conversation context in:

- `core.agent_conversations`
- `core.agent_turns`

Planner-loop memory flow:

```txt
session_id/conversationId
-> get_or_create_conversation()
-> get_context()
-> FollowUpResolver
-> append_user_turn()
-> planner/tool/render
-> append_assistant_turn()
```

The backend maps the frontend localStorage session id to an internal persistent conversation id. Existing `conversationId` payloads remain compatible and are treated as session ids when they are not DB UUIDs.

Stored context includes tool name, operation, metric, year/range, party/election, sections, summary, chart spec, methodology, caveats and suggested follow-ups. Result rows are capped at 50.

The store does not persist API keys, raw Gemini prompts, raw SQL, raw provider responses, stack traces or unbounded tables.

If persistent tables are unavailable, SocTrace rolls back the failed transaction and falls back to in-process memory so the dashboard is not broken before migration deployment.

## Frontend Integration

Fase 4.9 connects the existing Ask SocTrace dashboard panel to the real agent endpoint:

```txt
soctrace-web Ask panel -> POST /api/v1/ask -> Gemini planner/tool/render/memory -> AskResponse
```

The frontend preserves `session_id` in localStorage, stores returned `conversation_id`, sends active dashboard context, renders the LLM answer, shows suggested follow-up CTAs for the latest assistant message and updates the right-side `askChart` panel from backend `chartSpec`.

Debug/provider metadata is hidden in production. The frontend only adapts debug payloads in development when `VITE_ASK_SOCTRACE_DEBUG=true`.

## Testing Strategy

Automated tests mock Gemini responses and do not call the live Gemini API:

```bash
cd backend
python -m unittest tests/ask/test_gemini_planner_loop.py
```

The full backend suite should also pass:

```bash
python -m unittest discover -s tests
```

## Enabling

```env
LLM_PROVIDER=gemini
ASK_USE_LLM_PLANNER=true
GEMINI_API_KEY=...
```

## Disabling

```env
ASK_USE_LLM_PLANNER=false
LLM_PROVIDER=mock
```

This keeps the deterministic Ask SocTrace flow active.
