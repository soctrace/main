# Tool Layer v2

## Purpose

Tool Layer v2 is the controlled analytical API between Semantic Layer v2 and the SQL/data layer. It gives the future OpenAI planner a small set of reusable tools instead of raw SQL access or one-off handlers.

Flow:

```txt
question -> Semantic Layer v2 -> AnalyticalOperation -> Tool Layer v2 -> ToolResult -> renderer
```

## Tool List

- `rank_sections`
- `aggregate_municipality`
- `compare_years`
- `population_growth`
- `filter_sections`
- `section_profile`
- `party_strength`
- `persistent_winner`
- `historical_party_average`
- `age_cohort_projection`
- `cross_metric_ranking`
- `correlation_analysis` beta

## Schemas

Schemas live in `backend/app/ask/tools_v2/schemas.py`.

Base context:

```py
ToolContext(municipio_id="29070", municipio_nombre="Mijas", locale="es-ES")
```

Standard result:

```py
ToolResult(
    tool_name="rank_sections",
    operation="rank_sections",
    status="ok",
    rows=[...],
    summary={...},
    metadata={...},
    chart_spec={...},
    methodology_plain="...",
    caveats=[...],
    suggested_followups=[...],
    sources=["marts.agent_section_profile"],
    error_code=None,
    error_message=None,
)
```

## Tool Execution Layer

Fase 4.6 adds `ToolExecutorV2` in `backend/app/ask/tools_v2/executor.py`.

Execution contract:

```txt
validated Gemini tool call
-> registry lookup
-> Pydantic input validation
-> tool handler
-> SQL validation
-> QueryExecutor execution
-> result normalization
-> ToolResult
```

Gemini can choose a tool and propose JSON arguments, but it never receives SQL and never calculates final values. SocTrace owns validation, SQL execution and result normalization.

### Registry

`ToolRegistryV2` supports:

- `get_tool(tool_name)`
- `list_tools(status=None)`
- `get_llm_tool_schemas(include_beta=True)`

Executable tools have `status="supported"` or `status="beta"`. Pending tools are rejected by the executor, and hidden tools are unavailable unless the registry is created with debug mode.

### Input Validation

Before execution, the executor runs:

```py
tool.input_schema.model_validate(arguments)
```

Invalid arguments return:

```py
ToolResult(status="unsupported", error_code="invalid_tool_arguments")
```

The user-facing message is safe and does not include Pydantic traces.

### SQL Safety

All SQL tools build SQL from approved Tool v2 builders and validate it through `SqlValidator` before execution with `QueryExecutor`.

Rules:

- Tool SQL may use only `marts.agent_*` relations approved by the Semantic Catalog.
- Tool SQL must not use `marts.ask_*`, `core.*`, `raw.*` or `staging.*`.
- Only `SELECT`/`WITH` statements are allowed.
- Multiple statements, comments and write operations are rejected.
- `QueryExecutor` applies statement timeout and row limits.

SQL validation failure returns:

```py
ToolResult(status="error", error_code="sql_validation_failed")
```

Raw SQL, database exceptions and stack traces are logged internally only.

### Statuses

- `ok`: executable request with usable rows.
- `empty`: valid request, but no rows matched.
- `unsupported`: unknown, pending or invalid tool call, or unsupported arguments.
- `error`: controlled internal execution failure.

### Result Normalization

`ResultNormalizer` converts DB rows to dictionaries, adds `value_label`, fills `value` for ranking/change outputs where needed, preserves memory metadata, and creates default chart specs.

Default charts:

- Ranking: bar chart with `x="section_name"` and `y="value"`.
- Trend: line chart with `x="year"` and `y="value"`.
- Correlation: scatter chart with `x_value/y_value` when available.
- Single value: metric chart.

Metadata includes municipality, year/start/end year, metric, metric label, party, election context and section references for conversation memory.

## Rendering Support

Fase 4.7 consumes `ToolResult` through the Ask rendering layer:

```txt
ToolResult -> compress_tool_result_for_llm -> GeminiRenderer -> AskRenderedAnswer -> AskResponse
```

To support safe rendering, every Tool v2 result should provide:

- stable `rows` with concrete section names and values;
- `summary.value_label`;
- `metadata` with municipality, year/range, metric, party and sections where relevant;
- `methodology_plain`;
- `caveats`;
- `suggested_followups`;
- backend-owned `chart_spec`.

