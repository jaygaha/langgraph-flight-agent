# Flight search agent (LangGraph)

A LangGraph agent built as a learning reference; not a product. It takes a
plain-text flight request, extracts constraints with an LLM, searches for
matching flights, and pauses for human approval before booking.

## What this covers

- `AgentState` with a custom replace reducer (vs the `operator.add` accumulation trap)
- Conditional routing with a turn-limit guard
- Human-in-the-loop: `interrupt_before` + `update_state` + three-stream resumption
- Multi-provider LLM factory (Ollama, Anthropic, OpenAI) swapped via env vars
- Structured logging across all nodes and the router
- SqliteSaver for state that survives restarts
- FastAPI endpoints for search, approval, and session inspection
- Pydantic schemas for request/response validation and auto-generated API docs

## Project structure

```
flight_search_agent/
├── api/
│   ├── __init__.py
│   ├── app.py              #FastAPI entry point
│   ├── schemas.py          #request/response models
│   └── routes/
│       ├── __init__.py
│       └── flights.py      #/search, /approve, /session
├── src/
│   ├── config.py           #Pydantic Settings, logging setup
│   ├── state.py            #AgentState definition
│   ├── nodes.py            #node functions and mock flight search
│   ├── graph.py            #graph wiring, router, checkpointer
│   └── llm.py              #provider factory
├── tests/
│   └── test_nodes.py
├── main.py                 #CLI demo
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` to pick your provider. Ollama needs no key. Anthropic and OpenAI do.

CLI:
```bash
python main.py
```

API server:
```bash
uvicorn api.app:app --reload
```

API docs at `http://localhost:8000/docs` once running.

## Providers

| Provider | `LLM_PROVIDER` | `LLM_MODEL` | Key needed |
|---|---|---|---|
| Ollama (default) | `ollama` | `llama3.1` | No |
| Anthropic | `anthropic` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `gpt-4o` | `OPENAI_API_KEY` |

## Files

| File | What it does |
|---|---|
| `src/state.py` | `AgentState` with custom replace reducer |
| `src/graph.py` | Graph wiring, router, checkpointer, interrupt config |
| `src/nodes.py` | Three node functions and mock flight search |
| `src/llm.py` | Provider factory, swap at runtime via env var |
| `src/config.py` | Pydantic Settings, loads and validates env vars at startup |
| `api/app.py` | FastAPI instance and health check |
| `api/schemas.py` | Request and response models |
| `api/routes/flights.py` | `/search`, `/approve`, `/session` endpoints |
| `main.py` | CLI workflow: search, human override, book |

## Learning path

Each phase is a separate branch. Check them out to follow the build step by step.

1. **Basic implementation**: state, nodes, graph, human-in-the-loop, LLM factory
   → [feat/basic](https://github.com/jaygaha/langgraph-flight-agent/tree/feat/basic)
2. **Hardening**: config validation at startup, LLM retry with backoff, unit tests
   → [feat/hardening](https://github.com/jaygaha/langgraph-flight-agent/tree/feat/hardening)
3. **Persistence & API**: SqliteSaver persistence, FastAPI HTTP interface
   → [feat/api](https://github.com/jaygaha/langgraph-flight-agent/tree/feat/api)
4. **Deployment**: Dockerfile, docker-compose with Ollama, GitHub Actions CI *(todo)*
5. **Observability**: JSON structured logging, LangSmith tracing *(todo)*

---

**Phase 1: Basic implementation**
`AgentState` is a TypedDict that moves between nodes as shared memory. Each node reads from it and returns a dict of updates. `should_continue` is a plain function that routes after each search: replan, proceed, or hit the turn limit. `interrupt_before` pauses the graph before booking so a human can review the results. `app.stream(None)` resumes it.

**Phase 2: Hardening**
`Settings` (Pydantic Settings) loads all env vars at import time. If something is missing, it raises a clear error before any node runs. The LLM call in `gather_constraints_node` retries up to 3 times with exponential backoff, so a single timeout doesn't crash the graph. Four unit tests cover the core logic in `search_flights_node` and `trigger_booking_node`.

**Phase 3: Persistence & API**
`MemorySaver` swapped for `SqliteSaver`. Checkpoints write to a `.db` file now, so a server restart doesn't wipe every session mid-booking. The FastAPI layer adds three endpoints: `POST /flights/search` starts a session, `POST /flights/approve/{id}` takes optional constraint overrides and executes the booking, `GET /flights/session/{id}` returns the current state. Pydantic schemas handle request validation and generate the `/docs` page automatically.

**Phase 4: Deployment** *(todo)*

**Phase 5: Observability** *(todo)*
