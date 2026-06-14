# Gemini Provider

## 1. Purpose

`GeminiProvider` implements the SocTrace `LLMProvider` contract for Google's Gemini API. It is the MVP provider for low-cost testing while keeping Ask SocTrace provider-agnostic.

## 2. Architecture Fit

Gemini sits behind:

```txt
LLMProvider
```

It does not replace the Semantic Layer or Universal Tool Layer. Gemini only selects tools and writes final explanations from backend-provided results.

## 3. Required Environment Variables

```env
LLM_PROVIDER=gemini

GEMINI_API_KEY=
GEMINI_FAST_MODEL=gemini-2.5-flash-lite
GEMINI_DEFAULT_MODEL=gemini-2.5-flash
GEMINI_PRO_MODEL=gemini-2.5-pro
GEMINI_TIMEOUT_SECONDS=20
GEMINI_MAX_OUTPUT_TOKENS=1200
GEMINI_TEMPERATURE=0.2
```

`GEMINI_API_KEY` is backend-only and must not be exposed to frontend code.

## 4. Model Routing

| Complexity | Model setting | Default |
|---|---|---|
| `simple` | `GEMINI_FAST_MODEL` | `gemini-2.5-flash-lite` |
| `semi_complex` | `GEMINI_DEFAULT_MODEL` | `gemini-2.5-flash` |
| `complex` | `GEMINI_PRO_MODEL` | `gemini-2.5-pro` |

## 5. Function Calling

SocTrace passes generic `LLMToolSchema` objects into `GeminiProvider.plan()`.

`gemini_schema_adapter.py` converts them into Gemini function declarations. Gemini returns a function call, which SocTrace converts into:

```py
LLMToolCall(tool_name="rank_sections", arguments={...})
```

The backend then executes the selected SocTrace tool.

## 6. No Direct SQL

Gemini never receives database credentials, never accesses SQLAlchemy sessions and never executes SQL.

The backend remains responsible for:

- tool execution
- SQL generation
- validation
- calculations
- data access

## 7. Running Mock Tests

Automated tests do not call Gemini or require network:

```bash
cd backend
python -m unittest tests/ask/test_gemini_provider.py
python -m unittest tests/ask/test_llm_provider.py
```

## 8. Optional Live Test

To test a real Gemini call manually:

```bash
cd backend
export GEMINI_API_KEY=...
python scripts/test_gemini_provider_live.py
```

This script is not part of automated tests.

## 9. Switching Back To Mock

Set:

```env
LLM_PROVIDER=mock
```

The existing Ask SocTrace flow remains unchanged until the explicit integration phase.

## 10. Future OpenAI Migration

OpenAI can be added by implementing another `LLMProvider` adapter that accepts the same `LLMPlanRequest`, `LLMSynthesisRequest` and `LLMToolSchema` contracts.

The Universal Tool Layer and SQL execution should not need provider-specific changes.

## Complexity Router

Gemini does not decide its own model directly from user text. SocTrace first runs the provider-agnostic `ComplexityRouter`, which returns:

```json
{
  "complexity": "semi_complex",
  "score": 4,
  "reasons": ["temporal expression", "growth analysis"]
}
```

Then `GeminiProvider` maps complexity to model settings:

| Complexity | Model setting | Default |
|---|---|---|
| `simple` | `GEMINI_FAST_MODEL` | `gemini-2.5-flash-lite` |
| `semi_complex` | `GEMINI_DEFAULT_MODEL` | `gemini-2.5-flash` |
| `complex` | `GEMINI_PRO_MODEL` | `gemini-2.5-pro` |

This keeps routing portable. A future OpenAI provider can map the same complexity values to OpenAI models without changing the router.

The router is intentionally conservative with cost: direct rankings and lookups are `simple`; temporal comparisons, projections and deterministic multi-step analyses are `semi_complex`; strategy, correlations, clustering, prediction and causal diagnosis are `complex`.

## Exportación de Tools v2 a Gemini Function Declarations

Las herramientas de SocTrace son provider-agnostic. Cada Tool v2 expone primero un `LLMToolSchema` genérico con `name`, `description` y `parameters`.

Después `gemini_schema_adapter.py` convierte ese contrato a Gemini Function Declarations usando `google.genai.types` cuando el SDK está disponible.

```txt
Tool v2 input model
-> LLMToolSchema
-> Gemini FunctionDeclaration
-> Gemini function call
-> LLMToolCall
```

Gemini solo ve nombres, descripciones y argumentos permitidos. No ve SQL, nombres internos de tablas ni credenciales.

Solo se exportan tools con estado `supported` o `beta`. Las tools `pending` quedan fuera salvo que una fase futura añada un modo debug explícito.

La ejecución sigue siendo responsabilidad de SocTrace: Gemini elige la herramienta, SocTrace valida argumentos, ejecuta Tool Layer v2 y sintetiza la respuesta final desde `ToolResult`.

## Planner Loop

Fase 4.5 conecta Gemini al loop de Ask SocTrace solo si `ASK_USE_LLM_PLANNER=true`.

El flujo es:

```txt
ComplexityRouter -> GeminiProvider.plan() -> ToolExecutorV2 -> AnswerGuard -> GeminiProvider.synthesize()
```

Gemini no ejecuta herramientas. La llamada de función se valida y ejecuta dentro del backend.

## Hotfix — Gemini Activation

El agente Gemini requiere el SDK oficial actual:

```txt
google-genai>=1.20.0,<2.0
```

No usar `google-generativeai`, que corresponde al SDK anterior.

Comprobaciones operativas:

```bash
cd backend
python scripts/check_gemini_sdk.py
python scripts/test_gemini_connection.py
```

`check_gemini_sdk.py` valida `from google import genai`. `test_gemini_connection.py` carga la configuración, comprueba que `LLM_PROVIDER=gemini` y que `GEMINI_API_KEY` está cargada, instancia `GeminiProvider` y realiza una generación mínima con el modelo configurado. Nunca imprime la API key.

El backend expone:

```txt
GET /api/v1/ask/llm/health
```

Respuesta saludable esperada:

```json
{
  "provider": "gemini",
  "planner_enabled": true,
  "gemini_sdk": true,
  "api_key_loaded": true,
  "memory_tables": true,
  "tool_layer": true,
  "status": "healthy"
}
```

En arranque se registra un bloque de diagnóstico:

```txt
========================
SOC TRACE AI AGENT
========================

Provider: gemini
Planner: enabled
Gemini SDK: OK
Memory tables: OK
Tool Layer: OK

========================
```

Si falta el SDK, `GeminiProvider` falla con una instrucción explícita:

```txt
Gemini SDK missing.

Run:

pip install google-genai

Then restart backend.
```