Gemini receives a compressed ToolResult and may only explain it. It does not receive full chart rows beyond the top sample, SQL, debug payloads or database internals. `chart_spec` is preserved from the backend result and is not modified by Gemini.

Renderer guard checks reject answers that expose SQL/internal names or contradict top section, value, year or party. When that happens, `DeterministicRenderer` renders the same `ToolResult` without an LLM.

## Data Sources

SQL builders use only approved canonical views:

- `marts.agent_section_profile`
- `marts.agent_population_age`
- `marts.agent_electoral_results`
- `marts.agent_electoral_summary`
- `marts.agent_income_sources`
- `marts.agent_housing_profile`
- `marts.agent_section_lookup`

No v2 tool should reference `marts.ask_*`.

## Example Calls

Rank sections:

```json
{
  "metric": "population_total",
  "order": "desc",
  "limit": 5,
  "municipio_id": "29070"
}
```

Persistent winner:

```json
{
  "party": "PP",
  "election_type": "MUNICIPALES",
  "limit": 20,
  "municipio_id": "29070"
}
```

Cross-metric ranking:

```json
{
  "metrics": [
    {"metric": "income_individual", "direction": "low", "weight": 0.5},
    {"metric": "abstention_pct", "direction": "high", "weight": 0.5}
  ],
  "limit": 5,
  "municipio_id": "29070"
}
```

## Example ToolResult

```json
{
  "tool_name": "rank_sections",
  "operation": "rank_sections",
  "status": "ok",
  "rows": [
    {
      "section_id": "2907001023",
      "section_name": "Sección 23 · Riviera Sur",
      "value": 5351,
      "value_label": "Poblacion total",
      "year": 2025
    }
  ],
  "summary": {
    "row_count": 1,
    "top_section": "Sección 23 · Riviera Sur",
    "top_value": 5351
  },
  "sources": ["marts.agent_section_profile"]
}
```

## OpenAI Readiness

Every tool exposes `openai_schema()` with:

- `name`
- `description`
- `parameters`

This is enough for a future planner to export the registry as function/tool definitions without granting raw SQL access.

## Adding A Metric

Add the metric to Semantic Layer v2. If it points to an approved `agent_*` view and has a field, most tools can use it automatically. Do not add a new tool for each question.

## Adding A Tool

Add a tool only when the operation shape is genuinely new and cannot be expressed as metric + filter + aggregation + ordering. Add:

1. Input schema.
2. SQL builder.
3. Tool class and registry entry.
4. Normalization rules if needed.
5. Direct tests and semantic-to-tool tests.

## Current Limitations

- `cross_metric_ranking` is a beta percentile index, not a causal model.
- `correlation_analysis` is beta and currently oriented to section-level Pearson analysis.
- Section profile resolution is deterministic text matching, not an LLM resolver.
- The OpenAI planner is intentionally not implemented in this phase.

## LLM Schema Export

Tool Layer v2 exports provider-agnostic schemas for LLM tool/function calling.

Each executable tool class defines:

- `name`
- `description`
- `input_schema`
- `status`
- `examples`

The class method `llm_schema()` returns:

```py
LLMToolSchema(
    name=...,
    description=...,
    parameters=input_schema.model_json_schema(),
)
```

The registry function `get_llm_tool_schemas(include_beta=True)` returns deterministic, sorted schemas for tools with status `supported` or `beta`. Pending tools are not exported to Gemini.

To add a new tool and make it visible to Gemini:

1. Create a strict Pydantic input model with clear `Field(description=...)` metadata.
2. Create a Tool v2 class with a concise description.
3. Set `status = "supported"` or `status = "beta"`.
4. Add the class to `TOOL_CLASSES`.
5. Add tests for direct execution and schema export.

Do not build Gemini-specific schemas inside tools. Tools export `LLMToolSchema`; provider adapters convert that generic schema to Gemini, OpenAI or another provider later.

Gemini function declarations are generated in `backend/app/ask/llm/gemini_schema_adapter.py`. The adapter normalizes Pydantic JSON Schema, removes unsupported constructs such as `$defs`, `$ref`, `anyOf`, titles and examples, validates tool names and required fields, and parses Gemini function calls back into `LLMToolCall`.

In the Gemini planner loop, Tool Layer v2 remains the only execution boundary. Gemini can select a tool and propose arguments, but `ToolExecutorV2` validates and executes the tool inside SocTrace.
