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
- JSON structured logging (`python-json-logger`) parseable by Datadog, CloudWatch, Loki
- LangSmith tracing for full node-by-node visibility into every agent run

## Project structure

```
flight_search_agent/
├── .github/
│   └── workflows/
│       └── ci.yml          #runs pytest on push and PR
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
├── Dockerfile
├── compose.yml
├── .dockerignore
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
4. **Deployment**: Dockerfile, docker-compose with Ollama, GitHub Actions CI -> [feat/deployment](https://github.com/jaygaha/langgraph-flight-agent/tree/feat/deployment)
5. **Observability**: JSON structured logging, LangSmith tracing -> [feat/observability](https://github.com/jaygaha/langgraph-flight-agent/tree/feat/observability)

---

**Phase 1: Basic implementation**

`AgentState` is a TypedDict that moves between nodes as shared memory. Each node reads from it and returns a dict of updates. `should_continue` is a plain function that routes after each search: replan, proceed, or hit the turn limit. `interrupt_before` pauses the graph before booking so a human can review the results. `app.stream(None)` resumes it.

**Phase 2: Hardening**

`Settings` (Pydantic Settings) loads all env vars at import time. If something is missing, it raises a clear error before any node runs. The LLM call in `gather_constraints_node` retries up to 3 times with exponential backoff, so a single timeout doesn't crash the graph. Four unit tests cover the core logic in `search_flights_node` and `trigger_booking_node`.

**Phase 3: Persistence & API**

`MemorySaver` swapped for `SqliteSaver`. Checkpoints write to a `.db` file now, so a server restart doesn't wipe every session mid-booking. The FastAPI layer adds three endpoints: `POST /flights/search` starts a session, `POST /flights/approve/{id}` takes optional constraint overrides and executes the booking, `GET /flights/session/{id}` returns the current state. Pydantic schemas handle request validation and generate the `/docs` page automatically.

**Phase 4: Deployment**

`python:3.12-slim` image keeps the build small and avoids musl libc issues that alpine causes with some Python C extensions. The compose file points the agent at host Ollama via `host.docker.internal:11434` — no second Ollama container needed if you already have models installed. The named volume mounts to a directory (`/app/data`), not a file, because Docker creates directories for volume mount points and SQLite needs a file path inside one. GitHub Actions CI runs `pytest tests/ -v` with `LLM_PROVIDER=ollama` set — the unit tests never call the LLM, so no model or key is needed in the runner.

> **Note (dockerized Ollama):** The default `compose.yml` uses your host Ollama via `host.docker.internal`. To run Ollama inside Docker instead, uncomment the `ollama` service in `compose.yml`, remove the `OLLAMA_HOST` line from the `agent` environment block, then pull your model after first startup: `docker compose exec ollama ollama pull llama3.1`

**Phase 5: Observability**

`basicConfig` is replaced with a `JsonFormatter` handler from `python-json-logger`. Every log line is now a JSON object with `asctime`, `levelname`, `name`, and `message` fields that any log aggregator (Datadog, Loki, CloudWatch) can parse directly. LangSmith tracing needs no code changes: set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in `.env` and every `app.stream()` call sends a trace automatically. One catch for local runs: `load_dotenv()` at the top of `main.py` is needed to push `.env` vars into `os.environ` before LangSmith reads them. In Docker, compose handles this via `env_file`.

> **What LangSmith does?**
> 
> It's a tracing tool for LLM applications. Every time your agent runs, LangSmith records the full execution: which nodes fired, what the LLM received as input, what it returned, how many tokens it used, and how long each step took.
>  
> Why it matters for this project
>
> Without it, when something goes wrong you only have log lines like: `{"message": "Constraints extracted | origin=KTM destination=NRT"}`
>
> With LangSmith you get a visual trace showing:
>  - The exact system prompt and user message sent to the LLM
>  - The raw LLM response before your code parsed it
>  - Which node was slow (was it the LLM call or the flight search?)
>  - Token counts per run — useful for cost estimation with paid providers
>
> Concrete example: An agent occasionally returns None for origin. With logs alone you'd grep through output trying to reconstruct what happened. With LangSmith you open the trace, click gather_constraints_node, and see the exact prompt the LLM received and the exact JSON it returned - you know immediately whether it's a prompt problem or a parsing problem.
>
> For this learning project specifically — it's the fastest way to understand what LangGraph is actually doing inside each node without adding print statements everywhere.
> 

## Where to take this next

**Replace the mock flight API**

The mock data in `fetch_live_flights` is the most obvious gap. [Amadeus](https://developers.amadeus.com) and [Duffel](https://duffel.com/docs) both have free sandbox tiers. Swapping in a real API is where things get interesting: rate limits, pagination, inconsistent response shapes — none of that is in the mock.
  
**Frontend**

The `/search`, `/approve`, and `/session` endpoints are already there. A React or Next.js UI fits the flow: call `/search`, show results, wait for user input, call `/approve`. The interrupt-and-resume pattern you built was designed for this kind of two-step interaction.

**PostgreSQL**

SQLite works for a single server. For concurrent writes or horizontal scaling, swap `SqliteSaver` for
  `langgraph-checkpoint-postgres`. The graph code doesn't change, just the checkpointer initialization.

**Streaming**

The agent already streams internally through `app.stream()`, but the HTTP endpoints wait for the full run before responding. Expose it via FastAPI's `StreamingResponse` with SSE and the UI can update node by node instead of all at once.

**Auth**

Session IDs are anonymous UUIDs right now. Add JWT or OAuth, tie them to user accounts, and booking history carries across sessions and devices.

**More nodes**

The graph has three nodes. Natural extensions: a price-alert node that re-triggers search when fares drop, a multi-city planner that chains flights, or parallel nodes that search multiple providers and compare results.

happy coding 🚀
