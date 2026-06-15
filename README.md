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

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` to set your provider. Ollama runs locally with no key. Anthropic
and OpenAI require an API key.

```bash
python main.py
```

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
| `src/llm.py` | Provider factory — swap at runtime via env var |
| `main.py` | Three-part workflow: search, human override, book |
