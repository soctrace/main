# Frontend Ask SocTrace Agent Integration

Fase 4.9 connects the dashboard Ask SocTrace panel to the real backend agent flow without redesigning the dashboard.

## Endpoint

The frontend uses the versioned backend endpoint:

```txt
POST /api/v1/ask
```

Implementation:

```txt
soctrace-web/src/lib/api.ts
soctrace-web/src/features/ask-soctrace/services/askSocTraceService.ts
```

Requests include JSON headers and credentials.

## Request Contract

The service sends:

```ts
{
  question: string;
  sessionId?: string;
  session_id?: string;
  conversationId?: string;
  conversation_id?: string;
  municipioId?: string;
  activeMunicipality?: string;
  activeYear?: number | null;
  activeLayer?: string | null;
  selectedSectionId?: string | null;
  locale: "es-ES";
}
```

`municipioId` and `activeMunicipality` are both sent for compatibility. Mijas (`29070`) remains the MVP fallback.

## Response Normalization

The frontend accepts camelCase and snake_case aliases:

- `conversationId` / `conversation_id`
- `sessionId` / `session_id`
- `shortCaveat` / `short_caveat`
- `suggestedFollowUps` / `suggested_followups`
- `chartSpec` / `chart_spec`

The adapter maps backend responses into the existing dashboard `AskSocTraceResponse` shape so the panel and right sidebar keep their current UX.

## Session Handling

The hook stores:

```txt
soctrace.ask.session_id
soctrace.ask.conversation_id
```

Rules:

- `session_id` is stable across reloads.
- returned `conversation_id` is stored and reused.
- suggested CTA clicks use the same hook and therefore the same session/conversation.
- predefined test prompts use the same chat flow through `queuedAskPrompt`.

## Suggested Follow-Ups

Suggested follow-ups render as buttons in the latest assistant message only. Clicking a CTA:

1. adds the prompt as a user message;
2. sends it to `/api/v1/ask`;
3. preserves session/conversation ids;
4. renders the response;
5. updates the right chart panel when `chartSpec` is available.

Questions are normalized with Spanish opening/closing question marks.

## Test Library

The existing “Lista de tests” panel is preserved.

- Visible statuses are product-facing only: `Disponible` and `Próximamente`.
- `Disponible` tests are clickable and queue the prompt into the Ask panel using the same persistent chat session.
- `Próximamente` tests are disabled and show a short tooltip: `Esta consulta estará disponible en futuras versiones del agente SocTrace.`
- Internal Tool Layer states such as `supported`, `beta` and `pending` are not rendered in the UI.

The MVP catalog is audited in:

```txt
docs/test_catalog_audit.md
docs/test_catalog_available.md
```

The smoke validation script for available Tool Layer recipes is:

```bash
cd backend
python scripts/validate_mvp_test_catalog.py
```

## ChartSpec Handling

When `chartSpec.type !== "none"`, the right sidebar switches to `askChart`.

Supported render modes:

- `metric`: compact metric card;
- `bar`: compact horizontal bars;
- `line`: lightweight SVG line chart;
- `scatter`: lightweight SVG scatter plot;
- `table`: compact table/list fallback;
- `map`: table/list fallback until map highlight wiring exists.

If a chart cannot render, the panel shows:

```txt
No visualización disponible todavía para esta consulta.
```

The textual answer is still preserved in chat.

## Loading And Errors

While a request is running, Ask SocTrace adds an assistant placeholder:

```txt
SocTrace está analizando los datos...
```

The send button is disabled during the request.

User-facing errors are clean Spanish:

```txt
No he podido completar la consulta en este momento. Inténtalo de nuevo.
```

Raw stack traces, SQLAlchemy errors, psycopg errors and provider internals are not shown.

## Debug Behavior

Production hides:

- provider;
- model;
- tool name;
- latency;
- raw metadata;
- SQL/debug payloads.

Debug payloads are only adapted when:

```txt
import.meta.env.DEV
VITE_ASK_SOCTRACE_DEBUG=true
```

The current UI only shows debug blocks for `mode === "debug"`.

## Limitations

- Frontend unit test framework is not configured; validation is currently via TypeScript production build.
- `map` chart specs fall back to a compact list until section highlight wiring is added.
- The right sidebar charts are lightweight renderers, not a full charting library.
