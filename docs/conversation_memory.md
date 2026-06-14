# Persistent Conversation Memory

Fase 4.8 adds durable analytical memory for Ask SocTrace.

## Why It Exists

Ask SocTrace needs to answer follow-ups after page reloads and backend restarts:

- `¿Son datos de 2025?`
- `¿Y en 2023?`
- `¿Y esas secciones?`
- `¿Cómo lo has calculado?`
- `¿Cuántas son?`

The memory stores structured analytical context, not raw Gemini prompts.

## Database Tables

Migration:

```txt
sql/core/030_agent_conversation_memory.sql
```

Tables:

- `core.agent_conversations`
- `core.agent_turns`

`core` is used because the existing project already stores app metadata and audit-adjacent tables there.

## What Is Stored

Conversation:

- session id;
- optional user id;
- municipality;
- status;
- timestamps;
- small metadata JSON.

Turns:

- question and answer;
- operation and tool name;
- provider/model/complexity;
- metric and metric label;
- municipality;
- year/range/election/party;
- sections;
- capped result rows;
- summary;
- chart spec;
- methodology;
- caveats;
- suggested follow-ups;
- tool arguments;
- guard status;
- latency.

`result_rows` is capped at 50 rows. If the source result is larger, `summary.rows_truncated=true` and `summary.rows_total` are stored.

## What Is Not Stored

The persistent store avoids:

- API keys;
- raw Gemini prompts;
- raw provider responses;
- raw SQL unless a future explicit debug path stores it;
- stack traces;
- large unbounded result tables;
- sensitive user data.

## Store API

Backend implementation:

```txt
backend/app/ask/conversation/persistent_store.py
backend/app/ask/conversation/schemas.py
```

Main methods:

- `get_or_create_conversation()`
- `append_user_turn()`
- `append_assistant_turn()`
- `get_context()`
- `clear_conversation()`
- `delete_inactive(days=30)`

If the migration is not present, the service rolls back the failed transaction and falls back to the existing in-process memory.

## Follow-Up Resolver

At request start, the service hydrates `ConversationState` from `ConversationMemoryContext` when persistent memory exists. The existing `FollowUpResolver` then resolves follow-ups from the same state shape.

Supported memory-backed follow-ups include:

- year confirmation from `last_year`;
- methodology from `last_methodology_plain`;
- counts from saved sections/rows;
- section references from `last_sections`;
- year changes by rerunning the previous question with the requested year.

## Frontend Session Behavior

The frontend keeps a stable id in localStorage:

```txt
soctrace.ask.session_id
```

It sends both:

- `conversationId`
- `session_id`

The backend treats frontend session ids as the stable lookup key. The frontend also stores returned internal `conversation_id` values and sends both IDs on later turns, while preserving `session_id` as the durable browser-session key.

Suggested CTA clicks reuse the same hook and therefore the same session id.

## Privacy

Current isolation uses `session_id`. If authenticated users are added, `user_id` is stored and conversation lookup can be restricted to that user.

Different session ids produce different conversations. Session A is not loaded by Session B.

## Cleanup

`PersistentConversationStore.delete_inactive(days=30)` deletes inactive conversations older than the requested TTL. It is not run automatically; schedule it explicitly when operational policy is ready.

## Debug

Optional endpoint:

```txt
GET /api/ask/conversations/{conversation_id}/debug
```

It returns recent turns and context only when:

```txt
APP_ENV=development
ASK_DEBUG_ENABLED=true
```

It is disabled by default in production.

## Hotfix — Gemini Activation

La memoria persistente debe existir físicamente en PostgreSQL antes de activar el planner LLM en producción. El error operativo que delata una migración pendiente es:

```txt
relation "core.agent_conversations" does not exist
```

Scripts añadidos:

```bash
cd backend
python scripts/check_agent_memory.py
python scripts/apply_agent_memory_migration.py
python scripts/test_persistent_memory.py
```

`check_agent_memory.py` imprime el estado de cada tabla:

```txt
core.agent_conversations OK
core.agent_turns OK
```

`apply_agent_memory_migration.py` localiza `sql/core/030_agent_conversation_memory.sql`, lo ejecuta de forma idempotente y responde `migration applied` o `already exists`. Si el fichero no existiera, el script genera la migración con el contrato de Fase 4.8.

`test_persistent_memory.py` ejecuta dos turnos reales:

```txt
¿Cuál es la sección con mayor población?
¿Son datos de 2025?
```

Comprueba que se crea conversación, se almacenan turnos y que el follow-up usa memoria persistida.

El store usa adaptadores JSONB para PostgreSQL (`psycopg.types.json.Jsonb`) y mantiene serialización JSON de texto para SQLite en tests. Los errores por tablas inexistentes se convierten en un mensaje operativo claro:

```txt
Persistent memory tables missing.

Run memory migration before enabling ASK_USE_LLM_PLANNER:

python scripts/apply_agent_memory_migration.py
```

Otros errores SQL de memoria se informan como fallo de esquema/conexión sin exponer stack traces al usuario final.
