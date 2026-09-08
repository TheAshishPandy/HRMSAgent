# Smart Chat (AI Copilot)

The Smart Chat is a real, end-to-end, authentication-aware, RAG-based, multi-agent assistant. It is not a canned demo: it resolves the caller's identity from the JWT, routes to specialized agents, grounds answers in organization-scoped policy documents and live HR data, and never fabricates values.

## Guarantees

- **Identity from the session, never the message.** The backend resolves identity via `resolve_user_context(db, user)` from the validated JWT. Prompts are pre-filtered: the system never asks "what is your employee/candidate ID?", "what is your name?", "which company?", etc. A user cannot pass another person's ID to read their data — tools only accept the authenticated context.
- **Tenant isolation.** RAG only searches `KnowledgeDocument`s whose `organization_id` matches the caller and whose visibility flag (`employee_visible`/`candidate_visible`) admits the caller's user type.
- **Grounded answers.** Live facts come from SQLAlchemy queries against the caller's own records. When no data exists the assistant says so instead of guessing (e.g. "I could not retrieve your current payroll information").
- **Cross-user denial.** Questions attempting to view another employee's salary are blocked at the classifier (`wants_other_person_data`) and answered with an explicit "I can only share your own records" statement.
- **No chain-of-thought leakage.** The UI shows only high-level activity steps; internal reasoning never reaches the response.

## Request flow

```
POST /api/chat/messages {message, conversation_id?}
   │  JWT → get_current_user
   ▼
context.py  resolve_user_context  ── user_type / employee_id / candidate_id /
   │                                  org, department, designation, manager…
   ▼
classifier.py  classify(message, user_type, history)
   │  → agent list (employee_data, leave, attendance, payroll, rag, hr_policy,
   │                candidate_data, recruitment)
   ▼
supervisor.py  handle_message
   ├─ employee_data/leave/attendance/payroll agents → chat/tools.py
   │     get_employee_profile, get_leave_balances, get_leave_requests,
   │     get_attendance, get_payslips  (all scoped to ctx ids)
   ├─ candidate_data → get_candidate_applications (ctx.candidate_id)
   ├─ rag/hr_policy → rag.search_documents(org, user_type, query)
   ▼
synthesize(ctx, message, facts, sources, agents, denied)
   ├─ deterministic grounded composition (always available)
   └─ optional LLM synthesis when USER_LLM_* configured; validated against
      identity-ask phrases before use
   ▼
persist ChatMessage(user+assistant) → {reply, agents, sources, cards, activity, context}
```

## Components

| File | Responsibility |
| --- | --- |
| `app/modules/chat/context.py` | `resolve_user_context` — builds identity/tenant context from the `User` + linked `Employee`/org. |
| `app/modules/chat/classifier.py` | Keyword router + follow-up detection + cross-user-query detector. |
| `app/modules/chat/rag.py` | Document indexing + hybrid lexical retrieval (BM25-ish + token-overlap + cosine over terms), metadata/visibility filtering, snippet chunks per section. |
| `app/modules/chat/tools.py` | Authorized data tools: leave balances/requests, attendance, payslips, employee profile, candidate applications/interviews. No raw SQL from the LLM path — only these typed accessors. |
| `app/modules/chat/supervisor.py` | Orchestrates agents, calls RAG + tools, synthesizes deterministic answer, optional LLM polish, persists conversation + message metadata. |
| `app/modules/chat/router.py` | HTTP API: context, conversations, messages, knowledge-document management. |

## RAG design (hybrid, no vector DB required)

`KnowledgeDocument`s are chunked on ingestion (`chunk_text`) into section-aware `KnowledgeChunk` rows per org. Retrieval fuses:

- lexical overlap (BM25-flavored scoring),
- term-frequency cosine similarity, and
- keyword hit count,

then reranks and returns the top chunks with `title`, `section`, `category`, `version`, and a relevance `score`. This works fully offline; no embeddings service or vector store is required, matching the repo's "degraded without external services" principle. If `USER_LLM_*` is set, the chosen chunks are also passed to the LLM for answer phrasing, but the deterministic synthesizer already produces a grounded answer.

## Conversation memory

Messages are stored per `ChatConversation`. Follow-ups route with the last ~6 messages as context; e.g. after "What is my leave balance?", "How many are casual?" stays scoped to the caller's own balances.

## Knowledge documents

HR (or super admin) creates policy documents via `POST /api/chat/documents` (title, body, category, version, visibility). Seed data ships six documents: Leave Policy v3.2, Payroll Policy, Attendance Policy, Employee Handbook, Candidate Guidelines, Code of Conduct.

## Cards & activity in the UI

Responses can include structured cards (leave balance, latest payslip, application status) and an activity list ("Identified user as Employee", "Checking live leave balance", …). The floating widget (`frontend/src/components/SmartChat.vue`) renders messages, source chips, cards, and new-conversation affordances.

## Testing

`backend/tests/test_chat.py` covers: auth required; identity-from-JWT for leave balances and department; refusal to ask for identity; payroll isolation (another employee's salary never leaks); RAG grounding with source citations; combined leave-eligibility; candidate application status from JWT; cross-tenant policy isolation; conversation follow-up memory; grounded refusal when no payslip exists; and the `/api/chat/context` endpoint.
